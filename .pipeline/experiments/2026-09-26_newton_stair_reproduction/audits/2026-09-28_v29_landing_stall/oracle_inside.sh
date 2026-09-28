set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/oracle_probe_source -B /attempt/oracle_probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/oracle_probe_build.log 2>&1
cmake --build /attempt/oracle_probe_build -j2 --target oracle_probe >> /attempt/oracle_probe_build.log 2>&1
for state in landing onset; do
  mkdir -p /attempt/${state}_oracle
  set +e
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/attempt/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/${state}_oracle/result.json /attempt/oracle_probe_build/oracle_probe --ros-args --params-file /version/building_planner.yaml > /attempt/${state}_oracle/probe.log 2>&1
  echo "$?" > /attempt/${state}_oracle/probe_exit_code.txt
  set -e
done
