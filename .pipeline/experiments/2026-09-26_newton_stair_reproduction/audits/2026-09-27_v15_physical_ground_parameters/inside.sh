set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/soft_clearance.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p optimization.dist0:=0.05 > /attempt/soft_clearance.log 2>&1
mv /attempt/neighborhoods.json /attempt/soft_clearance_neighborhoods.json
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/native_3d.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.use_upstream_search_plane:=false > /attempt/native_3d.log 2>&1
mv /attempt/neighborhoods.json /attempt/native_3d_neighborhoods.json
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/quantization.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.reactive_terrain_band:=0.051 > /attempt/quantization.log 2>&1
mv /attempt/neighborhoods.json /attempt/quantization_neighborhoods.json
env VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/native_3d_soft.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.use_upstream_search_plane:=false -p optimization.dist0:=0.05 > /attempt/native_3d_soft.log 2>&1
mv /attempt/neighborhoods.json /attempt/native_3d_soft_neighborhoods.json
