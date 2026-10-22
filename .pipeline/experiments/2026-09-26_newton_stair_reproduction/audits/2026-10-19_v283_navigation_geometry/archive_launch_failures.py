"""Preserve five proven pre-physics rejections without counting formal attempts."""
from pathlib import Path
import hashlib
import json
import shutil
import time
from relocate_archive import inventory

HERE = Path(__file__).resolve().parent
BASE = Path('/data/sun/vla_mppi_20261009')
OUTPUT = Path('/home/sun/vla_exec/physical_runs_v283')
CASES = ['A04', 'G05', 'CU06', 'D07', 'S04']
RAW_FILES = {'request.json', 'retention_result.json', 'process.json',
             'entry_rebindings.json', 'run.log', 'executed_trial_entry.py'}


def main():
    status = HERE / 'results/physical_batch_status.json'
    out = HERE / 'results/recovery/zero_physics_launch_failures01'
    assert not out.exists()
    rows = json.loads(status.read_text())
    assert [r['case_id'] for r in rows] == CASES
    # Check all five before moving any directory. The traceback occurs before
    # source qualification, episode construction, simulator import or stepping.
    for cid in CASES:
        raw = OUTPUT / f'v283_{cid}_attempt01/runs/v283_{cid}_attempt01'
        assert {p.name for p in raw.iterdir()} == RAW_FILES
        log = (raw / 'run.log').read_text()
        assert log.endswith('RuntimeError: Less than10GiB free\n')
        assert 'executed_trial_entry.py", line 128, in main' in log
        assert json.loads((raw / 'process.json').read_text())['exit_code'] == 1
    out.mkdir(parents=True)
    shutil.copy2(status, out / 'original_batch_status.json')
    preserved = []
    for cid in CASES:
        task = OUTPUT / f'v283_{cid}_attempt01'
        target = OUTPUT / 'launch_failures01' / task.name
        evidence = BASE / 'generalization_v283' / cid / 'execution'
        archived = evidence.with_name('execution_launch_failure01')
        assert not target.exists() and not archived.exists()
        before = inventory(task)
        evidence_before = inventory(evidence)
        target.parent.mkdir(parents=True, exist_ok=True)
        task.rename(target)
        evidence.rename(archived)
        assert before == inventory(target)
        assert evidence_before == inventory(archived)
        case_out = out / cid
        case_out.mkdir()
        raw = target / 'runs' / target.name
        for name in RAW_FILES:
            shutil.copy2(raw / name, case_out / name)
        shutil.copytree(archived, case_out / 'execution')
        invocation = BASE / f'v283_{cid}_launch_invocation001.log'
        shutil.copy2(invocation, case_out / invocation.name)
        record = dict(case_id=cid, classification='zero_physics_launch_rejection',
            formal_attempt_started=False, physics_steps=0,
            proof='Exact pre-simulator disk-gate traceback and only six entry files',
            task_archive=str(target), execution_archive=str(archived),
            original_launch_log=str(invocation), task_inventory=before,
            execution_inventory=evidence_before)
        (case_out / 'preservation.json').write_text(json.dumps(record, indent=2) + '\n')
        preserved.append(record)
    result = dict(cases=CASES, count=5, physical_attempt_count=0,
        explanation='Old dispatch inferred formal start from a ledger written before episode validation; retain original status and reclassify from direct runtime evidence.',
        execution_manifest_sha256=hashlib.sha256((HERE.parents[1] / 'versions/v283/manifest.json').read_bytes()).hexdigest(),
        archived_utc_s=time.time(), all_content_hashes_verified=True)
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    status.rename(out / 'original_batch_status_moved.json')
    marker = HERE / 'results/resource_watch/stop_requested'
    if marker.exists():
        marker.rename(out / 'previous_resource_watch_stop_requested')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
