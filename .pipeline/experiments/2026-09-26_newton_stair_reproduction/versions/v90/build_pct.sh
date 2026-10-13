#!/usr/bin/env bash
set -eo pipefail
# Run inside the owned ARM64/Foxy container after materializing the pinned PCT
# package at /task/pct_workspace/src/pct_planner. No source network fetch occurs.
source /opt/ros/foxy/setup.bash
set -u
test "${ROS_DISTRO}" = foxy
test "$(dpkg --print-architecture)" = arm64
CMAKE=/task/cmake-tool/cmake/data/bin/cmake
"$CMAKE" -S /repo/references/upstream/2026-10-08_nav2_pct_foxy/osqp \
  -B /task/osqp-build02 -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_INSTALL_PREFIX=/task/osqp-install \
  -DFETCHCONTENT_SOURCE_DIR_QDLDL=/repo/references/upstream/2026-10-08_nav2_pct_foxy/qdldl \
  -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF
"$CMAKE" --build /task/osqp-build02 -j2
"$CMAKE" --install /task/osqp-build02
cd /task/pct_workspace
export CMAKE_PREFIX_PATH="/task/osqp-install:${CMAKE_PREFIX_PATH:-}"
colcon build --packages-select pct_planner --executor sequential \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DBUILD_TESTING=OFF -DPython3_EXECUTABLE=/usr/bin/python3
