#!/usr/bin/env bash
# Build all frozen packages in a private workspace; no old underlay mutations.
set -eo pipefail
cd /work
mkdir -p ros_logs ros_home
export ROS_LOG_DIR=/work/ros_logs ROS_HOME=/work/ros_home
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j2
source /opt/ros/foxy/setup.bash
export CMAKE_PREFIX_PATH=/work/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}
colcon --log-base logs/build01 build --base-paths src --executor sequential \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DPython3_EXECUTABLE=/usr/bin/python3
