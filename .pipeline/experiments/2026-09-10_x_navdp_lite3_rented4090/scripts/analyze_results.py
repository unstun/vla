"""Audit returned trial records and plot measured base trajectories."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np

EXP = Path(__file__).resolve().parents[1]


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def analyze(run):
    root = EXP/'runs'/run
    media = EXP/'media'/run
    cases = json.loads((root/'cases.json').read_text())
    report = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for case in cases:
        directory = root/case['id']
        config = json.loads((directory/'case.json').read_text())
        result = json.loads((directory/'result.json').read_text())
        trace = read_rows(directory/'trace.jsonl')
        frames = read_rows(directory/'frames/frames.jsonl')
        outputs = [json.loads(p.read_text()) for p in sorted((directory/'calls').glob('output_*.json'))]
        require(len(outputs) == result['model_calls_submitted'], 'Missing model output')
        require(len(list((directory/'calls').glob('input_*.npz'))) == len(outputs), 'Input/output count mismatch')
        require(len(frames) == result['frames'], 'Frame count mismatch')
        require(len({row['file'] for row in frames}) == len(frames), 'Duplicate frame name')
        require(len(list((directory/'frames').glob('*.jpg'))) == len(frames), 'Unexpected/missing JPEG')
        for rows, key in [(trace, 'mono'), (trace, 'sim_time'), (frames, 'mono')]:
            require(np.all(np.diff([r[key] for r in rows]) > 0), f'Nonmonotonic {key}')
        sequences = {o['seq'] for o in outputs}
        applied = {t['applied_seq'] for t in trace if t['applied_seq'] is not None}
        require(applied <= sequences, 'Applied command lacks inference evidence')
        require(len(applied) == result['model_calls_consumed'], 'Consumption count mismatch')
        for output in outputs:
            source = directory/'calls'/f"input_{output['seq']:04d}.npz"
            require(hashlib.sha256(source.read_bytes()).hexdigest() == output['input_sha256'], 'Input hash mismatch')
            with np.load(source) as data:
                require(data['rgb'].shape == (270, 480, 3) and data['rgb'].dtype == np.uint8, 'RGB contract')
                require(data['depth'].shape == (270, 480) and data['depth'].dtype == np.float32, 'Depth contract')
                require(np.isfinite(data['depth']).all() and np.all(data['depth'] > 0), 'Depth validity')
                require(float(data['capture_mono']) == output['capture_mono'], 'Input/output time mismatch')
            for key in ['path', 'all_paths', 'q_values', 'controls']:
                require(np.isfinite(output[key]).all(), f'Nonfinite {key}')
            require(output['mpc_status'] == 0, 'MPC solver failed')
        xy = np.array([t['pose'][:2] for t in trace])
        goal = np.array(config['goal_world'][:2])
        distances = np.linalg.norm(xy-goal, axis=1)
        require(np.allclose(distances, [t['goal_distance_m'] for t in trace]), 'Distance mismatch')
        require(np.allclose(xy[-1], result['final_pose'][:2]), 'Final state mismatch')
        require(abs(distances[-1]-result['final_goal_distance_m']) < 1e-10, 'Final distance mismatch')
        stops = [i for i, t in enumerate(trace) if t['termination'] is not None]
        require(stops and trace[stops[0]]['termination'] == 'external_goal_stop', 'Unexpected stop')
        require(distances[stops[0]] <= config['arrival_radius_m'], 'Stop outside radius')
        require(all(t['command'] == [0.0, 0.0] for t in trace[stops[0]+1:]), 'Nonzero post-stop command')
        require(all(t['telemetry']['obstacle_contact_steps'] == 0 and
                    t['telemetry']['boundary_contact_steps'] == 0 for t in trace), 'Contact recorded')
        tail = xy[np.array([t['mono'] for t in trace]) >= trace[-1]['mono']-.5]
        late_drift = float(np.max(np.linalg.norm(tail-tail[0], axis=1)))
        duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(media/f"{case['id']}.mp4")], text=True))
        recorded_span = frames[-1]['mono']-frames[0]['mono']+.1
        require(abs(duration-recorded_span) <= .2, 'Video duration differs from recorded wall time')
        inference = np.array([o['model_seconds'] for o in outputs])
        ages = np.array([o['finished_mono']-o['capture_mono'] for o in outputs])
        item = {
            'case': case['id'], 'goal_distance_m': case['distance_m'],
            'forward_displacement_m': result['forward_displacement_m'],
            'final_goal_distance_m': float(distances[-1]), 'path_length_m': result['path_length_m'],
            'arrival_wall_s': trace[stops[0]]['wall_elapsed'],
            'post_stop_recorded_s': trace[-1]['mono']-trace[stops[0]]['mono'],
            'late_half_second_xy_drift_m': late_drift, 'contact_steps': 0,
            'model_calls': len(outputs), 'model_p50_s': float(np.median(inference)),
            'model_p95_s': float(np.percentile(inference, 95)),
            'observation_age_on_completion_p95_s': float(np.percentile(ages, 95)),
            'watchdog_ticks': result['watchdog_ticks'], 'trace_rows': len(trace), 'frames': len(frames),
            'video_seconds': duration, 'video_minus_recorded_span_s': duration-recorded_span,
            'success_with_external_025m_stop': result['success'],
        }
        report.append(item)
        ax = axes[int(case['scene'] == 'blocked')]
        initial = np.array(config['initial_pose'][:2])
        line, = ax.plot(xy[:, 0], xy[:, 1], label=case['id'])
        ax.plot(*initial, 'o', color=line.get_color())
        ax.plot(*goal, '*', color=line.get_color(), markersize=12)
        ax.add_patch(Circle(goal, .25, fill=False, color=line.get_color(), alpha=.5))
    axes[1].add_patch(Rectangle((7.95, 13.35), .6, .9, color='#b96c20', alpha=.8, label='Obstacle'))
    for ax, title in zip(axes, ['Clear point goals', '4 m goals behind a box']):
        ax.set(title=title, xlabel='World X (m)', ylabel='World Y (m)')
        ax.axis('equal'); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('Measured Lite3 base paths | X-NavDP FP32 | circles: external 0.25 m stop radius')
    fig.savefig(media/'trajectories.png', dpi=180)
    plt.close(fig)
    identity = json.loads((root/'model_identity.json').read_text())
    identity.pop('unused_training_keys')
    gpu = [int(r['gpu'].split(',')[0]) for r in read_rows(root/'gpu_samples.jsonl') if 'gpu' in r]
    audit = {'status': 'passed', 'model_identity': identity, 'gpu_total_used_peak_MiB': max(gpu),
             'gpu_used_initial_MiB': gpu[0], 'cases': report,
             'scope': 'Four physical simulation trials; numeric goals; external stop; no language or real-robot validation.'}
    (root/'evidence_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    with (root/'measured_summary.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report[0]))
        writer.writeheader(); writer.writerows(report)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    analyze(parser.parse_args().run)
