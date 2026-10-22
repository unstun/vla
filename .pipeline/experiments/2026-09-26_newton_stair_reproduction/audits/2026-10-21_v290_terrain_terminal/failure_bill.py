"""Extract actual terminal errors from closed recordings, without new physics."""
from pathlib import Path
import hashlib
import json
import re
import sys
from collections import Counter

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v290'
sys.path.insert(0, str(VERSION.parent / 'v196'))
from analyze_remote import Capture


def error_counts(log):
    lines=log.splitlines()
    return dict(pool_exhaustion=sum('Ran out of pool' in l for l in lines),
        endpoint_adjustment_failed=sum('Unable to handle the initial or end point' in l for l in lines),
        astar_optimization_failed=sum('A-star failed' in l for l in lines),
        inside_obstacle=sum('The robot is inside an obstacle' in l for l in lines),
        lbfgs_minus1008=sum(bool(re.search(r'(?<![-\d])-1008(?!\d)', l)) for l in lines),
        minus1008_raw_substring_mentions=sum('-1008' in l for l in lines),
        no_executable_trajectory=sum('Native SCAN has no executable trajectory' in l for l in lines))

def stage_errors(log):
    lines=log.splitlines()
    return dict(rebound_minus1008=sum('Solver error. Return=-1008' in l for l in lines),
        refine_minus1008=sum('Solver error while refining: return=-1008' in l for l in lines),
        failed_to_make_progress=sum('Failed to make progress' in l for l in lines))


def reactive_counts(log):
    counts=Counter((int(a),int(b)) for a,b in re.findall(
        r'reactive_collision_blocked verdict=(\d+) voxel=(\d+)',log))
    return [dict(verdict=a,voxel=b,mentions=n) for (a,b),n in sorted(counts.items())]


def reference():
    rows=[]
    for cid in ('A04','G05','CU06','D07','S04','CD12','CM02','CM07','CS03','CE03'):
        raw=Path('/home/sun/vla_exec/physical_runs_v285')/f'v285_{cid}_attempt01/runs/v285_{cid}_attempt01'
        capture=Capture(raw);log=capture.read('nav2.log')
        rows.append(dict(case_id=cid,version='v285',counts=error_counts(log),reactive_blocked=reactive_counts(log),stage_errors=stage_errors(log),sources=capture.sources,
            raw_manifest_sha256=hashlib.sha256((raw/'raw_capture_manifest.json').read_bytes()).hexdigest()))
    out=HERE/'results/reference_v285_error_counts.json';out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(dict(physics_steps=0,cases=rows),f,indent=2)
    print(json.dumps(rows))

def first_error_contexts(lines):
    patterns=['Ran out of pool','Unable to handle the initial or end point','A-star failed',
        'The robot is inside an obstacle','-1008','Native SCAN has no executable trajectory']
    output={}
    for pattern in patterns:
        for i,line in enumerate(lines):
            if pattern in line and (pattern != '-1008' or re.search(r'(?<![-\d])-1008(?!\d)', line)):
                output[pattern]=dict(one_based_line=i+1,context=lines[max(0,i-2):i+3]);break
    return output

def main():
    rows = []
    for cid in json.loads((VERSION / 'manifest.json').read_text())['physical_cases']:
        raw = Path('/home/sun/vla_exec/physical_runs_v290') / f'v290_{cid}_attempt01/runs/v290_{cid}_attempt01'
        capture = Capture(raw)
        result = capture.json('result.json')
        log = capture.read('nav2.log')
        lines = log.splitlines()
        errors = [line for line in lines if '[ERROR]' in line]
        seed_rows=[dict(distance_m=float(m.group(1)),occupied=bool(int(m.group(2)))) for m in
            re.finditer(r'SCAN_MEASURED_SEED distance_m=([0-9.eE+-]+) occupied=([01])',log)]
        seed_audit=dict(count=len(seed_rows),distance_triggered=sum(r['distance_m']>.15 for r in seed_rows),
            occupancy_triggered=sum(r['occupied'] for r in seed_rows),
            maximum_predicted_distance_before_fallback_m=max((r['distance_m'] for r in seed_rows),default=None),
            examples=seed_rows[:8],claim='Actual FSM fallback decisions; not a reconstruction of the internal tracker phase')
        row = dict(case_id=cid, first_target_error_contexts=first_error_contexts(lines), target_errors=error_counts(log), reactive_blocked=reactive_counts(log), stage_errors=stage_errors(log), measured_seed_fallback=seed_audit, physics_duration_s=result['physics_duration_s'],
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
    reference() if '--reference-v285' in sys.argv else main()
