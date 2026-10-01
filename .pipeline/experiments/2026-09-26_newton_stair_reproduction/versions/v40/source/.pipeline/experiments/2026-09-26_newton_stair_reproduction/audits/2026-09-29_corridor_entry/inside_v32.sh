set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
# Review round 1, B2: v32 re-frozen at its live replan moment (prepare_inputs.py); v33's state is unchanged.
[ -d /attempt/v32_stand/inputs ] || python3 /attempt/prepare_inputs.py /archive /attempt v32_stand > /attempt/prepare_v32.log 2>&1
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build_v32.log 2>&1
cmake --build /attempt/probe_build -j2 --target corridor_probe >> /attempt/probe_build_v32.log 2>&1
for ground in state cells_fixed entry_filled both; do
  set +e
  if [ "$ground" = state ]; then override=""; else override="VLA_NAV_GROUND=/attempt/grounds/$ground.f32"; fi
  env $override VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/v32_stand/inputs VLA_GEOMETRY_OUTPUT=/attempt/v32_stand/result_$ground.json stdbuf -oL /attempt/probe_build/corridor_probe --ros-args --params-file /attempt/v32_stand/inputs/planner.yaml > /attempt/v32_stand/probe_$ground.log 2>&1
  echo "$?" > /attempt/v32_stand/probe_${ground}_exit_code.txt
  set -e
done
