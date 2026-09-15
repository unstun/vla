"""Phase D.0f: summarise fused-camera runs, gate the scripted preflight, and put VLA outcomes beside ideal-camera runs.

    python3 phase_d0f_fusion_summary.py RUN_DIR [RUN_DIR ...] [--reference RUN_DIR ...] --out ../analysis/X.json

Per fused run: the fusion geometry and measured intrinsics the server recorded; every fused frame from
`isaac/fusion_frames.jsonl`, split into decision frames (what the model received) and video frames, re-checked here
against the pinned Habitat c8 preflight bounds; the in-container recompute check; the device memory peak from `samples.csv`; and the
episode outcome (termination, success, oracle success, closest approach, System 2's first answers, monitor changes).
Reference runs (ideal camera) get the outcome only. Measurement only. Standard library only.

Bounds are pinned here (C8_BOUNDS, from the Habitat camera ablation's conditions.json `preflight.fused`, c8), not read
from the run, and the run's recorded bounds must equal them.

Preflight gate (`preflight_gate`, scripted-agent runs): the recorded bounds are the pinned ones; the camera intrinsics
and mounts were read back from Isaac and accepted; at least one decision frame, and one decision frame per image sent;
every decision AND video frame inside the bounds and different from the ideal render; the in-container recompute
(`fusion_recompute_check.json`) reproduced every saved fused image bit for bit and found the client's first frame is the
fused one; the episode ended by the client; and device memory <= ISAAC_ONLY_MAX_MIB.
"""

import argparse
import csv
import json
from pathlib import Path

C8_BOUNDS = {'max_uncovered_fraction': 0.04, 'min_fraction_from_head': 0.7, 'max_mean_abs_err_head_region': 10.0,
             'max_mean_abs_err_d435_region': 20.0, 'max_fusion_ms_per_frame': 300.0}
# PROVISIONAL, derived not measured with the fusion: 24,081 MiB usable on the 4090 minus the InternVLA-N1 client's
# 17,728 MiB (Phase B v4; D.0e 17,694) leaves about 6,350 MiB for Isaac. Phase B dual-720 Isaac with one-env buffers used
# 3,956 MiB and Phase C/D Isaac 3,788 MiB; the scripted client uses no GPU, so the preflight peak is Isaac alone.
ISAAC_ONLY_MAX_MIB = 6000
MOUNT_TOLERANCE_M, MOUNT_TOLERANCE_DEG = 0.0001, 0.01   # authored camera prim pose vs configuration


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def spread(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return {'min': values[0], 'median': values[len(values) // 2],
            'p95': values[min(len(values) - 1, int(round(0.95 * (len(values) - 1))))], 'max': values[-1],
            'n': len(values)}


def bound_failures(row, b):
    failures = []
    if row['coverage']['none'] > b['max_uncovered_fraction']:
        failures.append('uncovered')
    if row['coverage']['head'] < b['min_fraction_from_head']:
        failures.append('head_share')
    for region, key in (('head', 'max_mean_abs_err_head_region'), ('d435', 'max_mean_abs_err_d435_region')):
        value = row['error_vs_ideal'][region]['mean_abs_err']
        if value is None or value > b[key]:
            failures.append(region + '_error')
    return failures


def frame_stats(frames):
    return {
        'n': len(frames),
        'fusion_ms': spread([r['fusion_ms'] for r in frames]),
        'uncovered_fraction': spread([r['coverage']['none'] for r in frames]),
        'head_fraction': spread([r['coverage']['head'] for r in frames]),
        'd435_fraction': spread([r['coverage']['d435'] for r in frames]),
        'head_region_mean_abs_err': spread([r['error_vs_ideal']['head']['mean_abs_err'] for r in frames]),
        'd435_region_mean_abs_err': spread([r['error_vs_ideal']['d435']['mean_abs_err'] for r in frames]),
        'blend_region_mean_abs_err': spread([r['error_vs_ideal']['blend']['mean_abs_err'] for r in frames]),
        'd435_self_occlusion_fraction': spread([r['d435_self_occlusion_fraction'] for r in frames]),
    }


def device_peak_mib(run_dir):
    path = run_dir / 'samples.csv'
    if not path.exists():
        return None
    with open(path) as handle:
        values = [float(r['device_used_mib']) for r in csv.DictReader(handle) if r.get('device_used_mib')]
    return max(values) if values else None


def driver_setting(run_dir, key):
    """A VLA_* setting from the driver's command.txt, for runs that ended before the client wrote a record."""
    path = run_dir / 'command.txt'
    for token in (path.read_text().split() if path.exists() else []):
        if token.startswith(key + '='):
            return token.split('=', 1)[1] or None
    return None


def outcome(run_dir):
    isaac = load(run_dir / 'isaac' / 'isaac_episode.json')
    client = load(run_dir / 'client' / 'client_episode.json')
    relay = load(run_dir / 'relay' / 'relay_episode.json')
    episode = isaac.get('episode') or {}
    radius = episode.get('success_radius_m')
    closest = isaac.get('min_distance_to_target_m')
    decisions = rows(run_dir / 'client' / 'decisions.jsonl')
    return {
        'run': run_dir.name, 'episode': episode.get('name') or (client.get('episode') or {}).get('name'),
        'target': episode.get('target_landmark'), 'agent': client.get('agent') or driver_setting(run_dir, 'VLA_AGENT'),
        'isaac_termination': isaac.get('termination'), 'client_termination': client.get('termination'),
        'sim_seconds': isaac.get('sim_seconds'), 'decisions': client.get('decisions'),
        'stopped_by_model': client.get('stopped_by_model'), 'success': client.get('success'),
        'oracle_success': (closest <= radius) if closest is not None and radius is not None else None,
        'closest_to_target_m': None if closest is None else round(closest, 3),
        'final_distance_to_target_m': None if isaac.get('final_distance_to_target_m') is None
        else round(isaac['final_distance_to_target_m'], 3),
        'final_xy': [round(v, 3) for v in isaac['final_xy']] if isaac.get('final_xy') else None,
        'nonfoot_contact': isaac.get('termination') == 'nonfoot_contact',
        'commands_changed_by_monitor': relay.get('commands_changed_by_monitor'),
        'first_answers': [{'decision': d['decision'], 'llm_output': d.get('llm_output'),
                           'first_action': d.get('first_action'), 'pixel_goal': d.get('pixel_goal')}
                          for d in decisions[:3]],
        'device_peak_mib': device_peak_mib(run_dir),
    }


def fusion_summary(run_dir):
    isaac = load(run_dir / 'isaac' / 'isaac_episode.json')
    fusion = isaac.get('fusion')
    refusals = [name for name in ('FUSION_GEOMETRY_MISMATCH', 'FUSION_SETUP_ERROR')
                if (run_dir / 'isaac' / name).exists()]
    if not fusion and not refusals:
        return None
    recorded = {k: v for k, v in ((fusion or {}).get('config', {}).get('preflight_bounds_from_habitat_c8') or {}).items()
                if k in C8_BOUNDS}
    frames = rows(run_dir / 'isaac' / 'fusion_frames.jsonl')
    decision = [r for r in frames if r.get('kind') == 'decision']
    video = [r for r in frames if r.get('kind') == 'video']

    def outside(selection):
        return [{'kind': r['kind'], 'index': r['index'], 'sim_s': round(r['sim_ns'] / 1e9, 2),
                 'failures': bound_failures(r, C8_BOUNDS)} for r in selection if bound_failures(r, C8_BOUNDS)]
    mounts = (fusion or {}).get('mounts_authored') or {}
    return {
        'refusal_files': refusals,
        'recorded_bounds_equal_pinned': recorded == C8_BOUNDS,
        'geometry': (fusion or {}).get('geometry'), 'intrinsics_measured': (fusion or {}).get('intrinsics_measured'),
        'mounts_authored': mounts,
        'virtual_camera': (fusion or {}).get('virtual_camera'),
        'live_camera_pose_readback_record_only': (fusion or {}).get('live_camera_pose_readback_record_only'),
        'max_mount_position_error_m': max((m['position_error_m'] for m in mounts.values()), default=None),
        'max_mount_rotation_error_deg': max((m['rotation_error_deg'] for m in mounts.values()), default=None),
        'images_sent': isaac.get('images_sent'),
        'decision_frames': frame_stats(decision), 'video_frames': frame_stats(video),
        'decision_frames_outside_bounds': outside(decision), 'video_frames_outside_bounds': outside(video),
        'frames_equal_to_ideal': sum(1 for r in frames if not r['fused_differs_from_ideal_fraction'] > 0),
        'server_and_summary_bound_checks_disagree': sum(
            1 for r in frames if bool(bound_failures(r, C8_BOUNDS)) != bool(r['c8_bound_failures'])),
        'server_summary': (fusion or {}).get('summary'),
        'recompute_check': load(run_dir / 'fusion_recompute_check.json') or None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--reference', type=Path, action='append', default=[])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = {'fused': [], 'reference': [outcome(r) for r in args.reference]}
    for run_dir in args.runs:
        entry = outcome(run_dir)
        entry['fusion'] = fusion_summary(run_dir)
        f = entry['fusion'] or {}
        if entry['agent'] == 'scripted':
            recompute = f.get('recompute_check') or {}
            checks = {
                'fusion_recorded': bool(f) and f['geometry'] is not None,
                'recorded_bounds_equal_pinned': bool(f) and f['recorded_bounds_equal_pinned'],
                'geometry_accepted_by_server': bool(f) and not f['refusal_files'] and len(f['mounts_authored']) == 3
                and len(f['intrinsics_measured'] or {}) == 3,
                'camera_mounts_authored_as_configured': bool(f) and len(f['mounts_authored']) == 3 and all(
                    m['position_error_m'] <= MOUNT_TOLERANCE_M and m['rotation_error_deg'] <= MOUNT_TOLERANCE_DEG
                    for m in f['mounts_authored'].values()),
                'decision_frames_present': bool(f) and f['decision_frames']['n'] > 0,
                'one_decision_frame_per_image_sent': bool(f) and f['decision_frames']['n'] == f['images_sent'],
                'video_frames_present': bool(f) and f['video_frames']['n'] > 0,
                'all_decision_frames_inside_c8_bounds': bool(f) and not f['decision_frames_outside_bounds'],
                'all_video_frames_inside_c8_bounds': bool(f) and not f['video_frames_outside_bounds'],
                'no_frame_equal_to_ideal': bool(f) and f['frames_equal_to_ideal'] == 0,
                'recompute_check_passed': recompute.get('passed') is True,
                'episode_ended_by_client': entry['isaac_termination'] == 'client_end',
                'isaac_device_peak_within_limit': entry['device_peak_mib'] is not None
                and entry['device_peak_mib'] <= ISAAC_ONLY_MAX_MIB,
            }
            entry['preflight_gate'] = {'checks': checks, 'isaac_only_max_mib': ISAAC_ONLY_MAX_MIB,
                                       'passed': all(checks.values())}
        result['fused'].append(entry)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for entry in result['fused'] + result['reference']:
        f = entry.get('fusion') or {}
        d = f.get('decision_frames') or {}
        print('{run}: {isaac_termination} {sim_seconds}s success={success} oracle={oracle_success} closest={closest_to_target_m} '
              'contact={nonfoot_contact} changed={commands_changed_by_monitor} first={first} gpu_peak={device_peak_mib}'.format(
                  first=[a['llm_output'] for a in entry['first_answers'][:2]], **entry))
        if f:
            print('   fusion decision frames {} (outside bounds {}), video {} (outside {}); uncovered {}; head share {}; '
                  'err head {} d435 {}; self-occlusion {}; ms {}; mount err {} m / {} deg; recompute {}'.format(
                      d.get('n'), len(f['decision_frames_outside_bounds']), f['video_frames']['n'],
                      len(f['video_frames_outside_bounds']),
                      d.get('uncovered_fraction'), d.get('head_fraction'), d.get('head_region_mean_abs_err'),
                      d.get('d435_region_mean_abs_err'), d.get('d435_self_occlusion_fraction'), d.get('fusion_ms'),
                      f['max_mount_position_error_m'], f['max_mount_rotation_error_deg'],
                      (f.get('recompute_check') or {}).get('passed')))
        if 'preflight_gate' in entry:
            print('   PREFLIGHT_GATE', 'PASSED' if entry['preflight_gate']['passed'] else 'FAILED',
                  entry['preflight_gate']['checks'])


if __name__ == '__main__':
    main()
