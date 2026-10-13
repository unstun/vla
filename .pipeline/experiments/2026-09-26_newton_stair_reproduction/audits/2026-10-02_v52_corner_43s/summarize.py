"""Summarize original corner records; bulk input and full timeline stay remote."""
from pathlib import Path
import json, math, collections
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'timeline_compact.json').read_text())
obs=r['observations'];raw=[x for x in obs if x['event']=='raw_command'];curves=[x for x in obs if x['event']=='bspline'];last=curves[-1];streak=[]
for e in reversed(curves):
    if abs(e['end_sim_s']-last['end_sim_s'])>1e-6:break
    streak.append(e)
zero=next(x for x in raw if x['clock_s']>=42.353 and all(x['data']['twist'][a][c]==0 for a,c in [('linear','x'),('linear','y'),('angular','z')]))
focused=[x for x in r['focused_rounds'] if 42.338<=x['ros_s']<=44.0]
for x in focused: x.pop('seeds',None)
endpoint=[last['last_point'][k] for k in ('x','y','z')]
a=r['applied_samples'][8];xyz=a['measured']['base_xyz'];q=a['measured']['base_quat_wxyz'];yaw=math.atan2(2*(q[0]*q[3]+q[1]*q[2]),1-2*(q[2]**2+q[3]**2))
summary=dict(run=r['run'],last_success=r['last_success'],first_persistent_failure=r['first_persistent_failure'],last_curve=last,same_end_curve_streak=streak,first_raw_zero=zero,focused_rounds=focused,applied_samples=r['applied_samples'],applied_reasons=r['applied_reasons'],route_events=[x for x in obs if x['event']=='pct_route'],admission_counts=dict((str(k),v) for k,v in collections.Counter((x['data']['consumer'],x['data']['status'],x['data']['message']) for x in obs if x['event']=='scan_admission' and x['clock_s']>=42.353).items()),late_start_offset=dict(sample_sim_s=a['sim_s'],planned_endpoint=endpoint,measured=xyz,xyz_error_m=math.dist(endpoint,xyz),xy_error_m=math.dist(endpoint[:2],xyz[:2]),measured_yaw_rad=yaw,query_yaw_rad=.73619696),raw_series=[dict(sim_s=x['clock_s'],speed_mps=math.hypot(x['data']['twist']['linear']['x'],x['data']['twist']['linear']['y']),yaw_radps=x['data']['twist']['angular']['z']) for x in raw])
(HERE/'corner_evidence.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(bytes=(HERE/'corner_evidence.json').stat().st_size,first_raw_zero_s=zero['clock_s'])))
