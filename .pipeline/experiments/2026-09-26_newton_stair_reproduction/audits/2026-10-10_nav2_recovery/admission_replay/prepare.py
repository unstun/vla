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
BASE = HERE.parents[2]
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(BASE / 'versions/v127'))
from analyze_remote import Capture


def numbers(values):
    return ' '.join(format(float(x), '.17g') for x in values)


def pose(sensor, optical=False):
    p = sensor['sensor_position' if optical else 'position']
    w, x, y, z = sensor['sensor_quaternion' if optical else 'quaternion']
    return numbers([*p, x, y, z, w]) + '\n'


def main():
    tag = 'v131_candidate_attempt02'
    root = TASK / 'trials' / tag / 'runs' / tag
    out = TASK / 'recovery_admission_replay/input'
    out.mkdir(parents=True, exist_ok=False)
    capture = Capture(root)
    rows = capture.rows('artifacts/reactive_observations.jsonl')
    route = next(r for r in rows if r['event'] == 'pct_route' and r['data']['generation'] == 6)
    body = max((r['data'] for r in rows if r['event'] == 'lidar_pose'
                and r['data']['header']['stamp']['sec'] * 10**9 + r['data']['header']['stamp']['nanosec'] <= route['clock_ns']),
               key=lambda d: d['header']['stamp']['sec'] * 10**9 + d['header']['stamp']['nanosec'])
    records = json.loads((root / 'sensor_manifest.json').read_text())
    # Original native log reports cloud_stamp=52.003 at route6 entry. Choose its
    # exact retained source stamp, not the rounded printed number.
    last = min(records, key=lambda r: abs(r['sim_time_s'] - 52.003))
    assert abs(last['sim_time_s'] - 52.003) < .0006
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
    p, q = body['pose']['pose']['position'], body['pose']['pose']['orientation']
    (out / 'query_body.txt').write_text(numbers([*[p[k] for k in ('x', 'y', 'z')], *[q[k] for k in ('x', 'y', 'z', 'w')]]) + '\n')
    body_stamp = body['header']['stamp']['sec'] * 10**9 + body['header']['stamp']['nanosec']
    poses = route['data']['path']['poses']
    (out / 'route.txt').write_text(str(len(poses)) + '\n' + '\n'.join(numbers([r['pose']['position'][k] for k in ('x','y','z')]) for r in poses) + '\n')
    goal = route['data']['goal_pose']
    (out / 'goal.txt').write_text(numbers([*[goal['position'][k] for k in ('x','y','z')], *[goal['orientation'][k] for k in ('x','y','z','w')]]) + '\n')
    (out / 'query.txt').write_text(f"{route['clock_ns']} {body_stamp}\n")
    ground = TASK / 'fixed_curve_input'
    identity = json.loads((BASE / 'versions/v131/physical_floor_input.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, expected in [('navigation.f32', identity['navigation_payload_sha256']),
                           ('surface.f32', identity['selected_surface_payload_sha256']),
                           ('physical_floor.f32', identity['files']['physical_floor.f32']['sha256'])]:
        assert sha(ground / name) == expected
        shutil.copyfile(ground / name, out / name)
    result = {'run': tag, 'generation': 6, 'source_stamp_ns': last['stamp_ns'],
              'query_ns': route['clock_ns'], 'body_stamp_ns': body_stamp, 'scans': len(scans),
              'route': route['data'], 'source': capture.sources,
              'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
              'scope': 'Exact recorded points/poses, ordered published prefix. Original asynchronous map revision and DDS batching are not restored. Frozen clock counterfactuals are diagnostic only.'}
    (out / 'identity.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('run','generation','source_stamp_ns','query_ns','body_stamp_ns','scans')}), flush=True)


if __name__ == '__main__':
    main()
