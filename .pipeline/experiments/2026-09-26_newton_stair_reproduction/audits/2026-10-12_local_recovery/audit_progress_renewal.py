"""Inspect recorded recovery events without changing a closed raw capture."""
from pathlib import Path
import argparse
import bisect
import hashlib
import json
import math
import re
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version-dir', type=Path, required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.version_dir.resolve()))
    from analyze_remote import Capture
    capture = Capture(args.run_root)
    states = capture.json('video_states.json')
    times = [row['physics_time_s'] for row in states]
    pattern = re.compile(
        r'V170_RECOVERY_BUDGET_RENEW used=(\d+) checkpoints=(\d+) '
        r'xyz=\[([^]]+)\] source_s=([0-9.]+)')
    renewals = []
    for match in pattern.finditer(capture.read('nav2.log')):
        stamp = float(match[4])
        point = [float(value) for value in match[3].split(',')]
        index = bisect.bisect_left(times, stamp)
        closest = min(range(max(0, index - 1), min(len(times), index + 1)),
                      key=lambda i: abs(times[i] - stamp))
        renewals.append({
            'used_retries_before_renewal': int(match[1]),
            'checkpoint_count': int(match[2]),
            'source_sim_s': stamp,
            'measured_body_xyz': point,
            'nearest_physics_state_s': times[closest],
            'nearest_state_position_error_m': math.dist(point, states[closest]['joint_q'][:3]),
        })
    rows = capture.rows('artifacts/reactive_observations.jsonl')
    reverse = []
    fields = ('run_id', 'epoch', 'request_id', 'goal_id', 'route_id',
              'command_id', 'generation', 'map_epoch', 'map_revision', 'traj_id')
    for row in rows:
        if row['event'] != 'bspline' or not row['data'].get('reverse_motion'):
            continue
        curve = row['data']
        commands = [r for r in rows if r['event'] == 'raw_command' and
                    all(r['data'].get(k) == curve.get(k) for k in fields)]
        reverse.append({
            'identity': {key: curve[key] for key in fields},
            'clock_ns': row['clock_ns'],
            'matching_raw_commands': len(commands),
            'backward_raw_commands': sum(r['data']['twist']['linear']['x'] < -1e-6 for r in commands),
        })
    report = {
        'run': args.run_root.name,
        'budget_renewal_events': renewals,
        'budget_renewal_count': len(renewals),
        'reverse_splines': reverse,
        'source_files': capture.sources,
        'audit_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'claim': 'Recorded branch coverage and nearest physical state only. '
                 'Arrival, stop-proof qualification, and continuous reverse execution are separate checks.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'run': report['run'], 'renewals': len(renewals), 'reverse_splines': len(reverse)}))


if __name__ == '__main__':
    main()
