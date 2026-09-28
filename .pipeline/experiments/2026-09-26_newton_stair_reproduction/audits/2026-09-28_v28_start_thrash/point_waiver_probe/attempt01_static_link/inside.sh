set -e
source /opt/ros/humble/setup.bash
cd /workspace
colcon build --base-paths src --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > /attempt/build.log 2>&1
source /workspace/install/setup.bash
for state in stopped control; do
  mkdir -p /attempt/$state
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/audits/2026-09-28_v28_start_thrash/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result.json /archive/runs/v28_native_regression01/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/$state/probe.log 2>&1
  echo "$?" > /attempt/$state/probe_exit_code.txt
  set -e
done
