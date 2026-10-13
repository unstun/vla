#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v172/install/setup.bash
cd /task/recovery_v174
python3 - <<'VERIFY'
from pathlib import Path
import json,hashlib
r=json.loads(Path('source_identity.json').read_text());assert r['version']=='v174'
for n,h in r['files'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
VERIFY
export CMAKE_PREFIX_PATH="/task/recovery_v167/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}"
export MAKEFLAGS=-j2
colcon build --base-paths src --packages-select pct_planner --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v174/test_pct_degenerate.py
