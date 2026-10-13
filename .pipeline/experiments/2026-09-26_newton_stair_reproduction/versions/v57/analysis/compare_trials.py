"""Post-run evidence only: frozen v57 analysis plus measured wall-clock plots."""
from pathlib import Path
from collections import Counter
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys

import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
VERSION = HERE.parent
BASE = VERSION.parents[1]
ROOT = BASE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE / 'versions/v51'))
import artifacts


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + '\n')


def read_jsonl(run, name):
    with artifacts.open_text(run, name) as stream:
        for line in stream:
            yield json.loads(line)


def pauses(points, low, high):
    episodes, start, end = [], None, None
    for a, b in zip(points, points[1:]):
        dt = b['sim_time_s'] - a['sim_time_s']
        speed = np.linalg.norm(b['body_sensor']['linear_world'][:2])
        if low <= b['sim_time_s'] <= high and 0 < dt < .5 and speed < .05:
            start = a['sim_time_s'] if start is None else start
            end = b['sim_time_s']
        elif start is not None:
            episodes.append(dict(start_s=start, end_s=end, duration_s=end-start))
            start = end = None
    if start is not None:
        episodes.append(dict(start_s=start, end_s=end, duration_s=end-start))
    return [p for p in episodes if p['duration_s'] >= 1]


def analyze(run_name, analyzer):
    run = BASE / 'runs' / run_name
    metrics, rounds, starts, points, progress = analyzer.analyze(run_name)
    receipt = artifacts.archive_members(run)
    with artifacts.open_text(run, 'scan.log') as stream:
        log = stream.read()
    original = json.loads((run / 'video_states.json').read_text())
    timed = [r for r in original if 'wall_monotonic_s' in r]
    wall = np.array([r['wall_monotonic_s'] for r in timed])
    sim = np.array([r['physics_time_s'] for r in timed])
    assert np.all(np.diff(wall) > 0) and np.all(np.diff(sim) > 0)
    window = metrics['whole_window_rates']
    grid = np.arange(window['start_wall_s'] + 1, window['end_wall_s'], .05)
    mapped = np.interp(grid, wall, sim)
    sw = np.array([r['start_wall_s'] for r in starts])
    cw = np.array(sorted(r['start_wall_s'] + r['wall_s'] for r in rounds if r['success']))
    hz = np.searchsorted(sw, grid, side='right') - np.searchsorted(sw, grid-1, side='right')
    shz = np.searchsorted(cw, grid, side='right') - np.searchsorted(cw, grid-1, side='right')
    curves = []
    for event in read_jsonl(run, 'artifacts/reactive_observations.jsonl'):
        if event['event'] != 'bspline' or event['data'].get('emergency_stop'):
            continue
        data = event['data']
        degree, knots = data['order'], data['knots']
        begin = data['start_time']['sec'] + data['start_time']['nanosec'] * 1e-9
        end = begin + knots[-degree-1] - knots[degree]
        control = np.array([[p[k] for k in ('x', 'y', 'z')] for p in data['pos_pts']])
        endpoint = BSpline(knots, control, degree)(knots[-degree-1]).tolist()
        curves.append(dict(wall_s=event['wall_monotonic_ns']*1e-9,
                           traj_id=data['traj_id'], start_sim_s=begin,
                           end_sim_s=end, endpoint=endpoint))
    curves.sort(key=lambda row: row['wall_s'])
    indices = np.searchsorted([c['wall_s'] for c in curves], grid, side='right') - 1
    reserve = np.array([curves[i]['end_sim_s']-s if i >= 0 else np.nan
                        for i, s in zip(indices, mapped)])
    focus = (mapped >= 39) & (mapped <= 55) & np.isfinite(reserve)
    worst = max(rounds, key=lambda r:r['wall_s'])
    old_stand = np.array([7.4927184, -4.2497302, 1.8549563])
    xyz = np.array([p['body_sensor']['position'] for p in points])
    near = int(np.argmin(np.linalg.norm(xyz[:, :2]-old_stand[:2], axis=1)))
    metrics.update(
        rounds_over_33_333ms=sum(r['wall_s'] > 1/30 for r in rounds),
        warm_rejection_reasons=dict(Counter(re.findall(r'V48_WARM_SEED selected=0 reason=(\S+)', log))),
        focus_39_55_pauses_over_1s=pauses(points, 39, 55),
        focus_39_55_reserve_s=analyzer.core.distribution(reserve[focus].tolist()),
        observed_nonemergency_curves=len(curves),
        observed_curve_scope='Observer-received curves; unpublished native state is not reconstructed.',
        nearest_frozen_corner=dict(sim_s=points[near]['sim_time_s'],
            xy_distance_m=float(np.linalg.norm(xyz[near, :2]-old_stand[:2])),
            xyz_m=xyz[near].tolist(),
            subsequent_measured_3d_path_m=progress[-1]-progress[near],
            final_xy_distance_from_corner_m=float(np.linalg.norm(xyz[-1, :2]-old_stand[:2]))),
        worst_round=worst,
        startup_without_navigation_wall_timestamps_until_sim_s=float(sim[0]),
        frequency_mapping='Trailing 1 wall-second event counts; x uses recorded video-state wall/physics timestamps. Untimed factory startup is shaded.',
        archive_verification=dict(passed=True, members=len(receipt['members']),
            sha256=receipt['archive_sha256'], bytes=receipt['archive_bytes']),
    )
    metrics['sustained_30hz_validated'] = bool(
        window['successful_hz'] >= 29.9 and metrics['rounds_over_33_333ms'] == 0)
    metrics['tail_elimination_validated'] = metrics['rounds_at_least_100ms'] == 0
    save(run_name + '_metrics.json', metrics)
    save(run_name + '_curves.json', curves)
    save(run_name + '_rounds.json', rounds)
    with (HERE / (run_name + '_frequency.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'wall_s', 'attempt_hz_1wallsecond',
                         'successful_hz_1wallsecond', 'observed_curve_reserve_sim_s'])
        writer.writerows(zip(mapped, grid, hz, shz, reserve))
    with (HERE / (run_name + '_latency.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'solve_ms', 'success', 'warm_accepts'])
        writer.writerows((r['ros_s'], r['wall_s']*1000, int(r['success']), r['warm_accepts']) for r in rounds)
    with (HERE / (run_name + '_progress.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'measured_3d_path_m'])
        writer.writerows((p['sim_time_s'], distance) for p, distance in zip(points, progress))
    return metrics, rounds, points, progress, mapped, hz, shz, reserve


def plot(results):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/v57-review-mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'savefig.facecolor': 'white'})
    fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=True)
    for col, (metrics, rounds, points, progress, sim, hz, shz, reserve) in enumerate(results):
        window = metrics['whole_window_rates']
        ax = axes[0, col]
        ax.plot(sim, hz, color='#AAB1B9', lw=.9, label='Attempts')
        ax.plot(sim, shz, color='#126D8C', lw=1, label='Successful plans')
        ax.axhline(30, color='#353535', ls='--', lw=.8, label='30 Hz target')
        ax.set_ylim(0, max(35, float(hz.max())+1))
        ax.set_ylabel('Local planning (Hz)\nTrailing 1 wall second')
        ax.set_title(f"Trial {col+1}  |  {window['successful_hz']:.2f} successful Hz overall")
        ax.legend(loc='lower left', fontsize=8)
        ax = axes[1, col]
        xs = np.array([r['ros_s'] for r in rounds])
        ys = np.array([r['wall_s']*1000 for r in rounds])
        ok = np.array([r['success'] for r in rounds])
        warm_fast = np.array([r['warm_accepts'] > 0 for r in rounds]) & (ys < 10) & ok
        masks = [(warm_fast, '#17815C', 'Warm success <10 ms'),
                 (ok & ~warm_fast, '#C07715', 'Other success'), (~ok, '#BA3840', 'Failed round')]
        ax.axhspan(.5, 10, color='#E5F3EB')
        for mask, color, label in masks:
            ax.scatter(xs[mask], ys[mask], s=9, color=color, alpha=.65, label=label)
        ax.axhline(1000/30, color='#353535', ls='--', lw=.8)
        ax.set_yscale('log')
        ax.set_ylim(.5, max(1500, ys.max()*1.35))
        ax.set_ylabel('Full planning round (ms)')
        ax.set_title(f"Median {np.median(ys):.2f} ms | P99 {np.percentile(ys,99):.1f} ms | Max {ys.max():.1f} ms")
        ax.legend(loc='upper left', fontsize=8)
        axes[2, col].plot([p['sim_time_s'] for p in points], progress, color='#126D8C')
        axes[2, col].set_ylabel('Measured 3D path (m)')
        axes[2, col].set_xlabel('Simulation time (s)')
        axes[2, col].set_title(f"Path {progress[-1]:.2f} m | Pauses over 1 s: {len(metrics['pauses_over_1s'])}")
        for ax in axes[:, col]:
            ax.axvspan(0, metrics['startup_without_navigation_wall_timestamps_until_sim_s'], color='#E9EBEF', alpha=.6)
            ax.axvspan(39, 55, color='#D4E2F0', alpha=.17)
            ax.set_xlim(0, 90)
            ax.grid(alpha=.18)
    fig.suptitle('v57 Building recordings: measured planning cadence, solve latency and motion', fontsize=15)
    fig.tight_layout(rect=(0, .035, 1, .97))
    fig.text(.5, .012, 'Grey: factory startup; pale blue: 39–55 s corner focus. Full navigation-window rates include failures and pauses. Display FPS is separate.', ha='center', fontsize=9)
    for ext in ('png', 'pdf'):
        fig.savefig(HERE / ('v57_time_series.'+ext), dpi=170)
    plt.close(fig)


def compact_result(run):
    metrics = json.loads((HERE / (run + '_metrics.json')).read_text())
    def read(suffix):
        with (HERE / (run + suffix)).open() as stream:
            return list(csv.DictReader(stream))
    latency = read('_latency.csv')
    frequency = read('_frequency.csv')
    progress = read('_progress.csv')
    rounds = [dict(ros_s=float(r['simulation_s']), wall_s=float(r['solve_ms'])/1000,
                   success=bool(int(r['success'])), warm_accepts=int(r['warm_accepts'])) for r in latency]
    points = [dict(sim_time_s=float(r['simulation_s'])) for r in progress]
    return (metrics, rounds, points, [float(r['measured_3d_path_m']) for r in progress],
            *[np.array([float(r[k]) for r in frequency]) for k in
              ('simulation_s', 'attempt_hz_1wallsecond', 'successful_hz_1wallsecond',
               'observed_curve_reserve_sim_s')])


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--skip-plots', action='store_true')
    mode.add_argument('--plots-only', action='store_true')
    args = parser.parse_args()
    runs = ['v57_realtime_trial01', 'v57_realtime_trial02']
    if args.plots_only:
        plot([compact_result(run) for run in runs])
        return
    analyzer = load_module('frozen_analyzer', VERSION / 'analyze_trial.py')
    results = [analyze(run, analyzer) for run in runs]
    if not args.skip_plots:
        plot(results)
    manifest = json.loads((VERSION / 'manifest.json').read_text())
    assert all(artifacts.digest(ROOT/name) == digest for name, digest in manifest['source_files'].items())
    entry = load_module('actual_entry', VERSION / 'run_local_episode.py')
    entry.verify_native_build(entry.BUILD, manifest)
    save('verification.json', dict(passed=True, source_files=len(manifest['source_files']),
        installed_files=len(manifest['native_install_sha256']),
        manifest_sha256=artifacts.digest(VERSION/'manifest.json'),
        analyzer_sha256=artifacts.digest(VERSION/'analyze_trial.py'),
        supplemental_analysis_sha256=artifacts.digest(Path(__file__)),
        video_state_sha256={run:artifacts.digest(BASE/'runs'/run/'video_states.json') for run in runs},
        archives={r[0]['run']:r[0]['archive_verification'] for r in results}))
    print(json.dumps({r[0]['run']:{k:r[0][k] for k in
        ('local_solve_ms', 'whole_window_rates', 'measured_path_length_m', 'pauses_over_1s',
         'focus_39_55_pauses_over_1s', 'nearest_frozen_corner', 'sustained_30hz_validated')}
        for r in results}, indent=2), flush=True)


if __name__ == '__main__':
    main()
