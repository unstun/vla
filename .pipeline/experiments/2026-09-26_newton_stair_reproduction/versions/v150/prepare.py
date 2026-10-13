"""Extract the actual last Linux clear/blocked pair without changing its inputs."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import zipfile
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'v149'))
from analyze_remote import Capture


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numbers(values):
    return ' '.join(format(float(v), '.17g') for v in values)


def ns(stamp):
    return stamp['sec'] * 1000000000 + stamp['nanosec']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = args.task_root.resolve()
    root = task / 'failed09'
    out = task / 'replay_v150_input'
    out.mkdir(exist_ok=False)
    c = Capture(root)
    events = c.rows('artifacts/reactive_observations.jsonl')
    curve = next(r for r in events if r['event'] == 'bspline' and r['data']['traj_id'] == 2366)
    pair = [r for r in events if r['event'] == 'execution_safety' and r['data']['binding']['traj_id'] == 2366]
    assert len(pair) == 2 and [r['data']['clear'] for r in pair] == [True, False]
    assert pair[0]['data']['local_map_revision'] == pair[1]['data']['local_map_revision'] == 1191
    assert pair[0]['data']['observation_stamp_s'] == pair[1]['data']['observation_stamp_s']
    observation_ns = round(pair[0]['data']['observation_stamp_s'] * 1e9)
    records = c.json('sensor_manifest.json')
    published = {r['timestamp_ns'] for r in c.rows('bridge_scan_audit.jsonl')
                 if r['outcome'] == 'published_sequentially'}
    scans = [r for r in records if r['stamp_ns'] <= observation_ns and r['stamp_ns'] in published]
    assert scans and scans[-1]['stamp_ns'] == observation_ns
    snapshots = re.findall(r'V82_MAP_SNAPSHOT revision=(\d+) clouds=(\d+) cloud_stamp=([\d.]+)', c.read('nav2.log'))
    recorded_map = next(r for r in snapshots if int(r[0]) == 1191)
    assert abs(float(recorded_map[2]) - observation_ns / 1e9) < 1e-8
    index = c.json('raw_capture_manifest.json')['members']
    listing = []
    with zipfile.ZipFile(root / 'raw_capture.zip') as archive:
        for i, row in enumerate(scans):
            data = archive.read(row['file'])
            assert hashlib.sha256(data).hexdigest() == row['sha256'] == index[row['file']]['sha256']
            points = np.asarray(np.load(io.BytesIO(data), allow_pickle=False)['sensor_points'], dtype='<f4')
            assert points.shape == (row['sensor']['point_count'], 3)
            (out / f'cloud_{i:05d}.f32').write_bytes(points.tobytes())
            body = row['body_sensor']
            for label, prefix in [('body', ''), ('sensor', 'sensor_')]:
                q = body[prefix + 'quaternion']
                (out / f'{label}_{i:05d}.txt').write_text(numbers(body[prefix + 'position'] + q[1:] + q[:1]) + '\n')
            listing.append(f"{i} {row['stamp_ns']} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32")
    (out / 'scans.txt').write_text('\n'.join(listing) + '\n')
    poses = [r for r in events if r['event'] == 'body_pose_observer']
    queries = []
    for label, row in zip(('clear', 'blocked'), pair):
        query_ns = ns(row['data']['stamp'])
        body = max((r for r in poses if ns(r['data']['header']['stamp']) <= query_ns),
                   key=lambda r: ns(r['data']['header']['stamp']))
        pose = body['data']['pose']['pose']
        xyz = [pose['position'][k] for k in ('x', 'y', 'z')]
        q = [pose['orientation'][k] for k in ('x', 'y', 'z', 'w')]
        (out / (label + '_body.txt')).write_text(numbers(xyz + q) + '\n')
        queries.append({'label': label, 'query_ns': query_ns,
                        'body_ns': ns(body['data']['header']['stamp']), 'body': body, 'safety': row})
    (out / 'queries.txt').write_text('\n'.join(
        f"{r['label']} {r['query_ns']} {r['body_ns']} {r['label']}_body.txt" for r in queries) + '\n')
    data = curve['data']
    points = [[p[k] for k in ('x', 'y', 'z')] for p in data['pos_pts']]
    (out / 'curve.txt').write_text(f"{ns(data['start_time'])} {len(points)} {len(data['knots'])}\n" +
                                  '\n'.join(numbers(p) for p in points) + '\n' + numbers(data['knots']) + '\n')
    # Generate the original static payload bytes from the pinned local inputs.
    sys.path.insert(0, str(BASE / 'runtime_sources/bridge/lite3_sim_bridge'))
    from pct_sim_clock_core import load_pinned_map, load_paired_elevations, selected_ground_points, load_dense_surface_points
    source = load_pinned_map(BASE / 'inputs/new_building.pickle')
    paired = load_paired_elevations(BASE / 'inputs/new_building_original_precision.npz', source)
    (out / 'navigation.f32').write_bytes(selected_ground_points(source, paired_elevations=paired).astype('<f4').tobytes())
    (out / 'surface.f32').write_bytes(load_dense_surface_points(BASE / 'inputs/new_building_dense_surface.npy').astype('<f4').tobytes())
    shutil.copyfile(task / 'v149_graph_preflight/physical_floor.f32', out / 'physical_floor.f32')
    expected = json.loads((HERE.parent / 'v147/physical_floor_input.json').read_text())
    assert sha(out / 'navigation.f32') == expected['navigation_payload_sha256']
    assert sha(out / 'surface.f32') == expected['selected_surface_payload_sha256']
    assert sha(out / 'physical_floor.f32') == expected['files']['physical_floor.f32']['sha256']
    result = {'source_run': 'v147_full_candidate_attempt09', 'trajectory': curve,
              'queries': queries, 'scans': len(scans), 'observation_ns': observation_ns,
              'recorded_mapper_cloud_count': int(recorded_map[1]),
              'published_minus_recorded_mapper_count': len(scans) - int(recorded_map[1]),
              'sources': c.sources, 'preparer_sha256': sha(Path(__file__)),
              'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
              'claim': 'Original published inputs and observer body samples. Mapper count differs at startup; exact asynchronous batching and consumed live body pose are not restored. Require a matching failure oracle before causal claims.'}
    (out / 'identity.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'scans': len(scans), 'observation_ns': observation_ns,
                      'queries': [(r['label'], r['query_ns'], r['body_ns']) for r in queries]}))


if __name__ == '__main__':
    main()
