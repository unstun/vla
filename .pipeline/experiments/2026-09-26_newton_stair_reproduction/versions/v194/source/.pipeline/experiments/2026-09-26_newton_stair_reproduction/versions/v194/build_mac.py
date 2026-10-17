"""Build and test the v194 Option B Mac ARM64 overlay, using archived v176 binaries."""
from pathlib import Path
import argparse
import json
import platform
import shutil
import subprocess
import sys
from run_mac_full import ROOT, HERE, validate_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    parser.add_argument('--verify-existing', action='store_true',
                        help='Reuse the verified build and rerun its tests and receipt checks.')
    args = parser.parse_args()
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    if (HERE / 'manifest.json').exists():
        raise ValueError('Never rebuild a frozen version')
    task = validate_task(args.task_root)
    image = (task / 'evidence/image_id.txt').read_text().strip()
    assert subprocess.check_output(['docker', 'image', 'inspect', '--format',
                                   '{{.Os}}/{{.Architecture}}', image], text=True).strip() == 'linux/arm64'
    if not (task / 'recovery_v194').exists():
        if args.verify_existing:
            raise ValueError('Existing workspace required')
        subprocess.run([sys.executable, str(HERE / 'prepare_native.py'), '--task-root', str(task)], check=True)
    origins = json.loads((HERE / 'native_sources.json').read_text())
    from native_gate import sha
    source_files = {'src/' + str(p.relative_to(task / 'recovery_v194/src')): sha(p)
                    for p in (task / 'recovery_v194/src').rglob('*') if p.is_file()}
    assert source_files == origins['expected_files'], 'Existing source differs from v194 inventory'
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
cd /task/recovery_v194
colcon build --base-paths src --packages-select lite3_nav2_interfaces scan_planner_msgs lite3_nav2_plugins plan_env bspline_opt path_searching traj_utils scan_planner scan_nav2_controller lite3_nav2_bridge scan_reactive_tracker --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
source install/setup.bash
colcon test --packages-select scan_nav2_controller lite3_nav2_plugins lite3_nav2_bridge --executor sequential --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v194/test_profile_frames.py
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v194 -B terminal_qualification_build
cmake --build terminal_qualification_build -j2
terminal_qualification_build/terminal_capture_probe /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v194/terminal_fixture.txt
'''
    if args.verify_existing:
        script = '\n'.join(line for line in script.split('\n') if not line.startswith('colcon build '))
    evidence = task / 'evidence'
    (evidence / 'v194_build.sh').write_text(script)
    command = ['docker', 'run', '--rm', '--pull=never', '--platform=linux/arm64',
               '--network=none', '--cpus=4', '--memory=4g',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'OPENBLAS_NUM_THREADS=1',
               '-e', 'OMP_NUM_THREADS=1', '-v', f'{task}:/task:ro',
               '-v', f'{task / "recovery_v194"}:/task/recovery_v194:rw',
               '-v', f'{evidence}:/task/evidence:rw',
               '-v', f'{ROOT}:/repo:ro', '--entrypoint', '/bin/bash', image]
    previous_log = evidence / 'v194_native_build_previous.log'
    if args.verify_existing:
        shutil.copyfile(evidence / 'v194_native_build.log', previous_log)
    (evidence / 'v194_build_request.json').write_text(json.dumps({'command': command,
        'script': script, 'host': platform.platform(), 'reuse_existing_build': args.verify_existing,
        'source_identity_sha256': sha(task / 'recovery_v194/source_identity.json'),
        'original_build_log_sha256': sha(previous_log)
            if args.verify_existing else None}, indent=2) + '\n')
    with (evidence / 'v194_native_build.log').open('w') as stream:
        if args.verify_existing:
            stream.write('=== Existing native build evidence (preserved verbatim) ===\n')
            stream.write(previous_log.read_text())
            stream.write('\n=== Current qualification tests and terminal probe ===\n')
            stream.flush()
        subprocess.run(command + ['/task/evidence/v194_build.sh'], stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=900)
    receipt_script = ('source /opt/ros/foxy/setup.bash && source /task/recovery_v176/install/setup.bash && '
                      'source /task/recovery_v194/install/setup.bash && '
                      'python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/'
                      'v194/create_receipt.py --image-id ' + image)
    subprocess.run(command + ['-c', receipt_script], check=True, timeout=120)


if __name__ == '__main__':
    main()
