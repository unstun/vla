"""Execute the lead controller probe against one captured native SCAN build."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build_name')
    parser.add_argument('probe_name')
    args = parser.parse_args()
    for value in [args.build_name, args.probe_name]:
        if not value.replace('_', '').isalnum():
            raise ValueError('Unsafe name')
    build_dir = HERE / 'builds' / args.build_name
    build = json.loads((build_dir / 'build_result.json').read_text())
    if not build['passed']:
        raise RuntimeError('Unqualified build')
    out = build_dir / args.probe_name
    out.mkdir(exist_ok=False)
    probe = HERE / 'ros_controller_probe.py'
    (out / 'executed_probe.py').write_bytes(probe.read_bytes())
    remote = build['remote_workspace'] + '/' + args.probe_name
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'gpu5070ti']
    records = []

    def run(label, cmd, stdin=None):
        p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=120)
        (out / (label + '.log')).write_text(p.stdout + p.stderr)
        records.append({'label': label, 'command': cmd, 'exit_code': p.returncode})
        (out / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        print(label, p.returncode, flush=True)
        return p

    run('mkdir', ssh + [shlex.join(['mkdir', '-p', remote])]).check_returncode()
    run('sync', ['rsync', '-a', str(out / 'executed_probe.py'), 'gpu5070ti:' + remote + '/']).check_returncode()
    sha = hashlib.sha256(probe.read_bytes()).hexdigest()
    gate = ('import pathlib,hashlib\n' + f'p=pathlib.Path({remote!r})/"executed_probe.py"\n'
            + f'assert hashlib.sha256(p.read_bytes()).hexdigest()=={sha!r}\nprint("probe_source_match")\n')
    run('source_gate', ssh + ['python3 -'], gate).check_returncode()
    inner = ('set -e\nsource /opt/ros/foxy/setup.bash\nsource /workspace/install/setup.bash\n'
             'exec python3 /evidence/executed_probe.py --output /evidence/result')
    cmd = ['podman', 'run', '--rm', '--pull=never', '--network=none',
           '-e', 'ROS_DOMAIN_ID=95', '-e', 'ROS_LOCALHOST_ONLY=1', '-e', 'ROS_LOG_DIR=/evidence/ros_logs',
           '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', build['remote_workspace'] + ':/workspace:ro',
           '-v', remote + ':/evidence', build['image_id'], 'bash', '-lc', inner]
    executed = run('probe', ssh + [shlex.join(['timeout', '--kill-after=5', '60'] + cmd)])
    run('collect', ['rsync', '-a', 'gpu5070ti:' + remote + '/result/', str(out / 'result') + '/']).check_returncode()
    code = ('import pathlib,hashlib,json\n' + f'r=pathlib.Path({remote!r})/"result"\n'
            'print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob("*") if p.is_file()}))\n')
    raw = run('return_hashes', ssh + ['python3 -'], code)
    raw.check_returncode()
    expected = json.loads(raw.stdout)
    actual = {str(p.relative_to(out / 'result')): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (out / 'result').rglob('*') if p.is_file()}
    assert actual == expected
    (out / 'return_verdict.json').write_text(json.dumps({'matched': True, 'probe_exit_code': executed.returncode}, indent=2) + '\n')
    print((out / 'result/result.json').read_text())
    executed.check_returncode()


if __name__ == '__main__':
    main()
