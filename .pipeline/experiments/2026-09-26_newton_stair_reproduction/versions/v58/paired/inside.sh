set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /profile -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/build -j2 >> /attempt/build.log 2>&1
for run in v57_realtime_trial01 v57_realtime_trial02; do
  /attempt/build/goal_probe "$run" --ros-args --params-file /version/building_planner.yaml > "/attempt/$run.log" 2>&1
done
