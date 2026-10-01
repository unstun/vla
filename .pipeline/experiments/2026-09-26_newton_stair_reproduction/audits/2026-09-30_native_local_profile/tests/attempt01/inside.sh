set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /contract -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/probe_build -j2 >> /attempt/build.log 2>&1
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs VLA_GEOMETRY_OUTPUT=/attempt/geometry_result.json stdbuf -oL /attempt/probe_build/performance_probe --ros-args --params-file /archive/audits/2026-09-29_corridor_entry/v33_stand/inputs/planner.yaml > /attempt/probe.log 2>&1
