"""Measure the closed v192 failure without promoting process exit to arrival."""
from pathlib import Path
import collections
import hashlib
import json
import math
import re
import shutil
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1]
sys.path.insert(0, str(VERSION))
from analyze_remote import Capture

TRIAL = Path('/private/tmp/vla_stop_audit_20261012/v192_mac_full_attempt01')
SOURCE = TRIAL / 'runs' / TRIAL.name


def yaw(q):
    x, y, z, w = q
    return math.atan2(2 * (w*z + x*y), 1 - 2*(y*y + z*z))


def main():
    capture = Capture(SOURCE)
    result = capture.json('result.json')
    driver = capture.json('artifacts/stair_driver_result.json')
    frames = capture.json('video_states.json')
    obs = capture.rows('artifacts/reactive_observations.jsonl')
    clock = capture.rows('clock_samples.jsonl')
    sync = [r for r in clock if r.get('accepted') and r.get('samples', 0) >= 500]
    assert sync and len({r['responder'] for r in sync}) == 1
    remote = np.array([r['remote']/1e9 for r in sync])
    offsets = np.array([r['filtered_offset_ns']/1e9 for r in sync])
    def host(value):
        return value + float(np.interp(value, remote, offsets))
    commands = [r for r in obs if r['event'] == 'gated_command']
    stops, active, moving = [], None, False
    for row in commands:
        d = row['data']
        zero = max(abs(d[group][axis]) for group in ('linear', 'angular') for axis in ('x', 'y', 'z')) <= 1e-8
        stamp = host(row['wall_monotonic_ns']/1e9)
        if moving and zero:
            active = {'start_host_wall_s': stamp, 'start_sim_s': row['clock_ns']/1e9,
                      'resumed': False}
            stops.append(active)
        elif active is not None and not zero:
            active.update(end_host_wall_s=stamp, end_sim_s=row['clock_ns']/1e9,
                          wall_duration_s=stamp-active['start_host_wall_s'], resumed=True)
            active = None
        moving = not zero
    if active is not None:
        stamp = host(commands[-1]['wall_monotonic_ns']/1e9)
        active.update(end_host_wall_s=stamp, end_sim_s=commands[-1]['clock_ns']/1e9,
                      wall_duration_s=stamp-active['start_host_wall_s'],
                      end_boundary='last recorded command, no restart')
    route = next(r['data'] for r in obs if r['event'] == 'pct_route')
    orientation = route['poses'][-1]['pose']['orientation']
    desired_yaw = yaw([orientation[k] for k in ('x', 'y', 'z', 'w')])
    final_yaw = yaw(frames[-1]['joint_q'][3:7])
    scenario = capture.json('inputs/stair_scenario.json')
    log = capture.read('nav2.log')
    lines = log.splitlines()
    timeout_rows = [{'line': i+1, 'text': line} for i, line in enumerate(lines)
                    if 'Native SCAN did not publish a trajectory before timeout' in line]
    wait_rows = [{'line': i+1, 'text': line} for i, line in enumerate(lines)
                 if 'wait completed successfully' in line]
    failure_index = next(i for i, line in enumerate(lines) if ']: Navigation failed' in line)
    excerpt = [{'line': i+1, 'text': lines[i]}
               for i in range(max(0, failure_index-45), min(len(lines), failure_index+5))]
    old_path = VERSION.parent / 'v189/results/v189_mac_full_attempt01/recovery_proofs.json'
    old = json.loads(old_path.read_text())
    report = {
        'run': TRIAL.name, 'integration_version': 'v192', 'native_version': 'v191',
        'route_arrived': driver.get('route_arrived', False),
        'driver_execution_completed': driver['execution_completed'],
        'terminal_status': result['finish_request']['backend_terminal_status'],
        'driver_error': driver.get('error'), 'full_route_accepted': False,
        'final_held_pose_available': False,
        'last_recorded_xy_error_m': math.dist(frames[-1]['joint_q'][:2], scenario['goal_ground_xyz_m'][:2]),
        'last_recorded_yaw_error_rad': abs(math.atan2(math.sin(final_yaw-desired_yaw), math.cos(final_yaw-desired_yaw))),
        'last_recorded_body_xyz_m': frames[-1]['joint_q'][:3],
        'recorded_states': len(frames), 'first_physics_s': frames[0]['physics_time_s'],
        'last_physics_s': frames[-1]['physics_time_s'],
        'direct_command_stop_count': len(stops),
        'direct_command_restarted_stop_count': sum(r['resumed'] for r in stops),
        'direct_command_zero_wall_s': sum(r['wall_duration_s'] for r in stops),
        'direct_command_restarted_zero_wall_s': sum(r['wall_duration_s'] for r in stops if r['resumed']),
        'direct_command_stops': stops,
        'stop_definition': 'Direct cmd_vel nonzero-to-zero transitions at 1e-8 tolerance; initial zeros excluded. Durations use original mapped observer timestamps. Not physical-stop proofs.',
        'native_trajectory_timeouts': timeout_rows, 'completed_wait_recoveries': wait_rows,
        'terminal_log_excerpt': excerpt, 'event_counts': dict(collections.Counter(r['event'] for r in obs)),
        'comparison': {
            'v189_replacement_stops': old['replacement_owners'],
            'v189_cancel_to_proof_wall_s': sum(r['cancel_to_proof_wall_s'] for r in old['entries']),
            'v189_proof_to_new_route_wall_s': sum(r['proof_to_new_route_wall_s'] for r in old['entries']),
            'v189_proofs_sha256': hashlib.sha256(old_path.read_bytes()).hexdigest(),
            'v192_measured_stop_proofs': None, 'v192_measured_stop_wait_s': None,
            'same_full_route_comparison_available': False,
            'boundary': 'v189 traversed the route but failed its final held-yaw gate. v192 did not arrive. Option B removed P2B measured-stop proofs; command-zero durations are a different metric.'},
        'source_files': capture.sources,
        'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    assert not report['route_arrived'] and report['terminal_status'] == 'FAILED'
    (HERE / 'failure_metrics.json').write_text(json.dumps(report, indent=2)+'\n')
    (HERE / 'terminal_log_excerpt.txt').write_text('\n'.join(f"{r['line']}: {r['text']}" for r in excerpt)+'\n')
    for name in ('shared_state.json', 'retention_result.json', 'process.json', 'result.json'):
        (HERE / name).write_text(capture.read(name))
    shutil.copyfile(TRIAL / 'evidence/execution.json', HERE / 'execution.json')
    print(json.dumps({key: report[key] for key in (
        'route_arrived', 'terminal_status', 'last_recorded_xy_error_m',
        'direct_command_stop_count', 'direct_command_restarted_stop_count',
        'direct_command_zero_wall_s', 'direct_command_restarted_zero_wall_s', 'comparison')}, indent=2))


if __name__ == '__main__':
    main()
