set -eo pipefail
source /opt/ros/foxy/setup.bash
cd /task/step2_v126
cmake -S third_party/osqp -B dependencies/osqp-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_INSTALL_PREFIX="$PWD/dependencies/osqp-install" -DFETCHCONTENT_SOURCE_DIR_QDLDL="$PWD/third_party/qdldl" -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF
cmake --build dependencies/osqp-build -j2
cmake --install dependencies/osqp-build
export CMAKE_PREFIX_PATH="$PWD/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}"
export MAKEFLAGS=-j2
colcon build --base-paths src --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
colcon test --base-paths src --packages-select scan_nav2_controller lite3_nav2_plugins --executor sequential --return-code-on-test-failure
colcon test-result --verbose
