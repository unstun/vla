"""Feed original measured terminal poses and published curves to the native controller."""
from pathlib import Path
import hashlib
import json
import sys

import yaml

R = Path('/home/ubuntu/sun/vla_v290_20261021')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
sys.path.insert(0, str(P / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196'))
from analyze_remote import Capture


def main():
    c = Capture(P / 'physical_runs/v289_CD12_attempt01/runs/v289_CD12_attempt01')
    out = R / 'captured/CD12'
    out.mkdir(exist_ok=False)
    events = []
    fields = lambda p: [p['position'][k] for k in ['x', 'y', 'z']] + [p['orientation'][k] for k in ['x', 'y', 'z', 'w']]
    for index, row in enumerate(c.rows('artifacts/reactive_observations.jsonl')):
        ns, event, data = row['clock_ns'], row['event'], row['data']
        if ns > 115300000000:
            continue
        if event == 'pct_route':
            poses = data['poses']
            values = [len(poses)] + [x for p in poses for x in fields(p['pose'])]
            events.append((ns, 0, index, ['G', ns] + values))
        elif event == 'bspline':
            origin = data['start_time']['sec']*1000000000 + data['start_time']['nanosec']
            values = [data['traj_id'], origin, int(data['emergency_stop']), int(data['reverse_motion']), data['order'],
                len(data['pos_pts']), len(data['knots'])]
            values += [p[k] for p in data['pos_pts'] for k in ['x', 'y', 'z']] + data['knots']
            events.append((ns, 1, index, ['B', ns] + values))
    measured = []
    for index, row in enumerate(c.rows('telemetry.jsonl')):
        ns = round(row['physics_time_s']*1e9)
        if ns > 115300000000:
            continue
        body = row['body_sensor']
        values = body['position'] + body['quaternion'][1:] + body['quaternion'][:1]
        values += body['linear_body'] + body['angular_body']
        events.append((ns, 2, index, ['C', ns] + values))
        if ns >= 110000000000:
            measured.append(dict(stamp_ns=ns, position=body['position'], applied_command=row['effective_command'],
                mode=row['stance_mode'], measured_velocity=body['linear_world']))
    events.sort(key=lambda x: x[:3])
    p = out / 'events.txt'
    p.write_text(''.join(' '.join(map(str, e[3])) + '\n' for e in events))
    profile = yaml.safe_load(c.read('nav2_params.yaml'))['controller_server']['ros__parameters']
    profile['SCAN']['native_worker_enabled'] = False
    (out / 'profile.yaml').write_text(yaml.safe_dump({'controller_server': {'ros__parameters': profile}}))
    (out / 'measured_terminal.json').write_text(json.dumps(measured, indent=2) + '\n')
    (R / 'evidence/terminal_inputs01.json').write_text(json.dumps(dict(physics_steps=0, sources=c.sources,
        events=len(events), terminal_measured_samples=len(measured), events_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        claim='Actual Controller/LocalMotion/TrackingNode replay with recorded measured poses and published splines. '
            '20ms recorded pose ticks replace original callback scheduling. Native worker disabled; recorded curves supplied. '
            'Different commands do not predict new physical poses or certify CD12 geometry.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
