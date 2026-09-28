set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
for state in stairs_replan stairs_hold corridor_entry_replan upper_corridor_hold; do
  set +e
  env VLA_STOP_CANDIDATES=/attempt/$state/live_candidates.txt VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/live_candidates_result.json stdbuf -oL /attempt/candidate_probe_build/candidate_probe --ros-args --params-file /attempt/$state/inputs/planner.yaml > /attempt/$state/live_candidate_probe.log 2>&1
  echo "$?" > /attempt/$state/live_candidate_probe_exit_code.txt
  set -e
done
