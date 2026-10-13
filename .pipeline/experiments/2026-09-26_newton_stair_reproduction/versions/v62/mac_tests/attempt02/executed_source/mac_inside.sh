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
python3 - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/workspace/install')
records={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
         for p in root.rglob('*') if p.is_file()}
Path('/attempt/install_sha256.json').write_text(json.dumps(records,indent=2)+'\n')
PY
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
# Original recorded fixtures already exist on this Mac. Only rebuild the ROS
# wire schema in temporary storage; no new clouds or heavy returned artifacts.
mkdir /workspace/fixtures
python3 - <<'PY'
from pathlib import Path
import hashlib,json
source=Path('/archive/versions/v36/contract/convert_recorded_messages.py')
contents=source.read_text()
assert contents.count('out=Path("/attempt")')==1
adapted=contents.replace('out=Path("/attempt")','out=Path("/workspace/fixtures")')
target=Path('/workspace/convert_recorded_messages.py');target.write_text(adapted)
Path('/attempt/converter_provenance.json').write_text(json.dumps({
    'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'adapted_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'only_change':'temporary output directory; recorded values remain exact',
},indent=2)+'\n')
PY
python3 /workspace/convert_recorded_messages.py --mode convert_new > /attempt/recorded_conversion.log 2>&1
for state in v33_stand v32_stand; do
  cp /workspace/fixtures/$state/convert_new.json /attempt/${state}_convert_new.json
  env V59_EPOCH_CONTRACT=1 V53_REFRESH_CONTRACT=1 V50_REGION_CONTRACT=1 V48_WARM_CONTRACT=1 VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/workspace/fixtures/$state/converted_inputs VLA_GEOMETRY_OUTPUT=/attempt/${state}_geometry.json stdbuf -oL /workspace/probe_build/performance_probe --ros-args --params-file /archive/audits/2026-09-29_corridor_entry/$state/inputs/planner.yaml > /attempt/${state}.log 2>&1
done
export PYTHONPATH=/archive/versions/v59/backend_ros:/archive/runtime_sources/backend_adapter:/archive/runtime/foreground_py310:/archive/runtime_sources/pct_runtime/python:${PYTHONPATH:-}
export V36_EXPERIMENT_ROOT=/archive
PYTHONDONTWRITEBYTECODE=1 python3 /archive/versions/v59/test_backend_contract.py -v > /attempt/backend_tests.log 2>&1
