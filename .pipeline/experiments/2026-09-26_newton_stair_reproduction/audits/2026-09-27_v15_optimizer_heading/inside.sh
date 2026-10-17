set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j1
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/baseline.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/baseline.log 2>&1
mv /attempt/neighborhoods.json /attempt/baseline_neighborhoods.json
env VLA_DIAGNOSTIC_SHARED_HEADING=1 VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/shared.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/shared.log 2>&1
mv /attempt/neighborhoods.json /attempt/shared_neighborhoods.json
