"""Append observed-prefix metrics without fabricating the missing final result."""
from pathlib import Path
import collections
import csv
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
from analyze_remote import Capture, core

ROOT = Path('/private/tmp/vla_stop_audit_20261012/v191_mac_full_attempt01')
SOURCE = ROOT / 'runs' / ROOT.name


def yaw(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def main():
    c = Capture(SOURCE)
    assert not (SOURCE / 'result.json').exists()
    t = c.rows('telemetry.jsonl')
    v = c.json('video_states.json')
    obs = c.rows('artifacts/reactive_observations.jsonl')
    clock = c.rows('clock_samples.jsonl')
    sync = [r for r in clock if r.get('accepted') and r.get('samples', 0) >= 500]
    assert sync and len({r['responder'] for r in sync}) == 1
    remote = np.array([r['remote'] / 1e9 for r in sync])
    offset = np.array([r['filtered_offset_ns'] / 1e9 for r in sync])
    def host(value):
        return value + float(np.interp(value, remote, offset))
    text = c.read('nav2.log')
    class Log:
        def read_text(self):
            return text
    starts, rounds = core.parse_rounds(Log())
    pace = t[-1]['realtime_pacing']
    begin = pace['wall_anchor_monotonic_s']
    end = begin + pace['wall_elapsed_s']
    selected = [r for r in rounds if begin <= host(r['start_wall_s'] + r['wall_s']) <= end]
    with (HERE / 'latency.csv').open('w') as f:
        w = csv.writer(f)
        w.writerow(['simulation_s', 'wall_s_host', 'solve_ms', 'success', 'warm_accepts'])
        w.writerows((r['ros_s'], host(r['start_wall_s']), r['wall_s'] * 1000, int(r['success']), 0) for r in selected)
    routes = [r for r in obs if r['event'] == 'pct_route']
    splines = [r for r in obs if r['event'] == 'bspline']
    commands = [r for r in obs if r['event'] == 'gated_command']
    moving = False
    stops = []
    for r in commands:
        d = r['data']
        zero = max(abs(d['linear'][k]) for k in ('x', 'y', 'z')) <= 1e-8 and max(abs(d['angular'][k]) for k in ('x', 'y', 'z')) <= 1e-8
        if moving and zero:
            stops.append({'clock_ns': r['clock_ns'], 'host_wall_s': host(r['wall_monotonic_ns'] / 1e9)})
        moving = not zero
    scenario = c.json('inputs/stair_scenario.json')
    goal_q = routes[0]['data']['poses'][-1]['pose']['orientation']
    gy = yaw([goal_q[k] for k in ('x', 'y', 'z', 'w')])
    fy = yaw(v[-1]['joint_q'][3:7])
    old_path = VERSION.parent / 'v189/results/v189_mac_full_attempt01/recovery_proofs.json'
    old = json.loads(old_path.read_text())
    comparison = {
        'v189_replacement_stops': old['replacement_owners'],
        'v189_cancel_to_proof_wall_s': sum(r['cancel_to_proof_wall_s'] for r in old['entries']),
        'v189_proof_to_new_route_wall_s': sum(r['proof_to_new_route_wall_s'] for r in old['entries']),
        'user_reference_wait_s': 34.22,
        'v189_proofs_sha256': hashlib.sha256(old_path.read_bytes()).hexdigest(),
        'comparable_full_route': False,
        'reason': 'v191 interrupted near the start and removed the measured-stop protocol; zero observed stops is not improvement evidence.',
    }
    failure = c.json('applied_client_failure.json')
    copyback = c.json('state_copyback.json')
    metrics = {
        'run': ROOT.name, 'status': 'interrupted_applied_ack_timeout', 'full_qualification': False,
        'navigation_completed': False, 'final_result_available': False,
        'navigation_sim_duration_s': pace['native_elapsed_s'],
        'navigation_wall_duration_s': pace['wall_elapsed_s'], 'actual_rtf': pace['actual_rtf'],
        'measurement_boundary': 'Last completed telemetry pacing sample; excludes failed next ACK and process teardown.',
        'last_recorded_physics_s': v[-1]['physics_time_s'], 'recorded_states': len(v),
        'last_recorded_xy_error_m': math.dist(v[-1]['joint_q'][:2], scenario['goal_ground_xyz_m'][:2]),
        'last_recorded_yaw_error_rad': abs(math.atan2(math.sin(fy - gy), math.cos(fy - gy))),
        'last_recorded_yaw_rad': fy, 'requested_goal_yaw_rad': gy,
        'final_held_xy_error_m': None, 'final_held_yaw_error_rad': None,
        'pct_route_publications': len(routes), 'bspline_publications': len(splines),
        'emergency_stop_splines': sum(bool(r['data'].get('emergency_stop')) for r in splines),
        'direct_command_moving_to_zero_events': len(stops), 'direct_command_stop_events': stops,
        'stop_definition': 'Observed /quad_0/cmd_vel nonzero-to-zero transitions, excluding initial zeros; not physical-stop proof.',
        'measured_stop_proofs': None, 'measured_stop_wait_s': None,
        'protocol_boundary': 'Option B has no P2B measured-stop protocol. The recorder retains the historical event name gated_command for direct Twist.',
        'emergency_transitions': len(re.findall(r'from .* to EMERGENCY_STOP', text)),
        'event_counts': dict(collections.Counter(r['event'] for r in obs)),
        'state_copyback_verified': copyback['verified'], 'final_hold_verified': False,
        'minimum_recorded_base_up_z': min(r['base_up_z'] for r in t),
        'planning': {'completed': len(selected), 'successful': sum(r['success'] for r in selected),
                     'successful_wall_hz': sum(r['success'] for r in selected) / pace['wall_elapsed_s'],
                     'solve_ms': core.distribution([r['wall_s'] * 1000 for r in selected])},
        'frequency_definition': 'Observed interrupted navigation prefix only; host/container clocks mapped from original converged samples.',
        'failed_ack_sequence': failure['sequence'], 'failed_ack_attempts': len(failure['attempts']),
        'ack_timeout_budget_ms_per_attempt': failure['timeout_ms'],
        'failed_ack_total_wall_ms': (failure['attempts'][-1]['timed_out_monotonic_ns'] - failure['attempts'][0]['send_started_monotonic_ns']) / 1e6,
        'comparison': comparison, 'source_files': c.sources,
        'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (HERE / 'partial_metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    for name in ('state_copyback.json', 'applied_client_failure.json', 'retention_result.json', 'process.json'):
        if (SOURCE / name).exists():
            shutil.copyfile(SOURCE / name, HERE / name)
    shutil.copyfile(ROOT / 'evidence/execution.json', HERE / 'execution.json')
    print(json.dumps({k: metrics[k] for k in ('status', 'navigation_sim_duration_s', 'navigation_wall_duration_s', 'actual_rtf', 'last_recorded_xy_error_m', 'last_recorded_yaw_error_rad', 'pct_route_publications', 'bspline_publications', 'direct_command_moving_to_zero_events', 'comparison')}, indent=2))


if __name__ == '__main__':
    main()
