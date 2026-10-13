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
    tag = 'v144_full_candidate_attempt01'
    root = TASK / 'trials' / tag / 'runs' / tag
    out = TASK / 'results/full_route_diagnosis_v146/input'
    out.mkdir(parents=True, exist_ok=False)
    capture = Capture(root)
    import re
    lines = capture.read('nav2.log').splitlines()
    collision = next(s for s in lines if 'initial_spline_collision pos=(7.52920198' in s)
    query_time = float(re.search(r'now=([0-9.]+)', collision).group(1))
    yaw = float(re.search(r'yaw=([-0-9.]+)', collision).group(1))
    telemetry = capture.rows('telemetry.jsonl')
    body = max((r for r in telemetry if r['physics_time_s'] <= query_time + 1e-8), key=lambda r:r['physics_time_s'])
    records = json.loads((root / 'sensor_manifest.json').read_text())
    last = max((r for r in records if r['sim_time_s'] <= query_time), key=lambda r:r['sim_time_s'])
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
    ground = TASK / 'fixed_curve_input'
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
    (out / 'identity.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('run','candidate_yaw','source_stamp_ns','query_ns','body_stamp_ns','scans')}), flush=True)


if __name__ == '__main__':
    main()
