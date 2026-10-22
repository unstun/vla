"""Read-only compact status; never start or retry an execution."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sun/vla_exec/local_search_tracking_v285');RAW=Path('/home/sun/vla_exec/physical_runs_v285')
def read(p):
    try:return json.loads(p.read_text())
    except (FileNotFoundError,json.JSONDecodeError):return None
native=read(ROOT/'benchmark/native_ledger.json') or [];audits=read(ROOT/'benchmark/audit_ledger.json') or [];gate=read(ROOT/'benchmark/offline_gate.json')
print(json.dumps(dict(offline=dict(passed=gate['passed'],legal_passed=gate['positive_passed'],global_median_s=gate['global_median_s']) if gate else dict(native_finished=sum(r['state']=='finished' for r in native),audits=len(audits)))))
for name in ['execution_qualification01','authorized_continuation01','physical02_coordinator','after_physics01']:
    d=read(ROOT/(name+'.json'))
    if d:print(json.dumps(dict(coordinator=name,**{k:d.get(k) for k in ['stage','returncode','error']})))
closed=[]
for row in read(HERE/'results/physical_batch_status.json') or []:
    cid=row['case_id'];folder=RAW/f'v285_{cid}_attempt01/runs/v285_{cid}_attempt01';result=read(folder/'result.json')
    if row['stage']=='execution_closed_pending_analysis':
        closed.append(dict(case=cid,terminal=(result.get('finish_request') or {}).get('backend_terminal_status') if result else None,physics_s=result.get('physics_duration_s') if result else None,physics_steps=row.get('recorded_physics_steps')))
    else:
        output=dict(active_case=cid,stage=row['stage']);latest=read(folder/'backend_latest.json') or {};pose=latest.get('measurement_body_pose')
        if pose:output.update(physics_s=pose['stamp_ns']*1e-9,body=[pose[k] for k in ('x','y','z')])
        print(json.dumps(output))
print(json.dumps(dict(closed=closed)))
a=read(HERE/'results/analysis_batch_status.json')
if a:print(json.dumps(dict(analysis=a)))
