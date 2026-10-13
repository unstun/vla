"""Compact evidence from the recorded chain and the bounded native replay."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path.insert(0, str(BASE / 'versions/v51'))
import artifacts


def curve(message):
    points = np.array([[p[k] for k in ('x', 'y', 'z')] for p in message['pos_pts']])
    knots, degree = message['knots'], message['order']
    return BSpline(knots, points, degree), knots[degree], knots[-degree - 1] - knots[degree]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, default=3)
    args = parser.parse_args()
    path = HERE / f'attempt{args.attempt:02d}'
    result = json.loads((path / 'result.json').read_text())
    assert result['exit_code'] == 0 and result['source_unchanged']
    chain = json.loads((path / 'chain_evidence.json').read_text())
    old, new = chain['old_observed_curve']['data'], chain['recovery_observed_curve']['data']
    old_curve, old_zero, old_duration = curve(old)
    new_curve, new_zero, new_duration = curve(new)
    stamp = lambda m: m['start_time']['sec'] + m['start_time']['nanosec'] * 1e-9
    sample = chain['round']['ros_s']
    initial = chain['seeds'][0]
    pva = [np.array(initial['points'][0]), np.array(initial['derivatives'][0]), np.array(initial['derivatives'][2])]
    old_error, new_error = [], []
    for derivative in range(3):
        a, b = old_curve.derivative(derivative), new_curve.derivative(derivative)
        old_error.append(float(np.linalg.norm(a(old_zero + sample - stamp(old)) - pva[derivative])))
        new_error.append(float(np.linalg.norm(b(new_zero) - pva[derivative])))
    endpoint = old_curve(old_zero + old_duration)
    boundary = dict(old_curve_id=old['traj_id'], new_curve_id=new['traj_id'], original_sample_s=sample,
                    old_nominal_expiry_s=stamp(old) + old_duration, new_origin_s=stamp(new),
                    sample_rebased_by_s=stamp(new) - sample,
                    sampled_pva_old_curve_error=old_error, final_curve_initial_pva_error=new_error,
                    retry_position_max_abs_difference_m=chain['retry_position_max_abs_difference_m'],
                    retry_velocity_acceleration_exact=chain['retry_velocity_acceleration_exact'],
                    previous_endpoint_remaining_xy_m=float(np.linalg.norm((endpoint - pva[0])[:2])),
                    new_target_distance_m=float(np.linalg.norm(np.array(chain['seeds'][-1]['points'][-1]) - pva[0])),
                    old_endpoint=endpoint.tolist(), sampled_position=pva[0].tolist(),
                    new_initial_to_old_endpoint_m=float(np.linalg.norm(new_curve(new_zero) - endpoint)))
    assert max(old_error) < 1e-6 and max(new_error) < 1e-6
    assert boundary['sample_rebased_by_s'] > 1.2
    assert boundary['previous_endpoint_remaining_xy_m'] < .05

    native = (path / 'native.log').read_text().splitlines()
    trials, selected, current = [], [], None
    number = r'[-+\deE.]+'
    for line_number, line in enumerate(native, 1):
        if 'V59_DIAG_' in line or 'A-star failed; aborting optimization' in line:
            selected.append(dict(line=line_number, text=line))
        match = re.search(r'V59_DIAG_OPT_BEGIN case=(\d+) repeat=(\d+) height=(\d+)', line)
        if match:
            current = dict(case=int(match[1]), repeat=int(match[2]), height=bool(int(match[3])), searches=[], endpoints=[])
            trials.append(current)
        match = re.search(r'V59_DIAG_SEARCH_END phase=(\w+) code=(\d+) ms=(' + number + r') from=(.+?) to=(.+)', line)
        if match and current is not None:
            current['searches'].append(dict(phase=match[1], status=int(match[2]), ms=float(match[3]),
                start=[float(v) for v in match[4].split()], end=[float(v) for v in match[5].split()], line=line_number))
        if 'V59_DIAG_ENDPOINT' in line and current is not None:
            current['endpoints'].append(dict(line=line_number, text=line))
    repeat_case = [trial for trial in trials if trial['case'] == 1]
    assert len(repeat_case) == 4
    for trial in repeat_case:
        failed = [row for row in trial['searches'] if row['status'] != 0]
        trial['identical_failed_endpoints'] = bool(failed) and all(row['start'] == failed[0]['start'] and row['end'] == failed[0]['end'] for row in failed)
        assert len(failed) == 3 and trial['identical_failed_endpoints']
    rows = result['rows']['cold_native']
    warm = next(row for row in rows if row['kind'] == 'warm')
    assert warm['remaining_status'] == 0 and warm['warm_reason'] == 'target_connector'
    assert warm['blocked_sample'] == 0 and warm['binding_after_rejection'] == -1
    first = [row for row in rows if row['case'] == 1]
    assert all(row['initial_curve_status'] == 0 and row['accepted'] == 0 and row['final_curve_status'] == 1 for row in first)

    run = BASE / 'runs/v59_realtime_trial01'
    with artifacts.open_text(run, 'scan.log') as stream:
        raw = stream.read()
    lines = raw.splitlines()
    round_ = chain['round']
    live = list(enumerate(lines[round_['start_line'] - 1:round_['end_line']], round_['start_line']))
    evidence = [dict(line=i, text=line) for i, line in live if any(tag in line for tag in
        ('nominal_replan ', 'nominal_replan_result', 'V48_WARM_SEED', 'reference_prefix_proposal', 'A-star path search took',
         'A-star failed;', 'input_refresh', 'fixed_height_recovery', 'V59_TRAJECTORY_EPOCH', 'final_spline_rejected'))]
    replan_offsets = [i for i, (_, line) in enumerate(live) if '[rebo replan]' in line]
    live_attempts = []
    epoch = lambda line: float(re.search(r'\[(\d+\.\d+)\]', line)[1])
    for index, offset in enumerate(replan_offsets):
        end = replan_offsets[index + 1] if index + 1 < len(replan_offsets) else len(live)
        start_line = next(line for _, line in reversed(live[:offset]) if 'site=replan_start' in line)
        stop_line = next((line for _, line in reversed(live[:end]) if re.search(r'\[(\d+\.\d+)\]', line)), None)
        failures = sum('A-star failed; aborting optimization' in line for _, line in live[offset:end])
        live_attempts.append(dict(attempt=index + 1, source_line=live[offset][0], replan_marker=live[offset][1],
                                  following_log_interval_ms=(epoch(stop_line) - epoch(start_line)) * 1000,
                                  optimizer_search_failures=failures))
    summary = dict(recording='v59_realtime_trial01', round=round_, warm=warm, boundary=boundary,
                   native_repeated_trials=trials, native_outcomes=rows, live_attempts=live_attempts,
                   live_failed_optimizer_searches=len(chain['native_fail_log_lines']),
                   source_sha256={'scan.log': hashlib.sha256(raw.encode()).hexdigest(),
                       'native.log': artifacts.digest(path/'native.log'), 'chain_evidence.json': artifacts.digest(path/'chain_evidence.json'),
                       'analyze.py': artifacts.digest(Path(__file__))},
                   limitations=['Replay preserves original observer order, not exact native subscription batching.',
                       'Clock is fixed inside each probe; original live inputs continue changing.',
                       'Caches are shared across diagnostic repeats; these timings are not paired live speedup estimates.',
                       'Candidate optimizer success does not bypass the original subsequent dynamics or full-curve safety gates.',
                       'Nominal curve expiry and common-time PVA are distinct from exact controller pause/receipt state.'])
    (path/'diagnosis.json').write_text(json.dumps(summary, indent=2) + '\n')
    (path/'line_evidence.json').write_text(json.dumps(dict(live=evidence, native=selected), indent=2) + '\n')
    print(json.dumps(dict(boundary=boundary, warm=warm,
        repeated_search_counts=[len(trial['searches']) for trial in repeat_case],
        live_optimizer_failures=summary['live_failed_optimizer_searches'])))


if __name__ == '__main__':
    main()
