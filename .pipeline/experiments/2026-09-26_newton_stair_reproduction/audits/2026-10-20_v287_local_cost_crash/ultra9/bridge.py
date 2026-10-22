"""Build the original frozen v248 bridge against the rebuilt v287 packages."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v287_20261020')
VERSION = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    receipt = ROOT / 'evidence/bridge248_01.json'
    assert not receipt.exists()
    work = ROOT / 'bridge248/native'
    source = {str(p.relative_to(work)): sha(p) for p in (work / 'src').rglob('*') if p.is_file()}
    # Full bridge recovered from pinned snapshots; v248 stores three deltas.
    expected = json.loads((work / 'source_inventory.json').read_text())
    assert source == expected and len(source) == 20
    for rel, digest in source.items():
        delta = VERSION / 'v248' / rel
        if delta.exists():
            assert sha(delta) == digest, rel
    shell = 'source /opt/ros/foxy/setup.bash && source /native/install/setup.bash && '
    shell += 'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j2 && cd /bridge && '
    shell += 'colcon --log-base build_logs build --base-paths src --packages-select lite3_nav2_bridge '
    shell += '--executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3'
    command = ['docker', 'run', '--rm', '--pull=never', '--name', 'v287-ultra9-bridge248-01',
        '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g',
        '-v', str(ROOT / 'native') + ':/native:ro', '-v', str(work) + ':/bridge:rw',
        '--entrypoint', '/bin/bash', IMAGE, '-c', shell]
    log = ROOT / 'evidence/bridge248_01.log'
    began = time.monotonic()
    with log.open('x') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    receipt.write_text(json.dumps(dict(passed=code == 0, returncode=code, image=IMAGE,
        source_files=source, log_sha256=sha(log), wall_s=time.monotonic() - began,
        installed_files={str(p.relative_to(work)): sha(p) for p in (work / 'install').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}, physics_steps=0), indent=2) + '\n')
    raise SystemExit(code)

if __name__ == '__main__':
    main()
