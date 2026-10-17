#!/usr/bin/env bash
set -eo pipefail
cd /work
mkdir -p evidence/red01 ros_logs ros_home
export ROS_LOG_DIR=/work/ros_logs ROS_HOME=/work/ros_home PYTHONDONTWRITEBYTECODE=1
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /task/blocked_feedback_v230/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v168/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
colcon --log-base evidence/red01/colcon-build build --base-paths src --packages-select lite3_nav2_plugins --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 > evidence/red01/build.log 2>&1
source /work/install/setup.bash
set +e
/work/build/lite3_nav2_plugins/test_environmental_cost --gtest_filter=EnvironmentalRegression.* --gtest_output=xml:/work/evidence/red01/regression.xml > evidence/red01/regression.log 2>&1
status=$?
printf '%s\n' "$status" > evidence/red01/returncode.txt
exit "$status"
