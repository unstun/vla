"""Run the existing bridge transport tests in an isolated, CPU-only Foxy container."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent
HOST = 'gpu5070ti'
IMAGE = 'localhost/machine-dog-nav/foxy-scan:20260813'


def main():
    run_id = datetime.now(timezone.utc).strftime('ros_transport_%Y%m%dT%H%M%SZ')
    output = ROOT / 'validation' / run_id
    output.mkdir(parents=True)
    remote = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2a_qualification/' + run_id
    local = ROOT / 'source/machine-dog-nav/integration/lite3_sim_bridge'
    source = json.loads((ROOT / 'acquisition.json').read_text())
    expected = {name.removeprefix('integration/lite3_sim_bridge/'): digest for name, digest in source['sha256'].items()}
    for name, digest in expected.items():
        if hashlib.sha256((local / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Local frozen source drift: {name}')
    (output / 'source_sha256.json').write_text(json.dumps(expected, indent=2) + '\n')
    records = []
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', HOST]

    def run(command, label, data=None, timeout=120):
        result = subprocess.run(command, input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=timeout)
        (output / f'{label}.log').write_text(result.stdout)
        records.append({'label': label, 'command': command, 'exit_code': result.returncode})
        print(f'{label}: exit {result.returncode}', flush=True)
        if result.returncode:
            raise RuntimeError(f'{label}: {result.stdout[-3000:]}')
        return result.stdout

    try:
        run(ssh + [shlex.join(['mkdir', '-p', remote + '/bridge'])], 'mkdir')
        run(['rsync', '-a', '--exclude=__pycache__/', '--exclude=.pytest_cache/',
             str(local) + '/', f'{HOST}:{remote}/bridge/'], 'sync')
        code = ('import pathlib,hashlib,json,sys\n'
                f'root=pathlib.Path({(remote + "/bridge")!r})\n'
                f'expected={expected!r}\n'
                'actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}\n'
                "print(json.dumps({'all_match':actual==expected,'file_count':len(actual)}))\n"
                'sys.exit(0 if actual==expected else 1)\n')
        run(ssh + ['python3 -'], 'source_gate', data=code)
        image_id = run(ssh + [shlex.join(['podman', 'image', 'inspect', '--format', '{{.Id}}', IMAGE])], 'image_id').strip()
        if not re.fullmatch(r'(sha256:)?[0-9a-f]{64}', image_id):
            raise RuntimeError('Unexpected container image identity')
        inner = ('source /opt/ros/foxy/setup.bash\n'
                 "python3 -c 'import rclpy,sys; print(sys.version); print(rclpy.__file__)'\n"
                 'exec python3 -m unittest discover -s /bridge/tests -p test_transport.py -v')
        command = ['podman', 'run', '--rm', '--pull=never', '--network=none',
                   '--name', 'vla-' + run_id.lower(),
                   '-e', 'ROS_DOMAIN_ID=93', '-e', 'ROS_LOCALHOST_ONLY=1',
                   '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTHONPATH=/bridge',
                   '-v', remote + '/bridge:/bridge:ro', image_id, 'bash', '-lc', inner]
        raw = run(ssh + [shlex.join(command)], 'transport_tests')
        if 'test_foxy_bridge_publishes_dual_clouds_with_same_stamp_and_frame' not in raw or 'skipped' in raw:
            raise RuntimeError('The ROS-dependent test did not execute')
        result = {'passed': True, 'host': HOST, 'image_id': image_id, 'source_hashes_match': True,
                  'runtime_scope': 'real rclpy/Foxy bridge transport tests in isolated CPU container',
                  'network': 'none', 'source_mount': 'read-only', 'gpu_used': False,
                  'isaac_run': False, 'physical_actuation': False, 'commands': records}
    except Exception as error:
        result = {'passed': False, 'error': str(error), 'commands': records}
        raise
    finally:
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    main()
