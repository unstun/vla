set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
[ -d /attempt/control/inputs ] || python3 /attempt/prepare_inputs.py /archive /attempt
for state in control stopped; do
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result.json /archive/runs/v28_native_regression01/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/$state/probe.log 2>&1
  echo "$?" > /attempt/$state/probe_exit_code.txt
  set -e
done
