set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/candidate_probe_source -B /attempt/candidate_probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/candidate_probe_build.log 2>&1
cmake --build /attempt/candidate_probe_build -j2 --target candidate_probe >> /attempt/candidate_probe_build.log 2>&1
for state in stairs_replan stairs_hold corridor_entry_replan upper_corridor_hold; do
  set +e
  env VLA_STOP_CANDIDATES=/attempt/$state/candidates.txt VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/candidates_result.json stdbuf -oL /attempt/candidate_probe_build/candidate_probe --ros-args --params-file /attempt/$state/inputs/planner.yaml > /attempt/$state/candidate_probe.log 2>&1
  echo "$?" > /attempt/$state/candidate_probe_exit_code.txt
  set -e
done
