#!/usr/bin/env bash
set -e
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v86/freeze_sources.py verify v87
source /opt/ros/foxy/setup.bash
test "$ROS_DISTRO" = foxy
mkdir -p /task/integrated_workspace/src /task/results/integrated_build01
cp -a /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/scan_nav2_foxy_v86/src/. /task/integrated_workspace/src/
cp -a /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v87/plan_env/. /task/integrated_workspace/src/plan_env/
cp -a /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v86/nav2_controller /task/integrated_workspace/src/
cd /task/integrated_workspace
colcon build --packages-up-to nav2_controller --executor sequential --cmake-args \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=OFF \
  > /task/results/integrated_build01/build.log 2>&1
source install/setup.bash
colcon build --packages-select scan_nav2_controller --cmake-args -DBUILD_TESTING=ON \
  > /task/results/integrated_build01/test-build.log 2>&1
V86_NATIVE_PARAMS=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v87/building_planner.yaml \
  colcon test --packages-select scan_nav2_controller --event-handlers console_direct+ \
  > /task/results/integrated_build01/test.log 2>&1
colcon test-result --verbose > /task/results/integrated_build01/test-result.log 2>&1
