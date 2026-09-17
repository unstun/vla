"""Build a captured SCAN overlay in the pinned Foxy image, preserving evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time

HERE = Path(__file__).resolve().parent
IMAGE = 'e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build_name')
    args = parser.parse_args()
    if not args.build_name.replace('_', '').isalnum():
        raise ValueError('Invalid build name')
    base = HERE / 'builds' / args.build_name
    if (base / 'build_result.json').exists():
        raise RuntimeError('Build already has immutable result')
    sources = {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (base / 'src').rglob('*') if p.is_file()}
    if not sources:
        raise RuntimeError('No materialized source')
    (base / 'source_sha256.json').write_text(json.dumps(sources, indent=2) + '\n')
    remote = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/' + args.build_name
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'gpu5070ti']
    commands = []
    started = time.monotonic()
    result = {'passed': False, 'error': 'interrupted'}

    def run(label, command, stdin=None, timeout=120):
        p = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=timeout)
        (base / (label + '.log')).write_text(p.stdout + p.stderr)
        commands.append({'label': label, 'command': command, 'exit_code': p.returncode})
        print(label, p.returncode, flush=True)
        p.check_returncode()

    try:
        run('mkdir', ssh + [shlex.join(['mkdir', '-p', remote])])
        run('sync', ['rsync', '-a', str(base / 'src') + '/', 'gpu5070ti:' + remote + '/src/'])
        gate = ('import pathlib,hashlib,json\n' + f'root=pathlib.Path({remote!r});expected={sources!r}\n'
                'actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}\n'
                'assert expected==actual\nprint(json.dumps({"all_match":True,"files":len(actual)}))\n')
        run('source_gate', ssh + ['python3 -'], gate)
        inner = ('set -e\nsource /opt/ros/foxy/setup.bash\ncd /workspace\n'
                 'colcon build --base-paths src --executor sequential --event-handlers console_direct+ '
                 '--cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF')
        command = ['podman', 'run', '--rm', '--pull=never', '--network=none',
                   '--name', 'vla-p2b-build-' + args.build_name,
                   '-e', 'CMAKE_BUILD_PARALLEL_LEVEL=3', '-e', 'MAKEFLAGS=-j3',
                   '-v', remote + ':/workspace', IMAGE, 'bash', '-lc', inner]
        run('build', ssh + [shlex.join(['timeout', '--kill-after=15', '600'] + command)], timeout=630)
        run('source_gate_after', ssh + ['python3 -'], gate)
        result = {'passed': True, 'image_id': IMAGE, 'source_matches_before_after': True,
                  'remote_workspace': remote, 'source_manifest': 'source_sha256.json',
                  'claim': 'Actual C++/ROS message build only; no controller or motion execution.'}
    except Exception as error:
        result = {'passed': False, 'image_id': IMAGE, 'error': str(error), 'remote_workspace': remote}
        raise
    finally:
        result.update(commands=commands, elapsed_wall_s=time.monotonic() - started)
        (base / 'build_result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(base / 'build_result.json')


if __name__ == '__main__':
    main()
