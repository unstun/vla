"""Reconstruct the first failed v131 replacement from exact retained sensors."""
from pathlib import Path
import hashlib
import io
import json
import shutil
import sys
import zipfile
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--task-root',type=Path,required=True);TASK=parser.parse_args().task_root.resolve()
sys.path.insert(0, str(BASE / 'versions/v127'))
from analyze_remote import Capture


def numbers(values):
    return ' '.join(format(float(x), '.17g') for x in values)


def pose(sensor, optical=False):
    p = sensor['sensor_position' if optical else 'position']
    w, x, y, z = sensor['sensor_quaternion' if optical else 'quaternion']
    return numbers([*p, x, y, z, w]) + '\n'


def main():
    tag = 'v163_mac_full_attempt01'
    root = TASK / tag / 'runs' / tag
    out = TASK / 'replay_v163_stop_input'
    out.mkdir(parents=True, exist_ok=False)
    capture = Capture(root)
    import re
    lines = capture.read('nav2.log').splitlines()
    query_time=65.620568
    yaw=1.495
    collision='Ordered diagnostic snapshot during recorded generation3 first-spline failure; not exact executor reconstruction'
    telemetry = capture.rows('telemetry.jsonl')
    body = max((r for r in telemetry if r['physics_time_s'] <= query_time + 1e-8), key=lambda r:r['physics_time_s'])
    records = json.loads((root / 'sensor_manifest.json').read_text())
    events=capture.rows('artifacts/reactive_observations.jsonl')
    proof=max((r for r in events if r['event']=='execution_safety' and r['clock_ns']/1e9<=query_time),key=lambda r:r['clock_ns'])
    observation_ns=round(65.495635986*1e9)
    last=min(records,key=lambda r:abs(r['stamp_ns']-observation_ns))
    assert abs(last['stamp_ns']-observation_ns)<100
    audit = [json.loads(s) for s in (root / 'bridge_scan_audit.jsonl').read_text().splitlines() if s.strip()]
    published = {r['timestamp_ns'] for r in audit if r['outcome'] == 'published_sequentially'}
    scans = [r for r in records if r['stamp_ns'] <= last['stamp_ns'] and r['stamp_ns'] in published]
    assert scans and scans[-1]['stamp_ns'] == last['stamp_ns']
    listing = []
    raw_index = json.loads((root / 'raw_capture_manifest.json').read_text())
    with zipfile.ZipFile(root / 'raw_capture.zip') as archive:
        for i, r in enumerate(scans):
            data = archive.read(r['file'])
            assert hashlib.sha256(data).hexdigest() == r['sha256'] == raw_index['members'][r['file']]['sha256']
            points = np.asarray(np.load(io.BytesIO(data), allow_pickle=False)['sensor_points'], dtype='<f4')
            assert points.shape == (r['sensor']['point_count'], 3)
            (out / f'cloud_{i:05d}.f32').write_bytes(points.tobytes())
            (out / f'body_{i:05d}.txt').write_text(pose(r['body_sensor']))
            (out / f'sensor_{i:05d}.txt').write_text(pose(r['body_sensor'], True))
            listing.append(f"{i} {r['stamp_ns']} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32")
    (out / 'scans.txt').write_text('\n'.join(listing) + '\n')
    (out / 'query_body.txt').write_text(pose(body['body_sensor']))
    body_stamp = round(body['physics_time_s']*1e9)
    (out / 'query.txt').write_text(f"{round(query_time*1e9)} {body_stamp}\n")
    (out / 'candidate_yaw.txt').write_text(str(yaw)+'\n')
    ground = TASK / 'replay_v163_stop_static'
    ground.mkdir(exist_ok=False)
    sys.path.insert(0,str(BASE/'runtime_sources/bridge/lite3_sim_bridge'))
    from pct_sim_clock_core import load_pinned_map,load_paired_elevations,selected_ground_points,load_dense_surface_points
    source=load_pinned_map(BASE/'inputs/new_building.pickle')
    paired=load_paired_elevations(BASE/'inputs/new_building_original_precision.npz',source)
    (ground/'navigation.f32').write_bytes(selected_ground_points(source,paired_elevations=paired).astype('<f4').tobytes())
    (ground/'surface.f32').write_bytes(load_dense_surface_points(BASE/'inputs/new_building_dense_surface.npy').astype('<f4').tobytes())
    shutil.copyfile(TASK/'v154_graph_preflight/physical_floor.f32',ground/'physical_floor.f32')
    identity = json.loads((BASE / 'versions/v131/physical_floor_input.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, expected in [('navigation.f32', identity['navigation_payload_sha256']),
                           ('surface.f32', identity['selected_surface_payload_sha256']),
                           ('physical_floor.f32', identity['files']['physical_floor.f32']['sha256'])]:
        assert sha(ground / name) == expected
        shutil.copyfile(ground / name, out / name)
    result = {'run': tag, 'candidate_yaw': yaw, 'source_stamp_ns': last['stamp_ns'],
              'query_ns': round(query_time*1e9), 'body_stamp_ns': body_stamp, 'scans': len(scans),
              'collision_log': collision, 'source': capture.sources,
              'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
              'scope': 'Exact recorded points/poses, ordered published prefix. Original asynchronous map revision and DDS batching are not restored. Frozen clock counterfactuals are diagnostic only.'}
    routes=[r for r in events if r['event']=='pct_route' and r['clock_ns']/1e9<=query_time]
    route=max(routes,key=lambda r:r['clock_ns'])
    poses=route['data']['path']['poses']
    (out/'route.txt').write_text(str(len(poses))+'\n'+'\n'.join(numbers([r['pose']['position'][k] for k in ('x','y','z')]) for r in poses)+'\n')
    result['route']=route;result['safety_query']=proof
    (out / 'identity.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('run','candidate_yaw','source_stamp_ns','query_ns','body_stamp_ns','scans')}), flush=True)


if __name__ == '__main__':
    main()
