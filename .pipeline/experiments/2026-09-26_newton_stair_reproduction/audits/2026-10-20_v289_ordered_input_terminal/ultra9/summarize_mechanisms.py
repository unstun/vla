"""Read the closed recordings' new cost-descent and superseded-input witnesses."""
from pathlib import Path
import hashlib,json,math,re,sys
R=Path('/home/ubuntu/sun/vla_v289_20261020')
V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
sys.path.insert(0,str(V/'v196'))
from analyze_remote import Capture
assert json.loads((R/'evidence/physical_batch_complete.json').read_text())['all_closed']
cases=json.loads((R/'migration/physical_manifest01.json').read_text())['physical_cases']
rows=[]
for cid in cases:
    c=Capture(R/'physical_runs'/f'v289_{cid}_attempt01/runs/v289_{cid}_attempt01')
    lines=c.read('nav2.log').splitlines();ignored=[];restored=[]
    for i,line in enumerate(lines):
        m=re.search(r'ignored_older_body=(\d+)',line)
        if m:ignored.append((int(m[1]),i+1))
        m=re.search(r'LBFGS_RESTORED stage=(\w+) return=(-\d+) initial_cost=(\S+) best_cost=(\S+)',line)
        if m:
            stage,code,initial,best=m.groups();initial,best=float(initial),float(best)
            restored.append(dict(line=i+1,stage=stage,returncode=int(code),initial_cost=initial,best_cost=best,
                logged_cost_descended=math.isfinite(initial) and math.isfinite(best) and best<initial,
                equal_at_logged_precision=best==initial))
    terms=('regressed_body_source_stamp','body admission failed:','The robot is inside an obstacle',
        'A-star failed','Unable to handle the initial or end point','reactive_stair_seed_search_failed',
        'Native SCAN has no executable trajectory','Failed to make progress','native_node_unresponsive')
    witnesses={}
    for term in terms:
        hits=[(i+1,line) for i,line in enumerate(lines) if term in line]
        witnesses[term]=dict(count=len(hits),first=hits[0] if hits else None,last=hits[-1] if hits else None)
    rows.append(dict(case_id=cid,regressed_stamp_mentions=sum('regressed_body_source_stamp' in l for l in lines),
        any_body_admission_failure_mentions=sum('body admission failed:' in l for l in lines),
        max_recorded_gridmap_ignored_older=max((n for n,_ in ignored),default=0),
        ignored_counter_witness=max(ignored,default=(0,None)),negative_solver_recoveries=restored,
        indexed_log_witnesses=witnesses,sources=c.sources))
out=R/'physical_return/mechanism_witnesses.json'
assert not out.exists()
out.write_text(json.dumps(dict(cases=rows,analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    physics_steps=0,claim='Recorded GridMap counter is not the sum of GridMap and FSM drops. 12-digit logged cost equality cannot resolve a smaller double-precision descent. Geometry and dynamics admission are checked separately.'),indent=2)+'\n')
print('Closed-recording mechanism witnesses',len(rows))
