set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /attempt/prepare_inputs.py /archive /attempt
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/baseline.json /archive/runs/v24_native_regression01/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/baseline.log 2>&1
