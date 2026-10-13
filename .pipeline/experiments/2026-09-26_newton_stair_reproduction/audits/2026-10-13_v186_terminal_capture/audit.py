"""Check the prospective tail criterion on verified actual policy-input samples."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from analyze import analyze,groups

def audit(path,output):
 result=analyze(path,[]);plot=result.pop('plot')
 t=np.asarray(plot['time_s']);dt=np.diff(np.r_[t[0]-.02,t])
 speed=np.linalg.norm(np.array(plot['command'])[:,:2],axis=1)
 error=np.array([np.nan if x is None else x for x in plot['endpoint_error_m']])
 expired=np.array(plot['phase'])=='expired_endpoint'
 mask=expired&(speed>1e-6)&(speed<.1)&(error<.05)
 segments=[]
 for i,j in groups(mask):
  segments.append(dict(start_s=float(t[i]-dt[i]),end_s=float(t[j-1]),duration_s=float(dt[i:j].sum()),
   error_min_m=float(error[i:j].min()),error_max_m=float(error[i:j].max()),
   command_median_mps=float(np.median(speed[i:j])),samples=int(j-i)))
 bad=[r for r in segments if r['duration_s']>2.]
 events=[json.loads(x) for x in gzip.open(path/'events.jsonl.gz','rt')]
 cancellations=[r for r in events if r['event']=='scan_cancel']
 # Repeated cancel publications count once per complete owner and reason.
 unique={tuple(r['data'].get(k) for k in ('run_id','epoch','request_id','goal_id','route_id','command_id','generation','reason')) for r in cancellations}
 result['terminal_capture_acceptance']=dict(passed=not bad,criterion='expired spline, 0 < actual RL horizontal command < 0.1 m/s, endpoint error < 0.05 m, continuous duration > 2 s fails',
  max_tail_s=max([r['duration_s'] for r in segments],default=0.),tail_segments=segments,violations=bad,
  unique_cancellations=len(unique),cancel_reasons=[list(x) for x in sorted(unique,key=str)],
  phase_scope='Estimated from native curve origin minus observed yaw pauses, then matched to actual policy command values within 0.3 s. Not an exact controller clock replay.')
 output.mkdir(parents=True,exist_ok=False)
 with gzip.open(output/'plot.json.gz','wt') as f:json.dump(plot,f,separators=(',',':'))
 (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(run=result['source_run'],**result['terminal_capture_acceptance'])),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.input,a.output)
