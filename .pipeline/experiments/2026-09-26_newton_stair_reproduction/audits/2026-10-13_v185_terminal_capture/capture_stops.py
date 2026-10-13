"""Identify zero-output plateaus consistent with local capture, not stillness proof."""
from pathlib import Path
import argparse,gzip,json
from bisect import bisect_right
import numpy as np
from analyze import prepare_curve,stamp

def inspect(folder):
 rows=[json.loads(x) for x in gzip.open(folder/'telemetry.jsonl.gz','rt')]
 events=[json.loads(x) for x in gzip.open(folder/'events.jsonl.gz','rt')]
 raw=sorted([r['data'] for r in events if r['event']=='raw_command'],key=lambda r:stamp(r['stamp']))
 times=[stamp(r['stamp']) for r in raw]
 curves={(r['data']['generation'],r['data']['traj_id']):r['data'] for r in events if r['event']=='bspline'}
 prepared={k:prepare_curve(d) for k,d in curves.items() if not d['emergency_stop']}
 groups=[];active=[];last_key=None
 def close():
  if not active:return
  a=active[0];b=active[-1];duration=b['time']-a['time']+.02
  if duration<.2:return
  c=prepared[a['key']];position=np.array([r['position'] for r in active]);errors=[r['error'] for r in active]
  groups.append(dict(generation=a['key'][0],trajectory=a['key'][1],start_s=a['time'],end_s=b['time'],duration_s=duration,
   first_error_m=errors[0],last_error_m=errors[-1],first_position=a['position'],last_position=b['position'],
   curve_length_m=float(c['distance'][-1]),endpoint=c['endpoint'].tolist(),
   zero_period_displacement_m=float(np.linalg.norm(position[-1,:2]-position[0,:2])),
   first_stance_mode=a['mode'],last_stance_mode=b['mode']))
 for row in rows:
  t=row['physics_time_s'];j=bisect_right(times,t)-1;match=None
  if j>=0 and t-times[j]<.3:
   d=raw[j];key=(d['generation'],d['traj_id']);c=prepared.get(key)
   rc=[d['twist']['linear'][k] for k in ['x','y']]+[d['twist']['angular']['z']]
   if max(abs(x) for x in row['effective_command'])<=1e-6 and max(abs(x) for x in rc)<=1e-6 and c and times[j]>c['start']+c['duration']:
    error=float(np.linalg.norm(np.array(row['position'])[:2]-c['endpoint']))
    if error<.05:match=dict(key=key,time=t,error=error,position=row['position'],mode=row['stance_mode'])
  if not match or match['key']!=last_key:close();active=[]
  if match:active.append(match);last_key=match['key']
  else:last_key=None
 close()
 return groups
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result={'scope':'Zero native output and actual RL input after curve expiry, within5cm. Consistent with local completion; excludes emergency splines. Not a capture-state or causal proof.','periods':inspect(a.input)}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
