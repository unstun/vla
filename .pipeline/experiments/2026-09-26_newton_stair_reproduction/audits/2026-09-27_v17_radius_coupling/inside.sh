set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/r030.json /probe/moving_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.double_cylinder_radius:=0.3 > /attempt/r030.log 2>&1
mv /attempt/neighborhoods.json /attempt/r030_neighborhoods.json
env VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/r025.json /probe/moving_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.double_cylinder_radius:=0.25 > /attempt/r025.log 2>&1
mv /attempt/neighborhoods.json /attempt/r025_neighborhoods.json
