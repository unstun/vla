"""Compare camera conditions against the recorded baseline, per episode.

Groups public_scenes/runs/* into B0 (public_eval_v*) and cam_<condition>_v*,
reads the official progress.json metrics and the evidence traces, and reports
ranges rather than bare means because System 1 sampling is unseeded. Never
mixes conditions and never averages across episodes without saying so.

  python3 public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py
"""
import argparse
import collections
import glob
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REQ = Path(__file__).resolve().parent


def load_trace(p):
    return [json.loads(l) for l in open(p)]


def run_condition(run_name, conds):
    if run_name.startswith(conds['baseline']['run_id_prefix']):
        return 'b0_baseline'
    for c in conds['conditions']:
        if run_name.startswith(f'cam_{c}_v'):
            return c
    return None


def summarise_run(run):
    prog = run / 'progress.json'
    inputs = json.loads((run / 'inputs.json').read_text()) if (run / 'inputs.json').exists() else {}
    entry = {'run_id': run.name, 'episodes': {},
             'progress_json_present': prog.exists(),
             'exit': json.loads((run / 'exit.json').read_text()) if (run / 'exit.json').exists() else None,
             'evaluator_sha256': inputs.get('input_sha256', {}).get(
                 'internnav/habitat_extensions/vln/habitat_vln_evaluator.py'),
             'resolved_camera_geometry': inputs.get('resolved_camera_geometry')}
    if not prog.exists():
        # A crashed or deadline-killed run: keep it visible with its exit record and no episode rows.
        return entry
    by_ep = {}
    for line in prog.read_text().splitlines():
        r = json.loads(line)
        by_ep[r['episode_id']] = r
    for tf in sorted(glob.glob(str(run / 'trace_0' / '*.jsonl'))):
        recs = load_trace(tf)
        hdr, foot = recs[0], recs[-1]
        if foot.get('record') != 'episode_footer':
            continue
        steps = [r for r in recs if r['record'] == 'step']
        s2 = [r for r in recs if r['record'] == 's2_call']
        pg = [r for r in recs if r['record'] == 'pixel_goal']
        prov = [r for r in recs if r['record'] == 'stop_provenance']
        ep = hdr['episode_id']
        m = by_ep.get(ep, {})
        dists = [r['distance_to_goal'] for r in steps if r['distance_to_goal'] is not None]
        entry['episodes'][ep] = {
            'success': m.get('success'), 'spl': m.get('spl'), 'oracle_success': m.get('os'),
            'navigation_error_m': m.get('ne'), 'steps': m.get('steps'),
            'termination_reason': foot['termination_reason'],
            'ended_on_learned_stop': any(r['is_learned_episode_stop'] for r in steps),
            'entered_success_radius': (min(dists) <= 3.0) if dists else None,
            'min_distance_to_goal_m': round(min(dists), 3) if dists else None,
            'collisions_final': next((r['collisions'] for r in reversed(steps) if r['collisions'] is not None), None),
            'non_terminal_stop_events': dict(collections.Counter(r['kind'] for r in prov)),
            's2_calls': foot['s2_calls'], 's1_calls': foot['s1_calls'],
            's2_branches': dict(collections.Counter(r['branch'] for r in s2)),
            'pixel_goals': len(pg),
            'episode_wall_seconds': round(foot['episode_wall_seconds'], 1),
        }
    return entry


def rng(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {'min': round(min(vals), 3), 'median': round(statistics.median(vals), 3), 'max': round(max(vals), 3),
            'n': len(vals)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs-dir', default='public_scenes/runs')
    ap.add_argument('--out', default=str(REQ.relative_to(ROOT) / 'condition_summary.json'))
    ap.add_argument('--md', default=str(REQ.relative_to(ROOT) / 'condition_summary.md'))
    a = ap.parse_args()
    conds = json.loads((REQ / 'conditions.json').read_text())
    labels = {'b0_baseline': 'B0 baseline (recorded)'}
    labels.update({k: f"{k} ({v['label']})" for k, v in conds['conditions'].items()})
    geometry = {'b0_baseline': conds['baseline']}
    geometry.update({k: {kk: v[kk] for kk in ('height_m', 'forward_offset_m', 'pitch_down_deg', 'hfov_deg', 'tilt_angle_deg')}
                     for k, v in conds['conditions'].items()})

    runs_dir = ROOT / a.runs_dir
    grouped = collections.defaultdict(list)
    for run in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        c = run_condition(run.name, conds)
        if c is None:
            continue
        s = summarise_run(run)
        if s:
            grouped[c].append(s)

    out = {'conditions': {}, 'notes': [
        'Five unseeded runs per condition on two custom public-scene episodes: report ranges and counts, not means alone.',
        'Success and learned STOP are independent; an episode that stops in the wrong place still ends on a learned STOP.',
        'B0 is the recorded public_eval_v1..v5; it is not rerun. Its evaluator hash must match every cam_* run.',
        'This is a public-scene functional test, not an R2R benchmark; effect sizes between conditions only.',
        'n_runs counts runs with a recorded result for that episode; runs_without_progress_json lists launched runs that produced none.',
    ]}
    order = ['b0_baseline'] + list(conds['conditions'])
    for c in order:
        runs = grouped.get(c, [])
        per_ep = {}
        for ep in (1, 2):
            rows = [r['episodes'][ep] for r in runs if ep in r['episodes']]
            per_ep[f'episode_{ep}'] = {
                'n_runs': len(rows),
                'n_success': sum(1 for r in rows if r['success'] == 1.0),
                'n_oracle_success': sum(1 for r in rows if r['oracle_success'] == 1.0),
                'n_ended_on_learned_stop': sum(1 for r in rows if r['ended_on_learned_stop']),
                'n_entered_success_radius': sum(1 for r in rows if r['entered_success_radius']),
                'navigation_error_m': rng([r['navigation_error_m'] for r in rows]),
                'spl': rng([r['spl'] for r in rows]),
                'steps': rng([r['steps'] for r in rows]),
                'collisions_final': rng([r['collisions_final'] for r in rows]),
                'pixel_goals': rng([r['pixel_goals'] for r in rows]),
                's2_calls': rng([r['s2_calls'] for r in rows]),
                'termination_reasons': dict(collections.Counter(r['termination_reason'] for r in rows)),
                's2_branches_total': dict(sum((collections.Counter(r['s2_branches']) for r in rows), collections.Counter())),
                'non_terminal_stop_events_total': dict(sum((collections.Counter(r['non_terminal_stop_events']) for r in rows), collections.Counter())),
            }
        out['conditions'][c] = {
            'label': labels[c], 'geometry': geometry[c], 'run_ids': [r['run_id'] for r in runs],
            'runs_without_progress_json': [r['run_id'] for r in runs if not r['progress_json_present']],
            'evaluator_sha256_set': sorted({r['evaluator_sha256'] for r in runs if r['evaluator_sha256']}),
            'exits': [r['exit'] for r in runs],
            'per_episode': per_ep,
            'total_success_over_runs': sum(per_ep[e]['n_success'] for e in per_ep),
            'total_runs_over_episodes': sum(per_ep[e]['n_runs'] for e in per_ep),
            'runs': runs,
        }

    (ROOT / a.out).write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')

    lines = ['# Camera-condition summary', '',
             '| Condition | Height | Pitch | HFOV | Tilt | Ep1 success | Ep1 NE m (min/med/max) | Ep2 success | Ep2 NE m (min/med/max) | Ep2 collisions (min/med/max) | Learned STOP | Total |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for c in order:
        d = out['conditions'][c]
        g = d['geometry']
        e1, e2 = d['per_episode']['episode_1'], d['per_episode']['episode_2']

        def r3(x):
            return '-' if not x else f"{x['min']}/{x['median']}/{x['max']}"
        lines.append(f"| {d['label']} | {g['height_m']} m | {g['pitch_down_deg']} deg | {g['hfov_deg']} | {g['tilt_angle_deg']} "
                     f"| {e1['n_success']}/{e1['n_runs']} | {r3(e1['navigation_error_m'])} "
                     f"| {e2['n_success']}/{e2['n_runs']} | {r3(e2['navigation_error_m'])} | {r3(e2['collisions_final'])} "
                     f"| {e1['n_ended_on_learned_stop'] + e2['n_ended_on_learned_stop']}/{e1['n_runs'] + e2['n_runs']} "
                     f"| {d['total_success_over_runs']}/{d['total_runs_over_episodes']} |")
    lines += ['', '## Notes', ''] + [f'- {n}' for n in out['notes']]
    (ROOT / a.md).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('SUMMARY_WRITTEN', a.out, a.md)


if __name__ == '__main__':
    main()
