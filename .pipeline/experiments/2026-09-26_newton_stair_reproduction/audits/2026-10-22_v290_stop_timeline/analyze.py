"""Quantify terminal stop and drift in closed v290 recordings (zero physics).

Run after read_recordings.py, saving its stdout to a local JSON file. Original
source hashes must match the already returned capture manifest. All displacements
are horizontal straight-line displacement, never clearance or distance-to-goal.
"""
import argparse
import bisect
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PRIOR = HERE.parent / '2026-10-21_v290_terrain_terminal/ultra9/physical_return'


def yaw(q):
    w, x, y, z = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def angle(value):
    return math.atan2(math.sin(value), math.cos(value))


def displacement(start, end):
    return math.dist(start['body']['position'][:2], end['body']['position'][:2])


def is_zero(command):
    return max(map(abs, command)) < 1e-9


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(case, data):
    manifest = json.loads((PRIOR / case / 'results/capture_snapshot.json').read_text())
    for name, identity in data['sources'].items():
        assert identity == manifest['members'][name], (case, name, 'capture identity changed')
    rows = data['samples']
    times = [r['physics_time_s'] for r in rows]
    assert all(a < b for a, b in zip(times, times[1:]))
    goal = data['scenario']['goal_ground_xyz_m']
    goal_yaw = data['scenario']['goal_yaw_rad']

    def error(row):
        return math.dist(row['body']['position'][:2], goal[:2])

    def captured(row):
        return error(row) <= .25 and abs(row['body']['position'][2] - goal[2] - .3) <= .2

    entry = next(r for r in rows if captured(r))
    stop = next(r for r in rows if r['physics_time_s'] >= entry['physics_time_s'] and is_zero(r['effective_command']))
    tail = [r for r in rows if r['physics_time_s'] >= stop['physics_time_s']]
    assert all(is_zero(r['effective_command']) for r in tail), 'Stop sequence has a command restart'
    pd = next(r for r in tail if r['stance_mode'] == 'STAND_TRANSITION')
    fixed = next(r for r in tail if r['stance_mode'] == 'FIXED_STAND')
    maximum = max(tail, key=lambda r: displacement(stop, r))
    assert all(r['policy_owns_joints'] for r in tail if r['stance_mode'] == 'STAND_SETTLING')
    assert not pd['policy_owns_joints'] and not fixed['policy_owns_joints']

    def snapshot(row):
        return {'time_s': row['physics_time_s'], 'telemetry_row': row['source_row'],
                'xy_m': row['body']['position'][:2], 'goal_error_cm': error(row) * 100,
                'yaw_error_deg': math.degrees(angle(yaw(row['body']['quaternion']) - goal_yaw)),
                'stance': row['stance_mode'], 'stance_reason': row['stance_reason'],
                'policy_owns_joints': row['policy_owns_joints'],
                'effective_command': row['effective_command'],
                'speed_m_s': math.hypot(*row['body']['linear_world'][:2]),
                'displacement_from_applied_zero_cm': displacement(stop, row) * 100}

    observed = sorted((e for e in data['events'] if e['event'] == 'body_pose_observer'), key=lambda e: e['wall_monotonic_ns'])
    observed_times = [e['wall_monotonic_ns'] for e in observed]
    gated = [e for e in data['events'] if e['event'] == 'gated_command' and e['clock_ns'] / 1e9 >= entry['physics_time_s']]

    def command(event):
        d = event['data']
        return [d['linear']['x'], d['linear']['y'], d['angular']['z']]

    def command_witness(event):
        i = bisect.bisect_right(observed_times, event['wall_monotonic_ns']) - 1
        assert i >= 0
        observer = observed[i]
        p = observer['data']['pose']['pose']
        q = p['orientation']
        stamp = observer['data']['header']['stamp']
        return {'time_s': event['clock_ns'] / 1e9, 'observer_row': observer['source_row'],
                'observer_stamp_s': stamp['sec'] + stamp['nanosec'] * 1e-9,
                'command_row': event['source_row'], 'command': command(event),
                'observed_xy_error_cm': math.hypot(p['position']['x'] - goal[0], p['position']['y'] - goal[1]) * 100,
                'observed_yaw_error_rad': abs(angle(yaw([q[k] for k in ('w', 'x', 'y', 'z')]) - goal_yaw)),
                'association': 'latest recorded body observer received before this gated command; not an instrumented Controller branch trace'}

    first_xy_zero = next(e for e in gated if is_zero(command(e)[:2]))
    first_full_zero = next(e for e in gated if is_zero(command(e)))
    before = gated[gated.index(first_xy_zero) - 1]
    emergency = [e for e in data['events'] if e['event'] == 'bspline' and e['data']['emergency_stop'] and
                 entry['physics_time_s'] <= e['clock_ns'] / 1e9 <= first_full_zero['clock_ns'] / 1e9]
    if case == 'D07':
        assert emergency and emergency[0]['clock_ns'] == first_full_zero['clock_ns']
        assert command_witness(first_full_zero)['observed_yaw_error_rad'] > .25
    else:
        assert not emergency
        assert command_witness(before)['observed_yaw_error_rad'] > .125
        assert command_witness(first_xy_zero)['observed_yaw_error_rad'] <= .125

    margin_path = PRIOR / case / 'results/body_margins_with_raw.csv'
    margins = list(csv.DictReader(margin_path.open()))
    crossed = next(r for r in margins if float(r['native_source_solid_margin_m']) < 0)
    worst = min(margins, key=lambda r: float(r['native_source_solid_margin_m']))

    def margin_witness(margin):
        t = float(margin['time_s'])
        row = min(rows, key=lambda r: abs(r['physics_time_s'] - t))
        assert abs(row['physics_time_s'] - t) < 1e-8
        assert math.dist(row['body']['position'], [float(margin[k]) for k in ('x', 'y', 'z')]) < 1e-7
        return {**snapshot(row), 'source_solid_margin_cm': 100 * float(margin['native_source_solid_margin_m']),
                'raw_point_margin_cm': 100 * float(margin['raw_point_margin_m'])}

    durations = defaultdict(float)
    for a, b in zip(tail, tail[1:]):
        if a['stance_mode'] == 'STAND_SETTLING':
            durations[a['stance_reason']] += b['physics_time_s'] - a['physics_time_s']
    stop_to_pd = pd['physics_time_s'] - stop['physics_time_s']
    assert math.isclose(sum(durations.values()), stop_to_pd, abs_tol=1e-7)

    # Plot values only: keep 1-in-5 telemetry samples plus every named event.
    indices = {i for i, row in enumerate(rows) if row['physics_time_s'] >= entry['physics_time_s'] - .2 and i % 5 == 0}
    for row in (entry, stop, pd, fixed, maximum, rows[-1]):
        indices.add(rows.index(row))
    plot = [{'time_s': rows[i]['physics_time_s'], 'xy_m': rows[i]['body']['position'][:2],
             'drift_cm': displacement(stop, rows[i]) * 100,
             'goal_error_cm': error(rows[i]) * 100, 'stance': rows[i]['stance_mode']}
            for i in sorted(indices)]
    result = {
        'case': case, 'raw_root': data['root'], 'source_identity_matches': True, 'sources': data['sources'],
        'margin_csv_sha256': digest(margin_path), 'goal_ground_xyz_m': goal, 'goal_yaw_rad': goal_yaw,
        'capture_entry': snapshot(entry), 'command_before_stop': command_witness(before),
        'published_xy_zero': command_witness(first_xy_zero), 'published_full_zero': command_witness(first_full_zero),
        'emergency_spline_witnesses': emergency, 'applied_zero': snapshot(stop),
        'pd_transition': snapshot(pd), 'fixed_stand': snapshot(fixed), 'maximum_drift': snapshot(maximum),
        'last_sample': snapshot(rows[-1]), 'first_crossing': margin_witness(crossed), 'worst_margin': margin_witness(worst),
        'stop_to_pd_s': stop_to_pd, 'stop_to_fixed_s': fixed['physics_time_s'] - stop['physics_time_s'],
        'pre_pd_displacement_cm': displacement(stop, pd) * 100,
        'pd_transition_displacement_cm': displacement(pd, fixed) * 100,
        'fixed_stand_tail_displacement_cm': displacement(fixed, rows[-1]) * 100,
        'settling_reason_seconds': dict(durations), 'continuous_zero_to_record_end': True,
        'first_crossing_precedes_applied_zero_s': stop['physics_time_s'] - float(crossed['time_s']),
        'telemetry_sample_dt_min_max_s': [min(b-a for a,b in zip(times,times[1:])),max(b-a for a,b in zip(times,times[1:]))],
        'plot_samples': plot,
        'log_witnesses': [line for line in data['logs'] if
                          ('emergency stop in' in line['text'] and 113000 <= line['line'] <= 114000) or
                          'terminal_settle_timeout' in line['text'] or 'Native SCAN has no executable trajectory' in line['text']],
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=HERE / 'summary.json')
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    assert data['new_physics_steps'] == 0
    source_paths = ['scan_nav2_controller/src/controller.cpp', 'scan_nav2_controller/src/local_motion.cpp',
                    'scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp',
                    'plan_manage/src/scan_replan_fsm.cpp']
    report = {'schema': 1, 'date': '2026-10-22', 'new_physics_steps': 0,
              'analysis_kind': 'closed-recording measurement plus frozen-source branch attribution',
              'extraction_sha256': digest(HERE / 'read_recordings.py'), 'analyzer_sha256': digest(Path(__file__)),
              'source_files': {p: digest(BASE / 'versions/v290/src' / p) for p in source_paths},
              'definitions': {'drift': 'XY Euclidean displacement from first measured all-zero effective-command sample after terminal capture; max is over the entire remaining recording',
                              'pd_entry': 'first STAND_TRANSITION, policy_owns_joints=false; STAND_SETTLING is still RL',
                              'sampling': 'metrics use all ~50 Hz telemetry; plot keeps every fifth row plus named events; source margins are the existing ~10 Hz sampled audit',
                              'clock': 'original physics_time_s for telemetry and clock_ns/1e9 for observer events; no wall-clock log timestamp relabeled as simulation time',
                              'attribution': 'CD12 outer Controller attribution follows measured threshold crossing and code call order; original run did not log per-call branch IDs'},
              'cases': {case: analyze(case, data['cases'][case]) for case in ('D07', 'CD12')}}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for case, r in report['cases'].items():
        print(case, 'maximum drift cm', round(r['maximum_drift']['displacement_from_applied_zero_cm'], 4),
              'wait for PD s', round(r['stop_to_pd_s'], 4), 'pre-PD drift cm', round(r['pre_pd_displacement_cm'], 4))


if __name__ == '__main__':
    main()
