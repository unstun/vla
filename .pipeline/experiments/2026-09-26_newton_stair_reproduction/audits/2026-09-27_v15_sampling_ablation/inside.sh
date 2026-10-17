set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/spacing010.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.control_points_distance:=.1 > /attempt/spacing010.log 2>&1
mv /attempt/neighborhoods.json /attempt/spacing010_neighborhoods.json
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/spacing005.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.control_points_distance:=.05 > /attempt/spacing005.log 2>&1
mv /attempt/neighborhoods.json /attempt/spacing005_neighborhoods.json
