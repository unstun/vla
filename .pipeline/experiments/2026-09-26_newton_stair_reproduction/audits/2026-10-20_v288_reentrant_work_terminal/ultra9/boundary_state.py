"""Read actual control/stance ownership at first and worst recorded crossings."""
from pathlib import Path
import sys,json,csv,math,hashlib
R=Path('/home/ubuntu/sun/vla_v288_20261020');E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction';A=E/'audits/2026-10-20_v288_reentrant_work_terminal'
sys.path.insert(0,str(E/'versions/v196'))
from analyze_remote import Capture

def main():
 cohort=json.loads((R/'cohort/cases_manifest.json').read_text());summaries=[]
 for case in cohort['physical_cases']:
  d=A/'physical'/case;f=d/'results/body_margins_with_raw.csv';rows=list(csv.DictReader(f.open()));negative=[v for v in rows if float(v['native_source_solid_margin_m'])<0]
  if not negative:continue
  c=Capture(R/'physical_runs'/f'v288_{case}_attempt01'/'runs'/f'v288_{case}_attempt01');telemetry=c.rows('telemetry.jsonl');states=[]
  goal=next(v['goal'] for v in cohort['cases'] if v['case_id']==case)
  for name,w in [('first',negative[0]),('worst',min(negative,key=lambda v:float(v['native_source_solid_margin_m'])))]:
   t=float(w['time_s']);v=min(telemetry,key=lambda v:abs(v['physics_time_s']-t));yaw=float(w['yaw'])
   fields={k:v[k] for k in ['physics_time_s','controller_phase','stance_mode','stance_reason','policy_owns_joints','effective_command','command','requested_command','command_stale','command_reason','body_sensor']}
   fields.update(kind=name,margin_row=w,speed_xy_mps=math.hypot(*v['body_sensor']['linear_world'][:2]),goal_xy_distance_m=math.hypot(float(w['x'])-goal['ground'][0],float(w['y'])-goal['ground'][1]),goal_yaw_error_rad=math.atan2(math.sin(yaw-goal['yaw']),math.cos(yaw-goal['yaw'])))
   states.append(fields)
  result=dict(case_id=case,physics_steps=0,states=states,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),claim='Actual recorded mode/command at first/worst sampled crossing; temporal association is not proof of the first causal error.')
  (d/'results/boundary_state_audit.json').write_text(json.dumps(result,indent=2)+'\n');summaries.append(result)
  print(case,[{k:v[k] for k in ['kind','physics_time_s','stance_mode','effective_command','speed_xy_mps','goal_xy_distance_m','goal_yaw_error_rad']} for v in states],flush=True)
 (R/'evidence/boundary_state_summary01.json').write_text(json.dumps(dict(physics_steps=0,cases=summaries),indent=2)+'\n')
if __name__=='__main__':main()
