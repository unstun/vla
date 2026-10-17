#!/usr/bin/env bash
# All 14 packages are rebuilt from the exact 317-file v232 tree, without old underlays.
set -eo pipefail
cd /work
test ! -e evidence/rebuild01
mkdir -p evidence/rebuild01 ros_logs ros_home
export ROS_LOG_DIR=/work/ros_logs ROS_HOME=/work/ros_home PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j2
source /opt/ros/foxy/setup.bash
cmake -S third_party/osqp -B dependencies/osqp-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DCMAKE_INSTALL_PREFIX=/work/dependencies/osqp-install \
  -DFETCHCONTENT_SOURCE_DIR_QDLDL=/work/third_party/qdldl \
  -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF 2>&1 | tee evidence/rebuild01/osqp-configure.log
cmake --build dependencies/osqp-build -j2 2>&1 | tee evidence/rebuild01/osqp-build.log
cmake --install dependencies/osqp-build 2>&1 | tee evidence/rebuild01/osqp-install.log
export CMAKE_PREFIX_PATH=/work/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}
colcon --log-base evidence/rebuild01/colcon-build build --base-paths src --executor sequential \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DPython3_EXECUTABLE=/usr/bin/python3 \
  2>&1 | tee evidence/rebuild01/build.log
