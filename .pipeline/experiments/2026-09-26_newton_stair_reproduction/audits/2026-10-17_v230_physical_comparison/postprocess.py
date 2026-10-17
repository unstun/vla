"""Original full-route gate, closed archive proof and exact physical-window comparison."""
from pathlib import Path
import csv,hashlib,importlib.util,json,math,os,re,subprocess,sys,traceback,zipfile
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];VERSIONS=BASE/'versions'
sys.path.insert(0,str(VERSIONS/'v196'))
from analyze_remote import Capture,core
ROOT=Path('/data/sun/vla_mppi_20261009/trials');RUN='v231_linux_full_attempt01'
RAW=ROOT/RUN/'runs'/RUN;OUT=HERE/'results';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def summarize(raw):
 c=Capture(raw);sensor=c.rows('sensor.jsonl');telemetry=c.rows('telemetry.jsonl');log=c.read('nav2.log')
 class Log:
  def read_text(self):return log
 starts,rounds=core.parse_rounds(Log());done=[r for r in rounds if r.get('completed')]
 rr=[r for r in done if 45<=r.get('ros_s',-1)<55]
 bins=[{'start_s':s,'completed_rounds':sum(s<=r.get('ros_s',-1)<s+1 for r in done),
        'successful_rounds':sum(s<=r.get('ros_s',-1)<s+1 and bool(r['success']) for r in done)} for s in range(45,55)]
 crash_lines=[line for line in log.splitlines() if 'terminate called without an active exception' in line or ('controller_server' in line and 'process has died' in line)]
 last_live_time=None
 for line in log.splitlines():
  if 'reactive_collision_blocked' in line:
   m=re.search(r'\bnow=([0-9.]+)',line)
   if m:last_live_time=float(m.group(1))
 times=[r.get('physics_time_s',r.get('time_s')) for r in telemetry]
 end=max(times);window_reached=end>=45;covered=min(55.,end)-45. if window_reached else 0.
 pauses=[];begin=None;last=None
 for a,b in zip(sensor,sensor[1:]):
  dt=b['sim_time_s']-a['sim_time_s'];low=0<dt<.5 and math.hypot(*b['body_sensor']['linear_world'][:2])<.05
  if low:
   if begin is None:begin=a['sim_time_s']
   last=b['sim_time_s']
  elif begin is not None:
   if last-begin>=1:pauses.append({'start_s':begin,'end_s':last,'duration_s':last-begin})
   begin=None
 if begin is not None and last-begin>=1:pauses.append({'start_s':begin,'end_s':last,'duration_s':last-begin})
 overlaps=[dict(p,window_overlap_s=min(p['end_s'],55)-max(p['start_s'],45)) for p in pauses if min(p['end_s'],55)>max(p['start_s'],45)]
 part=[r for r,t in zip(telemetry,times) if 45<=t<55]
 from collections import Counter
 spatial=[r['sim_time_s'] for r in sensor if 6.7<=r['body_sensor']['position'][0]<=8.8 and -4.8<=r['body_sensor']['position'][1]<=-2.8 and 1.3<=r['body_sensor']['position'][2]<=2.3]
 report={'run':raw.name,'actual_physics_end_s':end,'window_reached':window_reached,'physical_recording_covers_window':end>=55,
 'window_coverage_s':max(0.,covered),'window_45_55':{'completed_rounds':len(rr) if window_reached else None,'successful_rounds':sum(bool(r['success']) for r in rr) if window_reached else None,
 'success_fraction':sum(bool(r['success']) for r in rr)/len(rr) if rr else None,'low_speed_pause_count':len(overlaps) if window_reached else None,'low_speed_pause_intervals':overlaps,
 'completed_rounds_by_start_second':bins,'last_completed_round_start_s':max((r.get('ros_s',-1) for r in rr),default=None),
 'incomplete_round_starts':[r.get('ros_s') for r in starts if not r.get('completed') and 45<=r.get('ros_s',-1)<55],
 'planning_continuity_qualified':not bool(crash_lines),'controller_crash_lines':crash_lines,
 'last_reactive_collision_ros_s':last_live_time,
 'pause_seconds_in_window':sum(p['window_overlap_s'] for p in overlaps) if window_reached else None,
 'stance_samples':dict(Counter(r['stance_mode'] for r in part)),'stance_reasons':dict(Counter(str(r.get('stance_reason')) for r in part))},
 'spatial_staircase_time_span_s':[min(spatial),max(spatial)] if spatial else None,
 'all_low_speed_intervals_over_1s':pauses,'route_deliveries':sum(e.get('event')=='pct_route' for e in c.rows('artifacts/reactive_observations.jsonl')),
 'feedback_messages':[s for s in log.splitlines() if 'pct_live_feedback session=' in s],
 'source':c.sources,'definitions':{'rounds':'completed nominal_replan rounds whose original ros_s starts in [45,55); internal seeds excluded; success fraction excludes missing rounds after a crash and cannot measure sustained planning availability','pause':'measured XY speed <0.05m/s, 0<dt<0.5s, whole interval >=1s; overlap with [45,55)','window_missing':'N/A when physics did not reach 45s; partial windows explicitly marked','crash_time':'last reactive collision ROS timestamp is a preceding observation, not the exact process-exit timestamp'}}
 tracks=HERE/'work';tracks.mkdir(exist_ok=True)
 with (tracks/(raw.name+'_poses.txt')).open('w') as f:
  for r in sensor:
   p=r['body_sensor']['position'];w,x,y,z=r['body_sensor']['quaternion'];yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
   f.write(' '.join(format(float(v),'.17g') for v in [r['sim_time_s'],*p,yaw])+'\n')
 return report

def main():
 env=dict(os.environ,PYTHONPATH=str(VERSIONS/'v196')+':'+os.environ.get('PYTHONPATH',''))
 with (OUT/'analysis.log').open('w') as log:
  result=subprocess.run([sys.executable,str(VERSIONS/'v196/analyze_remote.py'),'--run-root',str(RAW),'--output',str(OUT),'--metrics-only'],env=env,stdout=log,stderr=subprocess.STDOUT)
 save(OUT/'analysis_status.json',{'returncode':result.returncode,'analyzer_sha256':sha(VERSIONS/'v196/analyze_remote.py')})
 with (OUT/'full_route_gate.log').open('w') as log:
  gate=subprocess.run([sys.executable,str(VERSIONS/'v231/verify_full_route.py'),'--run-root',str(RAW)],env=env,stdout=log,stderr=subprocess.STDOUT)
 route=json.loads((RAW/'full_route_verification.json').read_text());save(OUT/'full_route_verification.json',route)
 c=Capture(RAW);actual=c.json('result.json');terminal=(actual.get('finish_request') or {}).get('backend_terminal_status')
 navlog=c.read('nav2.log')
 failure_lines=[line for line in navlog.splitlines() if 'terminate called without an active exception' in line or ('controller_server' in line and 'process has died' in line)]
 manifest=json.loads((RAW/'raw_capture_manifest.json').read_text());verified=0
 with zipfile.ZipFile(RAW/'raw_capture.zip') as archive:
  for name,record in manifest['members'].items():
   data=archive.read(name);assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'],name
   verified+=1
 outcome={'run':RUN,'navigation_source':'v230','execution_package':'v231','locomotion':'v216','full_route_gate_passed':bool(route['passed']),
 'overall_result':'PASSED' if route['passed'] else 'FAILED','process_failure':{'present':bool(failure_lines),'kind':'controller_server SIGABRT (-6)' if failure_lines else None,'evidence':failure_lines,'approximate_physics_s':46.7 if failure_lines else None,'display_marker_physics_s':47.0 if failure_lines else None,'time_definition':'Approximate from last reactive ROS observation 46.686s immediately before abort; display starts at47s. Exact exit physics timestamp was not recorded.'},
 'terminal_status':terminal or ('PHYSICAL_FALL' if actual.get('fallen') else 'BOUNDED_END'),'recorded_backend_terminal_status':terminal,'fallen':actual.get('fallen',False),'physics_duration_s':actual['physics_duration_s'],'physics_steps':actual['physics_steps'],
 'raw_root':str(RAW),'archive_sha256':sha(RAW/'raw_capture.zip'),'archive_bytes':(RAW/'raw_capture.zip').stat().st_size,'archive_members_verified':verified,
 'source_commits':{'v229':'420a0ff9','v230':'e9f8bec0'},'gate_returncode':gate.returncode,'analysis_returncode':result.returncode,
 'claim':'One original-start physical attempt; unchanged original gate. Failure remains failure. No repeated-reliability claim.'}
 save(OUT/'outcome.json',outcome)
 reports={name:summarize(ROOT/(name+'_linux_full_attempt01')/'runs'/(name+'_linux_full_attempt01')) for name in ('v219','v231')}
 save(OUT/'comparison.json',reports)
 print(json.dumps(outcome,indent=2));print(json.dumps({k:{x:v[x] for x in ('actual_physics_end_s','window_45_55','spatial_staircase_time_span_s')} for k,v in reports.items()},indent=2))
if __name__=='__main__':main()
