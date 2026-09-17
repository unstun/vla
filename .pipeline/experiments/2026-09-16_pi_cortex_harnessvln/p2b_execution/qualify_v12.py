"""Compare all pinned V12 runtime files locally and at the selected execution copy."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    base = ROOT / 'references/upstream/2026-09-11_lite3_v12_locomotion'
    expected = {}
    for line in (base / 'SHA256SUMS.txt').read_text().splitlines():
        sha, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != sha:
            raise RuntimeError('Local V12 source mismatch: ' + name)
        if name.startswith('source/v12_runtime/'):
            expected[name[len('source/v12_runtime/'):]] = sha
    code = ('import pathlib,hashlib,json,sys\n'
            'root=pathlib.Path("/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/source/v12")\n'
            f'expected={expected!r}\n'
            'actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() if (root/p).is_file() else None for p in expected}\n'
            'print(json.dumps({"matched":actual==expected,"file_count":len(expected),"mismatches":[p for p in expected if expected[p]!=actual[p]]},indent=2))\n'
            'sys.exit(0 if actual==expected else 1)\n')
    out = HERE / 'qualification' / datetime.now(timezone.utc).strftime('v12_%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True)
    attempts = []
    for attempt in range(1, 4):
        result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
                                 'gpu5070ti', 'python3 -'], input=code, text=True,
                                capture_output=True, timeout=90)
        (out / ('attempt_%d.log' % attempt)).write_text(result.stdout + result.stderr)
        attempts.append({'attempt': attempt, 'exit_code': result.returncode})
        if result.returncode == 0:
            verdict = json.loads(result.stdout)
            (out / 'result.json').write_text(json.dumps({'attempts': attempts, **verdict}, indent=2) + '\n')
            print(out, verdict, flush=True)
            return
        if result.returncode != 255:
            break
    (out / 'result.json').write_text(json.dumps({'attempts': attempts, 'matched': False}, indent=2) + '\n')
    raise RuntimeError('V12 qualification failed; raw attempts retained at ' + str(out))


if __name__ == '__main__':
    main()
