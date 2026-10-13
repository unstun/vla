"""Compare immutable cohorts and report measured, not merely commanded, speed."""
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parents[1]
RAW = Path('/private/tmp/vla_policy_stop_20261012/runs')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def walks(run):
    rows = [json.loads(s) for s in (RAW / run / 'telemetry.jsonl').read_text().splitlines()]
    result = []
    for phase in ('walk1', 'walk2'):
        chosen = [r for r in rows if r['phase'] == phase]
        if not chosen:
            result.append(dict(phase=phase, exercised=False))
            continue
        phase_start = chosen[0]['command_applied_start_s']
        selected = [r for r in chosen if r['physics_time_s'] - phase_start >= 1.0]
        if not selected:
            result.append(dict(phase=phase, exercised=False))
            continue
        velocity = np.array([r['joint_qd'][:2] for r in selected])
        speed = np.linalg.norm(velocity, axis=1)
        xyz = np.array([r['joint_q'][:3] for r in selected])
        times = np.array([r['physics_time_s'] for r in selected])
        result.append(dict(phase=phase, exercised=True, command_mps=chosen[0]['command'][0],
            window='after first 1s of this walk', samples=len(selected),
            mean_horizontal_speed_mps=float(speed.mean()),
            median_horizontal_speed_mps=float(np.median(speed)),
            p10_horizontal_speed_mps=float(np.quantile(speed, .1)),
            p90_horizontal_speed_mps=float(np.quantile(speed, .9)),
            mean_position_difference_speed_mps=float(np.linalg.norm(np.diff(xyz[:, :2], axis=0), axis=1).sum() / (times[-1] - times[0])),
            minimum_up_z=min(r['base_up_z'] for r in selected)))
    return result

cohorts = {}
for version in ('v179', 'v182'):
    summary = VERSIONS / version / 'results/summary.json'
    runs = json.loads(summary.read_text())['runs']
    assert len(runs) == 12, (version, 'incomplete cohort')
    for run in runs:
        run['measured_walks'] = walks(run['run'])
    cohorts[version] = runs

pairs = []
for low, nominal in zip(cohorts['v179'], cohorts['v182']):
    assert (low['terrain'], low['attempt']) == (nominal['terrain'], nominal['attempt'])
    assert low['run'][5:] == nominal['run'][5:]
    pairs.append(dict(terrain=low['terrain'], attempt=low['attempt'],
        low_run=low['run'], nominal_run=nominal['run'],
        low_command_mps=low['walks'][0]['command_mps'], nominal_command_mps=nominal['walks'][0]['command_mps'],
        low_stops=low['stops'], nominal_stops=nominal['stops'],
        low_measured_walks=low['measured_walks'], nominal_measured_walks=nominal['measured_walks']))

aggregates = []
for version, runs in cohorts.items():
    for terrain in ('flat', 'stairs'):
        selected = [r for r in runs if r['terrain'] == terrain]
        stops = [s for r in selected for s in r['stops']]
        aggregates.append(dict(version=version, terrain=terrain, runs=len(selected),
            outcomes={r['run']: r['execution']['outcome'] for r in selected},
            recorded_stops=len(stops), complete_stops=sum(s['complete_10s_window'] for s in stops),
            late_over_5cm=sum(s.get('late_drift_over_5cm_flag', False) for s in stops),
            largest_late_excursion_m=max(s.get('late_max_excursion_m', 0) for s in stops),
            largest_command_to_end_displacement_m=max(s['net_xy_m'] for s in stops)))

report = dict(stage='experiment + analysis', source_sha256=sha(Path(__file__)),
    summary_sha256={v: sha(VERSIONS / v / 'results/summary.json') for v in cohorts},
    measurement='50Hz Newton state; late excursion excludes first 2s of each 10s stop',
    threshold_note='5cm is a descriptive flag, not an upstream or accepted project standard',
    operating_floor_note='0.6m/s planned cruise is not a universal trained or measured-speed lower bound',
    causal_limit='Flat pairs vary command only; stair stop poses also change with speed. No training or real-robot claim.',
    aggregates=aggregates, pairs=pairs)
(HERE / 'speed_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(aggregates, indent=2))
