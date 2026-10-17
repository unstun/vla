#!/usr/bin/env bash
set -eo pipefail
cd /work
attempt=${1:?explicit component build attempt required}
case "$attempt" in attempt[0-9][0-9]) ;; *) exit 64 ;; esac
mkdir -p evidence /work/ros_logs /work/ros_home
mkdir "evidence/$attempt"
export ROS_LOG_DIR=/work/ros_logs ROS_HOME=/work/ros_home PYTHONDONTWRITEBYTECODE=1
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v168/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
packages="plan_env path_searching bspline_opt scan_planner pct_planner lite3_nav2_interfaces scan_nav2_controller lite3_nav2_plugins lite3_nav2_bridge"
colcon --log-base "evidence/$attempt/colcon-build" build --base-paths src --packages-select $packages --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 2>&1 | tee "evidence/$attempt/build.log"
source /work/install/setup.bash
export ROS_DOMAIN_ID=223
export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml
export TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json
export TERRAIN_TEST_DIRECTORY=/work/fixtures/building
export TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml
export TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml
export TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml
export PCT_TEST_MAP=/work/fixtures/flat.pct
set +e
colcon --log-base "evidence/$attempt/colcon-test" test --base-paths src --packages-select $packages --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_route_policy|test_direct_pct|test_shared_traversability|test_shared_support|test_wait_recovery|test_static_terrain|test_terrain_profile|test_terminal_tree|test_event_planning|test_mission_bridge|test_controller|test_tracking_behavior|test_tracking_parity|test_motion_exchange|test_terminal_completion|test_executor_shutdown|test_map_shell|test_static_support|test_reference_path_utils)$' 2>&1 | tee "evidence/$attempt/test.log"
test_status=${PIPESTATUS[0]}
colcon test-result --verbose 2>&1 | tee "evidence/$attempt/test-result.log"
exit "$test_status"
