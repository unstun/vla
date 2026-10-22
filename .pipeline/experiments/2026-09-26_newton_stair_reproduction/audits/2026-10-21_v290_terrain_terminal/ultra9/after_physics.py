"""Wait for the existing ten single attempts, then analyze recordings only."""
from pathlib import Path
import json
import os
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v290_20261021')
PYTHON = '/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python'

def main():
    receipt = ROOT / 'evidence/after_physics01.json'
    assert not receipt.exists()
    row = dict(pid=os.getpid(), stage='waiting_for_existing_physical_batch', physics_steps=0)
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    while not (ROOT / 'evidence/physical_batch_complete.json').exists():
        status_path=ROOT/'evidence/physical_batch_status.json'
        if not status_path.exists():
            time.sleep(5);continue
        status = json.loads(status_path.read_text())
        assert not any(r.get('stage') == 'startup_failure' for r in status), 'Inspect preserved zero-physics startup failure without retry'
        time.sleep(30)
    row['stage'] = 'closed_recording_analysis'
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    code = subprocess.run([PYTHON, str(ROOT / 'migration/analyze_all.py')]).returncode
    row.update(stage='analysis_closed', returncode=code, finished_utc_s=time.time())
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    raise SystemExit(code)

if __name__ == '__main__':
    main()
