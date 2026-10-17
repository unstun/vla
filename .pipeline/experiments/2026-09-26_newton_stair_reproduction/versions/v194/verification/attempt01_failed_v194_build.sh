set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v176/install/setup.bash
python3 - <<'VERIFY_PARENT'
from pathlib import Path
import hashlib,json
r=json.loads(Path('/task/evidence/v176_native_receipt.json').read_text())
assert r['passed'] and r['native_version']=='v176' and r['platform']=='linux/arm64'
for name,digest in r['files'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('V176_MAC_UNDERLAY_IDENTITY_PASS')
VERIFY_PARENT
export MAKEFLAGS=-j2
cd /task/recovery_v194
colcon build --base-paths src --packages-select lite3_nav2_interfaces scan_planner_msgs lite3_nav2_plugins plan_env bspline_opt path_searching traj_utils scan_planner scan_nav2_controller lite3_nav2_bridge scan_reactive_tracker --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
source install/setup.bash
colcon test --packages-select scan_nav2_controller lite3_nav2_plugins lite3_nav2_bridge --executor sequential --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v194/test_profile_frames.py
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v194 -B terminal_qualification_build
cmake --build terminal_qualification_build -j2
terminal_qualification_build/terminal_capture_probe /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v194/terminal_fixture.txt
