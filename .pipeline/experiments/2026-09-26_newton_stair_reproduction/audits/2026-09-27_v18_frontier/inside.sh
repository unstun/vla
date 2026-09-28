set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /attempt/prepare_inputs.py /archive /attempt
env VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/baseline.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.reactive_terrain_band:=0.05 > /attempt/baseline.log 2>&1
env VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/source_precision_probe.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml -p grid_map.reactive_terrain_band:=0.0502 > /attempt/source_precision_probe.log 2>&1
