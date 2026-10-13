set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /profile/prepare.py > /attempt/prepare.log 2>&1
cmake -S /profile -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/build -j2 >> /attempt/build.log 2>&1
/attempt/build/cold_probe --ros-args --params-file /version/building_planner.yaml > /attempt/native.log 2>&1
