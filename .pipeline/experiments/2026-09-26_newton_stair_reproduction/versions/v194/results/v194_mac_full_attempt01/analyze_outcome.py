"""Supplement frozen v194 analysis with final-pose, recovery and comparison evidence."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def yaw(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def main():
    trial = Path(sys.argv[1]).resolve()
    capture = Capture(trial / 'runs' / trial.name)
    result = capture.json('result.json')
    driver = capture.json('artifacts/stair_driver_result.json')
    frames = capture.json('video_states.json')
    observations = capture.rows('artifacts/reactive_observations.jsonl')
    scenario = capture.json('inputs/stair_scenario.json')
    original = json.loads((VERSION.parents[1] / 'inputs/historical_full_building.json').read_text())
    contract = json.loads((VERSION / 'navigation_contract.json').read_text())
    clock = capture.rows('clock_samples.jsonl')
    sync = [r for r in clock if r.get('accepted') and r.get('samples', 0) >= 500]
    assert sync and len({r['responder'] for r in sync}) == 1
    remote = np.array([r['remote'] / 1e9 for r in sync])
    offsets = np.array([r['filtered_offset_ns'] / 1e9 for r in sync])
    assert np.all(np.diff(remote) > 0)

    def host(stamp):
        return stamp + float(np.interp(stamp, remote, offsets))

    commands = [r for r in observations if r['event'] == 'gated_command']
    stops, active, moving = [], None, False
    for row in commands:
        data = row['data']
        zero = max(abs(data[group][axis]) for group in ('linear', 'angular')
                   for axis in ('x', 'y', 'z')) <= 1e-8
        stamp = host(row['wall_monotonic_ns'] / 1e9)
        if moving and zero:
            active = dict(start_host_wall_s=stamp, start_sim_s=row['clock_ns'] / 1e9,
                          resumed=False)
            stops.append(active)
        elif active is not None and not zero:
            active.update(end_host_wall_s=stamp, end_sim_s=row['clock_ns'] / 1e9,
                          wall_duration_s=stamp - active['start_host_wall_s'], resumed=True)
            active = None
        moving = not zero
    if active is not None:
        stamp = host(commands[-1]['wall_monotonic_ns'] / 1e9)
        active.update(end_host_wall_s=stamp, end_sim_s=commands[-1]['clock_ns'] / 1e9,
                      wall_duration_s=stamp - active['start_host_wall_s'],
                      end_boundary='last recorded command, no restart')

    routes = [r['data'] for r in observations if r['event'] == 'pct_route']
    endpoints = [r['poses'][-1]['pose'] for r in routes]
    assert endpoints
    desired_yaw = yaw([endpoints[0]['orientation'][k] for k in ('x', 'y', 'z', 'w')])
    final_yaw = yaw(frames[-1]['joint_q'][3:7])
    final_xyz = frames[-1]['joint_q'][:3]
    target = scenario['goal_ground_xyz_m']
    xy_error = math.dist(final_xyz[:2], target[:2])
    z_error = abs(final_xyz[2] - target[2] - original['locomotion_reference_height_m'])
    yaw_error = abs(math.atan2(math.sin(final_yaw - desired_yaw), math.cos(final_yaw - desired_yaw)))
    log = capture.read('nav2.log')
    lines = log.splitlines()

    def matches(text):
        return [dict(line=i + 1, text=line) for i, line in enumerate(lines) if text in line]

    transitions = [dict(line=i + 1, text=line, previous=m.group(1), next=m.group(2))
                   for i, line in enumerate(lines)
                   if (m := re.search(r'from (\w+) to (\w+)', line))
                   and 'EMERGENCY_STOP' in (m.group(1), m.group(2))]
    terminal_rows = [i for i, line in enumerate(lines)
                     if any(text in line for text in ('Navigation failed', 'Navigation succeeded', 'Reached the goal'))]
    terminal_index = terminal_rows[-1] if terminal_rows else len(lines) - 1
    excerpt = [dict(line=i + 1, text=lines[i])
               for i in range(max(0, terminal_index - 60), min(len(lines), terminal_index + 10))]
    final_control = (driver.get('final_snapshot') or {}).get('control', {})
    metrics = json.loads((HERE / 'metrics.json').read_text())
    gate = json.loads((HERE / 'full_route_verification.json').read_text())
    report = dict(
        run=trial.name, integration_version='v194', native_version='v194',
        terminal_status=result['finish_request']['backend_terminal_status'],
        route_arrived=driver.get('route_arrived', False),
        driver_execution_completed=driver.get('execution_completed', False),
        driver_error=driver.get('error'), full_route_gate_passed=gate['passed'],
        final_xy_error_m=xy_error, final_height_error_m=z_error, final_yaw_error_rad=yaw_error,
        desired_goal_yaw_rad=desired_yaw, final_body_yaw_rad=final_yaw,
        final_body_xyz_m=final_xyz, original_goal_ground_xyz_m=target,
        reference_body_height_m=original['locomotion_reference_height_m'],
        final_control=final_control,
        final_pd_hold=final_control.get('stance_mode') == 'FIXED_STAND'
                      and final_control.get('policy_owns_joints') is False,
        pose_tolerances=dict(xy_m=contract['xy_goal_tolerance_m'],
                            z_m=contract['z_goal_tolerance_m'], yaw_rad=contract['yaw_goal_tolerance_rad']),
        final_pose_within_tolerances=(xy_error <= contract['xy_goal_tolerance_m']
                                     and z_error <= contract['z_goal_tolerance_m']
                                     and yaw_error <= contract['yaw_goal_tolerance_rad']),
        canonical_terminal_pose_unchanged=all(p == endpoints[0] for p in endpoints),
        pct_route_publications=len(routes),
        bspline_publications=sum(r['event'] == 'bspline' for r in observations),
        recorded_states=len(frames), first_physics_s=frames[0]['physics_time_s'],
        last_physics_s=frames[-1]['physics_time_s'],
        recorded_state_body_path_m=sum(math.dist(a['joint_q'][:3], b['joint_q'][:3])
                                      for a, b in zip(frames, frames[1:])),
        measured_sensor_body_path_m=metrics['measured_path_m'],
        navigation_sim_s=metrics['navigation_sim_duration_s'],
        navigation_wall_s=metrics['navigation_wall_duration_s'], actual_rtf=metrics['actual_rtf'],
        local_planning_successful_wall_hz=metrics['planning']['successful_wall_hz'],
        controller_wall_hz=metrics['controller']['/quad_0/cmd_vel']['wall_hz'],
        emergency_stop_transitions=sum(r['next'] == 'EMERGENCY_STOP' for r in transitions),
        emergency_stop_entries=sum(r['next'] == 'EMERGENCY_STOP' and r['previous'] != 'EMERGENCY_STOP' for r in transitions),
        emergency_stop_self_transitions=sum(r['next'] == r['previous'] == 'EMERGENCY_STOP' for r in transitions),
        emergency_stop_exits=sum(r['previous'] == 'EMERGENCY_STOP' and r['next'] != 'EMERGENCY_STOP' for r in transitions),
        emergency_stop_transition_log=transitions,
        native_trajectory_timeouts=matches('Native SCAN did not publish a trajectory before timeout'),
        invalid_trajectory_samples=matches('Native SCAN trajectory sample invalid'),
        completed_wait_recoveries=matches('wait completed successfully'),
        progress_checker_failures=matches('Failed to make progress'),
        recovery_log_excerpt=[dict(line=j + 1, text=lines[j])
                              for i, line in enumerate(lines) if 'Failed to make progress' in line
                              for j in range(max(0, i - 8), min(len(lines), i + 12))],
        direct_command_stop_count=len(stops),
        direct_command_restarted_stop_count=sum(r['resumed'] for r in stops),
        direct_command_zero_wall_s=sum(r['wall_duration_s'] for r in stops),
        direct_command_stops=stops,
        stop_definition='Direct cmd_vel nonzero-to-zero transitions at 1e-8 tolerance; initial zeros excluded. Original observer timestamps mapped to host clock. Not physical-stop proofs.',
        measured_stop_proofs=None, measured_stop_wait_s=None,
        recovery_boundary='Option B has no P2B measured-stop proof. SCAN emergency transitions/exits, completed Nav2 Wait recoveries and command-zero transitions are separate counts; none alone proves physical holding.',
        event_counts=dict(collections.Counter(r['event'] for r in observations)),
        fallen=result.get('fallen', False), dropped_physics_steps=metrics['dropped_physics_steps'],
        shared_state_verified=metrics['shared_state_verified'],
        terminal_log_excerpt=excerpt, source_files=capture.sources,
        analyzer_sha256=sha(Path(__file__)),
        claim='One frozen Mac CPU Newton / ARM64 Foxy trial; no repeated reliability, collision-clearance, sustained 30 Hz or real-robot claim.')
    assert report['emergency_stop_transitions'] == metrics['emergency_transitions']
    (HERE / 'trial_analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    (HERE / 'terminal_log_excerpt.txt').write_text('\n'.join(f"{r['line']}: {r['text']}" for r in excerpt) + '\n')
    for name in ('shared_state.json', 'retention_result.json', 'process.json', 'result.json'):
        (HERE / name).write_text(capture.read(name))
    shutil.copyfile(trial / 'evidence/execution.json', HERE / 'execution.json')
    print(json.dumps({k:report[k] for k in (
        'terminal_status', 'route_arrived', 'full_route_gate_passed', 'final_xy_error_m',
        'final_height_error_m', 'final_yaw_error_rad', 'canonical_terminal_pose_unchanged',
        'emergency_stop_transitions', 'emergency_stop_exits', 'direct_command_stop_count',
        'direct_command_restarted_stop_count', 'direct_command_zero_wall_s')}, indent=2))


if __name__ == '__main__':
    main()
