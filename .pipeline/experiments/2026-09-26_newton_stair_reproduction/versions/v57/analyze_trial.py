"""Analyze original v57 captures remotely, including lossless archive members."""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
spec = importlib.util.spec_from_file_location('original_round_parser', BASE / 'versions/v47/analyze_trial.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def analyze(run):
    directory = BASE / 'runs' / run
    sources = {}

    def read(name):
        path = directory / name
        if path.exists():
            data = path.read_bytes()
        else:
            with zipfile.ZipFile(directory / 'raw_capture.zip') as archive:
                data = archive.read(name)
            receipt = json.loads((directory / 'raw_capture_manifest.json').read_text())
            row = receipt['members'][name]
            assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
        return data.decode('utf-8')

    text = read('scan.log')
    class Log:
        def read_text(self):
            return text
    starts, rounds = core.parse_rounds(Log())
    assert starts and rounds, 'No complete planning rounds'
    lines = text.splitlines()
    for row in rounds:
        segment = lines[row['start_line'] - 1:row['end_line']]
        row['profile'] = [json.loads(s.split('V50_PROFILE ', 1)[1]) for s in segment if 'V50_PROFILE ' in s]
        row['warm_accepts'] = sum('V48_WARM_RESULT accepted=1' in s for s in segment)
    result = json.loads(read('result.json'))
    latest = json.loads(read('backend_latest.json'))
    points = [json.loads(s) for s in read('sensor.jsonl').splitlines()]
    pace = result['realtime_pacing']
    begin = pace['wall_anchor_monotonic_s']
    end = begin + pace['wall_elapsed_s']
    completed = [r for r in rounds if begin <= r['start_wall_s'] + r['wall_s'] <= end]
    attempts = [r for r in starts if begin <= r['start_wall_s'] <= end]
    xyz = [p['body_sensor']['position'] for p in points]
    progress = [0.]
    pauses, pause = [], 0.
    for a, b in zip(points, points[1:]):
        progress.append(progress[-1] + math.dist(a['body_sensor']['position'], b['body_sensor']['position']))
        if not starts[0]['ros_s'] <= b['sim_time_s'] <= starts[-1]['ros_s']:
            continue
        dt = b['sim_time_s'] - a['sim_time_s']
        if 0 < dt < .5 and math.hypot(*b['body_sensor'].get('linear_world', [0, 0])[:2]) < .05:
            pause += dt
        elif pause:
            pauses.append(pause)
            pause = 0.
    if pause:
        pauses.append(pause)
    commands = {}
    for s in read('command_frequencies.jsonl').splitlines():
        row = json.loads(s)
        if begin <= row['wall_monotonic_s'] <= end:
            commands.setdefault(row['topic'], []).append(row['wall_monotonic_s'])
    metrics = dict(run=run, source_sha256=sources, physical_duration_s=result.get('physics_duration_s'),
        realtime_pacing=pace, local_solve_ms=core.distribution([r['wall_s'] * 1000 for r in rounds]),
        whole_window_solve_ms=core.distribution([r['wall_s'] * 1000 for r in completed]),
        whole_window_rates=dict(start_wall_s=begin, end_wall_s=end, duration_s=end - begin,
            attempt_starts=len(attempts), completed_rounds=len(completed),
            successful_completions=sum(r['success'] for r in completed),
            attempt_hz=len(attempts) / (end - begin), completed_hz=len(completed) / (end - begin),
            successful_hz=sum(r['success'] for r in completed) / (end - begin)),
        measured_path_length_m=progress[-1], measured_displacement_m=math.dist(xyz[0], xyz[-1]),
        initial_body_xyz_m=xyz[0], final_body_xyz_m=xyz[-1], maximum_body_z_m=max(p[2] for p in xyz),
        pauses_over_1s=[p for p in pauses if p >= 1],
        emergency_transitions=len(re.findall(r'from .* to EMERGENCY_STOP', text)),
        current_curve_invalid_events=text.count('remaining_spline_invalid'),
        warm_accepted_attempts=sum(r['warm_accepts'] for r in rounds),
        rounds_at_least_100ms=sum(r['wall_s'] >= .1 for r in rounds),
        rounds_at_least_1000ms=sum(r['wall_s'] >= 1 for r in rounds),
        incomplete_starts=len(starts) - len(rounds),
        controller_rates={topic:dict(samples=len(ts), hz=core.rate(ts)) for topic, ts in commands.items()},
        terminal_status=result.get('finish_request', {}).get('backend_terminal_status'),
        terminal_results=latest.get('terminal_results'),
        full_route_accepted=any(r.get('status') == 'arrived' for r in latest.get('terminal_results', [])),
        sustained_30hz_validated=False,
        comparison_boundary='Same configuration, independent physical trajectory; paired fixed-input replay isolates cache effect',
        frequency_definition='Counts in trailing (t-1,t] wall second, sampled every .05 wall seconds and mapped to simulation time',
        pause_definition='XY measured speed below .05 m/s, sensor intervals below .5 s, original nominal navigation interval')
    return metrics, rounds, starts, points, progress


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='v57_realtime_trial01')
    args = parser.parse_args()
    output = HERE / 'analysis'
    output.mkdir(exist_ok=True)
    metrics, rounds, starts, points, progress = analyze(args.run)
    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2) + '\n')
    save(args.run + '_metrics.json', metrics)
    save(args.run + '_rounds.json', rounds)
    save(args.run + '_max_round.json', max(rounds, key=lambda r:r['wall_s']))
    save('analysis_provenance.json', dict(source_sha256=metrics['source_sha256'],
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_parser_sha256=hashlib.sha256((BASE / 'versions/v47/analyze_trial.py').read_bytes()).hexdigest()))
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/v57-mpl')
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    window = metrics['whole_window_rates']
    end = window['end_wall_s']
    grid = np.arange(window['start_wall_s'] + 1, end, .05)
    sw = np.array([r['start_wall_s'] for r in starts])
    cw = np.array(sorted(r['start_wall_s'] + r['wall_s'] for r in rounds if r['success']))
    hz = np.searchsorted(sw, grid, side='right') - np.searchsorted(sw, grid - 1, side='right')
    shz = np.searchsorted(cw, grid, side='right') - np.searchsorted(cw, grid - 1, side='right')
    timed = [r for r in starts if r['start_wall_s'] < end]
    sim = np.interp(grid, [window['start_wall_s']] + [r['start_wall_s'] for r in timed] + [end],
                    [0.] + [r['ros_s'] for r in timed] + [metrics['physical_duration_s']])
    with (output / (args.run + '_frequency.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'wall_s', 'attempt_hz_1wallsecond', 'successful_hz_1wallsecond'])
        writer.writerows(zip(sim, grid, hz, shz))
    with (output / (args.run + '_latency.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'solve_ms', 'success', 'warm_accepts'])
        writer.writerows((r['ros_s'], r['wall_s'] * 1000, int(r['success']), r['warm_accepts']) for r in rounds)
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    axes[0].plot(sim, hz, color='#98A4B4', label='Attempts', linewidth=.8)
    axes[0].plot(sim, shz, color='#126D8C', label='Successful completions', linewidth=1)
    axes[0].axhline(30, color='#333333', linestyle='--')
    axes[0].set_ylabel('Local frequency (Hz)\nTrailing 1 wall second')
    axes[0].set_ylim(0, 35)
    axes[0].legend(loc='lower left')
    axes[0].set_title(f"{args.run}: full-window successful planning {window['successful_hz']:.2f} Hz")
    xs = np.array([r['ros_s'] for r in rounds]); ys = np.array([r['wall_s'] * 1000 for r in rounds])
    ok = np.array([r['success'] for r in rounds]); fast = ys < 10
    axes[1].axhspan(.5, 10, color='#E1F2E9')
    for mask, color, label in [(ok & fast, '#17815C', 'Success <10 ms'),
                               (ok & ~fast, '#176B94', 'Success >=10 ms'),
                               (~ok, '#B53B3B', 'Failed round')]:
        axes[1].scatter(xs[mask], ys[mask], s=8, c=color, alpha=.65, label=label)
    axes[1].axhline(1000 / 30, color='#333333', linestyle='--', linewidth=.8)
    axes[1].set_yscale('log'); axes[1].set_ylim(.5, max(1500, ys.max() * 1.3))
    axes[1].set_ylabel('Complete round solve (ms)')
    axes[1].set_title(f'Maximum {ys.max():.1f} ms'); axes[1].legend()
    axes[2].plot([p['sim_time_s'] for p in points], progress, color='#126D8C')
    axes[2].set_ylabel('Measured 3D path (m)'); axes[2].set_xlabel('Simulation time (s)')
    axes[2].set_title(f"Path {progress[-1]:.2f} m; longest pause {max(metrics['pauses_over_1s'], default=0):.2f} s")
    for ax in axes:
        ax.grid(alpha=.2); ax.set_xlim(0, metrics['physical_duration_s'])
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(output / (args.run + '_time_series.' + ext), dpi=160)
    plt.close(fig)
    print(json.dumps({k:metrics[k] for k in ('local_solve_ms', 'whole_window_rates',
        'measured_path_length_m', 'pauses_over_1s', 'emergency_transitions', 'current_curve_invalid_events')}, indent=2))


if __name__ == '__main__':
    main()
