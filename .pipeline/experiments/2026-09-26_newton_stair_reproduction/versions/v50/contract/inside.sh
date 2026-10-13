set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
g++ -std=c++17 -O2 -I/usr/include/eigen3 -I/workspace/src/plan_env/include /contract/goal_region_probe.cpp -o /attempt/goal_region_probe
/attempt/goal_region_probe > /attempt/goal_region_probe.log
cmake -S /contract -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/probe_build -j2 >> /attempt/build.log 2>&1
/attempt/probe_build/native_probe --ros-args --params-file /config/building_planner.yaml --params-file /config/controller.yaml > /attempt/native_probe.log 2>&1
/attempt/probe_build/cache_probe --ros-args --params-file /config/building_planner.yaml > /attempt/cache_probe.log 2>&1
for state in v33_stand v32_stand; do
  env V50_REGION_CONTRACT=1 V48_WARM_CONTRACT=1 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/versions/v36/tests/attempt09/$state/converted_inputs VLA_GEOMETRY_OUTPUT=/attempt/${state}_geometry.json stdbuf -oL /attempt/probe_build/performance_probe --ros-args --params-file /archive/audits/2026-09-29_corridor_entry/$state/inputs/planner.yaml > /attempt/${state}.log 2>&1
done
export PYTHONPATH=/version/backend_ros:/archive/runtime_sources/backend_adapter:/archive/runtime/foreground_py310:/archive/runtime_sources/pct_runtime/python:${PYTHONPATH:-}
export V36_EXPERIMENT_ROOT=/archive
PYTHONDONTWRITEBYTECODE=1 python3 /version/test_backend_contract.py -v > /attempt/backend_tests.log 2>&1
