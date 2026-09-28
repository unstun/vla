set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake --build /attempt/probe_build -j2
env VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/baseline_details.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/baseline_details.log 2>&1
mkdir /attempt/dense_inputs
cp /attempt/inputs/* /attempt/dense_inputs/
cp /archive/audits/2026-09-27_dense_static_sampling/ground.f32 /attempt/dense_inputs/ground.f32
env VLA_GEOMETRY_INPUT=/attempt/dense_inputs VLA_GEOMETRY_OUTPUT=/attempt/dense_probe.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/dense_probe.log 2>&1
