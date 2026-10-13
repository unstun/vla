"""Extract exact cold seeds and serialize the original observer stream remotely."""
from pathlib import Path
import copy
import hashlib
import io
import json
import re
import struct
import zipfile

import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from nav_msgs.msg import Odometry
from scan_planner_msgs.msg import Bspline
from sensor_msgs.msg import PointCloud2, PointField

BASE, OUT = Path('/archive'), Path('/attempt')
RUN = BASE / 'runs/v59_realtime_trial01'
archive = zipfile.ZipFile(RUN / 'raw_capture.zip')
sources = {}


def read(name):
    path = RUN / name
    data = path.read_bytes() if path.is_file() else archive.read(name)
    sources[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return data


obs = [json.loads(line) for line in read('artifacts/reactive_observations.jsonl').splitlines()]
sensors = [json.loads(line) for line in read('sensor.jsonl').splitlines()]
clouds = {row['stamp_ns']: f"clouds/{row['sensor']['scan_window']['scan_index']:05d}.npz" for row in sensors}
lines = read('scan.log').decode().splitlines()
tail = json.loads((BASE / 'versions/v59/analysis/v59_realtime_trial01_tail_evidence.json').read_text())['tails'][0]
round_ = tail['round']
assert round_['rebound_attempts'] == 8 and round_['wall_s'] == 1.236709246
segment = list(enumerate(lines[round_['start_line'] - 1:round_['end_line']], round_['start_line']))
epoch = lambda line: float(re.search(r'\[(\d+\.\d+)\]', line)[1])
anchor = epoch(segment[0][1])
wall = lambda line: round_['start_wall_s'] + epoch(line) - anchor
seeds = []
for number, line in segment:
    if 'spline_seed_capture ' in line:
        seeds.append(dict(line=number, wall_s=wall(line), **json.loads(line.split('spline_seed_capture ')[1])))
assert len(seeds) == 7
assert all(seed['points'][0] == seeds[0]['points'][0] and seed['derivatives'][0] == seeds[0]['derivatives'][0]
           and seed['derivatives'][2] == seeds[0]['derivatives'][2] for seed in seeds)
old = max((event for event in obs if event['event'] == 'bspline' and not event['data'].get('emergency_stop')
           and event['wall_monotonic_ns'] * 1e-9 < round_['start_wall_s']), key=lambda event: event['wall_monotonic_ns'])
new = min((event for event in obs if event['event'] == 'bspline' and not event['data'].get('emergency_stop')
           and event['wall_monotonic_ns'] * 1e-9 > round_['start_wall_s']), key=lambda event: event['wall_monotonic_ns'])
warm_line = next(line for _, line in segment if 'site=warm_seed_check' in line)
cases = [dict(id=0, kind=0, wall_s=wall(warm_line), sim_s=round_['ros_s'], label='original_warm_connector',
              points=[seeds[0]['points'][0], seeds[-1]['points'][-1]], derivatives=seeds[0]['derivatives'], interval=seeds[0]['interval'])]
for seed, label in [(seeds[0], 'first_shorter_target'), (seeds[2], 'second_shorter_target'), (seeds[-1], 'final_accepted_target')]:
    latest = max((event for event in obs if event.get('clock_ns') and event['wall_monotonic_ns'] * 1e-9 <= seed['wall_s']),
                 key=lambda event: event['wall_monotonic_ns'])
    cases.append(dict(id=len(cases), kind=1, sim_s=latest['clock_ns'] * 1e-9, label=label, **seed))
(OUT / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
record = dict(round=round_, seeds=seeds, old_observed_curve=old, recovery_observed_curve=new,
              native_fail_log_lines=[number for number, line in segment if 'A-star failed; aborting optimization' in line],
              epochs=[dict(line=number, text=line) for number, line in segment if 'V59_TRAJECTORY_EPOCH' in line],
              all_retry_initial_pva_exact=True,
              scope='Exact seed captures and observer curves; inferred wall association uses the nominal-round log anchor.')
(OUT / 'chain_evidence.json').write_text(json.dumps(record, indent=2) + '\n')

cursor = 0
counts = {}
target = OUT / 'events.bin'
with target.open('xb') as stream:
    def put(kind, clock, payload):
        stream.write(struct.pack('<BqI', kind, clock, len(payload)))
        stream.write(payload)
        counts[kind] = counts.get(kind, 0) + 1

    def probe():
        row = cases[cursor]
        values = [row['id'], row['kind'], len(row['points']), row['interval']]
        values += [value for point in row['points'] for value in point]
        values += [value for derivative in row['derivatives'] for value in derivative]
        put(5, round(row['sim_s'] * 1e9), ' '.join(str(value) for value in values).encode())

    for event in obs:
        while cursor < len(cases) and event['wall_monotonic_ns'] >= cases[cursor]['wall_s'] * 1e9:
            probe()
            cursor += 1
        if cursor == len(cases):
            break
        clock = event.get('clock_ns')
        if clock is None:
            continue
        kind, data = event['event'], event['data']
        if kind in ('body_pose_observer', 'lidar_pose', 'bspline'):
            msg = Bspline() if kind == 'bspline' else Odometry()
            set_message_fields(msg, copy.deepcopy(data))
            put({'body_pose_observer': 0, 'lidar_pose': 1, 'bspline': 3}[kind], clock, serialize_message(msg))
        elif kind == 'cloud':
            xyz = np.asarray(np.load(io.BytesIO(read(clouds[data['stamp_ns']])) )['sensor_points'], dtype='<f4')
            msg = PointCloud2()
            msg.header.frame_id = 'lidar'
            msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(data['stamp_ns'], 10**9)
            msg.height, msg.width, msg.point_step, msg.row_step, msg.is_dense = 1, len(xyz), 12, 12 * len(xyz), True
            msg.fields = [PointField(name=name, offset=4*i, datatype=PointField.FLOAT32, count=1) for i, name in enumerate(('x', 'y', 'z'))]
            msg.data = xyz.tobytes()
            put(2, clock, serialize_message(msg))
    while cursor < len(cases):
        probe()
        cursor += 1

(OUT / 'input_identity.json').write_text(json.dumps(dict(source_members=sources, counts=counts,
    stream_bytes=target.stat().st_size, stream_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    scope='Original observer order; fixed clock per probe; no live callback batching or mid-optimizer updates.'), indent=2) + '\n')
print(json.dumps(dict(cases=len(cases), seeds=len(seeds), counts=counts)))
