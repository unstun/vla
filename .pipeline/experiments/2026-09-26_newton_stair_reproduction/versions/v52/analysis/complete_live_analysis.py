"""Finish compact live diagnostics remotely; render plots from summaries locally."""
from pathlib import Path
import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
import json
import re
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
VERSION = HERE.parent
BASE = VERSION.parents[1]
ROOT = BASE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE / 'versions/v51'))
import artifacts


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='v52_realtime_trial02')
    args = parser.parse_args()
    run = BASE / 'runs' / args.run
    analyzer = load('frozen_analyzer', VERSION / 'analyze_trial.py')
    metrics, rounds, starts, points, progress = analyzer.analyze(args.run)
    with artifacts.open_text(run, 'scan.log') as stream:
        text = stream.read()
    window = metrics['whole_window_rates']
    end = window['end_wall_s']
    grid = np.arange(max(window['start_wall_s'], starts[0]['start_wall_s']) + 1, end, .05)
    sw = np.array([r['start_wall_s'] for r in starts])
    cw = np.array(sorted(r['start_wall_s'] + r['wall_s'] for r in rounds if r['success']))
    hz = np.searchsorted(sw, grid, side='right') - np.searchsorted(sw, grid - 1, side='right')
    shz = np.searchsorted(cw, grid, side='right') - np.searchsorted(cw, grid - 1, side='right')
    timed = [r for r in starts if r['start_wall_s'] < end]
    sim = np.interp(grid, [r['start_wall_s'] for r in timed] + [end],
                    [r['ros_s'] for r in timed] + [metrics['physical_duration_s']])
    with (HERE / (args.run + '_frequency.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'wall_s', 'attempt_hz_1wallsecond', 'successful_hz_1wallsecond'])
        writer.writerows(zip(sim, grid, hz, shz))
    with (HERE / (args.run + '_latency.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'solve_ms', 'success', 'warm_accepts'])
        writer.writerows((r['ros_s'], r['wall_s'] * 1000, int(r['success']), r['warm_accepts']) for r in rounds)
    with (HERE / (args.run + '_progress.csv')).open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['simulation_s', 'measured_3d_path_m'])
        writer.writerows((p['sim_time_s'], distance) for p, distance in zip(points, progress))
    worst = max(rounds, key=lambda row:row['wall_s'])
    lines = text.splitlines()
    segment = lines[worst['start_line'] - 1:worst['end_line']]
    reasons = Counter(re.findall(r'V48_WARM_SEED selected=0 reason=(\S+)', text))
    evidence = [dict(line=i + 1, text=line) for i, line in enumerate(lines)
                if worst['start_line'] <= i + 1 <= worst['end_line'] and any(marker in line for marker in
                    ('V48_WARM_SEED', 'reactive_stair_seed_search_failed', 'no_valid_new_constraints',
                     'First three control points', 'initial_spline_collision', 'fixed_height_recovery'))]
    latest_curve = None
    with artifacts.open_text(run, 'artifacts/reactive_observations.jsonl') as stream:
        for line in stream:
            event = json.loads(line)
            if event['wall_monotonic_ns'] >= worst['start_wall_s'] * 1e9:
                break
            if event['event'] == 'bspline' and not event['data'].get('emergency_stop'):
                curve = event['data']
                degree = curve['order']
                knots = curve['knots']
                stamp = curve['start_time']
                start = stamp['sec'] + stamp['nanosec'] * 1e-9
                duration = knots[-degree - 1] - knots[degree]
                latest_curve = dict(traj_id=curve['traj_id'], start_sim_s=start, duration_s=duration,
                    end_sim_s=start + duration, age_at_round_s=worst['ros_s'] - start,
                    expired_at_round=worst['ros_s'] >= start + duration,
                    scope='Latest observer-received nonemergency curve; unpublished native state is not reconstructed')
    diagnostic = dict(run=args.run, worst_round=worst, worst_round_evidence=evidence,
        warm_rejection_reasons=dict(reasons), latest_observed_curve_before_worst=latest_curve,
        periods_occupied_by_worst=worst['wall_s'] * 30,
        timer_model='Single-threaded native executor; missed nominal slots are skipped, no concurrent solves',
        profile_boundary='Inclusive stage timers overlap; do not sum their costs',
        analyzer_sha256=sha(VERSION / 'analyze_trial.py'), diagnostic_source_sha256=sha(Path(__file__)))
    (HERE / 'live_tail_diagnosis.json').write_text(json.dumps(diagnostic, indent=2) + '\n')
    receipt = artifacts.archive_members(run)
    frozen = json.loads((VERSION / 'manifest.json').read_text())
    assert all(sha(ROOT / name) == digest for name, digest in frozen['source_files'].items())
    launcher = load('frozen_launcher', VERSION / 'run_local_episode.py')
    launcher.verify_native_build(launcher.BUILD, frozen)
    verification = dict(passed=True, source_files=len(frozen['source_files']),
        install_files=len(frozen['native_install_sha256']), verified_archive_members=len(receipt['members']),
        archive_sha256=receipt['archive_sha256'], archive_bytes=receipt['archive_bytes'],
        integration_manifest_sha256=sha(VERSION / 'manifest.json'),
        plot_environment_note='Frozen analyzer computed metrics; remote matplotlib unavailable. Compact CSVs support local plotting; frozen source unchanged.')
    (HERE / 'live_verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    paths = [HERE / (args.run + suffix) for suffix in
             ('_metrics.json', '_rounds.json', '_max_round.json', '_frequency.csv', '_latency.csv', '_progress.csv')]
    paths += [HERE / name for name in ('analysis_provenance.json', 'live_tail_diagnosis.json', 'live_verification.json')]
    paths += [VERSION / 'trials/attempt02' / name for name in
              ('preflight.json', 'request.json', 'result.json', 'remote_artifact_manifest.json')]
    paths += [run / name for name in ('result.json', 'process.json', 'retention_result.json', 'raw_capture_manifest.json')]
    records = {str(path.relative_to(ROOT)):dict(sha256=sha(path), bytes=path.stat().st_size) for path in paths}
    (HERE / 'live_return_manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    (HERE / 'live_return_files.txt').write_text('\n'.join(records) + '\n' +
        str((HERE / 'live_return_manifest.json').relative_to(ROOT)) + '\n')
    print(json.dumps(dict(warm_reasons=dict(reasons), latest_curve=latest_curve,
        return_files=len(records), return_bytes=sum(row['bytes'] for row in records.values()),
        verification=verification), indent=2), flush=True)


if __name__ == '__main__':
    main()
