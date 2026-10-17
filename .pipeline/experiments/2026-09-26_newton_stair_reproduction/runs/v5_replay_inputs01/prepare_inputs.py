"""Format original recorded observations for the unchanged replay API."""
from pathlib import Path
import hashlib,importlib.util,json,pickle,shutil,sys
import numpy as np
base=Path(sys.argv[1]);out=Path(sys.argv[2]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write_inputs(target,events,points,config,provenance):
 target.mkdir(exist_ok=False)
 (target/'events.json').write_text(json.dumps(events)+'\n')
 if isinstance(points,Path): shutil.copyfile(points,target/'points.npz')
 else: np.savez_compressed(target/'points.npz',**points)
 shutil.copyfile(config,target/'planner.yaml')
 provenance.update(numpy_version=np.__version__,preparer_sha256=sha(Path(__file__)),files={p.name:sha(p) for p in target.iterdir()})
 (target/'input_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
def world_twist(item):
 q=np.asarray(item['quaternion']);q=q/np.linalg.norm(q);w=q[0];xyz=q[1:]
 for body,world in [('linear_body','linear'),('angular_body','angular')]:
  v=np.asarray(item[body]);c=2*np.cross(xyz,v);item[world]=(v+w*c+np.cross(xyz,c)).tolist()
 item['twist_schema']='world_and_body_v1'
audit=base/'audits/2026-09-27_v4_cause/replay_inputs';manifest=json.loads((audit/'input_manifest.json').read_text())
assert all(sha(audit/p)==v for p,v in manifest['files'].items())
events=json.loads((audit/'events.json').read_text())
for e in events:
 if e['kind']=='body':world_twist(e['data'])
for name,config in [('building_measured_fixed',audit/'planner.yaml'),('building_measured_height',base/'versions/v5/building_planner.yaml')]:
 write_inputs(out/name,events,audit/'points.npz',config,{'source_run':'v4_building_route01','source_manifest_sha256':sha(audit/'input_manifest.json'),'format_note':'Original body pose and body twist bytes retained; world-twist fields computed only to satisfy the existing replay dispatch predicate. assign_recorded_twist uses the original body vectors directly. Cloud/ground and route unchanged.'})
run=base/'runs/empty_long_root_live08';events=[];arrays={};limit=20.5e9
observations=run/'artifacts/reactive_observations.jsonl'
for record in map(json.loads,observations.read_text().splitlines()):
 if record['event']=='body_pose_observer':
  d=record['data'];stamp=d['header']['stamp']['sec']*10**9+d['header']['stamp']['nanosec']
  if stamp>limit:continue
  p=d['pose']['pose']['position'];q=d['pose']['pose']['orientation'];t=d['twist']['twist']
  item={'position':[p[k] for k in 'xyz'],'quaternion':[q[k] for k in 'wxyz'],'linear_body':[t['linear'][k] for k in 'xyz'],'angular_body':[t['angular'][k] for k in 'xyz']};world_twist(item)
  events.append({'stamp':stamp,'kind':'body','data':item})
 elif record['event']=='pct_route' and record['clock_ns']<=limit:
  events.append({'stamp':record['clock_ns'],'kind':'pct_route','data':record['data']})
for i,r in enumerate(json.loads((run/'sensor_manifest.json').read_text())):
 if r['stamp_ns']>limit:continue
 path=run/r['file'];assert sha(path)==r['sha256'];key=f'cloud_{i}'
 with np.load(path) as points:arrays[key]=points['sensor_points']
 sensor=r['body_sensor'];events.append({'stamp':r['stamp_ns'],'kind':'cloud','data':{'array':key,'position':sensor['sensor_position'],'quaternion':sensor['sensor_quaternion']}})
corepath=base/'references/pct_sim_clock_core.py';spec=importlib.util.spec_from_file_location('measured_replay_core',corepath);core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
with (run/'inputs/flat_floor.pickle').open('rb') as handle:arrays['ground']=core.selected_ground_points(pickle.load(handle))
events.sort(key=lambda e:(e['stamp'],{'body':0,'cloud':1,'pct_route':2}[e['kind']]))
write_inputs(out/'flat_measured',events,arrays,run/'planner.yaml',{'source_run':run.name,'end_at_recorded_physics_s':20.5,'source_files':{str(p.relative_to(base)):sha(p) for p in [observations,run/'sensor_manifest.json',run/'inputs/flat_floor.pickle',corepath]},'claim':'Original received body pose/twist, measured LiDAR and native PCT route. Partial recorded-input geometry check, not closed-loop physics acceptance.'})
print(json.dumps({name:len(json.loads((out/name/'events.json').read_text())) for name in ['building_measured_fixed','building_measured_height','flat_measured']},indent=2))
