"""Convert original observer messages/clouds to a deterministic ROS-message replay.
Observer receive order is retained; this is not a claim to reproduce native DDS drain order.
"""
from pathlib import Path
import hashlib,json,struct
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from nav_msgs.msg import Odometry
from scan_planner_msgs.msg import P2BRoute,Bspline
from sensor_msgs.msg import PointCloud2,PointField
BASE=Path('/archive');RUN=BASE/'runs/v50_realtime_trial01';OUT=Path('/attempt/replay');OUT.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rounds_path=Path('/profile/cases.json')
rounds=json.loads(rounds_path.read_text())
selected=[max((x for x in rounds if x['ros_s'] < 40),key=lambda x:x['wall_s']), max(rounds,key=lambda x:x['wall_s']), max((x for x in rounds if x['ros_s'] > 70),key=lambda x:x['wall_s'])]
selected.sort(key=lambda x:x['start_wall_s'])
obs=[json.loads(x) for x in (RUN/'artifacts/reactive_observations.jsonl').read_text().splitlines()]
sensors=[json.loads(x) for x in (RUN/'sensor.jsonl').read_text().splitlines()]
clouds={x['stamp_ns']:RUN/'clouds'/f"{x['sensor']['scan_window']['scan_index']:05d}.npz" for x in sensors}
sources={str(p.relative_to(BASE)):sha(p) for p in (RUN/'artifacts/reactive_observations.jsonl',RUN/'sensor.jsonl')}
sources['audits/2026-10-02_cold_tail_replay/cases.json']=sha(rounds_path)
case=0;counts={};last_wall=int(selected[-1]['start_wall_s']*1e9)
with (OUT/'events.bin').open('wb') as f:
 def put(kind,clock,payload):
  f.write(struct.pack('<BqI',kind,clock,len(payload)));f.write(payload);counts[kind]=counts.get(kind,0)+1
 for event in obs:
  wall=event['wall_monotonic_ns']
  while case<len(selected) and wall>=int(selected[case]['start_wall_s']*1e9):
   put(5,round(selected[case]['ros_s']*1e9),struct.pack('<I',case));case+=1
  if wall>=last_wall and case==len(selected):break
  clock=event.get('clock_ns');kind=event['event'];data=event['data']
  if clock is None:continue
  types={'body_pose_observer':(0,Odometry),'lidar_pose':(1,Odometry),'pct_route':(3,P2BRoute),'bspline':(4,Bspline)}
  if kind in types:
   tag,cls=types[kind];message=cls();set_message_fields(message,data);put(tag,clock,serialize_message(message))
  elif kind=='cloud':
   p=clouds[data['stamp_ns']];sources[str(p.relative_to(BASE))]=sha(p)
   points=np.asarray(np.load(p)['sensor_points'],dtype='<f4');m=PointCloud2();m.header.frame_id='lidar';m.header.stamp.sec=data['stamp_ns']//10**9;m.header.stamp.nanosec=data['stamp_ns']%10**9;m.height=1;m.width=len(points);m.point_step=12;m.row_step=12*len(points);m.is_dense=True
   m.fields=[PointField(name=name,offset=4*i,datatype=PointField.FLOAT32,count=1) for i,name in enumerate(('x','y','z'))];m.data=points.tobytes();put(2,clock,serialize_message(m))
assert case==len(selected)
identity={'source_files':sources,'cases':selected,'record_counts':counts,'events_sha256':sha(OUT/'events.bin'),'scope':'Paired deterministic replay of observer receive order, fixed per-case ROS clock, original messages and point arrays; native DDS take batching and original feasible-window hints are not reconstructed.'}
(OUT/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps({'cases':len(selected),'counts':counts,'bytes':(OUT/'events.bin').stat().st_size}))
