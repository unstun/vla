"""Return compact identities and replay original cloud prefixes; zero physics."""
from pathlib import Path
import hashlib
import json
import re
import sys

import numpy as np

R = Path('/home/ubuntu/sun/vla_v290_20261021')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
sys.path.insert(0, str(P / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196'))
from analyze_remote import Capture

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def pose(path, xyz, wxyz):
    path.write_text(' '.join(map(str, xyz + wxyz[1:] + wxyz[:1])) + '\n')


def main():
    report = dict(physics_steps=0, cases=[], claim=(
        'Synchronous replay of retained measured cloud prefixes. Search requests use rounded original log '
        'targets and exact measured sensor body positions; this is a captured-neighborhood diagnostic, '
        'not identical asynchronous mapper history, internal FSM state or a new physical trial.'))
    for case in ['A04', 'G05', 'CU06', 'CM02']:
        raw = P / f'physical_runs/v289_{case}_attempt01/runs/v289_{case}_attempt01'
        capture = Capture(raw)
        folder = R / 'captured' / case
        folder.mkdir(parents=True, exist_ok=False)
        sensors = capture.rows('sensor.jsonl')
        log = capture.read('nav2.log').splitlines()
        failures = [i for i, line in enumerate(log) if 'reactive_stair_seed_search_failed' in line]
        selected = []
        for i in [failures[0], failures[-1]]:
            prefix = '\n'.join(log[:i])
            start_goal = list(re.finditer(r'start:\s+([^,\n]+),[^\n]*\n[^\n]*goal:\s*([^,\n]+),', prefix))[-1]
            target = [float(x) for x in start_goal[2].split()]
            clocks = re.findall(r'ros_s=([0-9.]+)', prefix)
            now = float(clocks[-1])
            sensor_index = max(k for k, sample in enumerate(sensors) if sample['sim_time_s'] <= now)
            blocks = re.findall(r'reactive_collision_blocked verdict=7 voxel=2 q=\(([^)]+)\)', prefix)
            query = [float(x) for x in blocks[-1].split(',')]
            selected.append(dict(sensor_index=sensor_index, log_line=i+1, original_ros_s=now,
                rounded_log_start=[float(x) for x in start_goal[1].split()], rounded_log_goal=target,
                measured_start=sensors[sensor_index]['body_sensor']['position'], rounded_blocked_query=query))
        end = max(x['sensor_index'] for x in selected)
        listing = []
        for index, sample in enumerate(sensors[:end+1]):
            cloud = raw / sample['file']
            assert sha(cloud) == sample['sha256']
            points = np.load(cloud)['sensor_points']
            stem = f'scan_{index:04d}'
            points.astype('<f4').tofile(folder / (stem + '.f32'))
            body = sample['body_sensor']
            pose(folder / (stem + '_body.txt'), body['position'], body['quaternion'])
            pose(folder / (stem + '_sensor.txt'), body['sensor_position'], body['sensor_quaternion'])
            listing.append(f'{index} {sample["stamp_ns"]} {stem}_body.txt {stem}_sensor.txt {stem}.f32\n')
        (folder / 'scans.txt').write_text(''.join(listing))
        (folder / 'requests.txt').write_text(''.join(' '.join(map(str,
            [x['sensor_index']] + x['measured_start'] + x['rounded_log_goal'] + x['rounded_blocked_query'])) + '\n' for x in selected))
        (folder / 'profile.yaml').write_text(capture.read('nav2_params.scan.yaml'))
        row = dict(case_id=case, checkpoints=selected, scans=end+1, sources=capture.sources,
            generated={p.name: sha(p) for p in folder.iterdir() if p.is_file()})
        (folder / 'identity.json').write_text(json.dumps(row, indent=2) + '\n')
        report['cases'].append({k: v for k, v in row.items() if k != 'generated'})
        print(case, end+1, flush=True)
    (R / 'evidence/captured_inputs01.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
