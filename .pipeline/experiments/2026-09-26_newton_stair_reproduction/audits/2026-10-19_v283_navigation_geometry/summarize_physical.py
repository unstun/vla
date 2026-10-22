"""Assemble all ten actual attempts from locally returned, hash-verified evidence."""
from pathlib import Path
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
RETURN = HERE / 'physical_return'
VERSIONS = HERE.parents[1] / 'versions'
load = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inventory = load(RETURN / 'return_inventory.json')
for name, expected in inventory['analysis_source_files'].items():
    assert sha(HERE / name) == expected, name
selection = load(VERSIONS / 'v283/selection.json')['selected']
assert len(selection) == len(inventory['videos']) == 10
for relative, record in inventory['files'].items():
    assert sha(RETURN / relative) == record['sha256'], relative
for name, record in inventory['videos'].items():
    path = HERE / 'delivered' / name
    assert path.is_file() and not path.is_symlink() and sha(path) == record['sha256'], name

rows = []
for selected in selection:
    case = selected['case_id']
    directory = RETURN / case
    result = directory / 'results'
    outcome = load(result / 'outcome.json')
    route = load(result / 'full_route_verification.json')
    pd = load(result / 'terminal_pd_hold.json')
    scan = load(result / 'scanner_timing_summary.json')
    metrics = load(result / 'metrics.json')
    diagnostic = load(result / 'physical_diagnostics.json')
    windows = load(result / 'window_audit.json')['windows']
    support = load(result / 'physical_support_summary.json')
    navigation = windows['navigation_since_goal_request']
    gap = support['windows']['navigation_since_goal_request']
    cross = windows.get('cross_floor_transition')
    video = load(directory / 'video_checks/delivery_verification.json')
    assert support['existing_verdict_and_ENV_parity']
    assert video['passed'] and video['full_decode_passed'] and video['render_only_no_physics_steps']
    assert outcome['full_route_gate_passed'] == route['passed']
    assert scan['period_s'] == .1
    completed = navigation['completed_rounds']
    success = navigation['successful_rounds']
    measured_geometry_clear = (
        navigation['native_static_support']['free'] == navigation['native_static_support']['samples']
        and navigation['native_static_support']['samples'] > 0
        and navigation['source_solid_margin_min_m'] >= -1e-10
        and navigation['raw_point_margin_min_m'] >= -1e-10)
    rows.append(dict(case_id=case, stratum=selected.get('stratum'),
        terminal=outcome['terminal_status'], full_route_passed=route['passed'],
        terminal_pd_passed=pd['passed'], goal_and_pd_passed=bool(route['passed'] and pd['passed']),
        measured_geometry_clear=measured_geometry_clear,
        goal_pd_and_measured_geometry_clear=bool(route['passed'] and pd['passed'] and measured_geometry_clear),
        simulation_duration_s=outcome['physics_duration_s'],
        local_successes=success, local_completed=completed,
        local_success_rate=success / completed if completed else None,
        pauses_ge_05s=navigation['measured']['count_ge_05s'],
        pauses_ge_1s=navigation['measured']['count_ge_1s'],
        maximum_pause_s=navigation['measured']['max_single_s'],
        cross_floor_pauses_ge_05s=cross['measured']['count_ge_05s'] if cross else None,
        cross_floor_pauses_ge_1s=cross['measured']['count_ge_1s'] if cross else None,
        physical_gap_min_m=gap['minimum_gap_all_samples_m'],
        physical_gap_on_free_min_m=gap['minimum_gap_on_free_support_m'],
        ENV_edge_min_m=navigation['edge_margin']['minimum_m'],
        source_solid_min_m=navigation['source_solid_margin_min_m'],
        raw_point_min_m=navigation['raw_point_margin_min_m'],
        raw_negative_samples=navigation['raw_point_negative_samples'],
        hard_support_free=navigation['native_static_support']['free'],
        hard_support_samples=navigation['native_static_support']['samples'],
        hard_support_verdict_counts=navigation['native_static_support']['verdict_counts'],
        final_xy_error_m=diagnostic['final_xy_error_m'],
        final_height_error_m=diagnostic['final_height_error_m'],
        final_yaw_error_rad=route.get('final_yaw_error_rad'),
        final_pd_duration_s=pd['duration_s'],
        emergency_publications=len(navigation['emergency_times_s']),
        scanner_jobs=scan['jobs'], scanner_deadline_failures=scan['deadline_failures'],
        maximum_scan_ms=scan['maximum_total_ms'],
        native_process_failure=outcome['process_failure']['present'],
        endpoint_rejection_log_lines=diagnostic['endpoint_rejection_log_lines'],
        planner_failure_log_lines=diagnostic['planner_failure_log_lines'],
        static_readiness_unavailable_log_lines=diagnostic['static_readiness_unavailable_log_lines'],
        live_feedback_log_count=diagnostic['live_feedback_log_count'],
        video_file=f'delivered/v283_{case}_full_attempt01.mp4',
        video_sha256=video['video_sha256'], video_frames=video['frames'],
        video_full_decode_passed=True, margin_samples=support['samples']))

summary = dict(native='v283', execution='v283', formal_attempts=10, attempts_per_case=1,
    zero_physics_launch_rejections=5, zero_physics_launch_rejections_in_denominator=False,
    selected_baseline='v232/v233 unchanged',
    native_manifest_sha256=sha(VERSIONS / 'v283/native_manifest.json'),
    execution_manifest_sha256=sha(VERSIONS / 'v283/manifest.json'),
    goal_and_pd_passed=sum(row['goal_and_pd_passed'] for row in rows),
    goal_pd_and_measured_geometry_clear=sum(row['goal_pd_and_measured_geometry_clear'] for row in rows),
    recorded_finished=sum(row['terminal'] == 'FINISHED' for row in rows),
    scanner_jobs=sum(row['scanner_jobs'] for row in rows),
    scanner_deadline_failures=sum(row['scanner_deadline_failures'] for row in rows),
    native_process_failures=sum(row['native_process_failure'] for row in rows),
    margin_parity_samples=sum(row['margin_samples'] for row in rows),
    local_full_videos=10, video_bytes=sum(r['bytes'] for r in inventory['videos'].values()),
    compact_files=len(inventory['files']), compact_bytes=sum(r['bytes'] for r in inventory['files'].values()),
    cases=rows, notes=[
        'Single formal attempt per distinct case; no statistical reliability claim.',
        'Navigation windows exclude factory startup and final PD; initial planning waits and in-place turns remain in low-speed counts.',
        'Physical support and source/raw solid margins use 10 Hz measured body poses; not foot-contact or continuous-time certification.',
        'Margins saturate at +0.15 m. ENV soft atlas is reported separately from physical support.',
        'Resource overlap during physics is preserved in the resource-watch history; no all-idle-host timing claim.',
        'Recorded FINISHED, goal/PD acceptance and measured geometric excursions are separate fields.'])
(HERE / 'physical_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
with (HERE / 'physical_table.csv').open('w') as output:
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v) if isinstance(v, dict) else v for k, v in row.items()})
print(json.dumps({k: v for k, v in summary.items() if k not in ('cases', 'notes')}))
