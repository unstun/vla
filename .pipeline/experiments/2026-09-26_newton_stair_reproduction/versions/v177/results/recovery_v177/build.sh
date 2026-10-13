set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v175/install/setup.bash
cd /task/recovery_v177
colcon build --base-paths src --packages-select lite3_nav2_bridge --executor sequential
source install/setup.bash
python3 /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v177/test_profile_frames.py
cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v177 -B terminal_build
cmake --build terminal_build -j2
terminal_build/terminal_capture_probe /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v177/terminal_fixture.txt
python3 - <<'VERIFY'
from ament_index_python.packages import get_package_prefix
assert get_package_prefix('lite3_nav2_bridge')=='/task/recovery_v177/install/lite3_nav2_bridge'
for package in ['scan_nav2_controller','scan_planner','pct_planner','lite3_nav2_plugins']:
 assert get_package_prefix(package)=='/task/recovery_v175/install/'+package
print('V177_UNDERLAY_IDENTITY_PASS')
VERIFY
