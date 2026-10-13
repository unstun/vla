"""Read closed v175 failures after the cohort; do not modify raw captures."""
from pathlib import Path
import collections
import json
import math
import sys

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / 'versions/v175'))
from analyze_remote import Capture

TASK = Path('/data/sun/vla_mppi_20261009')
out = TASK / 'results/v175_failure_diagnostics'
out.mkdir(exist_ok=False)
for attempt in (2, 3, 5):
    tag = f'v175_full_candidate_attempt{attempt:02d}'
    capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
    rows = capture.rows('artifacts/reactive_observations.jsonl')
    log = capture.read('nav2.log')
    owners = {}
    for row in rows:
        data = row['data']
        generation = data.get('generation') if isinstance(data, dict) else None
        if generation is None:
            continue
        owner = owners.setdefault(generation, {'generation': generation, 'curves': 0, 'reverse_curves': 0})
        if row['event'] == 'pct_route':
            owner['route_clock_s'] = row['clock_ns'] / 1e9
        elif row['event'] == 'scan_cancel':
            owner['last_cancel'] = {'clock_s': row['clock_ns'] / 1e9, 'reason': data['reason']}
        elif row['event'] == 'bspline' and not data.get('emergency_stop'):
            owner['curves'] += 1
            owner['reverse_curves'] += bool(data.get('reverse_motion'))
            if 'first_curve' not in owner:
                points = data['pos_pts']
                owner['first_curve'] = {
                    'traj_id': data['traj_id'], 'clock_s': row['clock_ns'] / 1e9,
                    'start_xyz': [points[0][key] for key in 'xyz'],
                    'end_xyz': [points[-1][key] for key in 'xyz'],
                    'duration_s': data['knots'][len(points)] - data['knots'][3],
                    'reverse': data.get('reverse_motion', False),
                }
    patterns = ('V167_STEERING_PREFIX', 'V170_RECOVERY_BUDGET_RENEW',
                'output revoked reason=', 'Navigation failed', 'PCT rejected route:',
                'reference path rejected', 'Reference path rejected', 'reference_path_rejected')
    last_failure = log.rfind('scan_trajectory_missing')
    diagnostic_lines = log[max(0, last_failure - 12000):last_failure + 1000].splitlines()
    report = {
        'run': tag, 'owners': sorted(owners.values(), key=lambda x: x['generation']),
        'events': [line for line in log.splitlines() if any(pattern in line for pattern in patterns)],
        'last_missing_curve_context': diagnostic_lines,
        'sources': capture.sources,
    }
    (out / f'{tag}.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'run': tag, 'owners': report['owners'], 'events': report['events']}), flush=True)
