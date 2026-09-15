"""Phase D.0c: summarise scripted collision-monitor test runs (phase_d_run_monitor_test.sh outputs).

    python3 phase_d0c_monitor_summary.py RUN_DIR [RUN_DIR ...] [--reference RUN_DIR ...] --out ../analysis/X.json

Per run: simulator termination and largest non-foot force; ground-truth leg-width footprint clearance to every box at
every 20 ms policy step (the D.0a geometry, scripts/phase_d0_footprint_clearance.py); what the relay logged about the
monitor (first changed tick, stop and scaled ticks, cloud-perceived clearance, wait times); and, with --reference, the
first policy step whose position or applied command differs from each reference run (replay runs only). Measurement
only. Standard library only.
"""

import argparse
import json
import math
import shlex
from pathlib import Path

from phase_d0_footprint_clearance import FOOTPRINTS, place, rectangle, signed_distance

EXPERIMENT = Path(__file__).resolve().parent.parent


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_steps(sim_dir):
    for name in ('isaac_steps.jsonl', 'fake_steps.jsonl'):
        if (sim_dir / name).exists():
            steps = rows(sim_dir / name)
            for s in steps:
                s['xy2'] = (s['xyz'] if 'xyz' in s else s['xy'])[:2]
            return name.split('_')[0], steps
    raise FileNotFoundError('no step log in {}'.format(sim_dir))


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))] if values else None


def first_divergence(steps, reference):
    for a, b in zip(steps, reference):
        if a['step'] != b['step']:
            return {'step': a['step'], 'why': 'step index mismatch'}
        dxy = math.dist(a['xy2'], b['xy2'])
        dcmd = max(abs(x - y) for x, y in zip(a['applied'], b['applied']))
        if dxy > 0.0 or dcmd > 0.0:
            return {'step': a['step'], 'sim_s': round(a['sim_ns'] / 1e9, 2), 'xy_dev_m': dxy, 'applied_dev': dcmd}
    return None


def summarise(run_dir, references=None):
    run_dir = Path(run_dir)
    command_lines = (run_dir / 'command.txt').read_text().splitlines()
    tokens = shlex.split(command_lines[0])
    if (run_dir / 'isaac').is_dir():      # D.0d VLA episode (phase_d_run_vla_episode.sh: RUN_ID EPISODE)
        sim_kind, relay_mode, episode_file, client_args = 'isaac', 'monitor', tokens[2], ['vla']
        sim_dir, drop = run_dir / 'isaac', ''
    else:                                 # D.0c scripted test (phase_d_run_monitor_test.sh)
        sim_kind, relay_mode, episode_file, client_args = tokens[2], tokens[3], tokens[4], tokens[5:]
        sim_dir, drop = run_dir / 'sim', command_lines[0].split('=')[-1].strip()
    episode = json.loads((EXPERIMENT / 'phase_c' / 'episodes' / episode_file).read_text())
    boxes = {lm['name']: rectangle(lm['center'][0] - lm['size'][0] / 2, lm['center'][0] + lm['size'][0] / 2,
                                   lm['center'][1] - lm['size'][1] / 2, lm['center'][1] + lm['size'][1] / 2)
             for lm in episode['landmarks']}
    _, steps = load_steps(sim_dir)
    sim_record = json.loads(next(sim_dir.glob('*_episode.json')).read_text())
    legs = rectangle(*FOOTPRINTS['legs'])
    best = None
    for s in steps:
        placed = place(legs, s['xy2'][0], s['xy2'][1], s['yaw'])
        for name, box in boxes.items():
            d, _ = signed_distance(placed, box)
            if best is None or d < best['clearance_m']:
                best = {'clearance_m': round(d, 4), 'sim_s': round(s['sim_ns'] / 1e9, 2), 'landmark': name}
    forces = [(s.get('nonfoot_substep_max_n') or 0.0, s.get('nonfoot_substep_max_body'), s['sim_ns']) for s in steps]
    peak = max(forces) if forces else (None, None, None)

    relay_ticks = rows(run_dir / 'relay' / 'relay_ticks.jsonl')
    relay_record = json.loads((run_dir / 'relay' / 'relay_episode.json').read_text())
    changed = [t for t in relay_ticks if any(abs(a - b) > 1e-9 for a, b in zip(t['in'], t['out']))]
    stopped = [t for t in changed if all(v == 0.0 for v in t['out']) and any(v != 0.0 for v in t['in'])]
    perceived = [(t['cloud_min_leg_clearance_m'], t['tick']) for t in relay_ticks
                 if t.get('cloud_min_leg_clearance_m') is not None]
    waits = [t['monitor_wait_ms'] for t in relay_ticks if 'monitor_wait_ms' in t]
    target = episode['target_landmark']
    centre = next(lm['center'][:2] for lm in episode['landmarks'] if lm['name'] == target)
    final_xy = steps[-1]['xy2'] if steps else None

    result = {
        'run': run_dir.name, 'sim': sim_kind, 'relay_mode': relay_mode, 'episode': episode_file,
        'client_args': client_args, 'drop_cloud_after_s': drop,
        'termination': sim_record.get('termination'), 'sim_seconds': sim_record.get('sim_seconds'),
        'policy_steps': len(steps),
        'peak_nonfoot_force_n': round(peak[0], 1) if peak[0] is not None else None, 'peak_body': peak[1],
        'peak_sim_s': round(peak[2] / 1e9, 2) if peak[2] is not None else None,
        'min_leg_clearance_ground_truth': best,
        'final_xy': [round(v, 3) for v in final_xy] if final_xy else None,
        'final_distance_to_target_centre_m': round(math.dist(final_xy, centre), 3) if final_xy else None,
        'relay_ticks': len(relay_ticks), 'relay_end': relay_record.get('end_reason'),
        'commands_changed': len(changed),
        'first_changed': ({'tick': changed[0]['tick'], 'sim_s': round(changed[0]['sim_ns'] / 1e9, 2),
                           'in': changed[0]['in'], 'out': changed[0]['out']} if changed else None),
        'stop_ticks': len(stopped),
        'first_stop_sim_s': round(stopped[0]['sim_ns'] / 1e9, 2) if stopped else None,
        'monitor_no_reply_ticks': relay_record.get('monitor_no_reply_ticks'),
        'clouds_received': relay_record.get('clouds_received'),
        'first_cloud_points': relay_record.get('first_cloud_points'),
        'min_cloud_points': relay_record.get('min_cloud_points'),
        'min_cloud_perceived_leg_clearance_m': min(perceived)[0] if perceived else None,
        'monitor_wait_ms_p50_p95_max': [percentile(waits, 0.5), percentile(waits, 0.95), max(waits)] if waits else None,
    }
    if references and client_args and client_args[0] == 'replay':
        # None means identical over the common length of the two step logs.
        result['first_divergence_from'] = {name: first_divergence(steps, ref) for name, ref in references.items()
                                          if name != run_dir.name}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--reference', type=Path, action='append', default=[],
                        help='a run directory (Phase C isaac/ or Phase D sim/ step log) that replay runs are compared '
                             'with; repeatable')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    references = {ref.name: load_steps(ref / 'isaac' if (ref / 'isaac').is_dir() else ref / 'sim')[1]
                  for ref in args.reference}
    results = [summarise(run, references) for run in args.runs]
    args.out.write_text(json.dumps(results, indent=2) + '\n')
    for r in results:
        gt = r['min_leg_clearance_ground_truth']
        print('{run}: {termination} at {sim_seconds}s peak {peak_nonfoot_force_n}N {peak_body}; legs clearance '
              '{gt_c} m at {gt_s}s ({gt_box}); changed {commands_changed}, stops {stop_ticks}, first change {fc}; '
              'perceived {min_cloud_perceived_leg_clearance_m}; divergence {div}'.format(
                  gt_c=gt['clearance_m'], gt_s=gt['sim_s'], gt_box=gt['landmark'],
                  fc=(r['first_changed'] or {}).get('sim_s'), div=r.get('first_divergence_from', '-'), **r))


if __name__ == '__main__':
    main()
