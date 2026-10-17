set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /audit/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build.log 2>&1
cmake --build /attempt/probe_build -j2 --target corridor_probe >> /attempt/probe_build.log 2>&1
for state in v33_stand v32_stand; do
  mkdir -p /attempt/$state
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/audit/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result_green.json stdbuf -oL /attempt/probe_build/corridor_probe --ros-args --params-file /audit/$state/inputs/planner.yaml > /attempt/$state/probe_green.log 2>&1
  echo "$?" > /attempt/$state/probe_green_exit_code.txt
  set -e
done
