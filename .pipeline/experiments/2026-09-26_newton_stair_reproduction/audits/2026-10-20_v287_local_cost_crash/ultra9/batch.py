"""Zero-step preflight barrier, then one physical recording for each selected case."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile

ROOT = Path('/home/ubuntu/sun/vla_v287_20261020')
MIGRATION = ROOT / 'migration'
VERSION = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v287'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)

def cases():
    return json.loads((ROOT / 'cohort/cases_manifest.json').read_text())['physical_cases']

def preflight():
    target = ROOT / 'evidence/physical_preflights01.json'
    assert not target.exists()
    rows = []
    for cid in cases():
        tag = os.environ.get('V287_PREFLIGHT_ID', '01')
        log = ROOT / 'evidence' / f'preflight_{cid}_{tag}.log'
        began = time.monotonic()
        with log.open('x') as stream:
            code = subprocess.run([sys.executable, str(MIGRATION / 'physical.py'), '--preflight-only'],
                env=dict(os.environ, V287_CASE_ID=cid, V287_PREFLIGHT_ID=tag),
                stdout=stream, stderr=subprocess.STDOUT, timeout=300).returncode
        row = dict(case_id=cid, tag=tag, exit_code=code, physics_steps=0,
            log_sha256=sha(log), wall_s=time.monotonic() - began)
        rows.append(row)
        save(ROOT / 'evidence/physical_preflight_progress.json', rows)
        print(json.dumps(row), flush=True)
        if code:
            raise SystemExit(code)
    save(target, dict(passed=True, cases=rows, physics_steps=0))

def recorded_steps(raw):
    path = raw / 'result.json'
    if path.exists():
        return json.loads(path.read_text())['physics_steps']
    archive = raw / 'raw_capture.zip'
    manifest = raw / 'raw_capture_manifest.json'
    if archive.exists() and manifest.exists():
        records = json.loads(manifest.read_text())['members']
        if 'result.json' in records:
            with zipfile.ZipFile(archive) as stream:
                data = stream.read('result.json')
            assert hashlib.sha256(data).hexdigest() == records['result.json']['sha256']
            return json.loads(data)['physics_steps']
    return None

def run():
    manifest = MIGRATION / 'physical_manifest01.json'
    identity = json.loads(manifest.read_text())
    assert identity['frozen'] and identity['authorized_attempts_per_case'] == 1
    returned = json.loads((ROOT / 'evidence/execution_local_return01.json').read_text())
    assert returned['physical_manifest_sha256'] == sha(manifest)
    assert identity['physical_cases'] == cases()
    status = ROOT / 'evidence/physical_batch_status.json'
    rows = json.loads(status.read_text()) if status.exists() else []
    with (ROOT / 'evidence/physical_batch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for cid in cases():
            row = next((r for r in rows if r['case_id'] == cid), None)
            ledger = ROOT / 'generalization_v287' / cid / 'execution/physical_launch_once.json'
            task = ROOT / 'physical_runs' / f'v287_{cid}_attempt01'
            if row and row.get('stage') == 'closed' and ledger.exists():
                continue
            assert not ledger.exists() and not task.exists(), 'Never retry an existing invocation; inspect recorded physics first'
            assert row is None
            row = dict(case_id=cid, state='starting', formal_attempt_started=False,
                manifest_sha256=sha(manifest), started_utc_s=time.time())
            rows.append(row)
            save(status, rows)
            log = ROOT / 'evidence' / f'physical_{cid}_attempt01.log'
            print(json.dumps(dict(case_id=cid, stage='starting')), flush=True)
            with log.open('x') as stream:
                code = subprocess.run([sys.executable, str(MIGRATION / 'physical.py')],
                    env=dict(os.environ, V287_CASE_ID=cid), stdout=stream, stderr=subprocess.STDOUT).returncode
            steps = recorded_steps(task / 'runs' / task.name)
            row.update(exit_code=code, physics_steps=steps, formal_attempt_started=bool(steps and steps > 0),
                stage='closed' if steps and steps > 0 and ledger.exists() else 'startup_failure',
                finished_utc_s=time.time(), log_sha256=sha(log))
            save(status, rows)
            print(json.dumps(row), flush=True)
            if row['stage'] != 'closed':
                raise SystemExit('No positive physical recording: retain startup failure, do not consume another route')
    save(ROOT / 'evidence/physical_batch_complete.json', dict(cases=10, attempts_per_case=1,
        positive_physics_recordings=10, all_closed=True, manifest_sha256=sha(manifest)))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('preflight', 'run'))
    dict(preflight=preflight, run=run)[p.parse_args().mode]()
