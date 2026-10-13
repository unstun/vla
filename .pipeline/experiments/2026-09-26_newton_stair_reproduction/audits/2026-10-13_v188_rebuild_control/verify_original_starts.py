"""Verify actual frame-zero position/yaw and selected route for every attempt."""
from pathlib import Path
import argparse,hashlib,json,math,zipfile

def read(root,name):
 manifest=json.loads((root/'raw_capture_manifest.json').read_text())
 if (root/name).exists():
  trial=root.parent.parent;task=trial.parent.parent;tag=root.name;version=tag.split('_')[0]
  closed=json.loads((task/f'results/{version}_full_repeats'/tag/'remote_artifacts.json').read_text())
  expected=closed['files'][f'runs/{tag}/{name}'];data=(root/name).read_bytes()
 else:
  expected=manifest['members'][name]
  with zipfile.ZipFile(root/'raw_capture.zip') as z:data=z.read(name)
 assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],name
 return json.loads(data),expected
p=argparse.ArgumentParser();p.add_argument('--task',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
base=a.task/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction';source=base/'inputs/historical_full_building.json';original=json.loads(source.read_text());results=[]
for version,attempts in [('v177',range(6,11)),('v185',range(1,6)),('v186',range(1,6)),('v187',range(1,6)),('v188',range(1,6))]:
 for n in attempts:
  tag=f'{version}_full_candidate_attempt{n:02d}';root=a.task/'trials'/tag/'runs'/tag
  request,rp=read(root,'episode_request.json');initial,ip=read(root,'initial_state.json');scenario,sp=read(root,'inputs/stair_scenario.json');video,vp=read(root,'video_states.json')
  assert request['integration_version']==version and request['scene']=='building_full' and request['building_route_profile']=='historical_full'
  assert request['startup_mode']=='factory_pd'
  for key in ['spawn_ground_xyz_m','spawn_yaw_rad','goal_ground_xyz_m']:assert scenario[key]==original[key]
  f=initial['frame'];assert initial['physics_steps']==0 and f['physics_time_s']==0.0 and video[0]==f
  expected=list(original['spawn_ground_xyz_m']);expected[2]+=.14
  assert max(abs(x-y) for x,y in zip(f['joint_q'][:3],expected))<1e-5
  x,y,z,w=f['joint_q'][3:7];yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));error=yaw-original['spawn_yaw_rad'];error=math.atan2(math.sin(error),math.cos(error));assert abs(error)<1e-5
  results.append({'run':tag,'passed':True,'actual_initial_xyz':f['joint_q'][:3],'yaw_error_rad':error,'video_frames':len(video),'sources':{'request':rp,'initial':ip,'scenario':sp,'video':vp}})
r={'passed':True,'runs':results,'original_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'claim':'Actual original spatial frame zero and unchanged requested route. A failed attempt is not a completed route.'};a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'runs':len(results)}))
