"""Supplement frozen v196 analysis with final-pose, recovery and comparison evidence."""
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
        run=trial.name, integration_version='v196', native_version='v196',
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
    supplement(report, capture, metrics, trial)
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


# Supplemental functions are inserted below before main is called.

def refresh_evidence(capture):
    rows = capture.rows('backend_states.jsonl')
    samples, changes = [], []
    previous = {}
    for row in rows:
        for rid, job in row['data'].get('jobs', {}).items():
            if 'refresh_status' not in job:
                continue
            item = dict(request_id=rid, sim_time_s=row['sim_time_s'],
                        refresh_status=job['refresh_status'], retained_count=job['retained_count'])
            samples.append(item)
            key = (item['refresh_status'], item['retained_count'])
            if previous.get(rid) != key:
                changes.append(item)
            previous[rid] = key
    last = {r['request_id']: r for r in samples}
    return dict(available=bool(samples),
                refresh_status=next(iter(last.values()))['refresh_status'] if len(last) == 1 else None,
                retained_count=sum(r['retained_count'] for r in last.values()) if last else None,
                status_observation_counts=dict(collections.Counter(r['refresh_status'] for r in samples)),
                status_change_counts=dict(collections.Counter(r['refresh_status'] for r in changes)),
                changes=changes, final_jobs=last,
                definition='HTTP backend-state samples: status samples/changes are not exact refresh-event counts. Final retained_count is the mission cumulative fallback count. PCT route publications are counted separately from ROS observations. Missing v194 fields are not zero.')


def pause_evidence(capture, metrics):
    points = capture.rows('sensor.jsonl')
    frames = capture.json('video_states.json')
    timed = [r for r in frames if 'wall_monotonic_s' in r]
    native = np.array([r['physics_time_s'] for r in timed])
    wall = np.array([r['wall_monotonic_s'] for r in timed])
    pauses = []
    for pause in metrics['pauses_over_1s']:
        selected = [p for p in points if pause['start_sim_s'] <= p['sim_time_s'] <= pause['end_sim_s']]
        poses = [p['body_sensor']['position'] for p in selected]
        state = min(frames, key=lambda r: abs(r['physics_time_s'] - pause['start_sim_s']))
        pauses.append(dict(pause, duration_wall_s=float(np.interp(pause['end_sim_s'], native, wall)
                                                       - np.interp(pause['start_sim_s'], native, wall)),
                           mean_xyz_m=np.mean(poses, axis=0).tolist(),
                           start_xyz_m=poses[0], end_xyz_m=poses[-1],
                           start_stance_mode=state.get('stance_mode'),
                           start_policy_owns_joints=state.get('policy_owns_joints')))
    return pauses


def supplement(report, capture, metrics, trial):
    report['pauses_over_1s'] = pause_evidence(capture, metrics)
    report['pause_definition'] = 'Frozen analyzer: measured horizontal speed < 0.05 m/s, consecutive sensor dt < 0.5 s, interval >= 1 simulation second. Includes terminal holding. Wall durations use captured wall/physics timestamp pairs.'
    report['longest_pause_sim_s'] = metrics['longest_pause_sim_s']
    report['pct_refresh'] = refresh_evidence(capture)
    route_stamps = [r['wall_monotonic_ns']/1e9 for r in capture.rows('artifacts/reactive_observations.jsonl')
                    if r['event'] == 'pct_route']
    report['pct_refresh'].update(configured_hz=1.0,
        publication_interval_median_container_wall_s=float(np.median(np.diff(route_stamps))) if len(route_stamps)>1 else None,
        route_publications=len(route_stamps))
    report['source_files'] = capture.sources
    prior_dir = VERSION.parent / 'v194/results/v194_mac_full_attempt01'
    prior = json.loads((prior_dir / 'trial_analysis.json').read_text())
    prior_metrics = json.loads((prior_dir / 'metrics.json').read_text())
    prior_raw = trial.parent / 'v194_mac_full_attempt01/runs/v194_mac_full_attempt01'
    before_capture = Capture(prior_raw)
    prior['pct_refresh'] = refresh_evidence(before_capture)
    prior['pauses_over_1s'] = pause_evidence(before_capture, prior_metrics)
    prior['longest_pause_sim_s'] = prior_metrics['longest_pause_sim_s']
    baseline_stall = max(prior['pauses_over_1s'], key=lambda p: p['duration_sim_s'])
    center = np.array(baseline_stall['mean_xyz_m'])
    frames = capture.json('video_states.json')
    near = [f for f in frames if np.linalg.norm(np.array(f['joint_q'][:3]) - center) <= 1.0]
    nearby_pauses = [p for p in report['pauses_over_1s']
                     if np.linalg.norm(np.array(p['mean_xyz_m']) - center) <= 1.0]
    report['v194_second_floor_stall_comparison'] = dict(
        v194_pause=baseline_stall, spatial_radius_m=1.0,
        v196_visited_neighborhood=bool(near),
        minimum_recorded_distance_m=min(float(np.linalg.norm(np.array(f['joint_q'][:3])-center)) for f in frames),
        v196_nearby_pauses_over_1s=nearby_pauses,
        v196_max_nearby_pause_sim_s=max((p['duration_sim_s'] for p in nearby_pauses), default=0.0),
        ten_second_stall_observed=any(p['duration_sim_s'] >= 10 for p in nearby_pauses),
        claim='Spatial single-capture comparison within 1 m of the old stall mean position; elapsed simulation timestamps are not matched route locations. A missing stall in this run is not repeated reliability evidence.')
    old = json.loads((prior_dir / 'comparison.json').read_text())
    root = VERSION.parents[4]
    for name, expected in old['sources'].items():
        assert sha(root / name) == expected['sha256'], name
    keys = ('terminal_status', 'route_arrived', 'full_route_gate_passed', 'final_pd_hold',
            'final_xy_error_m', 'final_height_error_m', 'final_yaw_error_rad',
            'navigation_sim_s', 'navigation_wall_s', 'actual_rtf',
            'local_planning_successful_wall_hz', 'controller_wall_hz',
            'pct_route_publications', 'pct_refresh', 'pauses_over_1s', 'longest_pause_sim_s',
            'emergency_stop_entries', 'emergency_stop_exits', 'direct_command_stop_count',
            'direct_command_zero_wall_s', 'completed_wait_recoveries', 'native_trajectory_timeouts')
    def summary(r):
        d = {k: r.get(k) for k in keys}
        for k in ('completed_wait_recoveries', 'native_trajectory_timeouts'):
            d[k] = len(d[k]) if isinstance(d[k], list) else d[k]
        return d
    comparison = dict(runs={**{k: v for k, v in old['runs'].items() if k in ('v189','v192')},
                            'v194': summary(prior), 'v196': summary(report)},
                      sources=dict(old['sources']),
                      restored_v194_raw_sources=before_capture.sources,
                      v194_second_floor_stall_comparison=report['v194_second_floor_stall_comparison'],
                      comparison_boundary=old['comparison_boundary'],
                      v196_minus_v194={k: report[k]-prior[k] for k in keys
                                      if isinstance(report.get(k), (int,float))
                                      and not isinstance(report.get(k), bool)
                                      and isinstance(prior.get(k), (int,float))})
    for version in ('v189','v192'):
        row = comparison['runs'][version]
        row['navigation_sim_s'] = row['navigation_sim_duration_s']
        row['navigation_wall_s'] = row['navigation_wall_duration_s']
    for path in (prior_dir/'comparison.json', prior_dir/'trial_analysis.json', HERE/'metrics.json'):
        comparison['sources'][str(path.relative_to(root))] = dict(sha256=sha(path), bytes=path.stat().st_size)
    (HERE/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    def fmt(value):
        if isinstance(value,bool): return str(value).lower()
        if isinstance(value,float): return f'{value:.9f}'
        if value is None: return 'N/A (not recorded)'
        return str(value)
    table = ['| Measurement | v194 | v196 |','|---|---:|---:|']
    for key in keys:
        if key in ('pct_refresh','pauses_over_1s'): continue
        table.append(f'| {key} | {fmt(comparison["runs"]["v194"][key])} | {fmt(comparison["runs"]["v196"][key])} |')
    for key in ('refresh_status','retained_count'):
        table.append(f'| PCT {key} | {fmt(prior["pct_refresh"][key])} | {fmt(report["pct_refresh"][key])} |')
    pause_lines = [f'- {p["start_sim_s"]:.6f}–{p["end_sim_s"]:.6f} s: {p["duration_sim_s"]:.6f} simulation seconds / {p["duration_wall_s"]:.6f} wall seconds; mean XYZ {p["mean_xyz_m"]}.' for p in report['pauses_over_1s']]
    cohort_table = ['| Measurement | v189 | v192 | v194 | v196 |','|---|---:|---:|---:|---:|']
    for key in ('terminal_status','route_arrived','full_route_gate_passed','final_xy_error_m',
                'final_height_error_m','final_yaw_error_rad','navigation_sim_s','navigation_wall_s',
                'actual_rtf','local_planning_successful_wall_hz','controller_wall_hz'):
        cohort_table.append('| '+key+' | '+' | '.join(fmt(comparison['runs'][v].get(key)) for v in ('v189','v192','v194','v196'))+' |')
    outcome = 'passed' if report['full_route_gate_passed'] else 'failed'
    text = f'''# v196 Mac attempt 01: full-route gate {outcome}

Stage: experiment + analysis. This is a new execution after the reboot erased the previous temporary capture. The earlier reported arrival is not recoverable trial evidence and is not combined with this run. Frozen v196 source, configuration and historical qualification files remain unchanged.

The new capture reports **{report['terminal_status']}**, route_arrived={report['route_arrived']}, full_route_gate_passed={report['full_route_gate_passed']}, final_pd_hold={report['final_pd_hold']}. This is one Mac ARM64 CPU Newton / ARM64 Foxy trial, not repeated reliability, sustained 30 Hz, general collision-clearance or real-robot acceptance.

## v194 versus v196

'''+'\n'.join(table)+f'''

Both use direct Nav2 Twist. Rates are wall-clock measurements from the frozen analyzer; simulation/wall time excludes startup and closure. Final height error is relative to original goal ground Z + 0.30 m. The exact final PD state and unchanged goal pose are recorded in trial_analysis.json. Broader v189/v192 comparisons and source hashes are in comparison.json; v192 did not finish and v189 used a different command/recovery path.

## Retained Mac cohorts

'''+ '\n'.join(cohort_table) + f'''

## Pauses and PCT refresh

'''+'\n'.join(pause_lines)+f'''

The old v194 stall lasted {baseline_stall['duration_sim_s']:.6f} s. v196 visited its 1 m neighborhood: {bool(near)}. Its longest >=1 s low-speed interval in that neighborhood was {report['v194_second_floor_stall_comparison']['v196_max_nearby_pause_sim_s']:.6f} s; a >=10 s stall was observed: {report['v194_second_floor_stall_comparison']['ten_second_stall_observed']}. These are spatially compared single captures, not evidence that all future stalls are eliminated. Terminal holding is included in the general pause list.

The configured PCT refresh is 1 Hz. Actual ROS route publications are {report['pct_route_publications']}; final refresh_status={report['pct_refresh']['refresh_status']}, retained_count={report['pct_refresh']['retained_count']}. HTTP status samples and status transitions are reported separately and cannot count every planning invocation. v194 did not export these two counters; unavailable is not zero.

Emergency entries/exits, zero commands and completed Nav2 Wait recoveries are different measurements. Option B has no P2B measured-stop proof. A zero command alone does not establish physical stillness. The final PD hold is checked independently by the original full-route verifier.

## Artifacts and reproducibility

See ARTIFACTS.json, trial_archive_manifest.json and remote_verification.json for the remotely verified closed trial. The rebuilt native overlay and fresh component-test evidence have separate archive identities. Heavy captures remain in the task's temporary Mac workspace and durable gpu5070ti archive. The v197 display, if the route gate passes, replays this capture with zero physics steps.
'''
    (HERE/'RESULTS.md').write_text(text)


if __name__ == '__main__':
    main()
