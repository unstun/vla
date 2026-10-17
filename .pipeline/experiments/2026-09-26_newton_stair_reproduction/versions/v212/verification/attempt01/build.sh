#!/usr/bin/env bash
set -eo pipefail
cd /work
mkdir -p evidence
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v168/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
colcon build --packages-select lite3_nav2_plugins lite3_nav2_bridge --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 2>&1 | tee evidence/build.log
source /work/install/setup.bash
export ROS_DOMAIN_ID=212
export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml
export TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json
export TERRAIN_TEST_DIRECTORY=/work/fixtures/building
export TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml
export TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml
export PCT_TEST_MAP=/work/fixtures/flat.pct
colcon test --packages-select lite3_nav2_plugins lite3_nav2_bridge --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_route_policy|test_direct_pct|test_wait_recovery|test_static_terrain|test_terrain_profile|test_terminal_tree|test_event_planning|test_mission_bridge)$' 2>&1 | tee evidence/test.log
colcon test-result --verbose 2>&1 | tee evidence/test-result.log
