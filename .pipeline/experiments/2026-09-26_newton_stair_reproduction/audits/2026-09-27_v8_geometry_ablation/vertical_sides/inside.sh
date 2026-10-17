set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/side/up_only.json /attempt/probe_build/frontier_probe --ros-args --params-file /inputs/planner.yaml -p grid_map.obstacles_inflation_z_up:=0.1 > /side/up_only.log 2>&1
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/side/down_only.json /attempt/probe_build/frontier_probe --ros-args --params-file /inputs/planner.yaml -p grid_map.obstacles_inflation_z_down:=0.1 > /side/down_only.log 2>&1
