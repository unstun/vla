set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build.log 2>&1
cmake --build /attempt/probe_build -j2 --target gen_probe >> /attempt/probe_build.log 2>&1
cmake -S /attempt/breakdown_source -B /attempt/breakdown_build -DCMAKE_BUILD_TYPE=Release > /attempt/breakdown_build.log 2>&1
cmake --build /attempt/breakdown_build -j2 --target landing_probe >> /attempt/breakdown_build.log 2>&1
S=/archive/audits/2026-09-28_v28_start_thrash
L=/archive/audits/2026-09-28_v29_landing_stall
G=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32
for pair in stopped:$S/stopped/inputs z_0p35490:$S/fine_sweep/z_0p35490/inputs z_0p3600:$S/height_sweep/z_0p3600/inputs z_0p3650:$S/height_sweep/z_0p3650/inputs z_0p3700:$S/height_sweep/z_0p3700/inputs z_0p3800:$S/height_sweep/z_0p3800/inputs control:$S/control/inputs landing:$L/landing/inputs onset:$L/onset/inputs; do
  name=${pair%%:*}
  input=${pair#*:}
  mkdir -p /attempt/$name
  set +e
  env VLA_RAW_GROUND=$G VLA_GEOMETRY_INPUT=$input VLA_GEOMETRY_OUTPUT=/attempt/$name/result.json /attempt/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/$name/probe.log 2>&1
  echo "$?" > /attempt/$name/probe_exit_code.txt
  set -e
done
for name in landing onset; do
  set +e
  env VLA_RAW_GROUND=$G VLA_GEOMETRY_INPUT=$L/$name/inputs VLA_GEOMETRY_OUTPUT=/attempt/$name/breakdown.json /attempt/breakdown_build/landing_probe --ros-args --params-file /version/building_planner.yaml > /attempt/$name/breakdown.log 2>&1
  echo "$?" > /attempt/$name/breakdown_exit_code.txt
  set -e
done
