set -e
source /opt/ros/humble/setup.bash
mkdir -p /workspace/src
cp -a /candidate/src/. /workspace/src/
cd /workspace
python3 --version
g++ --version
dpkg-query -W > /attempt/package_versions.txt
colcon build --base-paths src --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > /attempt/native_build.log 2>&1
source /workspace/install/setup.bash
python3 /version/contract/prepare_retry_harness.py /parent /candidate /workspace/retry /attempt/retry_harness.json
mkdir /workspace/contract
cp -a /version/contract/. /workspace/contract/
cp /version/contract/CMakeLists.mac.txt /workspace/contract/CMakeLists.txt
cmake -S /workspace/contract -B /workspace/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/probe_build.log 2>&1
cmake --build /workspace/probe_build -j2 >> /attempt/probe_build.log 2>&1
env V62_RETRY_OUTPUT=/attempt/parent_retry_epoch.json /workspace/probe_build/retry_parent_probe --ros-args --params-file /version/building_planner.yaml > /attempt/parent_retry_probe.log 2>&1
env V62_RETRY_OUTPUT=/attempt/candidate_retry_epoch.json /workspace/probe_build/retry_candidate_probe --ros-args --params-file /version/building_planner.yaml > /attempt/candidate_retry_probe.log 2>&1
g++ -std=c++17 -O2 -I/workspace/src/plan_env/include /version/contract/physical_floor_probe.cpp -o /workspace/physical_floor_probe
/workspace/physical_floor_probe > /attempt/physical_floor_probe.log 2>&1
g++ -std=c++17 -O2 -I/usr/include/eigen3 -I/workspace/src/plan_env/include /version/contract/goal_region_probe.cpp -o /workspace/goal_region_probe
/workspace/goal_region_probe > /attempt/goal_region_probe.log 2>&1
/workspace/probe_build/controller_epoch_probe --ros-args -p use_sim_time:=true > /attempt/controller_epoch_probe.log 2>&1
/workspace/probe_build/endpoint_probe --ros-args --params-file /version/building_planner.yaml > /attempt/endpoint_probe.log 2>&1
/workspace/probe_build/native_probe --ros-args --params-file /version/building_planner.yaml --params-file /version/controller.yaml > /attempt/native_probe.log 2>&1
/workspace/probe_build/cache_probe --ros-args --params-file /version/building_planner.yaml > /attempt/cache_probe.log 2>&1
export PYTHONPATH=/archive/versions/v59/backend_ros:/archive/runtime_sources/backend_adapter:/archive/runtime/foreground_py310:/archive/runtime_sources/pct_runtime/python:${PYTHONPATH:-}
export V36_EXPERIMENT_ROOT=/archive
PYTHONDONTWRITEBYTECODE=1 python3 /archive/versions/v59/test_backend_contract.py -v > /attempt/backend_tests.log 2>&1
python3 - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/workspace/install')
records={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
         for p in root.rglob('*') if p.is_file()}
Path('/attempt/install_sha256.json').write_text(json.dumps(records,indent=2)+'\n')
PY
