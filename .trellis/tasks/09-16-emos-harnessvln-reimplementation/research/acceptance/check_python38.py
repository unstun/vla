"""Lead-run, hash-gated Python 3.8 compatibility checks in the existing Foxy image."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[5]
SERVICE = '.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/navigation_service'
ACCEPTANCE = '.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance'
HOST = 'gpu5070ti'


def main():
    run_id = datetime.now(timezone.utc).strftime('python38_%Y%m%dT%H%M%SZ')
    out = ROOT / ACCEPTANCE / run_id
    out.mkdir()
    files = [SERVICE + '/' + name for name in ['__init__.py', 'core.py', 'test_core.py']]
    files.append(ACCEPTANCE + '/test_p2a_adversarial.py')
    source_bytes = {name: (ROOT / name).read_bytes() for name in files}
    expected = {name: hashlib.sha256(data).hexdigest() for name, data in source_bytes.items()}
    for name, data in source_bytes.items():
        snapshot = out / 'source_snapshot' / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
    (out / 'files.txt').write_text('\n'.join(files) + '\n')
    (out / 'source_sha256.json').write_text(json.dumps(expected, indent=2) + '\n')
    remote = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2a_qualification/' + run_id
    previous = ROOT / 'references/upstream/2026-09-16_lite3_isaac_harness_backend/validation/ros_transport_20260916T140123Z/result.json'
    image = json.loads(previous.read_text())['image_id']
    if not re.fullmatch(r'(sha256:)?[0-9a-f]{64}', image):
        raise RuntimeError('Invalid frozen image ID')
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', HOST]
    records = []
    result = {'passed': False, 'error': 'interrupted', 'commands': records}

    def run(command, label, stdin=None):
        p = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=120)
        (out / (label + '.log')).write_text(p.stdout + p.stderr)
        records.append({'label': label, 'command': command, 'exit_code': p.returncode})
        print(label, p.returncode, flush=True)
        if p.returncode:
            raise RuntimeError(label + ': ' + (p.stdout + p.stderr)[-2000:])
        return p

    try:
        run(ssh + [shlex.join(['mkdir', '-p', remote])], 'mkdir')
        run(['rsync', '-a', '--files-from=' + str(out / 'files.txt'), str(ROOT) + '/', HOST + ':' + remote + '/'], 'sync')
        check = ('import json,pathlib,hashlib,sys\n'
                 f'root=pathlib.Path({remote!r})\nexpected={expected!r}\n'
                 'actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}\n'
                 "print(json.dumps({'all_match':actual==expected,'files':actual},indent=2))\n"
                 'sys.exit(0 if actual==expected else 1)\n')
        run(ssh + ['python3 -'], 'source_gate', check)
        inner = ('set -e\nsource /opt/ros/foxy/setup.bash\npython3 --version\n'
                 f'python3 -m unittest discover -s /review/{SERVICE} -p test_core.py -v\n'
                 f'python3 /review/{ACCEPTANCE}/test_p2a_adversarial.py')
        cmd = ['podman', 'run', '--rm', '--pull=never', '--network=none',
               '--name', 'vla-' + run_id.lower(), '-e', 'PYTHONDONTWRITEBYTECODE=1',
               '-v', remote + ':/review:ro', image, 'bash', '-lc', inner]
        run(ssh + [shlex.join(cmd)], 'tests')
        run(ssh + ['python3 -'], 'source_gate_after', check)
        current = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
        if current != expected:
            raise RuntimeError('Local source changed during qualification')
        cleanup = run(ssh + [shlex.join(['podman', 'ps', '-a', '--filter',
                      'name=^vla-' + run_id.lower() + '$', '--format', '{{.Names}}'])], 'cleanup_check')
        if cleanup.stdout.strip():
            raise RuntimeError('Qualification container was not removed')
        result = {'passed': True, 'image_id': image, 'source_hashes_match': True,
                  'source_hashes_match_after_tests': True, 'local_source_unchanged': True,
                  'container_removed': True, 'source_snapshot': 'source_snapshot/',
                  'scope': 'actual Python 3.8 lifecycle/contract tests; no simulator or motion',
                  'commands': records}
    except Exception as error:
        result = {'passed': False, 'error': str(error), 'commands': records}
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
