"""Assess actual metric stopping after local artifact verification."""

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from distance_probe import INSTRUCTION, sustained_stop_windows


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_id')
    args = parser.parse_args()
    run = ROOT / 'runs' / args.run_id
    inventory = json.loads((run / 'artifact_sha256.json').read_text())
    checks = []
    with tarfile.open(run / 'raw_overlay_frames.tar.gz') as archive:
        for entry in inventory:
            if entry['path'].startswith('frames/'):
                stream = archive.extractfile(entry['path'])
                if stream is None:
                    raise RuntimeError(f'Missing archived frame {entry["path"]}')
                actual = hashlib.sha256(stream.read()).hexdigest()
            else:
                actual = hashlib.sha256((run / entry['path']).read_bytes()).hexdigest()
            assert actual == entry['sha256'], entry['path']
            checks.append({'path': entry['path'], 'sha256': actual})
    save(run / 'local_integrity.json', {'passed': True, 'checks': checks})
    meta = json.loads((run / 'meta.json').read_text())
    base = json.loads((run / 'analysis.json').read_text())
    assert meta['exit_code'] == 0 and not meta['timed_out']
    assert not meta['goal_termination_enabled'] and not meta['automatic_backup_enabled']
    assert meta['distance_is_evaluation_only']
    assert base['finite_30x2'] and base['model_instructions'] == [INSTRUCTION]
    states = [json.loads(line) for line in (run / 'telemetry.jsonl').read_text().splitlines()]
    states = [s for s in states if s.get('distance_probe') is not None]
    assert states and all(s['instruction'] == INSTRUCTION for s in states)
    assert not any(s['held'] or s['backing_up'] or s['waiting_after_backup'] for s in states)
    measurements = [s['distance_probe'] for s in states]
    times = np.array([m['timeline_seconds'] for m in measurements])
    assert np.all(np.diff(times) > 0), 'Timeline must advance for a duration claim'
    windows = sustained_stop_windows(measurements)
    crossing = next((i for i, m in enumerate(measurements) if m['forward_m'] >= 3.0), None)
    path_crossing = next((i for i, m in enumerate(measurements) if m['sampled_path_length_m'] >= 3.0), None)
    closest = min(measurements, key=lambda m: m['target_error_m'])
    episode = base['episode']
    child_crashed = 'exited with code -' in (run / 'stdout.log').read_text(errors='replace')
    runtime_complete = not episode.get('error') and not child_crashed and episode.get('duration_frames') == 1020
    physical_collision = episode.get('physical_collision_detected') if runtime_complete else None
    # Preserve raw evaluator fields; exact collision key mapping is checked in the result.
    summary = {
        'run_id': args.run_id, 'instruction': INSTRUCTION, 'model_calls': base['model_calls'],
        'artifact_checks': len(checks), 'sample_count': len(measurements),
        'timeline_duration_after_command_s': float(times[-1] - times[0]),
        'frame_derived_duration_after_command_s': measurements[-1]['elapsed_frame_derived_seconds'],
        'largest_timeline_sampling_gap_s': float(np.max(np.diff(times))),
        'video_wall_span_seconds': base['video_wall_span_seconds'],
        'goal_termination_enabled': False, 'automatic_backup_enabled': False,
        'qualifying_stop_windows': windows, 'stopped_near_3m_for_2s': bool(windows),
        'last_sample_qualifies': measurements[-1]['qualifying_stop_sample'],
        'maximum_forward_m': max(m['forward_m'] for m in measurements),
        'maximum_absolute_cross_track_m': max(abs(m['lateral_m']) for m in measurements),
        'first_forward_3m_crossing': measurements[crossing] if crossing is not None else None,
        'first_cumulative_path_3m_crossing': measurements[path_crossing] if path_crossing is not None else None,
        'closest_target_sample': closest, 'final_before_timeout': measurements[-1],
        'runtime_complete': runtime_complete,
        'benchmark_episode': episode if runtime_complete else {'valid': False, 'error': episode.get('error'),
                                                               'child_crashed': child_crashed},
        'physical_collision_detected': physical_collision,
        'gpu_peak_sampled_mib': base['gpu_peak_sampled_mib'],
        'termination': 'fixed observation timeout, not a policy stop' if runtime_complete else 'incomplete child execution',
        'boundary': 'one Chinese instruction trial through the unchanged waypoint controller; not general language capability validation',
    }
    save(run / 'distance_analysis.json', summary)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    t = times - times[0]
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(t, [m['forward_m'] for m in measurements], label='Forward displacement', color='#00798c')
    axes[0].plot(t, [m['sampled_path_length_m'] for m in measurements], label='Cumulative path', color='#edae49', alpha=.8)
    axes[0].axhline(3, color='#d1495b', ls='--', label='3 m reference (no stop trigger)')
    axes[0].axhspan(2.75, 3.25, color='#d1495b', alpha=.08)
    axes[0].set_ylabel('Distance (m)')
    axes[0].legend(loc='upper left')
    axes[1].plot(t, [m['lateral_m'] for m in measurements], color='#6a4c93')
    axes[1].axhspan(-.25, .25, color='#00798c', alpha=.1)
    axes[1].set_ylabel('Cross-track (m)')
    axes[2].plot(t, [m['actual_planar_speed_m_s'] for m in measurements], label='Measured planar speed', color='#00798c')
    axes[2].plot(t, [m['desired_v_m_s'] for m in measurements], label='Desired speed', color='#d1495b', alpha=.7)
    axes[2].axhline(.05, color='gray', ls=':')
    axes[2].set_ylabel('Speed (m/s)')
    axes[2].set_xlabel('Elapsed simulator timeline after instruction (s)')
    axes[2].legend(loc='upper left')
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle('Chinese command: go straight 3 meters, then stop')
    fig.tight_layout()
    fig.savefig(run / 'distance_speed.png', dpi=170)
    fig.savefig(run / 'distance_speed.pdf')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
