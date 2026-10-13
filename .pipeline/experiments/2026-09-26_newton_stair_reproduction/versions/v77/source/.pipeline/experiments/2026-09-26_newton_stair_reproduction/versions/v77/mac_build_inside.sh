set -e
source /opt/ros/humble/setup.bash
mkdir -p /workspace/src
cp -a /candidate/src/. /workspace/src/
cp /candidate/LICENSE /candidate/NOTICE /candidate/THIRD_PARTY_NOTICES.md /workspace/
cd /workspace
colcon build --base-paths src --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > /evidence/native_build.log 2>&1
python3 - <<'PY'
from pathlib import Path
import hashlib,json
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
root=Path('/workspace');expected=json.loads(Path('/candidate/source_sha256.json').read_text())
assert all(sha(root/name)==h for name,h in expected.items())
installed={str(p.relative_to(root)):sha(p) for p in (root/'install').rglob('*') if p.is_file()}
Path('/evidence/build_receipt.json').write_text(json.dumps({
    'passed':True,'source_unchanged':True,'native_source_sha256':expected,
    'native_install_sha256':installed,'host':'Mac desktop-linux emulation',
    'image':'sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb',
},indent=2)+'\n')
PY
