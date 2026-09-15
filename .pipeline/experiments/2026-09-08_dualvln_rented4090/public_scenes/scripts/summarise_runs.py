"""Collect the official metrics and the evidence trace of every completed run.

Reports each run separately and never averages a metric across runs without
saying so. Success and STOP provenance are kept apart: an episode that ends on a
learned STOP is still a failure if it stopped in the wrong place.
"""
import argparse
import collections
import glob
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_trace(p):
    return [json.loads(l) for l in open(p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs-dir', default='public_scenes/runs')
    ap.add_argument('--out', default='public_scenes/setup/run_summary.json')
    a = ap.parse_args()

    runs_dir = ROOT / a.runs_dir
    out = {'runs': [], 'per_episode_across_runs': {}, 'notes': []}

    for run in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        prog = run / 'progress.json'
        if not prog.exists():
            continue
        entry = {'run_id': run.name, 'episodes': [],
                 'aggregate_reported_by_evaluator': json.loads((run / 'result.json').read_text())
                 if (run / 'result.json').exists() else None,
                 'exit': json.loads((run / 'exit.json').read_text()) if (run / 'exit.json').exists() else None}
        by_ep = {}
        for line in prog.read_text().splitlines():
            r = json.loads(line)
            by_ep[r['episode_id']] = r
        for tf in sorted(glob.glob(str(run / 'trace_0' / '*.jsonl'))):
            recs = load_trace(tf)
            hdr = recs[0]
            foot = recs[-1]
            steps = [r for r in recs if r['record'] == 'step']
            s2 = [r for r in recs if r['record'] == 's2_call']
            s1 = [r for r in recs if r['record'] == 's1_call']
            pg = [r for r in recs if r['record'] == 'pixel_goal']
            prov = [r for r in recs if r['record'] == 'stop_provenance']
            ep_id = hdr['episode_id']
            path_len = 0.0
            prev = None
            for r in steps:
                if prev is not None:
                    path_len += math.dist(r['position'], prev)
                prev = r['position']
            dists = [r['distance_to_goal'] for r in steps if r['distance_to_goal'] is not None]
            learned = [r['step_id'] for r in steps if r['is_learned_episode_stop']]
            entry['episodes'].append({
                'episode_id': ep_id,
                'instruction': hdr['instruction'],
                'geodesic_distance_m': hdr['geodesic_distance'],
                'official_metrics': by_ep.get(ep_id),
                'termination_reason': foot['termination_reason'],
                'hit_evaluator_step_cap': foot['final_step_id'] > foot['evaluator_step_cap'],
                'ended_on_learned_stop_from_system2_text': bool(learned),
                'learned_stop_step_ids': learned,
                'non_terminal_stop_events': dict(collections.Counter(r['kind'] for r in prov)),
                'actions': dict(collections.Counter(r['action_name'] for r in steps)),
                'action_sources': dict(collections.Counter(r['action_source'] for r in steps)),
                'agent_path_length_m': round(path_len, 3),
                'distance_to_goal_first_min_last_m': [round(dists[0], 3), round(min(dists), 3),
                                                      round(dists[-1], 3)],
                'entered_success_radius_at_any_point': min(dists) <= 3.0,
                'collisions_final': next((r['collisions'] for r in reversed(steps)
                                          if r['collisions'] is not None), None),
                'pixel_goals': len(pg),
                # In public_eval_v1 this label was read after the loop variable
                # `action` had been reassigned, so it says 'level' when the goal
                # actually came from the look-down call. Corrected from v2 on.
                # `s2_branches` and `pixel_goal_model_input_sizes` below are
                # reliable in every run; prefer them.
                'pixel_goal_source_view_UNRELIABLE_IN_v1': dict(collections.Counter(
                    r.get('view_kind') for r in pg)),
                'pixel_goal_model_input_sizes': dict(collections.Counter(
                    'x'.join(str(v) for v in r['model_input_image_size']) for r in pg)),
                's2_calls': foot['s2_calls'],
                's2_seconds_total_whole_call': round(foot['s2_seconds_total'], 3),
                's2_mean_whole_call_seconds': round(foot['s2_seconds_total'] / max(foot['s2_calls'], 1), 4),
                's2_branches': dict(collections.Counter(r['branch'] for r in s2)),
                's1_calls': foot['s1_calls'],
                's1_seconds_total_whole_call': round(foot['s1_seconds_total'], 3),
                's1_mean_whole_call_seconds': round(foot['s1_seconds_total'] / max(foot['s1_calls'], 1), 4),
                'episode_wall_seconds': round(foot['episode_wall_seconds'], 2),
                'cuda_max_memory_allocated_bytes_cumulative_never_reset':
                    foot['cuda_max_memory_allocated_bytes_whole_run_so_far'],
            })
        gpu = run / 'gpu_samples_every_5s.csv'
        if gpu.exists():
            rows = [l.split(',') for l in gpu.read_text().splitlines()[1:] if l.strip()]
            used = [int(r[2].strip().split()[0]) for r in rows if len(r) > 2]
            if used:
                entry['device_memory_sampled_every_5s_MiB'] = {
                    'samples': len(used), 'max_used_whole_device': max(used),
                    'min_used_whole_device': min(used),
                    'scope': 'whole GPU, shared with a pre-existing isaac-sim container',
                }
        out['runs'].append(entry)

    for ep_id in (1, 2):
        rows = []
        for r in out['runs']:
            e = next((x for x in r['episodes'] if x['episode_id'] == ep_id), None)
            if e and e['official_metrics']:
                rows.append({'run_id': r['run_id'],
                             'success': e['official_metrics']['success'],
                             'spl': e['official_metrics']['spl'],
                             'oracle_success': e['official_metrics']['os'],
                             'navigation_error_m': round(e['official_metrics']['ne'], 3),
                             'steps': e['official_metrics']['steps'],
                             'termination_reason': e['termination_reason'],
                             'ended_on_learned_stop': e['ended_on_learned_stop_from_system2_text']})
        out['per_episode_across_runs'][f'episode_{ep_id}'] = {
            'runs': rows,
            'n_runs': len(rows),
            'n_success': sum(1 for r in rows if r['success'] == 1.0),
            'navigation_error_m_min_max': [min(r['navigation_error_m'] for r in rows),
                                           max(r['navigation_error_m'] for r in rows)] if rows else None,
            'all_ended_on_learned_stop': all(r['ended_on_learned_stop'] for r in rows) if rows else None,
        }

    out['notes'] = [
        'Repeated runs of the identical frozen episodes give different outcomes. '
        'System 2 is deterministic (do_sample=False); System 1 is a flow-matching '
        'diffusion sampler and the pinned evaluator seeds numpy only '
        '(np.random.seed(local_rank)), never torch, so its initial noise differs per run.',
        'Success and STOP provenance are independent: every episode here ended on a '
        'learned STOP emitted as text by System 2, and half of them still failed.',
        'pixel_goal_source_view is mislabelled in public_eval_v1 only; use s2_branches '
        'and pixel_goal_model_input_sizes, which are correct in every run. A 640x480 '
        'model input means the look-down view, 384x384 means the level view.',
    ]
    (ROOT / a.out).write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')

    print(f"{'run':<16}{'ep':>3}{'succ':>6}{'spl':>7}{'os':>5}{'NE m':>8}{'steps':>7}{'minNE':>7}  termination")
    for r in out['runs']:
        for e in r['episodes']:
            m = e['official_metrics'] or {}
            print(f"{r['run_id']:<16}{e['episode_id']:>3}{m.get('success',0):>6.1f}{m.get('spl',0):>7.3f}"
                  f"{m.get('os',0):>5.1f}{m.get('ne',0):>8.2f}{m.get('steps',0):>7}"
                  f"{e['distance_to_goal_first_min_last_m'][1]:>7.2f}  {e['termination_reason']}")
    for k, v in out['per_episode_across_runs'].items():
        print(f"{k}: {v['n_success']}/{v['n_runs']} successful, NE range {v['navigation_error_m_min_max']}, "
              f"all ended on learned STOP: {v['all_ended_on_learned_stop']}")
    print('SUMMARY_WRITTEN', a.out)


if __name__ == '__main__':
    main()
