#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v159/install/setup.bash
cd /task/recovery_v160
python3 - <<'VERIFY'
from pathlib import Path
import json,hashlib
r=json.loads(Path('source_identity.json').read_text());assert r['version']=='v160'
for n,h in r['files'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
print('V160_SOURCE_IDENTITY_PASS')
VERIFY
export CMAKE_PREFIX_PATH="/task/recovery_v158/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}"
export MAKEFLAGS=-j2
colcon build --base-paths src --packages-select scan_nav2_controller --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
colcon test --base-paths src --packages-select scan_nav2_controller --executor sequential --return-code-on-test-failure
colcon test-result --verbose
