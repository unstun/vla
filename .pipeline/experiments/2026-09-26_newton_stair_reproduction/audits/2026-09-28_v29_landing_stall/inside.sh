set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
[ -d /attempt/landing/inputs ] || python3 /attempt/prepare_inputs.py /archive /attempt > /attempt/prepare.log 2>&1
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build.log 2>&1
cmake --build /attempt/probe_build -j2 --target landing_probe >> /attempt/probe_build.log 2>&1
for state in landing onset; do
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/baseline.json /archive/runs/v29_native_regression01/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/$state/baseline.log 2>&1
  echo "$?" > /attempt/$state/baseline_exit_code.txt
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result.json /attempt/probe_build/landing_probe --ros-args --params-file /version/building_planner.yaml > /attempt/$state/probe.log 2>&1
  echo "$?" > /attempt/$state/probe_exit_code.txt
  set -e
done
