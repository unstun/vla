set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake --build /attempt/probe_build -j2
env VLA_GEOMETRY_INPUT=/attempt/dense_inputs VLA_GEOMETRY_OUTPUT=/attempt/dense_prefix.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/dense_prefix.log 2>&1
