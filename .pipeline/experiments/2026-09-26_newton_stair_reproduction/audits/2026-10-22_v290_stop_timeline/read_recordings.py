"""Read-only extraction from two closed v290 runs; execute through SSH stdin.

No robot, ROS, simulator or original capture file is modified. Output is JSON
on stdout; the caller saves it locally for deterministic offline analysis.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import socket

ROOT = Path('/home/ubuntu/sun/vla_v290_20261021/physical_runs')
FIELDS = ('physics_steps', 'physics_time_s', 'effective_command', 'requested_command',
          'command_sequence', 'command_reason', 'command_source_timestamp_linux_ns',
          'stance_mode', 'stance_reason', 'stance_progress', 'policy_owns_joints',
          'foot_forces_n', 'base_up_z', 'wall_s')


def main():
    result = {'host': socket.gethostname(), 'new_physics_steps': 0, 'cases': {}}
    for case, since in [('D07', 95.0), ('CD12', 100.0)]:
        root = ROOT / f'v290_{case}_attempt01' / 'runs' / f'v290_{case}_attempt01'
        sources = {}

        def read(name):
            data = (root / name).read_bytes()
            sources[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            return data

        samples = []
        for line_number, line in enumerate(read('telemetry.jsonl').splitlines(), 1):
            row = json.loads(line)
            if row['physics_time_s'] < since:
                continue
            selected = {key: row.get(key) for key in FIELDS}
            selected['source_row'] = line_number
            body = row['body_sensor']
            selected['body'] = {key: body[key] for key in
                                ('position', 'quaternion', 'linear_world', 'angular_world')}
            selected['pacing'] = {key: row['realtime_pacing'][key] for key in
                                  ('wall_anchor_monotonic_s', 'native_anchor_s', 'wall_elapsed_s')}
            samples.append(selected)
        events, types, examples = [], Counter(), {}
        for line_number, line in enumerate(read('artifacts/reactive_observations.jsonl').splitlines(), 1):
            row = json.loads(line)
            kind = row.get('event')
            types[kind] += 1
            if kind not in examples:
                examples[kind] = str(row)[:1200]
            if row.get('clock_ns', 0) < since * 1e9:
                continue
            if kind not in ('pct_route', 'bspline', 'pointcloud', 'cloud'):
                events.append({'source_row': line_number, **row})
            elif kind == 'bspline' and row['data'].get('emergency_stop'):
                data = row['data']
                events.append({'source_row': line_number, 'clock_ns': row['clock_ns'],
                               'event': kind, 'data': {key: data.get(key) for key in
                               ('traj_id', 'emergency_stop', 'reverse_motion', 'start_time')}})
        logs = []
        pattern = re.compile(r'goal|Goal|terminal|stop|Stop|frozen|Frozen|executable|inside an obstacle|reactive_collision_blocked|Aborting|recovery|Recovery')
        for line_number, line in enumerate(read('nav2.log').decode().splitlines(), 1):
            if pattern.search(line):
                logs.append({'line': line_number, 'text': line})
        result['cases'][case] = {
            'root': str(root), 'since_s': since, 'samples': samples, 'events': events,
            'event_counts': dict(types), 'event_examples': examples, 'logs': logs,
            'clock_samples': [json.loads(line) for line in read('clock_samples.jsonl').splitlines()],
            'scenario': json.loads(read('inputs/stair_scenario.json')),
            'result': json.loads(read('result.json')),
            'nav2_params': read('nav2_params.yaml').decode(), 'sources': sources,
        }
    print(json.dumps(result, separators=(',', ':')))


if __name__ == '__main__':
    main()
