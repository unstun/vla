"""Closed-recording analysis. Original full-route verifier and geometry oracles."""
from pathlib import Path
import csv,hashlib,importlib.util,json,math,os,re,subprocess,sys,time
import numpy as np
CAMPAIGN=Path('/home/ubuntu/sun/vla_v291_pair24_20261022');OLD=Path('/home/ubuntu/sun/vla_v290_20261021')
EXP=OLD/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction';VERSIONS=EXP/'versions'
ORIGINAL=EXP/'audits/2026-10-18_v240_gpu5070ti_physical/verify_full_route.py'
PROBES=EXP/'audits/2026-10-21_v290_terrain_terminal/physical/D07/margin_build'
IMAGE='sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
os.environ.setdefault('V290_CASE_ID','D07');sys.path[:0]=[str(CAMPAIGN/'source'),str(VERSIONS/'v196'),str(OLD/'migration')]
from analyze_remote import Capture
from stop_metrics import summarize as stop_summary
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def optional(capture,name,fallback):
 try:return capture.json(name)
 except (FileNotFoundError,KeyError):return fallback

def route_verify(raw,case,variant):
 scenario=OLD/'cohort/cases'/case/'scenario.json';code=ORIGINAL.read_text();before="    original_path = BASE / 'inputs/historical_full_building.json'\n    identity = json.loads((HERE / 'full_route_input.json').read_text())";assert code.count(before)==1
 code=code.replace(before,"    original_path = SCENARIO\n    identity = dict(json.loads(SCENARIO.read_text()),source_sha256=hashlib.sha256(SCENARIO.read_bytes()).hexdigest())").replace("'historical_full'","'generalization'").replace("'v241'",repr(variant))
 scope=dict(__file__=str(ORIGINAL),__name__='paired_original_route',SCENARIO=scenario);exec(compile(code,str(ORIGINAL),'exec'),scope)
 try:report=scope['verify'](raw)
 except Exception as error:report=dict(passed=False,error=repr(error))
 report.update(original_verifier_sha256=sha(ORIGINAL),executed_verifier_sha256=hashlib.sha256(code.encode()).hexdigest());return report

def base_metrics(slot):
 run=slot['run'];raw=CAMPAIGN/'physical_runs'/run/'runs'/run;out=CAMPAIGN/'analysis'/run;out.mkdir(parents=True,exist_ok=True);capture=Capture(raw)
 telemetry=capture.rows('telemetry.jsonl');scenario=capture.json('inputs/stair_scenario.json');driver=optional(capture,'artifacts/stair_driver_result.json',{});journal=driver.get('journal',[])
 goal=next((r for r in journal if r.get('event')=='goal_request'),None)
 video=optional(capture,'video_states.json',[])
 nav_start=goal['initial_snapshot']['sim_time_s'] if goal else next((r['physics_time_s'] for r in video if r.get('goal_sent')),None)
 route=route_verify(raw,slot['case_id'],slot['variant']);result=optional(capture,'result.json',None)
 activation=capture.json('locomotion_activation.json');expected='v291' if slot['variant']=='v291' else 'v216';assert activation['locomotion']==expected
 ends=[]
 for r in reversed(telemetry):
  if r.get('stance_mode')!='FIXED_STAND' or r.get('policy_owns_joints') is not False:break
  ends.append(r)
 pd_duration=ends[0]['physics_time_s']-ends[-1]['physics_time_s'] if ends else 0.
 target=scenario['goal_ground_xyz_m'];drift=stop_summary(telemetry,target,nav_start) if nav_start is not None else dict(terminal_seen=False,first=None,episodes=[],reason='goal not sent')
 def event_snapshot(row):
  w,x,y,z=row['body_sensor']['quaternion'];yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));error=scenario['goal_yaw_rad']-yaw
  return dict(t=row['physics_time_s'],goal_xy_error_cm=math.dist(row['body_sensor']['position'][:2],target[:2])*100,goal_yaw_error_deg=math.degrees(math.atan2(math.sin(error),math.cos(error))),linear_speed_mps=float(np.linalg.norm(row['joint_qd'][:3])),angular_speed_radps=float(np.linalg.norm(row['joint_qd'][3:6])),effective_command=row['effective_command'],mode=row['stance_mode'],reason=row.get('stance_reason'),foot_forces_n=row.get('foot_forces_n'),capture_mask=row.get('settling_contact_mask'))
 # Keep exact peaks and handoff points in the decimated plotting data.
 for episode in drift['episodes']:
  band=telemetry[episode['start_telemetry_row']-1:episode['end_telemetry_row']];anchor=band[0]['body_sensor']['position'][:2]
  distance=lambda r:math.dist(r['body_sensor']['position'][:2],anchor)*100
  peak=max(range(len(band)),key=lambda i:distance(band[i]));indices=set(range(0,len(band),5))|{0,len(band)-1,peak}
  indices.update(i for i in range(1,len(band)) if band[i]['stance_mode']!=band[i-1]['stance_mode'])
  for mode in ('STAND_TRANSITION','FIXED_STAND'):
   match=next((i for i,r in enumerate(band) if r['stance_mode']==mode),None)
   if match is not None:indices.add(match)
  episode['plot']=[dict(t=band[i]['physics_time_s'],cm=distance(band[i]),mode=band[i]['stance_mode']) for i in sorted(indices)]
  episode['initial_goal_error_cm']=math.dist(band[0]['body_sensor']['position'][:2],target[:2])*100
  episode['final_goal_error_cm']=math.dist(band[-1]['body_sensor']['position'][:2],target[:2])*100
  episode['start_state']=event_snapshot(band[0]);episode['end_state']=event_snapshot(band[-1])
  episode['restart_state']=event_snapshot(telemetry[episode['end_telemetry_row']]) if episode['command_restarted'] else None
  before=[r for r in telemetry[max(0,episode['start_telemetry_row']-120):episode['start_telemetry_row']-1] if r['physics_time_s']>=episode['start_s']-2]
  if before:
   episode['preceding_2s']=dict(samples=len(before),start_s=before[0]['physics_time_s'],end_s=before[-1]['physics_time_s'],start_state=event_snapshot(before[0]),end_state=event_snapshot(before[-1]),mean_command_xy_cm_s=sum(math.hypot(*r['effective_command'][:2])*100 for r in before)/len(before),net_xy_movement_cm=math.dist(before[0]['body_sensor']['position'][:2],before[-1]['body_sensor']['position'][:2])*100)
  for mode,key in [('STAND_TRANSITION','post_pd_entry'),('FIXED_STAND','post_fixed_stand')]:
   start=next((i for i,r in enumerate(band) if r['stance_mode']==mode),None)
   episode[key+'_max_cm']=None if start is None else max(math.dist(r['body_sensor']['position'][:2],band[start]['body_sensor']['position'][:2])*100 for r in band[start:])
 scan=capture.rows('scan_timing.jsonl');assert all(r['period_s']==.1 for r in scan)
 sensor=capture.rows('sensor.jsonl');handoff=optional(capture,'factory_handoff.json',None)
 relative_height=None
 if handoff and video:
  frame=min(video,key=lambda r:abs(r['physics_time_s']-handoff['physics_time_s']));relative_height=frame['joint_q'][2]-scenario['spawn_ground_xyz_m'][2]
 explicit=False
 if goal:explicit=goal['payload']['target_yaw_rad']==scenario['goal_yaw_rad']
 physical_finish=driver.get('final_snapshot',{}).get('sim_time_s') if driver.get('execution_completed') else None
 wall_elapsed=None
 if physical_finish is not None and nav_start is not None:
  t=np.array([r['physics_time_s'] for r in telemetry]);w=np.array([r['realtime_pacing']['wall_anchor_monotonic_s']+r['realtime_pacing']['wall_elapsed_s'] for r in telemetry]);assert np.all(np.diff(w)>0);wall_elapsed=float(np.interp(physical_finish,t,w)-np.interp(nav_start,t,w))
 report=dict(**slot,route=route,arrival_and_pd=bool(route['passed'] and pd_duration>=2 and explicit and relative_height is not None and relative_height>=.25),final_pd_duration_s=pd_duration,
  terminal=(result.get('finish_request') or {}).get('backend_terminal_status') if result else None,result_present=result is not None,
  original_body_telemetry_samples=len(telemetry),physics_end_s=telemetry[-1]['physics_time_s'],goal_sent=nav_start is not None,nav_start_s=nav_start,
  nav_complete_sim_s=None if physical_finish is None or nav_start is None else physical_finish-nav_start,nav_complete_wall_s=wall_elapsed,
  final_xy_error_m=math.dist(telemetry[-1]['body_sensor']['position'][:2],target[:2]),factory_relative_height_m=relative_height,
  requested_goal_heading_submitted=explicit,scanner_jobs=len(scan),scanner_deadline_failures=sum(bool(r.get('deadline_failed')) for r in scan),max_scan_ms=max((r['total_s']*1000 for r in scan if 'total_s' in r),default=None),
  actual_locomotion=activation,stop=drift,sources=capture.sources,analysis_sha256=sha(__file__),new_physics_steps=0)
 report['failed_scan_details']=[r for r in scan if r.get('deadline_failed')]
 report['native_process_failure']=optional(capture,'native_process_failure.json',None)
 report['shared_state']=optional(capture,'shared_state.json',None)
 report['retention']=optional(capture,'retention_result.json',None)
 report['recording_failure_kind']='scan_deadline' if report['scanner_deadline_failures'] else 'missing_result' if result is None else 'backend_failed' if report['terminal']=='FAILED' else None
 native_text=capture.read('nav2.log');event_pattern=re.compile(r'Failed to make progress|TerminalSettleTimeout|terminal_settle|Aborting handle|Reached the goal|Goal reached')
 report['native_event_lines']=[dict(line=i,text=line) for i,line in enumerate(native_text.splitlines(),1) if event_pattern.search(line) and len(line)<1000]
 report['progress_checker_failures']=native_text.count('Failed to make progress')
 transitions=[]
 for previous,row in zip(telemetry,telemetry[1:]):
  if drift.get('terminal_entry_s') is not None and row['physics_time_s']>=drift['terminal_entry_s'] and previous['stance_mode']!=row['stance_mode']:
   transitions.append(dict(t=row['physics_time_s'],before=previous['stance_mode'],after=row['stance_mode'],reason=row.get('stance_reason'),state=event_snapshot(row)))
 report['terminal_stance_transitions']=transitions
 report['terminal_pd_aborts']=sum(x['before']=='STAND_TRANSITION' and x['after']=='RL' for x in transitions)
 save(out/'metrics.json',report);return capture,report,out,sensor

def geometry(capture,out,sensor):
 from registered_point_oracle import margin
 factory=optional(capture,'factory_video_states.json',[])
 streams={'navigation_and_tail':[(r['sim_time_s'],r['body_sensor']['position'],r['body_sensor']['quaternion']) for r in sensor],
          'factory':[(r['physics_time_s'],r['joint_q'][:3],[r['joint_q'][6],*r['joint_q'][3:6]]) for r in factory]}
 reports={}
 for name,rows in streams.items():
  if not rows:reports[name]={'samples':0,'passed':False};continue
  query=out/(name+'_poses.txt');angles=[]
  with query.open('w') as f:
   for t,xyz,q in rows:
    w,x,y,z=q;a=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));angles.append(a);f.write(' '.join(map(str,[t,*xyz,a]))+'\n')
  shell='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && '
  shell+=f'/probes/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/{name}_poses.txt /audit/{name}_body.csv $RAW_FIELD $RAW_FNV && /probes/edge_diagnostic /audit/{name}_poses.txt > /audit/{name}_support.jsonl'
  cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=3g','-v',str(OLD/'native')+':/work:ro','-v',str(PROBES)+':/probes:ro','-v',str(out)+':/audit:rw','--entrypoint','/bin/bash',IMAGE,'-c',shell]
  with (out/(name+'_geometry.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
  native=list(csv.DictReader((out/(name+'_body.csv')).open()));support=[json.loads(s) for s in (out/(name+'_support.jsonl')).read_text().splitlines()];assert len(native)==len(support)==len(rows)
  raw=[margin(np.array(xyz),a)[0] for (_,xyz,_),a in zip(rows,angles)]
  for r,value in zip(native,raw):r['raw_point_margin_m']=value
  with (out/(name+'_all_margins.csv')).open('w') as f:
   writer=csv.DictWriter(f,fieldnames=list(native[0]));writer.writeheader();writer.writerows(native)
  mins={'support_gap_m':min(r['support_gap_extra_margin_m'] for r in support),'source_solid_m':min(float(r['native_source_solid_margin_m']) for r in native),'raw_point_m':min(raw)}
  reports[name]=dict(samples=len(rows),minimum=mins,passed=all(v>=-1e-10 for v in mins.values()),pose_sha256=sha(query),native_verdict_counts={str(v):sum(int(r['static_support_verdict'])==v for r in native) for v in {int(r['static_support_verdict']) for r in native}})
 value={'streams':reports,'passed':all(x['passed'] for x in reports.values()),'body_probe_sha256':sha(PROBES/'body_margin'),'support_probe_sha256':sha(PROBES/'edge_diagnostic'),'new_physics_steps':0,'scoring':'Original v290 whole-recorded physical envelope: support gap/source-solid/raw-point margins >=-1e-10, factory separately included; nominal-height verdict counts retained separately.'};save(out/'geometry.json',value);return value

def main():
 request=json.loads((CAMPAIGN/'source/request.json').read_text());slots=request['schedule'];status=json.loads((CAMPAIGN/'evidence/batch_status.json').read_text());closed={r['run'] for r in status if r['state']=='closed'}
 selected=[r for r in slots if r['run'] in closed]
 full='--full' in sys.argv
 if full:
  assert len(closed)==24,'Keep heavy audit out of the physical paired runs'
  from analyze_case import bind_raw_oracle
  binding=bind_raw_oracle();from registered_point_oracle import activate;activate();save(CAMPAIGN/'analysis/oracle_binding.json',binding)
 reports=[]
 for slot in selected:
  cached=CAMPAIGN/'analysis'/slot['run']/'metrics.json'
  if not full and cached.exists() and json.loads(cached.read_text()).get('analysis_sha256')==sha(__file__):
   reports.append(json.loads(cached.read_text()));continue
  c,r,out,sensor=base_metrics(slot)
  if full:
   g=geometry(c,out,sensor);r.update(geometry=g,success=bool(r['arrival_and_pd'] and g['passed']));r['sources']=c.sources;save(out/'summary.json',r)
  reports.append(r);print(json.dumps({'run':slot['run'],'arrival_pd':r['arrival_and_pd'],'first_drift_cm':(r['stop'].get('first') or {}).get('max_displacement_cm'),'success':r.get('success')}),flush=True)
 save(CAMPAIGN/'analysis'/('summary.json' if full else 'preliminary.json'),dict(new_physics_steps=0,full_geometry=full,runs=reports))
if __name__=='__main__':(CAMPAIGN/'analysis').mkdir(exist_ok=True);main()
