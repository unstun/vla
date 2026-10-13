#!/usr/bin/env bash
set -e
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v86/freeze_sources.py verify v86
source /opt/ros/foxy/setup.bash
test "$(dpkg --print-architecture)" = arm64
test "$ROS_DISTRO" = foxy
mkdir -p /task/workspace/src /task/results/build01
cp -a /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/scan_nav2_foxy_v86/src/. /task/workspace/src/
cp -a /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v86/nav2_controller /task/workspace/src/
cd /task/workspace
dpkg-query -W > /task/results/build01/packages.tsv
colcon build --base-paths src --packages-up-to scan_nav2_controller nav2_controller scan_planner \
  --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=OFF \
  > /task/results/build01/build.log 2>&1
source install/setup.bash
colcon build --base-paths src --packages-select scan_nav2_controller \
  --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=ON \
  > /task/results/build01/test-build.log 2>&1
