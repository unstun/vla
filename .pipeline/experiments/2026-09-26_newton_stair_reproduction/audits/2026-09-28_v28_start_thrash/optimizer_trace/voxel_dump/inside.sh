set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
# Fresh probe build directory: the first trace run reused a copied build tree whose
# objects were newer than the edited gen_probe.cpp, so its voxel dump was not compiled.
cmake -S /attempt/probe_source -B /attempt/voxel_dump/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/voxel_dump/probe_build.log 2>&1
cmake --build /attempt/voxel_dump/probe_build -j2 --target gen_probe >> /attempt/voxel_dump/probe_build.log 2>&1
S=/archive/audits/2026-09-28_v28_start_thrash
for pair in stopped:$S/stopped/inputs z_0p3600:$S/height_sweep/z_0p3600/inputs control:$S/control/inputs; do
  name=${pair%%:*}
  input=${pair#*:}
  mkdir -p /attempt/voxel_dump/$name
  set +e
  env VLA_TRACE=1 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=$input VLA_GEOMETRY_OUTPUT=/attempt/voxel_dump/$name/result.json stdbuf -oL -eL /attempt/voxel_dump/probe_build/gen_probe --ros-args --params-file /version/building_planner.yaml > /attempt/voxel_dump/$name/probe.log 2>&1
  echo "$?" > /attempt/voxel_dump/$name/probe_exit_code.txt
  set -e
done
