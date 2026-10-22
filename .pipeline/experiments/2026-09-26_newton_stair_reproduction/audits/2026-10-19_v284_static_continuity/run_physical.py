"""Resume unstarted cases only; one formal attempt per frozen selected route."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from watch_resources import sample

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v284'
BASE = Path('/data/sun/vla_mppi_20261009')
OUTPUT = Path('/home/sun/vla_exec/physical_runs_v284')
STATUS = HERE / 'results/physical_batch_status.json'


def resume_action(row, ledger_exists, task_exists):
    if ledger_exists:
        if row and row.get('stage') == 'execution_closed_pending_analysis':
            return 'skip_closed'
        raise RuntimeError('An existing formal ledger needs inspection; never retry it')
    if row and row.get('formal_attempt_started'):
        raise RuntimeError('Recorded formal attempt has no ledger; identity inconsistency')
    if task_exists:
        raise RuntimeError('A partial execution directory needs inspection; retain evidence')
    return 'start_unattempted'


def save(rows):
    temporary = STATUS.with_suffix('.tmp')
    temporary.write_text(json.dumps(rows, indent=2) + '\n')
    temporary.replace(STATUS)


def main():
    with (HERE / 'results/physical_batch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        freeze = json.loads((VERSION / 'manifest.json').read_text())
        assert freeze['frozen']
        cases = freeze['physical_cases']
        assert len(cases) == len(set(cases)) == 10
        rows = json.loads(STATUS.read_text()) if STATUS.exists() else []
        assert len({r['case_id'] for r in rows}) == len(rows)
        assert {r['case_id'] for r in rows} <= set(cases)
        for cid in cases:
            row = next((r for r in rows if r['case_id'] == cid), None)
            ledger = BASE / 'generalization_v284' / cid / 'execution/physical_launch_once.json'
            task = OUTPUT / f'v284_{cid}_attempt01'
            if resume_action(row, ledger.exists(), task.exists()) == 'skip_closed':
                continue
            if row is None:
                row = dict(case_id=cid, attempt=1, formal_attempt_started=False,
                    native_manifest_sha256=hashlib.sha256((VERSION / 'native_manifest.json').read_bytes()).hexdigest(),
                    execution_manifest_sha256=hashlib.sha256((VERSION / 'manifest.json').read_bytes()).hexdigest())
                rows.append(row)
            assert row['execution_manifest_sha256'] == hashlib.sha256((VERSION / 'manifest.json').read_bytes()).hexdigest()
            while True:
                resource = sample()
                row.update(stage='waiting_resources', resource_check=resource)
                save(rows)
                if not resource['passed']:
                    time.sleep(60)
                    continue
                resume_action(row, ledger.exists(), task.exists())
                row.update(stage='starting', started_utc_s=time.time())
                save(rows)
                number = next(n for n in range(1, 1000)
                    if not (BASE / f'v284_{cid}_launch_invocation{n:03d}.log').exists())
                log_path = BASE / f'v284_{cid}_launch_invocation{number:03d}.log'
                row['launch_log'] = str(log_path)
                save(rows)
                print(json.dumps(dict(case_id=cid, stage='starting', invocation=number)), flush=True)
                with log_path.open('x') as log:
                    code = subprocess.run([sys.executable, str(VERSION / 'launch.py')],
                        env=dict(os.environ, V284_CASE_ID=cid), stdout=log, stderr=subprocess.STDOUT).returncode
                started = ledger.exists()
                raw = task / 'runs' / task.name
                # The inherited ledger precedes episode validation. Do not
                # consume further routes after a known zero-physics rejection.
                entry_log = raw / 'run.log'
                if (entry_log.exists() and
                        entry_log.read_text().endswith('RuntimeError: Less than10GiB free\n') and
                        not (raw / 'episode_request.json').exists()):
                    row.update(stage='zero_physics_launch_rejection',
                        process_exit_code=code, finished_utc_s=time.time(),
                        formal_attempt_started=False)
                    save(rows)
                    raise RuntimeError(f'{cid}: pre-physics disk rejection; preserve and inspect')
                row.update(stage='execution_closed_pending_analysis' if started else 'not_started_preflight_failure',
                    process_exit_code=code, finished_utc_s=time.time(), formal_attempt_started=started)
                save(rows)
                print(json.dumps(row), flush=True)
                if started:
                    break
                if not task.exists() and 'Resource admission held:' in log_path.read_text():
                    time.sleep(60)
                    continue
                raise RuntimeError(f'{cid}: no formal attempt; inspect preserved preflight failure')


if __name__ == '__main__':
    main()
