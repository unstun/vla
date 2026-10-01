set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /contract -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/probe_build -j2 >> /attempt/build.log 2>&1
/attempt/probe_build/native_probe --ros-args --params-file /config/building_planner.yaml --params-file /config/controller.yaml > /attempt/probe.log 2>&1
for invalid in -1 0 nan inf 101 1e-310; do
  V36_INVALID_CONTROLLER_FREQUENCY=$invalid /attempt/probe_build/native_probe > /attempt/invalid_${invalid}.log 2>&1
done
export PYTHONPATH=/config/backend_ros:/archive/runtime_sources/backend_adapter:/archive/runtime/foreground_py310:/archive/runtime_sources/pct_runtime/python
export V36_EXPERIMENT_ROOT=/archive
export LD_LIBRARY_PATH=/archive/runtime_sources/pct_runtime/lib:${LD_LIBRARY_PATH:-}
python3 /config/test_backend_contract.py -v > /attempt/backend_tests.log 2>&1
python3 /contract/global_probe.py > /attempt/global_native.log 2>&1
for state in v33_stand v32_stand; do
  mkdir /attempt/$state
  env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/audits/2026-09-29_corridor_entry/$state/inputs VLA_GEOMETRY_OUTPUT=/attempt/$state/result.json stdbuf -oL /attempt/probe_build/performance_probe --ros-args --params-file /archive/audits/2026-09-29_corridor_entry/$state/inputs/planner.yaml > /attempt/$state/probe.log 2>&1
done
