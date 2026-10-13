"""Audit commanded stop versus body drift and stance entry from full telemetry."""
from pathlib import Path
import collections
import hashlib
import io
import json
import math
import sys

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'versions/v177'))
from analyze_remote import Capture
TASK=Path('/data/sun/vla_mppi_20261009')
tag='v177_full_candidate_attempt01'
c=Capture(TASK/'trials'/tag/'runs'/tag)
rows=c.rows('artifacts/reactive_observations.jsonl')

def moving(twist):return any(abs(twist[a][b])>1e-9 for a,b in [('linear','x'),('linear','y'),('angular','z')])
begin=next(r['clock_ns']/1e9 for r in rows if r['event']=='scan_cancel' and r['data']['generation']==4)
end=next(r['clock_ns']/1e9 for r in rows if r['event']=='raw_command' and r['data']['generation']>4
         and r['clock_ns']/1e9>begin and moving(r['data']['twist']))
gated=[r for r in rows if r['event']=='gated_command' and begin<=r['clock_ns']/1e9<end]
samples=[]
for line in io.StringIO(c.read('telemetry.jsonl')):
    r=json.loads(line)
    if begin<=r['physics_time_s']<=end:
        samples.append({k:r[k] for k in ('physics_time_s','stance_mode','stance_reason','policy_owns_joints',
            'effective_command','foot_forces_n','base_up_z','command','requested_command','command_reason','body_sensor')})
assert samples
after=[r for r in samples if r['physics_time_s']>=begin+.2]
modes=collections.Counter(r['stance_mode'] for r in after)
reasons=collections.Counter(r['stance_reason'] for r in after)
nonzero=[r for r in after if max(abs(v) for v in r['effective_command'])>1e-9]
zero=[r for r in after if max(abs(v) for v in r['effective_command'])<=1e-9]
failures=collections.Counter();start=None;maximum=0.0;max_dt=0.0
last=None
for r in after:
    t=r['physics_time_s'];body=r['body_sensor'];speed=math.sqrt(sum(x*x for x in body['linear_world']))
    angular=math.sqrt(sum(x*x for x in body['angular_world']));tilt=math.degrees(math.acos(max(-1,min(1,r['base_up_z']))))
    failure=('new_command' if max(abs(v) for v in r['effective_command'])>1e-3 else
             'linear_speed' if speed>.15 else 'angular_speed' if angular>.5 else
             'tilt' if tilt>10 else 'four_contact' if min(r['foot_forces_n'])<10 else 'none')
    failures[failure]+=1
    if last is not None:max_dt=max(max_dt,t-last)
    last=t
    if failure=='none':
        if start is None:start=t
        maximum=max(maximum,t-start)
    else:start=None
def brief(r):return {k:v for k,v in r.items() if k not in ('body_sensor',)}|{'position':r['body_sensor']['position']}
out={'run':tag,'begin_sim_s':begin,'end_sim_s':end,'duration_s':end-begin,
     'gated_command_samples':len(gated),'gated_nonzero_samples':sum(moving(r['data']) for r in gated),
     'telemetry_samples':len(samples),'exclude_first_s':.2,'mode_counts_after_exclusion':dict(modes),
     'reason_counts_after_exclusion':dict(reasons),'effective_nonzero_after_exclusion':len(nonzero),
     'effective_zero_after_exclusion':len(zero),'stance_gate_failure_counts':dict(failures),
     'maximum_observed_all_gates_dwell_s':maximum,'maximum_telemetry_interval_s':max_dt,
     'first':brief(samples[0]),'last':brief(samples[-1]),
     'zero_command_first':brief(zero[0]) if zero else None,'zero_command_last':brief(zero[-1]) if zero else None,
     'xy_displacement_m':math.dist(samples[0]['body_sensor']['position'][:2],samples[-1]['body_sensor']['position'][:2]),
     'zero_command_xy_displacement_m':math.dist(zero[0]['body_sensor']['position'][:2],zero[-1]['body_sensor']['position'][:2]) if zero else None,
     'sources':c.sources,'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
     'scope':'Recorded telemetry sampled at its original interval. Dwell calculation is a diagnostic sampled upper bound, not a new physical stop qualification.'}
path=TASK/'results/v177_stop_drift_detailed.json';path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('first','last','zero_command_first','zero_command_last','sources')}))
