#!/bin/bash
# P3 on gpu5070ti: versions/v33/ros_smoke.py (trial variant), byte-identical, in the pinned image through the docker
# shim, with run_ros_smoke.sh's container command; only the root path and the writable output directory differ.
set -euo pipefail
export PATH=$HOME/vla_exec/bin:$PATH
P=$HOME/vla_exec/vla
E="${P}/.pipeline/experiments/2026-09-26_newton_stair_reproduction"
V="${E}/hosts/2026-09-29_gpu5070ti"
mkdir -p "${V}"
cp -p "${E}/versions/v33/ros_smoke.py" "${V}/ros_smoke.py"
cmp "${E}/versions/v33/ros_smoke.py" "${V}/ros_smoke.py"
LOG="${V}/ros_smoke_trial_attempt01_stdout.log"
test ! -e "${LOG}"
set +e
docker run --rm --pull=never --platform=linux/amd64 -e ROS_DOMAIN_ID=219 -e ROS_LOCALHOST_ONLY=1 \
  -e PYTHONDONTWRITEBYTECODE=1 -v "${P}:${P}:ro" -v "${V}:${V}:rw" \
  -v "${E}/runtime/scan64_input_refresh_v31:/workspace:ro" --entrypoint /bin/bash \
  sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb -c "
set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export PYTHONPATH=${E}/runtime/foreground_py310:${E}/runtime_sources/backend_adapter:${E}/runtime_sources/backend_ros:${E}/runtime_sources/bridge:${E}/runtime_sources/pct_runtime/python:\${PYTHONPATH:-}
export LD_LIBRARY_PATH=${E}/runtime_sources/pct_runtime/lib:\${LD_LIBRARY_PATH:-}
python3 ${V}/ros_smoke.py trial 1" 2>&1 | tee "${LOG}"
STATUS=${PIPESTATUS[0]}
set -e
cmp "${E}/versions/v33/ros_smoke.py" "${V}/ros_smoke.py"
exit "${STATUS}"
