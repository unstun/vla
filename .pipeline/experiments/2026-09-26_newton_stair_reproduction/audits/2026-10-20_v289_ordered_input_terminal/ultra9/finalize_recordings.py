"""Collect the existing ten recordings after analysis; never launch physics."""
from pathlib import Path
import json
import os
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v289_20261020')
PYTHON = '/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python'


def main():
    receipt = ROOT / 'evidence/finalize_recordings01.json'
    assert not receipt.exists()
    row = dict(pid=os.getpid(), stage='waiting_for_analysis', physics_steps=0, steps=[])
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    while True:
        ready = ROOT / 'evidence/after_physics01.json'
        if ready.exists():
            state = json.loads(ready.read_text())
            if state.get('stage') == 'analysis_closed':
                assert state['returncode'] == 0, 'Inspect preserved analysis failure; no physical rerun'
                break
        time.sleep(20)
    for name in ('startup_audit.py', 'input_order_audit.py', 'collect_results.py', 'summarize_mechanisms.py'):
        row['stage'] = name
        receipt.write_text(json.dumps(row, indent=2) + '\n')
        log = ROOT / 'evidence' / (name[:-3] + '_final01.log')
        with log.open('x') as stream:
            code = subprocess.run(['nice', '-n', '10', PYTHON, str(ROOT / 'migration' / name)],
                stdout=stream, stderr=subprocess.STDOUT).returncode
        row['steps'].append(dict(name=name, returncode=code, log=str(log)))
        receipt.write_text(json.dumps(row, indent=2) + '\n')
        assert code == 0, (name, code)
    row.update(stage='closed', finished_utc_s=time.time())
    receipt.write_text(json.dumps(row, indent=2) + '\n')


if __name__ == '__main__':
    main()
