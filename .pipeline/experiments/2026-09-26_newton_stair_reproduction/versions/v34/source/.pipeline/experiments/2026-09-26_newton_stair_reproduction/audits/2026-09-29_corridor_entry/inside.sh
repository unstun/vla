set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
[ -d /attempt/v32_stand/inputs ] || python3 /attempt/prepare_inputs.py /archive /attempt > /attempt/prepare.log 2>&1
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build.log 2>&1
cmake --build /attempt/probe_build -j2 --target corridor_probe >> /attempt/probe_build.log 2>&1
for state in v33_stand v32_stand; do
  for ground in state cells_fixed entry_filled both; do
    set +e
    if [ "$ground" = state ]; then override=""; else override="VLA_NAV_GROUND=/attempt/grounds/$ground.f32"; fi
    env $override VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result_$ground.json stdbuf -oL /attempt/probe_build/corridor_probe --ros-args --params-file /attempt/$state/inputs/planner.yaml > /attempt/$state/probe_$ground.log 2>&1
    echo "$?" > /attempt/$state/probe_${ground}_exit_code.txt
    set -e
  done
done
