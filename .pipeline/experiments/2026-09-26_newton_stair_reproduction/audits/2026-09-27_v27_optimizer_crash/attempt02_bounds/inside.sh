set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build /attempt/probe_build -j2
export UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/parent/inputs VLA_GEOMETRY_OUTPUT=/attempt/result.json /attempt/probe_build/crash_probe --ros-args --params-file /version/building_planner.yaml > /attempt/replay.log 2>&1
