set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env  VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/ground.f32 VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/dense_selected.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/dense_selected.log 2>&1
env  VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/dense_raw_surface.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/dense_raw_surface.log 2>&1
env VLA_FULL_RAW_RISER=1 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/dense_raw_riser.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/dense_raw_riser.log 2>&1
