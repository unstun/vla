"""Wait for the owned ten-case batch, then analyze recorded states only."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/sun/vla_exec/local_search_tracking_v285')
PYTHON = '/home/sun/vla_exec/envs/newton_worker/bin/python'


def main():
    tag = os.environ.get('V285_ANALYSIS_ID','01')
    assert len(tag)==2 and tag.isdigit()
    receipt = ROOT / f'after_physics{tag}.json'
    assert not receipt.exists()
    row = dict(pid=os.getpid(), started_utc_s=time.time(), physics_steps=0,
               stage='waiting_for_physical_batch')
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    while True:
        coordinator = json.loads((ROOT / 'physical02_coordinator.json').read_text())
        if 'returncode' in coordinator:
            assert coordinator['returncode'] == 0, 'Physical dispatch failed; inspect without retry'
            break
        time.sleep(30)
    physical = json.loads((HERE / 'results/physical_batch_status.json').read_text())
    assert len(physical) == 10 and all(r['formal_attempt_started'] and
        r['stage'] == 'execution_closed_pending_analysis' for r in physical)
    row.update(stage='recorded_state_analysis', physical_attempts=10)
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    for name in ('postprocess_all.py', 'failure_bill.py', 'collect_physical.py','verify_delivery_remote.py'):
        subprocess.run([PYTHON, str(HERE / name)], check=True)
    row.update(stage='ready_for_compact_return', finished_utc_s=time.time())
    receipt.write_text(json.dumps(row, indent=2) + '\n')


if __name__ == '__main__':
    main()
