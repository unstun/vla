"""Compare measured boundary witnesses with the latest causal published curve.

Read-only recording analysis, zero physics. No reconstruction of tracker phase.
"""
from pathlib import Path
import os,sys,json,csv,math,subprocess
import numpy as np
from scipy.interpolate import BSpline
R=Path('/home/ubuntu/sun/vla_v287_20261020');E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction';A=E/'audits/2026-10-20_v287_local_cost_crash';V=E/'versions'
os.environ.setdefault('V287_CASE_ID','A04');sys.path[:0]=[str(R/'migration'),str(V/'v196')]
from analyze_remote import Capture
from analyze_case import bind_raw_oracle

def main():
 bind_raw_oracle()
 from registered_point_oracle import activate,margin
 activate();summaries=[]
 for case in json.loads((R/'cohort/cases_manifest.json').read_text())['physical_cases']:
  d=A/'physical'/case;f=d/'results/body_margins_with_raw.csv'
  if not f.exists():continue
  rows=list(csv.DictReader(f.open()));w=min(rows,key=lambda v:float(v['native_source_solid_margin_m']))
  if float(w['native_source_solid_margin_m'])>=0:continue
  out=d/'results/boundary_witness_audit.json';assert not out.exists()
  raw=R/'physical_runs'/f'v287_{case}_attempt01'/'runs'/f'v287_{case}_attempt01';capture=Capture(raw)
  t=float(w['time_s']);sensor=min(capture.rows('sensor.jsonl'),key=lambda v:abs(v['sim_time_s']-t))
  telemetry=capture.rows('telemetry.jsonl');body_wall=np.array([v['realtime_pacing']['wall_anchor_monotonic_s']+v['realtime_pacing']['wall_elapsed_s'] for v in telemetry]);body_times=np.array([v['physics_time_s'] for v in telemetry]);wall=float(np.interp(t,body_times,body_wall))
  sync=[v for v in capture.rows('clock_samples.jsonl') if v.get('accepted') and v.get('samples',0)>=500];remote=np.array([v['remote']/1e9 for v in sync]);offset=np.array([v['filtered_offset_ns']/1e9 for v in sync])
  events=[]
  for v in capture.rows('artifacts/reactive_observations.jsonl'):
   host=v['wall_monotonic_ns']/1e9;host+=float(np.interp(host,remote,offset))
   if host<=wall+1e-6 and v['clock_ns']/1e9<=t+1e-6:events.append(v)
  curves=[v for v in events if v['event']=='bspline'];commands=[v for v in events if v['event']=='gated_command']
  curve=curves[-1] if curves else None;command=commands[-1] if commands else None
  result=dict(case_id=case,physics_steps=0,measured_witness=w,body_pose=sensor['body_sensor'],latest_causal_command=command,latest_causal_curve=curve,
    claim='Latest published geometry and nearest spatial sample only; scaled internal tracker phase and actual curve execution are not reconstructed.')
  if curve and not curve['data'].get('emergency_stop',False):
   data=curve['data'];knots=np.array(data['knots']);q=np.array([[v['x'],v['y'],v['z']] for v in data['pos_pts']]);degree=int(data['order']);b=BSpline(knots,q,degree,extrapolate=False);u=np.linspace(knots[degree],knots[-degree-1],151);points=b(u);deriv=b.derivative()(u)
   duration=float(u[-1]-u[0]);ahead=b(np.minimum(u+.8,u[-1]))-points
   tangent=np.arctan2(deriv[:,1],deriv[:,0]);lookahead=np.arctan2(ahead[:,1],ahead[:,0]);lookahead[np.linalg.norm(ahead[:,:2],axis=1)<1e-9]=tangent[np.linalg.norm(ahead[:,:2],axis=1)<1e-9]
   body=np.array([float(w[k]) for k in ['x','y','z']]);index=int(np.argmin(np.linalg.norm(points-body,axis=1)))
   query=d/'boundary_curve_queries.txt'
   with query.open('x') as stream:
    for mode,yaws in enumerate([tangent,lookahead]):
     for i,(p,yaw) in enumerate(zip(points,yaws)):stream.write(' '.join(map(str,[mode*1000+i,*p,float(yaw)]))+'\n')
   shell='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && /audit/margin_build/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/boundary_curve_queries.txt /audit/results/boundary_curve_native_margins.csv $RAW_FIELD $RAW_FNV'
   subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=3g','-v',str(R/'native')+':/work:ro','-v',str(d)+':/audit:rw','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c',shell],check=True,stdout=subprocess.DEVNULL)
   checked=list(csv.DictReader((d/'results/boundary_curve_native_margins.csv').open()));nearest=[]
   for mode,yaws in enumerate([tangent,lookahead]):
    selected=checked[mode*len(points):(mode+1)*len(points)];item=selected[index];raw_margin=margin(points[index],float(yaws[index]))[0]
    nearest.append(dict(heading_mode='tangent' if mode==0 else '0.8s_lookahead',point=points[index].tolist(),yaw=float(yaws[index]),distance_to_body_m=float(np.linalg.norm(points[index]-body)),curve_parameter_s=float(u[index]),source_margin_m=float(item['native_source_solid_margin_m']),ENV_margin_m=float(item['solid_margin_m']),raw_margin_m=raw_margin,whole_curve_source_min_m=min(float(v['native_source_solid_margin_m']) for v in selected)))
   result.update(curve_duration_s=duration,curve_age_ros_s=t-curve['clock_ns']/1e9,nearest_spatial_samples=nearest)
  out.write_text(json.dumps(result,indent=2)+'\n');summaries.append(result);print(case,json.dumps(result.get('nearest_spatial_samples')),flush=True)
 (R/'evidence/boundary_witness_summary01.json').write_text(json.dumps(dict(physics_steps=0,cases=summaries),indent=2)+'\n')

if __name__=='__main__':main()
