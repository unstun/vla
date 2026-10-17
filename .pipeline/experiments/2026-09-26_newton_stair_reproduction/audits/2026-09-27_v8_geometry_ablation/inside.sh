set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/ablation/radius_only.json /attempt/probe_build/frontier_probe --ros-args --params-file /inputs/planner.yaml -p grid_map.double_cylinder_radius:=0.25 > /ablation/radius_only.log 2>&1
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/ablation/z_only.json /attempt/probe_build/frontier_probe --ros-args --params-file /inputs/planner.yaml -p grid_map.obstacles_inflation_z_up:=0.1 -p grid_map.obstacles_inflation_z_down:=0.1 > /ablation/z_only.log 2>&1
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/ablation/old_envelope.json /attempt/probe_build/frontier_probe --ros-args --params-file /inputs/planner.yaml -p grid_map.double_cylinder_radius:=0.25 -p grid_map.obstacles_inflation_z_up:=0.1 -p grid_map.obstacles_inflation_z_down:=0.1 > /ablation/old_envelope.log 2>&1
