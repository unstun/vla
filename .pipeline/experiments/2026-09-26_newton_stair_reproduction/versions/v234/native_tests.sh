#!/usr/bin/env bash
# /work is the private v234 build; /source contains immutable v232 test helpers.
set -eo pipefail
cd /work
attempt=${1:?explicit fresh test attempt required}
case "$attempt" in v234_attempt[0-9][0-9]) ;; *) exit 64 ;; esac
test -f /work/v234_private_test_copy
test ! -e "/work/evidence/$attempt"
mkdir -p "/work/evidence/$attempt" /work/ros_logs /work/ros_home
export ROS_LOG_DIR=/work/ros_logs ROS_HOME=/work/ros_home PYTHONDONTWRITEBYTECODE=1
source /opt/ros/foxy/setup.bash
source /work/install/setup.bash
export CMAKE_PREFIX_PATH=/work/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-218} ROS_LOCALHOST_ONLY=1
export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml
export TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json
export TERRAIN_TEST_DIRECTORY=/work/fixtures/building
export TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml
export TERRAIN_NATIVE_PROFILE=/work/fixtures/component234.scan.yaml
export TERRAIN_TEST_PROFILE=/work/fixtures/component234.yaml
export PCT_TEST_MAP=/work/fixtures/flat.pct FEEDBACK_OUTPUT=/work/feedback_output
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
# Remove old XML only inside this disposable copy. Every counted result must be new.
python3 - <<'PY'
from pathlib import Path
import shutil
for path in Path('/work/build').glob('*/test_results'):
    shutil.rmtree(path)
for path in Path('/work/build').glob('*/ament_cmake_pytest/**/*.xml'):
    path.unlink()
PY
packages="plan_env path_searching bspline_opt scan_planner pct_planner lite3_nav2_interfaces scan_nav2_controller lite3_nav2_plugins lite3_nav2_bridge"
set +e
colcon --log-base "evidence/$attempt/colcon-test" test --base-paths src --packages-select $packages --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_environmental_cost|test_route_policy|test_direct_pct|test_shared_traversability|test_shared_support|test_wait_recovery|test_static_terrain|test_terrain_profile|test_terminal_tree|test_event_planning|test_mission_bridge|test_controller|test_tracking_behavior|test_tracking_parity|test_motion_exchange|test_terminal_completion|test_executor_shutdown|test_map_shell|test_static_support|test_reference_path_utils|test_uniform_bspline)$' 2>&1 | tee "evidence/$attempt/test.log"
status=${PIPESTATUS[0]}
colcon test-result --verbose 2>&1 | tee "evidence/$attempt/test-result.log"
python3 /source/tools/snapshot_tests.py /work "$attempt"
exit "$status"
