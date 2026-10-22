"""Actual parent/candidate controllers over identical recorded inputs; no physics."""
from pathlib import Path
import csv,hashlib,json,os,subprocess,sys
import yaml
R=Path('/home/ubuntu/sun/vla_v291_20261022');OLD=Path('/home/ubuntu/sun/vla_v290_20261021');P=Path('/home/ubuntu/sun/vla_v289_20261020')
sys.path.insert(0,str(P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196'))
from analyze_remote import Capture
IMAGE='sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
report={'new_physics_steps':0,'cases':{},'claim':'Recorded 20 ms poses and splines are fixed; command differences are not counterfactual robot motion.'}
for case,limit,window in [('D07',108.,(107.4,107.8)),('CD12',116.,(115.1,115.18))]:
 c=Capture(OLD/f'physical_runs/v290_{case}_attempt01/runs/v290_{case}_attempt01');out=R/'captured'/case;out.mkdir(parents=True,exist_ok=False);events=[]
 fields=lambda p:[p['position'][k] for k in ['x','y','z']]+[p['orientation'][k] for k in ['x','y','z','w']]
 for i,row in enumerate(c.rows('artifacts/reactive_observations.jsonl')):
  ns,event,data=row['clock_ns'],row['event'],row['data']
  if ns>limit*1e9:continue
  if event=='pct_route':
   poses=data['poses'];values=[len(poses)]+[x for p in poses for x in fields(p['pose'])];events.append((ns,0,i,['G',ns]+values))
  elif event=='bspline':
   origin=data['start_time']['sec']*1000000000+data['start_time']['nanosec'];values=[data['traj_id'],origin,int(data['emergency_stop']),int(data['reverse_motion']),data['order'],len(data['pos_pts']),len(data['knots'])]+[p[k] for p in data['pos_pts'] for k in ['x','y','z']]+data['knots'];events.append((ns,1,i,['B',ns]+values))
 for i,row in enumerate(c.rows('telemetry.jsonl')):
  ns=round(row['physics_time_s']*1e9)
  if ns>limit*1e9:continue
  b=row['body_sensor'];values=b['position']+b['quaternion'][1:]+b['quaternion'][:1]+b['linear_body']+b['angular_body'];events.append((ns,2,i,['C',ns]+values))
 events.sort(key=lambda e:e[:3]);path=out/'events.txt';path.write_text(''.join(' '.join(map(str,e[3]))+'\n' for e in events))
 profile=yaml.safe_load(c.read('nav2_params.yaml'))['controller_server']['ros__parameters'];profile['SCAN']['native_worker_enabled']=False
 (out/'profile.yaml').write_text(yaml.safe_dump({'controller_server':{'ros__parameters':profile}}));rows={}
 for name,root in [('parent',OLD),('candidate',R)]:
  cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/capture/ros_home','-e','ROS_LOG_DIR=/capture/ros_logs','-v',str(root/'native')+':/work:ro','-v',str(root/'evaluation')+':/evaluation:ro','-v',str(P/'native/fixtures')+':/work/fixtures:ro','-v',str(out)+':/capture:rw','--entrypoint','/bin/bash',IMAGE,'-c','source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && export ROS_DOMAIN_ID=162 ROS_LOCALHOST_ONLY=1 TRACKING_INPUT=/capture/events.txt TRACKING_OUTPUT=/capture/'+name+'.csv && /evaluation/build/captured_tracking_probe --ros-args --params-file /capture/profile.yaml --log-level error']
  with (out/(name+'.log')).open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
  assert code==0,(case,name,code)
  rows[name]=list(csv.DictReader((out/(name+'.csv')).open()))
 paired=list(zip(rows['parent'],rows['candidate']));assert all(a['stamp_ns']==b['stamp_ns'] for a,b in paired) and len(rows['parent'])==len(rows['candidate'])
 selected=[(a,b) for a,b in paired if window[0]<=int(a['stamp_ns'])/1e9<=window[1]];assert selected
 check=all(float(b['speed_m_s'])==0 for a,b in selected) if case=='D07' else all(a['braking']=='1' and b['braking']=='0' and float(b['speed_m_s'])>0.01 for a,b in selected)
 assert check,(case,selected)
 report['cases'][case]={'sources':c.sources,'events':len(events),'events_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'controller_ticks':len(paired),'window_s':window,'window_passed':check,'window_samples':[{'t_s':int(a['stamp_ns'])/1e9,'parent':a,'candidate':b} for a,b in selected], 'csv_sha256':{name:hashlib.sha256((out/(name+'.csv')).read_bytes()).hexdigest() for name in rows}}
(R/'evidence/controller_replay01.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({case:{'ticks':x['controller_ticks'],'passed':x['window_passed']} for case,x in report['cases'].items()}))
