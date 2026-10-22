"""Extract actual terminal errors from closed recordings, without new physics."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v284'
sys.path.insert(0, str(VERSION.parent / 'v196'))
from analyze_remote import Capture


def main():
    rows = []
    for cid in json.loads((VERSION / 'manifest.json').read_text())['physical_cases']:
        raw = Path('/home/sun/vla_exec/physical_runs_v284') / f'v284_{cid}_attempt01/runs/v284_{cid}_attempt01'
        capture = Capture(raw)
        result = capture.json('result.json')
        log = capture.read('nav2.log')
        lines = log.splitlines()
        errors = [line for line in lines if '[ERROR]' in line]
        row = dict(case_id=cid, physics_duration_s=result['physics_duration_s'],
            physics_steps=result['physics_steps'], finish=result.get('finish_request'),
            planner_failure_lines=[line for line in lines if 'PCT plugin failed to plan' in line],
            final_error_lines=errors[-16:], error_line_count=len(errors),
            mission_error_lines=[line for line in errors if '[controller_server]:' in line or
                '[nav2_internal.bt_navigator]:' in line],
            refinement_error_count=log.count('Solver error while refining'),
            astar_optimization_failure_count=log.count('A-star failed; aborting optimization'),
            abort_handle_lines=[line for line in lines if 'Aborting handle' in line][-12:],
            sources=capture.sources,
            raw_manifest_sha256=hashlib.sha256((raw / 'raw_capture_manifest.json').read_bytes()).hexdigest())
        rows.append(row)
    out = HERE / 'results/failure_terminal_bill.json'
    if out.exists():
        previous = out.with_name('failure_terminal_bill_first_extract.json')
        assert not previous.exists()
        out.rename(previous)
    out.write_text(json.dumps(dict(physics_steps=0, actual_attempts=10,
        analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        execution_manifest_sha256=hashlib.sha256((VERSION / 'manifest.json').read_bytes()).hexdigest(),
        cases=rows), indent=2) + '\n')
    for row in rows:
        print(json.dumps(dict(case_id=row['case_id'], finish=row['finish']['backend_terminal_status'],
            final_errors=row['final_error_lines'][-4:]), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
