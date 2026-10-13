"""Read closed v177 captures; produce compact, source-indexed stop evidence."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / 'versions/v177'))
from analyze_remote import Capture


def small(row):
    data = dict(row['data'])
    if row['event'] == 'pct_route':
        data['path_points'] = len(data.pop('path')['poses'])
    if row['event'] == 'bspline':
        pts = data.pop('pos_pts')
        data['first_points'] = pts[:3]
        data['last_points'] = pts[-3:]
        data['duration_s'] = data['knots'][len(pts)] - data['knots'][3]
    return {'event': row['event'], 'sim_s': row['clock_ns'] / 1e9,
            'wall_s': row['wall_monotonic_ns'] / 1e9, 'data': data}


def audit(task, attempt):
    tag = f'v177_full_candidate_attempt{attempt:02d}'
    capture = Capture(task / 'trials' / tag / 'runs' / tag)
    rows = capture.rows('artifacts/reactive_observations.jsonl')
    groups = collections.defaultdict(list)
    for index, row in enumerate(rows, 1):
        row['source_line'] = index
        groups[row['event']].append(row)
    lines = capture.read('nav2.log').splitlines()
    revokes = [(i, line) for i, line in enumerate(lines)
               if 'SCAN output revoked reason=' in line]
    first_cancels = {}
    for row in groups['scan_cancel']:
        first_cancels.setdefault(row['data']['generation'], row)
    assert len(revokes) == len(first_cancels), (tag, len(revokes), len(first_cancels))
    owners = []
    relevant = ('rejected', 'invalid', 'failed', 'Failed', 'EMERGENCY_STOP',
                'V82_MAP_SNAPSHOT', 'V167_STEERING', 'V170_RECOVERY', 'timeout',
                'SAFETY', 'finish', 'Finish', 'SCAN evidence', 'V154_', 'V158_')
    for (line_index, line), (generation, cancel) in zip(revokes, first_cancels.items()):
        reason = re.search(r'reason=(\S+)', line).group(1)
        assert reason == cancel['data']['reason'], (tag, generation, reason, cancel)
        t = cancel['clock_ns'] / 1e9
        route = next(r for r in groups['pct_route'] if r['data']['generation'] == generation)
        curves = [r for r in groups['bspline'] if r['data']['generation'] == generation]
        safety = [r for r in groups['execution_safety']
                  if r['data']['binding']['generation'] == generation
                  and t - 1 <= r['clock_ns'] / 1e9 <= t + .1]
        context = [{'line': i + 1, 'text': lines[i]} for i in range(max(0, line_index-100), min(len(lines), line_index+25))
                   if any(word in lines[i] for word in relevant)]
        owners.append({'generation': generation, 'route': small(route),
                       'cancel': small(cancel), 'cancel_source_line': cancel['source_line'],
                       'revocation_log_line': line_index+1, 'revocation_log': line,
                       'curves': len(curves),
                       'first_curve': small(curves[0]) if curves else None,
                       'last_curve': small(curves[-1]) if curves else None,
                       'safety_near_stop': [small(r) for r in safety],
                       'log_context': context})
    sensors = capture.rows('sensor.jsonl')
    # Preserve the existing metric's definition, including final low-speed hold.
    metrics_path = BASE / 'versions/v177/results/repeats' / tag / 'metrics.json'
    metrics = json.loads(metrics_path.read_text())
    pauses = []
    for index, p in enumerate(metrics['pauses_over_1s'], 1):
        start, end = p['start_sim_s'], p['end_sim_s']
        sample = [r for r in sensors if start <= r['sim_time_s'] <= end]
        subset = {k: [r for r in groups[k] if start <= r['clock_ns']/1e9 <= end]
                  for k in ('raw_command', 'gated_command', 'bspline', 'scan_cancel', 'scan_admission', 'pct_route')}
        commands = subset['raw_command']
        zeros = sum(all(abs(d['data']['twist'][typ][axis]) < 1e-9
                        for typ, axis in (('linear','x'),('linear','y'),('angular','z'))) for d in commands)
        prior = [o for o in owners if o['route']['sim_s'] <= start]
        nearby = [o['generation'] for o in owners if start-1 <= o['cancel']['sim_s'] <= end+.1]
        admissions = collections.Counter((r['data']['consumer'], r['data']['status'], r['data']['message'])
                                         for r in subset['scan_admission'])
        pauses.append(dict(p, index=index, active_generation_at_start=prior[-1]['generation'] if prior else None,
                           revocations_near=nearby, raw_commands=len(commands), zero_raw_commands=zeros,
                           curves=len(subset['bspline']),
                           first_command=small(commands[0]) if commands else None,
                           last_command=small(commands[-1]) if commands else None,
                           first_xyz=sample[0]['body_sensor']['position'] if sample else None,
                           last_xyz=sample[-1]['body_sensor']['position'] if sample else None,
                           max_angular_z=max((abs(r['body_sensor']['angular_world'][2]) for r in sample),default=None),
                           admissions=[{'key':key,'count':n} for key,n in admissions.items()]))
    event_lines = [{'line':i+1,'text':l} for i,l in enumerate(lines)
                   if any(k in l for k in ('V167_STEERING_PREFIX', 'Failed to make progress',
                       'Controller native validation rejected', 'SCAN evidence rejected',
                       'SCAN output revoked', 'V170_RECOVERY_BUDGET_RENEW'))]
    return dict(run=tag, owners=owners, pauses=pauses, event_lines=event_lines,
                stop_proofs=[small(r) for r in groups['measured_stop_proof']],
                event_counts=dict(collections.Counter(r['event'] for r in rows)),
                sources=capture.sources, metrics_sha256=hashlib.sha256(metrics_path.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--task',type=Path,default=Path('/data/sun/vla_mppi_20261009'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    for attempt in range(1,6):
        result=audit(args.task,attempt)
        path=args.output/f'attempt{attempt:02d}.json'
        path.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'run':result['run'],'stops':len(result['owners']),
                          'pauses':len(result['pauses'])}),flush=True)
    manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in args.output.glob('attempt*.json')}
    (args.output/'manifest.json').write_text(json.dumps({'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':manifest},indent=2)+'\n')
