#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v167/install/setup.bash
cd /task/recovery_v170
python3 - <<'VERIFY'
from pathlib import Path
import json,hashlib
r=json.loads(Path('source_identity.json').read_text());assert r['version']=='v170'
for n,h in r['files'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
print('V170_SOURCE_IDENTITY_PASS')
VERIFY
export CMAKE_PREFIX_PATH="/task/recovery_v167/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}"
export MAKEFLAGS=-j2
colcon build --base-paths src --packages-select lite3_nav2_plugins lite3_nav2_bridge --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
colcon test --base-paths src --packages-select lite3_nav2_plugins --executor sequential --return-code-on-test-failure
colcon test-result --verbose
source install/setup.bash
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v170/test_reference_reuse.py
