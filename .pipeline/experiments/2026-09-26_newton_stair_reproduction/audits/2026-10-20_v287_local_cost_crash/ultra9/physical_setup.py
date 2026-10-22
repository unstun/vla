"""Prepare and freeze host-only bindings and the original physical input bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v287_20261020')
VERSION = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
MIGRATION = ROOT / 'migration'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    output = ROOT / 'evidence/physical_setup01.json'
    assert not output.exists()
    original = VERSION / 'v234/bin/docker'
    text = original.read_text()
    text = text.replace('HERE = Path(__file__).resolve().parents[1]', 'HERE = Path(' + repr(str(VERSION / 'v234')) + ')')
    old = "(PREFIX / 'evidence' / (name + '_adapter.json'))"
    assert text.count(old) == 1
    text = text.replace(old, '(Path(' + repr(str(ROOT / 'evidence')) + ") / (name + '_adapter.json'))")
    directory = MIGRATION / 'bin'
    directory.mkdir(exist_ok=False)
    (directory / 'docker').write_text(text)
    for name in ('ffmpeg', 'ffprobe'):
        shutil.copy2(VERSION / 'v234/bin' / name, directory / name)
    for path in directory.iterdir():
        path.chmod(0o755)
    input_inventory = json.loads((VERSION / 'v235/input_identity.json').read_text())['files']
    for rel, digest in input_inventory.items():
        assert sha(ROOT / 'repo' / rel) == digest, rel
    output.write_text(json.dumps(dict(passed=True, original_inputs=len(input_inventory),
        factory_adapter_source_sha256=sha(original), current_adapter_sha256=sha(directory / 'docker'),
        factory_bootstrap_read_only='/home/ubuntu/sun/vla_v234_20261017/bootstrap',
        adapter_receipts_redirected_to=str(ROOT / 'evidence'), physics_steps=0), indent=2) + '\n')

def freeze():
    target = MIGRATION / 'physical_manifest01.json'
    assert not target.exists()
    import offline02
    offline02.verify()
    gate = json.loads((ROOT / 'benchmark/offline_gate.json').read_text())
    assert gate['passed']
    cases = json.loads((ROOT / 'cohort/cases_manifest.json').read_text())['physical_cases']
    preflight = json.loads((ROOT / 'evidence/physical_preflights01.json').read_text())
    assert preflight['passed'] and [r['case_id'] for r in preflight['cases']] == cases
    assert all(r['exit_code'] == 0 and r['physics_steps'] == 0 for r in preflight['cases'])
    files = {}
    def add(path):
        files[str(path.relative_to(ROOT))] = sha(path)
    for rel, digest in json.loads((VERSION / 'v235/input_identity.json').read_text())['files'].items():
        path = ROOT / 'repo' / rel
        assert sha(path) == digest, rel
        add(path)
    for name in ('Dockerfile.debug', 'physical.py', 'batch.py', 'preflight.py', 'physical_setup.py',
                 'offline.py', 'offline02.py', 'native_manifest01.json', 'runtime_binding02.json'):
        add(MIGRATION / name)
    for directory in (MIGRATION / 'bin', ROOT / 'profile_reference', ROOT / 'bridge248/native/src', ROOT / 'bridge248/native/install'):
        for path in directory.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                add(path)
    for name in ('complete.json', 'offline_gate.json', 'matrix_summary.json', 'native_ledger.json', 'audit_ledger.json', 'selection.json'):
        add(ROOT / 'benchmark' / name)
    for name in ('physical_setup01.json', 'physical_preflights01.json', 'bridge248_01.json', 'current_geometry01.json'):
        add(ROOT / 'evidence' / name)
    result = dict(version='v287', frozen=True, host='ultra9', migration_only=False,
        navigation_source_changed=True, physical_cases=cases, authorized_attempts_per_case=1,
        hard_radius_m=.35, sensor_period_s=.1, debug_image='sha256:af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec', native_manifest_sha256=sha(VERSION / 'v287/native_manifest.json'),
        new_host_native_manifest_sha256=sha(offline02.MANIFEST), files=files, frozen_utc_s=time.time(),
        original_policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, manifest_sha256=sha(target), files=len(files))))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('prepare', 'freeze'))
    dict(prepare=prepare, freeze=freeze)[p.parse_args().mode]()
