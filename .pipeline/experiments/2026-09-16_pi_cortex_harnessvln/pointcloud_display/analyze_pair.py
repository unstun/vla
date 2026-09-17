#!/usr/bin/env python3
"""Compare one instrumented navigation run with one live RViz display run."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess


HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def quantile(values, percentile):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] * (upper - index) + values[upper] * (index - lower) if upper != lower else values[lower]


def summarize(values):
    values = [v for v in values if v is not None]
    return {'count': len(values), 'median': statistics.median(values), 'p95': quantile(values, 0.95),
            'maximum': max(values)} if values else {'count': 0}


def read_run(run):
    artifacts = run / 'returned_artifacts'
    summary = load(artifacts / 'runner_output/summary.json')
    metrics = lines(artifacts / 'runner_output/metrics.jsonl')
    samples = lines(artifacts / 'pointcloud_observer/resource_samples.jsonl')
    start, end = metrics[0]['state_sample_monotonic_ns'], metrics[-1]['state_sample_monotonic_ns']
    active = [r for r in samples if start <= r['monotonic_ns'] <= end]
    if len(active) < 5:
        raise ValueError('insufficient resource samples during active physics')
    spec = importlib.util.spec_from_file_location('p2b_physics_review', HERE.parent / 'p2b_execution/review_two_goal.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    navigation = module.review(run)
    gpu_memory = [r['gpus'][0]['memory_used_mib'] for r in active if r.get('gpus')]
    gpu_util = [r['gpus'][0]['utilization_percent'] for r in active if r.get('gpus')]
    process = {}
    names = set(name for row in active for name in row['processes'])
    for name in names:
        process[name] = {
            'scope': 'Registered PID only; child processes are not included. Use host totals for complete load.',
            'cpu_percent_one_core': summarize([r['processes'].get(name, {}).get('cpu_percent_one_core') for r in active]),
            'rss_mib': summarize([r['processes'].get(name, {}).get('rss_bytes', 0) / 2**20 for r in active if 'rss_bytes' in r['processes'].get(name, {})]),
        }
    return {
        'run_id': run.name,
        'mode': load(run / 'observer/config.json')['mode'],
        'navigation': navigation,
        'observer': load(artifacts / 'pointcloud_observer/session.json'),
        'sim_seconds': summary['sim_seconds'],
        'physics_loop_wall_seconds': summary['wall_seconds'],
        'wall_seconds_per_sim_second': summary['wall_seconds'] / summary['sim_seconds'],
        'real_time_factor': summary['sim_seconds'] / summary['wall_seconds'],
        'control_loop_timing': summary['control_loop_timing'],
        'command_watchdog_events': summary['command_watchdog_events'],
        'dropped_telemetry_frames': summary['dropped_telemetry_frames'],
        'telemetry_transport': summary['telemetry_transport'],
        'active_resource_samples': len(active),
        'active_gpu_memory_mib': summarize(gpu_memory),
        'active_gpu_utilization_percent': summarize(gpu_util),
        'active_encoder_utilization_percent': summarize([r['gpus'][0].get('encoder_utilization_percent') for r in active if r.get('gpus')]),
        'active_encoder_session_count': summarize([r['gpus'][0].get('encoder_session_count') for r in active if r.get('gpus')]),
        'whole_run_gpu_memory_peak_mib': max(r['gpus'][0]['memory_used_mib'] for r in samples if r.get('gpus')),
        'active_host_cpu_percent': summarize([r.get('host_cpu_percent') for r in active]),
        'active_host_used_ram_gib': summarize([(r['host_memory_bytes']['MemTotal'] - r['host_memory_bytes']['MemAvailable']) / 2**30 for r in active]),
        'active_swap_used_mib': summarize([(r['host_memory_bytes']['SwapTotal'] - r['host_memory_bytes']['SwapFree']) / 2**20 for r in active]),
        'active_processes': process,
        'resource_errors': [error for r in samples for error in r['errors']],
        'cleanup': load(artifacts / 'result.json').get('post_cleanup_ports'),
    }


def analyze(baseline, display):
    off, on = read_run(baseline), read_run(display)
    if off['mode'] != 'off' or on['mode'] not in {'rviz', 'rviz-gpu'}:
        raise ValueError('expected baseline off and a display condition')
    receipts = lines(display / 'returned_artifacts/pointcloud_observer/cloud_receipts.jsonl')
    video = display / 'returned_artifacts/pointcloud_observer/rviz_live_wall_time.mp4'
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)],
                           text=True, capture_output=True, check=True)
    video_info = json.loads(probe.stdout)
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(video), '-f', 'null', '-'],
                             text=True, capture_output=True, timeout=120)
    log_path = display / 'returned_artifacts/pointcloud_observer/Ogre.log'
    renderer_lines = [line for line in log_path.read_text(errors='replace').splitlines() if 'GL_RENDERER' in line or 'GL_VENDOR' in line] if log_path.exists() else []
    stamps = [r['source_stamp_ns'] for r in receipts]
    identities = [load(run / 'source_env_hashes.json') for run in (baseline, display)]
    identity_keys = ('patched_runner_sha256', 'accepted_scan_build_identity')
    source_match = all(identities[0][key] == identities[1][key] for key in identity_keys)
    pilot_match = load(baseline / 'inputs/pilot.json') == load(display / 'inputs/pilot.json')
    checks = {
        'baseline_navigation_passed': off['navigation']['passed'],
        'display_navigation_passed': on['navigation']['passed'],
        'baseline_sampler_clean': not off['resource_errors'] and off['observer'].get('monitor_exit_code') == 0,
        'display_sampler_clean': not on['resource_errors'] and on['observer'].get('monitor_exit_code') == 0,
        'observer_no_errors': not on['observer']['errors'],
        'advancing_cloud_receipts': len(stamps) > 10 and all(b > a for a, b in zip(stamps, stamps[1:])),
        'nonempty_clouds': bool(receipts) and all(r['points'] > 0 for r in receipts),
        'rviz_video_recorded': bool(video_info.get('streams')),
        'video_fully_decoded': decoded.returncode == 0 and not decoded.stderr.strip(),
        'frozen_navigation_sources_and_pilot_match': source_match and pilot_match,
        'both_runs_returned_hashes_match': all(r['navigation']['checks']['returned_hashes_match'] for r in (off, on)),
        'both_runs_ports_released': all(p['free'] for run in (off, on) for p in run['cleanup'].values()),
    }
    if on['mode'] == 'rviz-gpu':
        checks['nvidia_renderer_verified'] = (
            on['observer'].get('nvidia_renderer_verified') is True
            and any('GL_RENDERER' in line and 'NVIDIA' in line and '5070 Ti' in line for line in renderer_lines)
        )
        checks['nvenc_recording_verified'] = (
            on['observer']['config'].get('capture_encoder') == 'h264_nvenc'
            and on['active_encoder_session_count'].get('maximum', 0) >= 1
            and any('h264_nvenc' in c for c in on['observer']['commands'] if c and c[0] == 'ffmpeg')
            and checks['video_fully_decoded']
        )
    observer_checks = {key: value for key, value in checks.items()
                       if key not in {'baseline_navigation_passed', 'display_navigation_passed'}}
    return {
        'passed': all(checks.values()),
        'display_recording_and_provenance_checks_passed': all(observer_checks.values()),
        'checks': checks,
        'baseline': off,
        'display': on,
        'wall_per_sim_second_change_percent': (on['wall_seconds_per_sim_second'] / off['wall_seconds_per_sim_second'] - 1) * 100,
        'control_p95_change_percent': (on['control_loop_timing']['p95_s'] / off['control_loop_timing']['p95_s'] - 1) * 100,
        'active_gpu_memory_peak_delta_mib': on['active_gpu_memory_mib']['maximum'] - off['active_gpu_memory_mib']['maximum'],
        'cloud_receipts': {'count': len(receipts), 'points': summarize([r['points'] for r in receipts]),
                           'source_span_seconds': (stamps[-1] - stamps[0]) / 1e9},
        'renderer_log_lines': renderer_lines,
        'video': video_info,
        'video_sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
        'video_decode': {'returncode': decoded.returncode, 'stderr': decoded.stderr},
        'limitations': [
            'One exploratory off/on pair on this fixed small-cloud scene; not a general performance estimate.',
            'The display condition includes low-rate capture and its CPU encoding overhead.',
            'GPU and RAM values are sampled host totals; peaks between samples can be missed.',
            'Video is recorded in wall time; physics duration comes from simulator records.',
            'A failed navigation condition invalidates complete-navigation acceptance; display/resource evidence remains separately inspectable.',
            'Physics-loop timing includes any protected stationary tail after a navigation failure.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--display', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.baseline, args.display)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': report['passed'], 'checks': report['checks'],
                      'wall_per_sim_second_change_percent': report['wall_per_sim_second_change_percent'],
                      'control_p95_change_percent': report['control_p95_change_percent']}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
