set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
# The corridor-entry audit re-froze v32 at its live replan moment (its review round 1, B2); v33's state is unchanged.
cmake -S /audit/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build_v32.log 2>&1
cmake --build /attempt/probe_build -j2 --target corridor_probe >> /attempt/probe_build_v32.log 2>&1
mkdir -p /attempt/v32_stand
set +e
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/audit/v32_stand/inputs VLA_GEOMETRY_OUTPUT=/attempt/v32_stand/result_green.json stdbuf -oL /attempt/probe_build/corridor_probe --ros-args --params-file /audit/v32_stand/inputs/planner.yaml > /attempt/v32_stand/probe_green.log 2>&1
echo "$?" > /attempt/v32_stand/probe_green_exit_code.txt
set -e
