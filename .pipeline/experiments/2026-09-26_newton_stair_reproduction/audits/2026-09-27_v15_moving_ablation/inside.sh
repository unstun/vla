set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/native_3d.json /recorded/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.use_upstream_search_plane:=false > /attempt/native_3d.log 2>&1
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/quantization_band.json /recorded/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.reactive_terrain_band:=0.051 > /attempt/quantization_band.log 2>&1
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/native_3d_and_band.json /recorded/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.use_upstream_search_plane:=false -p grid_map.reactive_terrain_band:=0.051 > /attempt/native_3d_and_band.log 2>&1
