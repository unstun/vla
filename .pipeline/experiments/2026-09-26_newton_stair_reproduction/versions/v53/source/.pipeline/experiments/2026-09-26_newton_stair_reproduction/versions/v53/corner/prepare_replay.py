"""Read the archived v52 capture without expanding bulk files.

The first failing round needs one documented ordering correction: the route
observed 5.725 ms after nominal start was applied before start in native scan.log.
All other inputs retain observer receipt order. This is a bounded reconstruction,
not a claim to recover native DDS batching or map changes during a live solve.
"""
from pathlib import Path
import hashlib
import copy
import io
import json
import struct
import zipfile
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from nav_msgs.msg import Odometry
from scan_planner_msgs.msg import P2BRoute, Bspline
from sensor_msgs.msg import PointCloud2, PointField

BASE = Path('/archive')
RUN = BASE / 'runs/v52_realtime_trial02'
OUT = Path('/attempt/replay')
OUT.mkdir()
archive = zipfile.ZipFile(RUN / 'raw_capture.zip')
sources = {}
def read(name):
    path = RUN / name
    data = path.read_bytes() if path.is_file() else archive.read(name)
    sources[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return data
obs = [json.loads(x) for x in read('artifacts/reactive_observations.jsonl').splitlines()]
sensors = [json.loads(x) for x in read('sensor.jsonl').splitlines()]
clouds = {x['stamp_ns']:f"clouds/{x['sensor']['scan_window']['scan_index']:05d}.npz" for x in sensors}
timeline = json.loads(Path('/profile/timeline_summary.json').read_text())
first = timeline['first_persistent_failure']
first_wall = round(first['start_wall_s'] * 1e9)
first_clock = round(first['ros_s'] * 1e9)
route = next(e for e in obs if e['event'] == 'pct_route' and
             first_wall <= e['wall_monotonic_ns'] <= first_wall + 10_000_000)
# Replay two probes at native-order first failure and a third at 44.34725571,
# when the live optimizer explicitly recorded its initial-point collision.
late_clock = 44_347_255_707
phase_clock = 42_553_241_730
phase_wall = next(e['wall_monotonic_ns'] for e in obs if e['event']=='body_pose_observer' and e.get('clock_ns')==phase_clock)
late_wall = next(e['wall_monotonic_ns'] for e in obs if
                e['event']=='body_pose_observer' and e.get('clock_ns') is not None
                and e['clock_ns'] >= late_clock)
geometry = dict(route_receipt_delay_ms=(route['wall_monotonic_ns'] - first_wall)/1e6,
    correction='Apply captured route before nominal first-failure probe, as scan.log establishes.',
    routes=[dict(clock_s=e['clock_ns']/1e9, data=e['data']) for e in obs
            if e['event']=='pct_route' and 40 <= e['clock_ns']/1e9 <= 44.4])
counts = {}
with (OUT / 'events.bin').open('wb') as stream:
    def put(kind, clock, payload):
        stream.write(struct.pack('<BqI', kind, clock, len(payload)))
        stream.write(payload)
        counts[kind] = counts.get(kind, 0) + 1
    def event_put(event):
        clock = event.get('clock_ns')
        if clock is None: return
        kind, data = event['event'], event['data']
        classes = {'body_pose_observer':(0,Odometry), 'lidar_pose':(1,Odometry),
                   'pct_route':(3,P2BRoute), 'bspline':(4,Bspline)}
        if kind in classes:
            tag, cls = classes[kind]; message = cls()
            set_message_fields(message, copy.deepcopy(data))
            put(tag, clock, serialize_message(message))
        elif kind == 'cloud':
            points = np.asarray(np.load(io.BytesIO(read(clouds[data['stamp_ns']])) )['sensor_points'], dtype='<f4')
            m = PointCloud2(); m.header.frame_id = 'lidar'
            m.header.stamp.sec = data['stamp_ns']//10**9
            m.header.stamp.nanosec = data['stamp_ns']%10**9
            m.height=1; m.width=len(points); m.point_step=12; m.row_step=12*len(points); m.is_dense=True
            m.fields=[PointField(name=name, offset=4*i, datatype=PointField.FLOAT32, count=1)
                      for i,name in enumerate(('x','y','z'))]
            m.data=points.tobytes(); put(2,clock,serialize_message(m))
    marked = False
    phase_marked = False
    for event in obs:
        if event is route: continue
        if not marked and event['wall_monotonic_ns'] >= first_wall:
            put(5, first_clock, struct.pack('<I', 0))  # before route, diagnostic only
            event_put(route)
            put(5, first_clock, struct.pack('<I', 1))  # native-order first failure
            marked = True
        event_put(event)
        if not phase_marked and event['wall_monotonic_ns'] >= phase_wall:
            put(5,phase_clock,struct.pack('<I',3)); phase_marked = True
        if event['wall_monotonic_ns'] >= late_wall:
            put(5,late_clock,struct.pack('<I',2)); break
assert marked
(OUT / 'identity.json').write_text(json.dumps(dict(sources=sources, counts=counts,
    events_sha256=hashlib.sha256((OUT/'events.bin').read_bytes()).hexdigest(),
    ordering_correction=geometry['correction'], route_receipt_delay_ms=geometry['route_receipt_delay_ms'],
    limitations='Feasible-window hint reconstructed only for pre-route probe; live mid-solve sensor refresh and clock progression are not reconstructed.'), indent=2)+'\n')
(OUT / 'corner_geometry.json').write_text(json.dumps(geometry, indent=2)+'\n')
print(json.dumps(dict(counts=counts, bytes=(OUT/'events.bin').stat().st_size)))
