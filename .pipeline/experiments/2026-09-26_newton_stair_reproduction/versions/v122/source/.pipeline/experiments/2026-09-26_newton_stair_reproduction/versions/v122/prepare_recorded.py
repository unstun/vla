"""Prepare verified original v98 scans for native same-input collision queries."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('recorded', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(BASE/'runtime_sources/bridge/lite3_sim_bridge'))
    from pct_sim_clock_core import load_pinned_map, load_paired_elevations
    from pct_sim_clock_core import selected_ground_points, load_dense_surface_points
    source = load_pinned_map(BASE/'inputs/new_building.pickle')
    elevations = load_paired_elevations(BASE/'inputs/new_building_original_precision.npz', source)
    navigation = selected_ground_points(source, paired_elevations=elevations)
    surface = load_dense_surface_points(BASE/'inputs/new_building_dense_surface.npy')
    (args.output/'navigation.f32').write_bytes(navigation.astype('<f4').tobytes())
    (args.output/'surface.f32').write_bytes(surface.astype('<f4').tobytes())
    subprocess.run([sys.executable, str(HERE.parent/'v98/derive_mac_floor.py'),
                    '--output', str(args.output/'physical_floor.f32')], check=True)
    rows = [json.loads(s) for s in (args.recorded/'sensor.jsonl').read_text().splitlines()][:20]
    telemetry = [json.loads(s) for s in (args.recorded/'telemetry.jsonl').read_text().splitlines()]
    raw = json.loads((args.recorded/'raw_capture_manifest.json').read_text())['members']
    bridge = {r['timestamp_ns']: r for r in map(json.loads,
               (args.recorded/'bridge_scan_audit.jsonl').read_text().splitlines())}
    listing = []
    max_error = 0.0
    for index, row in enumerate(rows):
        path = args.recorded/row['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == raw[row['file']]['sha256']
        with np.load(path) as data:
            points, world = data['sensor_points'], data['world_points']
        body = row['body_sensor']
        q = body['sensor_quaternion']
        rotation = Rotation.from_quat(q[1:]+q[:1])
        error = np.max(np.linalg.norm(rotation.apply(points)+body['sensor_position']-world, axis=1))
        max_error = max(max_error, float(error))
        assert error < 1e-4
        published = bridge[row['stamp_ns']]
        assert published['planning_point_count'] == published['raw_point_count'] == len(points)
        assert published['filtered_ground_point_count'] == published['conservative_retained_point_count'] == 0
        files = [f'{index:03d}.body', f'{index:03d}.sensor', f'{index:03d}.cloud']
        for name, prefix in zip(files[:2], ('', 'sensor_')):
            q = body[prefix+'quaternion']
            values = body[prefix+'position']+q[1:]+q[:1]
            (args.output/name).write_text(' '.join(format(v, '.17g') for v in values)+'\n')
        (args.output/files[2]).write_bytes(points.astype('<f4').tobytes())
        later = next(t for t in telemetry if round(t['physics_time_s']*1e9) > row['stamp_ns'])
        later_stamp = round(later['physics_time_s']*1e9)
        assert 0 < later_stamp-row['stamp_ns'] < 30000000
        later_body = later['body_sensor']
        q = later_body['quaternion']
        name = f'{index:03d}.later_body'
        (args.output/name).write_text(' '.join(format(v, '.17g') for v in
            later_body['position']+q[1:]+q[:1])+'\n')
        listing.append(f'{index} {row["stamp_ns"]} '+ ' '.join(files)+f' {later_stamp} {name}')
    (args.output/'scans.txt').write_text('\n'.join(listing)+'\n')
    result = {'source': 'verified v98 original physics; first 20 actually published scans',
              'scans': len(rows), 'sensor_world_max_error_m': max_error,
              'planning_count_matches_original_bridge': True,
              'files': {str(f.relative_to(args.output)): hashlib.sha256(f.read_bytes()).hexdigest()
                        for f in args.output.rglob('*') if f.is_file()}}
    (args.output/'identity.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}))


if __name__ == '__main__':
    main()
