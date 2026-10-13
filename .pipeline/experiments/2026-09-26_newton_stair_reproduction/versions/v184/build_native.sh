#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v176/install/setup.bash
cd /task/recovery_v184
python3 - <<'VERIFY'
from pathlib import Path
import json,hashlib
r=json.loads(Path('source_identity.json').read_text());assert r['version']=='v184'
for n,h in r['files'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
VERIFY
export MAKEFLAGS=-j2
colcon build --base-paths src --packages-select scan_nav2_controller lite3_nav2_bridge --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
colcon test --packages-select scan_nav2_controller --executor sequential --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v184/test_profile_frames.py
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v184 -B /task/recovery_v184/terminal_build
cmake --build /task/recovery_v184/terminal_build -j2
/task/recovery_v184/terminal_build/terminal_capture_probe /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v184/terminal_fixture.txt
