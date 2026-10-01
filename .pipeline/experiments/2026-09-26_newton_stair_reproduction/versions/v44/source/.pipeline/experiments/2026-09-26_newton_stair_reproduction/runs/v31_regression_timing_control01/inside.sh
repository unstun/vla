# Paired A* wall-time control for the v31 native regression (see execute.py).
# Runs the four timing-sensitive regression fixtures once, with the regression's
# own commands, against the probe build and runtime mounted at /probe and /workspace.
set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
out=/attempt/$VLA_REP
mkdir -p $out
run() {
  name=$1; shift
  set +e
  env "$@" > $out/$name.log 2>&1
  echo "$?" > $out/${name}_exit_code.txt
  set -e
}
run v18 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=$out/v18.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml
run v23 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/audits/2026-09-27_v23_frontier/inputs VLA_GEOMETRY_OUTPUT=$out/v23.json /probe/gen_probe --ros-args --params-file /version/building_planner.yaml
run v23_repeat VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/audits/2026-09-27_v23_frontier/inputs VLA_GEOMETRY_OUTPUT=$out/v23_repeat.json /probe/gen_probe --ros-args --params-file /version/building_planner.yaml
run mapped_low_box VLA_RAW_GROUND=/archive/audits/2026-09-27_pct_ground_negatives/mapped_low_box/qualified_ground.f32 VLA_GEOMETRY_INPUT=/archive/audits/2026-09-27_pct_ground_negatives/mapped_low_box VLA_GEOMETRY_OUTPUT=$out/mapped_low_box.json /probe/measured_cloud_probe --ros-args --params-file /version/building_planner.yaml
run unmapped_low_box VLA_GEOMETRY_INPUT=/archive/runs/generic_sensor_cases_v1/low_box VLA_GEOMETRY_OUTPUT=$out/unmapped_low_box.json /probe/measured_cloud_probe --ros-args --params-file /version/building_planner.yaml
