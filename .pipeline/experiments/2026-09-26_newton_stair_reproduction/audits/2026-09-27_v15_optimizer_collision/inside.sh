set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j1
env  VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/selected.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/selected.log 2>&1
mv /attempt/neighborhoods.json /attempt/selected_neighborhoods.json
env VLA_DIAGNOSTIC_PHYSICAL_GROUND=1 VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/physical.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/physical.log 2>&1
mv /attempt/neighborhoods.json /attempt/physical_neighborhoods.json
env VLA_DIAGNOSTIC_PHYSICAL_GROUND=1 VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/physical_fixed_height.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p optimization.optimize_height:=false > /attempt/physical_fixed_height.log 2>&1
mv /attempt/neighborhoods.json /attempt/physical_fixed_height_neighborhoods.json
