set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
[ -d /attempt/upper_corridor_hold/inputs ] || python3 /attempt/prepare_inputs.py /archive /attempt > /attempt/prepare.log 2>&1
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build.log 2>&1
cmake --build /attempt/probe_build -j2 --target stop_probe >> /attempt/probe_build.log 2>&1
for state in stairs_replan stairs_hold corridor_entry_replan upper_corridor_hold; do
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result.json stdbuf -oL /attempt/probe_build/stop_probe --ros-args --params-file /attempt/$state/inputs/planner.yaml > /attempt/$state/probe.log 2>&1
  echo "$?" > /attempt/$state/probe_exit_code.txt
  env VLA_STOP_REFRESH_POSE=1 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result_fresh_pose.json stdbuf -oL /attempt/probe_build/stop_probe --ros-args --params-file /attempt/$state/inputs/planner.yaml > /attempt/$state/probe_fresh_pose.log 2>&1
  echo "$?" > /attempt/$state/probe_fresh_pose_exit_code.txt
  set -e
done
