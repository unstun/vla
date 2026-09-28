set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
for variant in $(ls -d /attempt/height_sweep/z_*/ | xargs -n1 basename); do
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/height_sweep/$variant/inputs VLA_GEOMETRY_OUTPUT=/attempt/height_sweep/$variant/result.json /archive/runs/v28_native_regression01/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/height_sweep/$variant/probe.log 2>&1
  echo "$?" > /attempt/height_sweep/$variant/probe_exit_code.txt
  set -e
done
