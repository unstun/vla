"""Analyze and render two closed recordings at a time, without new physics."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path('/home/ubuntu/sun/vla_v290_20261021')
MIGRATION = ROOT / 'migration'
AUDIT = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-21_v290_terrain_terminal'
STOP = threading.Event()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def resources():
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    gpu = [int(line.strip()) for line in subprocess.check_output(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True).splitlines()]
    return available >= 8 * 1024**3 and min(gpu) >= 2048 and shutil.disk_usage(ROOT).free >= 10 * 1024**3

def process(cid):
    result = AUDIT / 'physical' / cid / 'results'
    if (result / 'local_video_delivery.json').exists():
        data = json.loads((result / 'local_video_delivery.json').read_text())
        assert sha(Path(data['video'])) == data['sha256']
        return dict(case_id=cid, passed=True, already_delivered=True, physics_steps=0)
    while not resources():
        if STOP.is_set():
            return dict(case_id=cid, skipped=True, physics_steps=0)
        time.sleep(30)
    for name in ('analyze_case.py', 'render_case.py'):
        if STOP.is_set():
            return dict(case_id=cid, skipped=True, physics_steps=0)
        number = next(n for n in range(1, 100) if not (ROOT / 'evidence' / f'{name[:-3]}_{cid}_{n:02d}.log').exists())
        log = ROOT / 'evidence' / f'{name[:-3]}_{cid}_{number:02d}.log'
        with log.open('x') as stream:
            code = subprocess.run(['nice', '-n', '10', sys.executable, str(MIGRATION / name)],
                env=dict(os.environ, V290_CASE_ID=cid, V290_RENDER_ID=f'{number:02d}'), stdout=stream, stderr=subprocess.STDOUT).returncode
        if code:
            STOP.set()
            return dict(case_id=cid, passed=False, stage=name, exit_code=code, log=str(log), physics_steps=0)
    return dict(case_id=cid, passed=True, physics_steps=0)

def main():
    complete = json.loads((ROOT / 'evidence/physical_batch_complete.json').read_text())
    assert complete['all_closed'] and complete['positive_physics_recordings'] == 10
    manifest = json.loads((MIGRATION / 'physical_manifest01.json').read_text())
    cases = manifest['physical_cases']
    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(process, cid): cid for cid in cases}
        for future in as_completed(jobs):
            try:
                row = future.result()
            except Exception as error:
                STOP.set()
                row = dict(case_id=jobs[future], passed=False, error=repr(error), physics_steps=0)
            rows.append(row)
            (ROOT / 'evidence/analysis_batch_status.json').write_text(json.dumps(rows, indent=2) + '\n')
            print(json.dumps(row), flush=True)
    assert len(rows) == 10 and all(r.get('passed') for r in rows), rows

if __name__ == '__main__':
    main()
