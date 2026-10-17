set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/soft_clearance.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p optimization.dist0:=0.05 > /attempt/soft_clearance.log 2>&1
mv /attempt/neighborhoods.json /attempt/soft_clearance_neighborhoods.json
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/first_reached.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.goal_approach_max_iterations:=1 > /attempt/first_reached.log 2>&1
mv /attempt/neighborhoods.json /attempt/first_reached_neighborhoods.json
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/ground_quantization.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.reactive_terrain_band:=0.051 > /attempt/ground_quantization.log 2>&1
mv /attempt/neighborhoods.json /attempt/ground_quantization_neighborhoods.json
