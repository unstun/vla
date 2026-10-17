"""Build and test only the v189 Mac ARM64 overlay, using archived v176 binaries."""
from pathlib import Path
import argparse
import json
import platform
import subprocess
import sys
from run_mac_full import ROOT, HERE, validate_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    task = validate_task(args.task_root)
    image = (task / 'evidence/image_id.txt').read_text().strip()
    assert subprocess.check_output(['docker', 'image', 'inspect', '--format',
                                   '{{.Os}}/{{.Architecture}}', image], text=True).strip() == 'linux/arm64'
    subprocess.run([sys.executable, str(HERE / 'prepare_native.py'), '--task-root', str(task)], check=True)
    script = '''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v176/install/setup.bash
python3 - <<'VERIFY_PARENT'
from pathlib import Path
import hashlib,json
r=json.loads(Path('/task/evidence/v176_native_receipt.json').read_text())
assert r['passed'] and r['native_version']=='v176' and r['platform']=='linux/arm64'
for name,digest in r['files'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('V176_MAC_UNDERLAY_IDENTITY_PASS')
VERIFY_PARENT
export MAKEFLAGS=-j2
cd /task/recovery_v189
colcon build --base-paths src --packages-select scan_nav2_controller lite3_nav2_bridge --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
colcon test --packages-select scan_nav2_controller --executor sequential --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v189/test_profile_frames.py
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v189 -B terminal_build
cmake --build terminal_build -j2
terminal_build/terminal_capture_probe /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v189/terminal_fixture.txt
'''
    evidence = task / 'evidence'
    (evidence / 'v189_build.sh').write_text(script)
    command = ['docker', 'run', '--rm', '--pull=never', '--platform=linux/arm64',
               '--network=none', '--cpus=4', '--memory=4g',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'OPENBLAS_NUM_THREADS=1',
               '-e', 'OMP_NUM_THREADS=1', '-v', f'{task}:/task:rw',
               '-v', f'{ROOT}:/repo:ro', '--entrypoint', '/bin/bash', image]
    (evidence / 'v189_build_request.json').write_text(json.dumps({'command': command,
        'script': script, 'host': platform.platform()}, indent=2) + '\n')
    with (evidence / 'v189_native_build.log').open('x') as stream:
        subprocess.run(command + ['/task/evidence/v189_build.sh'], stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=900)
    receipt_script = ('source /opt/ros/foxy/setup.bash && source /task/recovery_v189/install/setup.bash && '
                      'python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/'
                      'v189/create_receipt.py --image-id ' + image)
    subprocess.run(command + ['-c', receipt_script], check=True, timeout=120)


if __name__ == '__main__':
    main()
