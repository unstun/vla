set -e
source /opt/ros/humble/setup.bash
mkdir -p /workspace/src
cp -a /candidate/src/. /workspace/src/
cd /workspace
colcon build --base-paths src --packages-up-to plan_env --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > /results/native_build.log 2>&1
source /workspace/install/setup.bash
cmake -S /profile -B /workspace/map_probe_build -DCMAKE_BUILD_TYPE=Release > /results/probe_build.log 2>&1
cmake --build /workspace/map_probe_build -j2 >> /results/probe_build.log 2>&1
python3 - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/workspace');expected=json.loads(Path('/candidate/source_sha256.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(root/name)==value for name,value in expected.items())
proof={'passed':True,'native_source_unchanged':True,'native_source_sha256':expected,
       'installed_sha256':{str(p.relative_to(root)):sha(p) for p in (root/'install').rglob('*') if p.is_file()},
       'probe_sha256':{p.name:sha(p) for p in (root/'map_probe_build').glob('*map_probe')},
       'instrumented_translation_unit_sha256':sha(Path('/generated/instrumented_grid_map.cpp')),
       'physics_executed':False,'gpu_job_started':False}
Path('/results/build_receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
print('V78_MAP_BUILD_PASSED')
PY
