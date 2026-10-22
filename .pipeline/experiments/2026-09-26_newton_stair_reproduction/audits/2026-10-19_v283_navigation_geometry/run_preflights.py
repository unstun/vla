"""Resume only zero-step preflights; retain every unsuccessful invocation."""
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time
from watch_resources import sample

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v283'
BASE = Path('/data/sun/vla_mppi_20261009/generalization_v283')
OUTPUT = Path('/home/sun/vla_exec/physical_runs_v283')


def main():
    status = HERE / 'results/preflight_batch_status.json'
    with (HERE / 'results/preflight_batch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        selected = json.loads((VERSION / 'selection.json').read_text())['selected']
        for item in selected:
            case = item['case_id']
            out = BASE / case
            out.mkdir(parents=True, exist_ok=True)
            receipt = out / 'preflight_passed.json'
            if receipt.exists():
                assert json.loads(receipt.read_text())['passed']
                continue
            while True:
                resources = sample()
                row = dict(case_id=case, stage='checking_resources', resources=resources)
                status.write_text(json.dumps(row, indent=2) + '\n')
                if not resources['passed']:
                    time.sleep(60)
                    continue
                tag = next(f'{i:02d}' for i in range(1, 100)
                           if not (out / f'preflight_invocation_{i:02d}.log').exists()
                           and not (out / f'preflight_steps_{i:02d}.json').exists()
                           and not (out / ('deadline_tests.log' if i == 1 else f'deadline_tests_{i:02d}.log')).exists()
                           and not (OUTPUT / f'v283_{case}_preflight{i:02d}').exists())
                row.update(stage='zero_step_preflight', tag=tag)
                status.write_text(json.dumps(row, indent=2) + '\n')
                with (out / f'preflight_invocation_{tag}.log').open('x') as log:
                    code = subprocess.run([sys.executable, str(VERSION / 'preflight_runner.py')],
                        env=dict(os.environ, V283_CASE_ID=case, V283_PREFLIGHT_ID=tag),
                        stdout=log, stderr=subprocess.STDOUT).returncode
                row.update(exit_code=code, finished_utc_s=time.time())
                status.write_text(json.dumps(row, indent=2) + '\n')
                if code == 0:
                    assert json.loads(receipt.read_text())['passed']
                    print(json.dumps(row), flush=True)
                    break
                graph = out / ('graph.log' if tag == '01' else f'graph_{tag}.log')
                if graph.exists() and 'Resource admission held:' in graph.read_text():
                    time.sleep(60)
                    continue
                raise RuntimeError(f'{case} preflight {tag} failed; inspect preserved logs')
        status.write_text(json.dumps(dict(stage='all_zero_step_preflights_passed',
            cases=[x['case_id'] for x in selected], physics_steps=0, utc_epoch_s=time.time()), indent=2) + '\n')


if __name__ == '__main__':
    main()
