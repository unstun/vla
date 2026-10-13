"""Serialize original observed inputs for a fixed-clock native AStar probe."""
from pathlib import Path
import copy
import hashlib
import io
import json
import struct
import zipfile
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2, PointField

BASE = Path('/archive')
HERE = Path('/profile')
OUT = Path('/attempt')


def prepare(run_name):
    run = BASE/'runs'/run_name
    archive = zipfile.ZipFile(run/'raw_capture.zip')
    sources = {}
    def read(name):
        p = run/name
        data = p.read_bytes() if p.is_file() else archive.read(name)
        sources[name] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        return data
    obs = [json.loads(s) for s in read('artifacts/reactive_observations.jsonl').splitlines()]
    sensors = [json.loads(s) for s in read('sensor.jsonl').splitlines()]
    clouds = {p['stamp_ns']:f"clouds/{p['sensor']['scan_window']['scan_index']:05d}.npz" for p in sensors}
    cases = json.loads((HERE/(run_name+'_cases.json')).read_text())
    target = OUT/(run_name+'.bin')
    counts = {}
    cursor = 0
    with target.open('xb') as stream:
        def put(kind, clock, payload):
            stream.write(struct.pack('<BqI',kind,clock,len(payload)))
            stream.write(payload)
            counts[kind] = counts.get(kind,0)+1
        def probe():
            row=cases[cursor]
            put(5,round(row['sim_s']*1e9),struct.pack('<I6d',cursor,*row['start'],*row['goal']))
        for event in obs:
            while cursor<len(cases) and event['wall_monotonic_ns']>=cases[cursor]['wall_s']*1e9:
                probe();cursor+=1
            if cursor==len(cases):break
            clock=event.get('clock_ns')
            if clock is None:continue
            kind=event['event'];data=event['data']
            if kind in ('body_pose_observer','lidar_pose'):
                msg=Odometry();set_message_fields(msg,copy.deepcopy(data))
                put(0 if kind=='body_pose_observer' else 1,clock,serialize_message(msg))
            elif kind=='cloud':
                xyz=np.asarray(np.load(io.BytesIO(read(clouds[data['stamp_ns']])) )['sensor_points'],dtype='<f4')
                msg=PointCloud2();msg.header.frame_id='lidar'
                msg.header.stamp.sec=data['stamp_ns']//10**9;msg.header.stamp.nanosec=data['stamp_ns']%10**9
                msg.height=1;msg.width=len(xyz);msg.point_step=12;msg.row_step=12*len(xyz);msg.is_dense=True
                msg.fields=[PointField(name=name,offset=4*i,datatype=PointField.FLOAT32,count=1) for i,name in enumerate(('x','y','z'))]
                msg.data=xyz.tobytes();put(2,clock,serialize_message(msg))
        while cursor<len(cases):probe();cursor+=1
    identity=dict(run=run_name,source_members=sources,counts=counts,bytes=target.stat().st_size,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        case_sha256=hashlib.sha256((HERE/(run_name+'_cases.json')).read_bytes()).hexdigest(),
        scope='Original observer order; exact logged first seed point and latest observed route endpoint. No live DDS batching or mid-search clock progression.')
    (OUT/(run_name+'_input_identity.json')).write_text(json.dumps(identity,indent=2)+'\n')
    print(run_name,counts,target.stat().st_size,flush=True)


for run in ['v57_realtime_trial01','v57_realtime_trial02']:
    prepare(run)
