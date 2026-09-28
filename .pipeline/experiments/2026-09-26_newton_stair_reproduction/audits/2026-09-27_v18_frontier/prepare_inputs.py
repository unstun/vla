"""Freeze the actual v18 moving-stair stopping continuation inputs for native FSM/manager diagnosis."""
from pathlib import Path
import copy,hashlib,json,sys
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from scan_planner_msgs.msg import P2BRoute,Bspline
base=Path(sys.argv[1]);audit=Path(sys.argv[2]);out=audit/'inputs';out.mkdir(exist_ok=False)
run=base/'runs/v18_building_route01';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
obs=[json.loads(l) for l in (run/'artifacts/reactive_observations.jsonl').read_text().splitlines()]
route=next(x for x in obs if x['event']=='pct_route');spline=next(x for x in reversed(obs) if x['event']=='bspline' and x['clock_ns'] is not None and x['clock_ns']<=30000141144)
body=next(x for x in obs if x['event']=='body_pose_observer' and x['clock_ns'] is not None and x['clock_ns']>=30000141144);now=body['clock_ns']
assert now==30000141144
for name,record,cls in [('route',route,P2BRoute),('spline',spline,Bspline)]:
 msg=cls();set_message_fields(msg,copy.deepcopy(record['data']));(out/(name+'.cdr')).write_bytes(serialize_message(msg));(out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
def pose(path,p,q,v=(0,0,0),w=(0,0,0)):
 path.write_text(' '.join(format(float(x),'.17g') for x in [*p,q[1],q[2],q[3],q[0],*v,*w])+'\n')
clouds=[r for r in json.loads((run/'sensor_manifest.json').read_text()) if round(r['published_at_physics_s']*1e9)<=now]
lines=[];files=[]
for i,r in enumerate(clouds):
 p=run/r['file'];assert sha(p)==r['sha256']
 with np.load(p) as d:points=np.asarray(d['sensor_points'],dtype='<f4')
 filename=f'cloud_{i:03d}.f32';points.tofile(out/filename);files.append(filename);b=r['body_sensor']
 pose(out/f'body_{i:03d}.txt',b['position'],b['quaternion'],b['linear_body'],b['angular_body']);pose(out/f'sensor_{i:03d}.txt',b['sensor_position'],b['sensor_quaternion'])
 lines.append(f"{r['stamp_ns']} body_{i:03d}.txt sensor_{i:03d}.txt")
(out/'clouds.txt').write_text('\n'.join(files)+'\n');(out/'poses.txt').write_text('\n'.join(lines)+'\n')
(out/'body_pose.txt').write_bytes((out/'body_000.txt').read_bytes());(out/'sensor_pose.txt').write_bytes((out/'sensor_000.txt').read_bytes())
b=body['data'];p=b['pose']['pose']['position'];q=b['pose']['pose']['orientation'];t=b['twist']['twist'];pose(out/'final_body.txt',[p[k] for k in 'xyz'],[q[k] for k in 'wxyz'],[t['linear'][k] for k in 'xyz'],[t['angular'][k] for k in 'xyz']);(out/'final_clock.txt').write_text(str(now)+'\n')
parent=base/'audits/2026-09-27_v4_cause/replay_inputs';m=json.loads((parent/'input_manifest.json').read_text());assert sha(parent/'points.npz')==m['files']['points.npz']
with np.load(parent/'points.npz') as data:np.asarray(data['ground'],dtype='<f4').tofile(out/'ground.f32')
assert sha(out/'ground.f32') in (run/'pct_support.log').read_text()
(out/'last_progress.txt').write_text('1.789229282396\n');(out/'planner.yaml').write_bytes((run/'planner.yaml').read_bytes())
record={'source_run':run.name,'now_ns':now,'clouds':len(clouds),'last_cloud_stamp_ns':clouds[-1]['stamp_ns'],'last_spline_traj_id':spline['data']['traj_id'],'source_sha256':{str(p.relative_to(base)):sha(p) for p in [run/'artifacts/reactive_observations.jsonl',run/'sensor_manifest.json',run/'planner.yaml',parent/'points.npz']},'condition':'Original published scans up to actual recorded clock; paired original captured sensor/body states and original latest body message. No semantic actor data or altered timestamps. Restore previous accepted spline and unmodified original PCT route.','files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}}
(out/'input_manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ['now_ns','clouds','last_cloud_stamp_ns']},indent=2))
