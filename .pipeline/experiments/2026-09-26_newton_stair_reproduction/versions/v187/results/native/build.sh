set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v186/install/setup.bash
export MAKEFLAGS=-j2
cd /task/recovery_v187
colcon build --base-paths src --packages-select scan_nav2_controller lite3_nav2_bridge --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
colcon test --packages-select scan_nav2_controller --executor sequential --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
python3 /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v187/test_profile_frames.py
cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v187 -B terminal_build
cmake --build terminal_build -j2
terminal_build/terminal_capture_probe /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v187/terminal_fixture.txt
python3 - <<'VERIFY'
from ament_index_python.packages import get_package_prefix
assert get_package_prefix('lite3_nav2_bridge')=='/task/recovery_v187/install/lite3_nav2_bridge'
assert get_package_prefix('scan_nav2_controller')=='/task/recovery_v187/install/scan_nav2_controller'
for package in ['scan_planner','pct_planner','lite3_nav2_plugins']:
 assert get_package_prefix(package)=='/task/recovery_v175/install/'+package
print('V187_UNDERLAY_IDENTITY_PASS')
VERIFY
