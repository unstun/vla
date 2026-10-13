"""Trace original planning, identity and applied-control records around the stall."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
RUN = BASE / 'runs/v52_realtime_trial02'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE / 'versions/v51'))
import artifacts


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def rows(name):
    with artifacts.open_text(RUN, name) as stream:
        for number, line in enumerate(stream, 1):
            yield number, json.loads(line)


def owner(data):
    return {key:data.get(key) for key in ('run_id', 'epoch', 'request_id', 'goal_id',
        'route_id', 'command_id', 'generation', 'map_epoch', 'map_revision')}


def main():
    spec = importlib.util.spec_from_file_location('original_parser', BASE / 'versions/v47/analyze_trial.py')
    parser = importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
    with artifacts.open_text(RUN, 'scan.log') as stream:
        text = stream.read()
    class Log:
        def read_text(self): return text
    starts, rounds = parser.parse_rounds(Log())
    lines = text.splitlines()
    focused = []
    markers = ('V48_WARM_SEED', 'V48_WARM_RESULT', 'reactive_stair_seed_search_failed',
        'First three control points', 'rebound_no_valid_new_constraints',
        'initial_spline_collision', 'near_sensor_verdict', 'reactive_collision_blocked',
        'reference_prefix_proposal', 'P2B_ROUTE', 'fixed_height_recovery',
        'reference_window_committed', 'final_plan_success=', 'V47_WINDOW_HINT')
    for row in rounds:
        if not 39 <= row['ros_s'] <= 47: continue
        item = dict(row)
        segment = lines[row['start_line'] - 1:row['end_line']]
        item['warm_seeds'] = [dict(selected=bool(int(m[0])), reason=m[1])
            for line in segment for m in re.findall(r'V48_WARM_SEED selected=(\d+) reason=(\S+)', line)]
        item['profiles'] = [json.loads(line.split('V50_PROFILE ', 1)[1])
                           for line in segment if 'V50_PROFILE ' in line]
        item['seeds'] = [dict(sha256=hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest(),
            seed=seed) for line in segment if 'spline_seed_capture ' in line
            for seed in [json.loads(line.split('spline_seed_capture ', 1)[1])]]
        item['evidence'] = [dict(line=row['start_line'] + i, text=line)
                           for i, line in enumerate(segment) if any(k in line for k in markers)]
        focused.append(item)
    last_success = max((r for r in rounds if r['success']), key=lambda r:r['start_wall_s'])
    first_persistent_failure = next(r for r in focused if r['start_wall_s'] > last_success['start_wall_s'])
    low = min(r['start_wall_s'] for r in focused)
    high = max(r['start_wall_s'] + r['wall_s'] for r in focused)
    observations, kinds = [], Counter()
    for number, event in rows('artifacts/reactive_observations.jsonl'):
        kinds[event['event']] += 1
        wall = event['wall_monotonic_ns'] / 1e9
        if not low - 1 <= wall <= high + 1: continue
        if event['event'] not in ('bspline', 'pct_route', 'scan_admission', 'raw_command', 'gated_command'): continue
        data = event['data']
        item = dict(source_line=number, event=event['event'], wall_s=wall,
                    clock_s=None if event.get('clock_ns') is None else event['clock_ns'] / 1e9,
                    owner=owner(data))
        if event['event'] == 'bspline':
            stamp = data['start_time']; start = stamp['sec'] + stamp['nanosec'] * 1e-9
            duration = data['knots'][-data['order'] - 1] - data['knots'][data['order']]
            item.update(traj_id=data['traj_id'], start_sim_s=start, duration_s=duration,
                        end_sim_s=start + duration, emergency_stop=data.get('emergency_stop'),
                        first_point=data['pos_pts'][0], last_point=data['pos_pts'][-1])
        elif event['event'] == 'pct_route':
            poses = data.get('path', {}).get('poses', [])
            item.update(path_points=len(poses), path_sha256=hashlib.sha256(json.dumps(poses, sort_keys=True).encode()).hexdigest(),
                        first_point=poses[0]['pose']['position'], last_point=poses[-1]['pose']['position'])
        else: item['data'] = data
        observations.append(item)
    applied, reasons = [], Counter()
    for number, row in rows('applied_sent.jsonl'):
        state = row['snapshot']
        if not 39 <= state['sim_time_s'] <= 47: continue
        reasons[state['command_reason']] += 1
        applied.append(dict(source_line=number, sim_s=state['sim_time_s'],
            wall_s=state['wall_monotonic_ns'] / 1e9, command_reason=state['command_reason'],
            raw_command=state['raw_command'], admitted_command=state['admitted_command'],
            applied_command=state['applied_command'], measured=state['measured'],
            command_stale=state['command_stale']))
    result = dict(run=RUN.name, last_success=last_success, first_persistent_failure=first_persistent_failure,
        focused_rounds=focused, observations=observations, observation_kinds=dict(kinds),
        applied_rows=applied, applied_reasons=dict(reasons),
        scope='Original recorded order; observer receipt alone does not establish native callback application')
    (HERE / 'timeline.json').write_text(json.dumps(result, indent=2) + '\n')
    samples = [min(applied, key=lambda x:abs(x['sim_s'] - t))
               for t in (39, 40, 41, 42.338, 42.353, 42.8, 43.38, 43.85, 44.35, 45, 46.9)]
    compact = dict(result); compact.pop('applied_rows'); compact['applied_samples'] = samples
    (HERE / 'timeline_compact.json').write_text(json.dumps(compact, indent=2) + '\n')
    with (HERE / 'rounds.csv').open('w') as stream:
        writer = csv.writer(stream); writer.writerow(['simulation_s', 'wall_s', 'solve_ms', 'success', 'search_attempts', 'warm_reasons'])
        writer.writerows((r['ros_s'], r['start_wall_s'], r['wall_s'] * 1000, r['success'],
            r['rebound_attempts'], ','.join(x['reason'] for x in r['warm_seeds'])) for r in focused)
    summary = dict(last_success=last_success, first_persistent_failure={k:first_persistent_failure[k]
        for k in ('ros_s', 'start_wall_s', 'wall_s', 'warm_seeds')}, observation_kinds=dict(kinds),
        applied_reasons=dict(reasons), focused_rounds=len(focused), focused_observations=len(observations))
    (HERE / 'timeline_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    receipt = json.loads((RUN / 'raw_capture_manifest.json').read_text())
    identity = dict(script_sha256=digest(Path(__file__)), archive_sha256=receipt['archive_sha256'],
        original_sources={n:receipt['members'][n] if n in receipt['members'] else
                         dict(sha256=digest(RUN / n), bytes=(RUN / n).stat().st_size)
                         for n in ('scan.log', 'artifacts/reactive_observations.jsonl', 'applied_sent.jsonl')})
    (HERE / 'timeline_identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__': main()
