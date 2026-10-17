set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/historical_radius.json /recorded/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.double_cylinder_radius:=0.25 > /attempt/historical_radius.log 2>&1
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/historical_radius_and_band.json /recorded/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.double_cylinder_radius:=0.25 -p grid_map.reactive_terrain_band:=0.051 > /attempt/historical_radius_and_band.log 2>&1
