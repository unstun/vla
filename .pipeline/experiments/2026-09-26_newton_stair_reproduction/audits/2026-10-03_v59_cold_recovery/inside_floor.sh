set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /profile -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/build --target floor_probe -j2 >> /attempt/build.log 2>&1
/attempt/build/floor_probe --ros-args --params-file /version/building_planner.yaml > /attempt/floor.log 2>&1
