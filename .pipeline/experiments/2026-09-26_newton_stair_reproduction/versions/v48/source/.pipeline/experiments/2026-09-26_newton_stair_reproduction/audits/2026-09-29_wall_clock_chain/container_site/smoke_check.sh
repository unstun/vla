#!/bin/bash
# Smoke check of sitecustomize.py in the pinned planner image (observation only; writes to a temporary dir).
# Usage: bash smoke_check.sh <output dir outside the repository>
set -euo pipefail
P=/Users/sun/tongbu/study/phdproject/vla
E="${P}/.pipeline/experiments/2026-09-26_newton_stair_reproduction"
OUT="$1"
mkdir -p "${OUT}"
docker run --rm --pull=never --platform=linux/amd64 -v "${P}:${P}:ro" -v "${OUT}:/out:rw" \
  -e "PYTHONPATH=${E}/runtime_sources/bridge:${E}/audits/2026-09-29_wall_clock_chain/container_site" \
  -e DIAG_CONTAINER_OUT=/out --entrypoint /bin/bash \
  sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb -c '
source /opt/ros/humble/setup.bash
python3 --version
python3 -c "
import sitecustomize, gc, time
print(\"sitecustomize:\", sitecustomize.__file__)
x = [[i] for i in range(100000)]
gc.collect()
from lite3_sim_bridge.state_stream import CompleteStateStream
from lite3_sim_bridge.foxy_bridge_node import FoxyBridgeNode
print(\"patched:\", CompleteStateStream.offer.__name__, CompleteStateStream.take.__name__, FoxyBridgeNode._publish_latest.__name__)
time.sleep(1.2)
"'
python3 - "${OUT}" <<'PY'
import array, glob, sys
for path in sorted(glob.glob(sys.argv[1] + "/*_gc.i64")):
    data = array.array("q"); data.frombytes(open(path, "rb").read())
    print(path.split("/")[-1], len(data) % 5 == 0 and "complete rows" or "PARTIAL ROW", len(data) // 5, "collections")
PY
