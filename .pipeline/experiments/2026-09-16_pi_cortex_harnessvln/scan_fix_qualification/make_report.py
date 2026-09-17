#!/usr/bin/env python3
"""Data and figures for the SCAN terminal-acceleration fix report (task design.md section 5, panels 1-9).

Reads returned files only. Writes these files under --output (default scan_fix_qualification/report/):
  figures/panel2_*.png ... figures/panel9_timeline_eNN.png
  videos/eNN.mp4      hardlink (copy fallback) to each ledger episode's walk_review/walk_review.mp4
  report_data.json    panel 1 (verdict table) and panel 7 (episode table) as data, the numbers behind
                      every figure, and the SHA-256 of every input read and every output written
No HTML is written. The lead builds the page from these files.

Integrity checks:
- The native suite is re-analysed in memory with analyze_suite.analyze(), which checks the returned
  hashes, the run package manifest and the frozen thresholds. The result must equal the stored
  comparison.json and paths.json. An optional --stop-replay-run (implement.md C5) gets the same check.
- Isaac episodes come from the series ledger. Each returned episode is re-reviewed in memory with
  review_two_goal.review(), and its checks must equal the stored review.json. A mismatch is reported,
  not hidden.
- Nothing runs on a remote host. Run directories, the ledger and the suite outputs are only read.

Stop positions: review_two_goal.py takes the cancel terminal's base_xyz from the last physics row
before the backend confirmed the cancellation. The robot can still move a few millimetres after that.
The native replay fixtures (make_fixtures.py) start from the resubmitted PCT request, which the driver
sends from the still-confirmed pose (post_stop_proof). Panels 2 and 8 therefore place stops at the
still-confirmed pose. Panel 7 lists all three values.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import sys
from collections import Counter
from datetime import datetime, timezone


HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parents[2]
PRD = REPO / '.trellis/tasks/archive/2026-09/09-16-scan-terminal-accel-fix-qualification/prd.md'
SUITE_RUN = HERE / 'runs/native_suite_20260917T083723Z'
LEDGER = HERE / 'isaac_series/series_ledger.jsonl'
OUTPUT = HERE / 'report'
RESULT_MD = HERE / 'RESULT.md'
SCAN_03 = EXP / 'p2b_execution/builds/scan_03'
SCAN_04 = EXP / 'p2b_execution/builds/scan_04'
# Sep 16 continuous two-goal runs with the original SCAN build (prd.md Background).
OLD_RUNS = (
    ('actual4', EXP / 'isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4'),
    ('display off', EXP / 'pointcloud_display/runs/pointcloud_20260916T171400Z_off'),
    ('RViz', EXP / 'pointcloud_display/runs/pointcloud_20260916T172100Z_rviz'),
    ('RViz GPU', EXP / 'pointcloud_display/runs/pointcloud_20260916T173400Z_rviz_gpu'),
)
READ_ONLY_ROOTS = (EXP / 'isaac_runner/two_goal_runs', EXP / 'pointcloud_display/runs', HERE / 'runs',
                   HERE / 'isaac_series', HERE / 'fixtures')

# Ledger outcomes written by run_isaac_series.py. Only these two are navigation results (PRD D11). Any
# other outcome (host_not_idle, prepare_/execute_failed, prepare_/execute_timeout, review_error) is listed
# separately and left for the lead to classify.
COUNTED_OUTCOMES = {'passed': True, 'review_failed': False}
CONFIDENCE = 0.95
BUILDS = ('original', 'candidate')
BUILD_LABEL = {'original': 'original (scan_03)', 'candidate': 'fixed (scan_04)'}
GATE_REASON = 'acceleration_gate'
ATTEMPT = re.compile(r'-attempt-(\d+)$')
CRITERION = re.compile(r'^- \[( |x)\] (AC\d+) (.*)$')

# Okabe-Ito colour-blind-safe palette.
BUILD_COLOR = {'original': '#D55E00', 'candidate': '#0072B2'}
STATE_COLOR = {'accepted': '#009E73', 'accepted_with_collision': '#CC79A7',
               'acceleration_gate': '#D55E00', 'other_rejection': '#56B4E9'}
STATE_LABEL = {'accepted': 'accepted', 'accepted_with_collision': 'accepted, collision sample',
               'acceleration_gate': 'rejected: acceleration gate', 'other_rejection': 'rejected: other reason'}
OUTCOME_STYLE = {True: ('o', '#009E73', 'passed'), False: ('X', '#CC79A7', 'failed'),
                 None: ('o', '#7F7F7F', 'not counted')}
EPISODE_COLORS = ('#0072B2', '#E69F00', '#009E73', '#CC79A7', '#56B4E9', '#D55E00', '#000000', '#F0E442')
DPI = 150
FIG_W = 11.0
STYLE = {
    'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10, 'xtick.labelsize': 9,
    'ytick.labelsize': 9, 'legend.fontsize': 9, 'axes.spines.top': False, 'axes.spines.right': False,
    'legend.frameon': False, 'figure.facecolor': 'white', 'savefig.facecolor': 'white',
}


class ReportError(RuntimeError):
    pass


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CODE = {
    'analyze_suite': HERE / 'analyze_suite.py',
    'make_fixtures': HERE / 'make_fixtures.py',
    'run_isaac_series': HERE / 'run_isaac_series.py',
    'review_two_goal': EXP / 'p2b_execution/review_two_goal.py',
    'make_walk_review': EXP / 'isaac_runner/make_walk_review.py',
}
an = load_module('scan_fix_report_analyze_suite', CODE['analyze_suite'])
mf = load_module('scan_fix_report_make_fixtures', CODE['make_fixtures'])
ris = load_module('scan_fix_report_run_isaac_series', CODE['run_isaac_series'])
rtg = load_module('scan_fix_report_review_two_goal', CODE['review_two_goal'])
mwr = load_module('scan_fix_report_make_walk_review', CODE['make_walk_review'])


# ---------------------------------------------------------------------------------------------
# Small helpers.

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True))


def fmt(value, digits=2):
    return 'n/a' if value is None else '%.*f' % (digits, value)


def rounded(value, digits=6):
    return None if value is None else round(float(value), digits)


class InputLog:
    """SHA-256, size and role of every file whose content feeds the report."""

    def __init__(self):
        self.files = {}

    def add(self, path, role):
        path = Path(path)
        if not path.is_file():
            raise ReportError('missing input: %s' % path)
        key = rel(path)
        entry = self.files.get(key)
        if entry is None:
            entry = self.files[key] = {'path': key, 'sha256': sha256_file(path), 'bytes': path.stat().st_size,
                                       'roles': []}
        if role not in entry['roles']:
            entry['roles'].append(role)
        return path

    def json(self, path, role):
        return json.loads(self.add(path, role).read_text())

    def records(self):
        return [self.files[k] for k in sorted(self.files)]


def binomial_lower_bound(successes, trials, confidence=CONFIDENCE):
    """Exact (Clopper-Pearson) one-sided lower confidence bound for a binomial success probability."""
    if trials <= 0:
        return None
    if not 0 <= successes <= trials:
        raise ValueError('successes must be within 0..trials')
    alpha = 1.0 - confidence
    if successes == 0:
        return 0.0
    if successes == trials:
        return alpha ** (1.0 / trials)

    def upper_tail(p):
        return sum(math.comb(trials, i) * p ** i * (1.0 - p) ** (trials - i) for i in range(successes, trials + 1))

    low, high = 0.0, 1.0
    for _ in range(200):
        mid = (low + high) / 2.0
        if upper_tail(mid) < alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


# ---------------------------------------------------------------------------------------------
# Native suite.

def verified_native_run(run_dir, inputs, role):
    """analyze_suite.analyze() on the run; the stored comparison.json and paths.json must equal it."""
    run_dir = Path(run_dir)
    try:
        report, paths = an.analyze(run_dir)
    except an.AnalysisRefused as error:
        raise ReportError('analyze_suite refused %s: %s' % (run_dir, error))
    fresh = {'comparison.json': normalized(report), 'paths.json': normalized(paths)}
    for name, value in fresh.items():
        if inputs.json(run_dir / name, role) != value:
            raise ReportError('%s differs from a fresh analyze_suite.analyze() result' % (run_dir / name))
    for name in ('returned_artifacts/artifact_hashes.json', 'package_manifest.json', 'request.json',
                 'managers/manager_identity.json', 'returned_artifacts/result.json'):
        inputs.add(run_dir / name, role + ' (checked by analyze_suite.analyze)')
    fixtures = inputs.json(run_dir / 'inputs/fixtures/suite_cases.json', role + ' fixtures (package manifest)')
    return fresh['comparison.json'], fresh['paths.json'], fixtures


def is_resume_start(start):
    provenance = start.get('provenance') or {}
    request = provenance.get('source_request_id') or provenance.get('base_source_request_id') or ''
    match = ATTEMPT.search(request)
    return bool(match) and int(match.group(1)) >= 2


def first_call(row):
    return next((c for c in row['calls'] if c.get('call') == 0 and c.get('success')), None)


def resume_outcomes(report, fixtures, groups=None):
    """First-call outcome per resume start and build: empty map, polynomial initialization, seed 0."""
    runs = {}
    for row in report['rows']:
        if row['kind'] != 'single' or row['map_id'] != 'empty' or row['random_poly']:
            continue
        call = first_call(row)
        runs.setdefault(row['start_id'], {}).setdefault(row['build'], []).append({
            'repeat': row['repeat'], 'accepted': row['accepted'], 'reason': row['reason'],
            'gate_value': row['gate_value'], 'max_acc': call['max_acc'] if call else None,
            'endpoint_xy_m': call['endpoint_xy_m'] if call else None})
    out = []
    for start in fixtures['starts']:
        if start['id'] not in runs or not is_resume_start(start) or (groups and start['group'] not in groups):
            continue
        entry = {'start_id': start['id'], 'group': start['group'], 'x': start['start'][0],
                 'source': (start.get('provenance') or {}).get('source_run')
                 or (start.get('provenance') or {}).get('base_source_run'), 'builds': {}}
        for build, items in runs[start['id']].items():
            items.sort(key=lambda r: r['repeat'])
            head = items[0]
            same = all((r['accepted'], r['reason'], r['gate_value'], r['max_acc']) ==
                       (head['accepted'], head['reason'], head['gate_value'], head['max_acc']) for r in items)
            entry['builds'][build] = {
                'accepted': head['accepted'], 'reason': head['reason'], 'gate_value': head['gate_value'],
                'max_acc': head['max_acc'], 'endpoint_xy_m': head['endpoint_xy_m'], 'repeats': len(items),
                'repeats_identical': same, 'reasons': dict(Counter(r['reason'] for r in items))}
        out.append(entry)
    return sorted(out, key=lambda e: e['x'])


def all_rejected(build_entry, reason=GATE_REASON):
    return bool(build_entry) and set(build_entry['reasons']) == {reason}


def failure_band(points, build='original', reason=GATE_REASON):
    """Contiguous sweep positions where every repeat of `build` is rejected for `reason`.

    Shading runs to the midpoint between a rejected position and its accepted neighbour (the sweep
    resolution bounds the true edge), or to the rejected position itself at the end of the sweep.
    """
    pts = sorted((p['x'], all_rejected(p['builds'].get(build), reason)) for p in points)
    segments, i = [], 0
    while i < len(pts):
        if not pts[i][1]:
            i += 1
            continue
        j = i
        while j + 1 < len(pts) and pts[j + 1][1]:
            j += 1
        low = (pts[i - 1][0] + pts[i][0]) / 2.0 if i > 0 else pts[i][0]
        high = (pts[j][0] + pts[j + 1][0]) / 2.0 if j + 1 < len(pts) else pts[j][0]
        segments.append({'first_rejected_x': pts[i][0], 'last_rejected_x': pts[j][0],
                         'shade_from_x': round(low, 9), 'shade_to_x': round(high, 9), 'positions': j - i + 1})
        i = j + 1
    steps = sorted({round(b[0] - a[0], 9) for a, b in zip(pts, pts[1:])})
    return {'build': build, 'reason': reason, 'segments': segments, 'sweep_positions': len(pts),
            'sweep_steps_m': steps, 'sweep_range_x': [pts[0][0], pts[-1][0]] if pts else None,
            'rule': 'every repeat rejected by the acceleration gate; shading extends halfway to the '
                    'nearest accepted sweep position'}


def band_position(x, band):
    """'inside' between rejected sweep positions, 'edge' in the half-step margin, 'beyond_sweep' outside the
    swept range (no native evidence), else 'outside'."""
    if x is None:
        return None
    low, high = band.get('sweep_range_x') or (-math.inf, math.inf)
    if not low <= x <= high:
        return 'beyond_sweep'
    if any(s['first_rejected_x'] <= x <= s['last_rejected_x'] for s in band['segments']):
        return 'inside'
    if any(s['shade_from_x'] <= x <= s['shade_to_x'] for s in band['segments']):
        return 'edge'
    return 'outside'


def replay_verdicts(report, fixtures, run_ids):
    """Native verdict at each Isaac stop pose, keyed by run id (fixtures from make_fixtures.py from-journals)."""
    out = {}
    for entry in resume_outcomes(report, fixtures, groups={'recorded_isaac_stop'}):
        run_id = next((r for r in sorted(run_ids, key=len, reverse=True) if entry['start_id'].startswith(r + '__')), None)
        if run_id is None:
            continue
        verdict = {}
        for build in BUILDS:
            item = entry['builds'].get(build)
            verdict[build] = ', '.join('%s %d/%d' % (reason, count, item['repeats'])
                                       for reason, count in sorted(item['reasons'].items())) if item else 'missing'
        record = {'start_id': entry['start_id'], 'x': entry['x'], 'verdict': verdict, 'builds': entry['builds']}
        current = out.get(run_id)
        # Prefer the first resubmission of goal A when a run has several resubmitted requests.
        if current is None or entry['start_id'].endswith('goal_a_attempt_2'):
            out[run_id] = record
    return out


# ---------------------------------------------------------------------------------------------
# Ledger, PRD and AC1.

def parse_ledger(path):
    episodes, ends = [], []
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as error:
            raise ReportError('ledger line %d is not JSON: %s' % (number, error))
        if 'series_end_utc' in record:
            ends.append(dict(record, ledger_line=number))
            continue
        if not isinstance(record.get('episode'), int):
            raise ReportError('ledger line %d has no integer episode' % number)
        episodes.append(dict(record, ledger_line=number))
    return episodes, ends


def series_summary(episodes, ends, planned):
    counted = [e for e in episodes if e.get('outcome') in COUNTED_OUTCOMES]
    passed = sum(1 for e in counted if COUNTED_OUTCOMES[e['outcome']])
    trials = len(counted)
    problems = [e['episode'] for e in episodes if e.get('problems')]
    if trials and passed < trials:
        status = 'fail'
    elif problems:
        status = 'needs_review'
    elif ends and trials == len(planned) and passed == trials:
        status = 'pass'
    elif ends:
        status = 'incomplete'
    else:
        status = 'in_progress'
    bound = binomial_lower_bound(passed, trials)
    return {
        'status': status,
        'planned_episodes': len(planned),
        'planned': planned,
        'counted_episodes': trials,
        'passed_episodes': passed,
        'failed_episodes': trials - passed,
        'success_lower_bound': rounded(bound, 4),
        'bound_rule': 'exact binomial (Clopper-Pearson) one-sided %d %% lower bound over the counted episodes'
                      % round(CONFIDENCE * 100),
        'counted_outcomes': sorted(COUNTED_OUTCOMES),
        'uncounted': [{'episode': e['episode'], 'run_id': e.get('run_id'), 'outcome': e.get('outcome'),
                       'ledger_line': e['ledger_line']} for e in episodes if e.get('outcome') not in COUNTED_OUTCOMES],
        'episodes_with_integrity_problems': problems,
        'series_ended': bool(ends),
        'series_end': [{k: v for k, v in e.items() if k != 'host_after'} for e in ends],
        'host_after': [e.get('host_after') for e in ends],
    }


def parse_criteria(text):
    items, current = [], None
    for line in text.splitlines():
        match = CRITERION.match(line)
        if match:
            current = {'id': match.group(2), 'checked': match.group(1) == 'x', 'text': match.group(3).strip()}
            items.append(current)
        elif current is not None and line.startswith('      ') and line.strip():
            current['text'] += ' ' + line.strip()
        else:
            current = None
    for item in items:
        head, found, tail = item['text'].partition(' Passed')
        item['requirement'] = head.strip()
        item['prd_evidence'] = ('Passed' + tail).strip() if found else None
    return items


def ac1_facts(inputs):
    compare = inputs.json(SCAN_04 / 'tree_compare_scan_03.json', 'AC1 source tree comparison')
    build = inputs.json(SCAN_04 / 'build_result.json', 'AC1 build result')
    new = inputs.json(SCAN_04 / 'install_identity.json', 'AC1 install identity')
    old = inputs.json(SCAN_03 / 'install_identity.json', 'AC1 install identity (reference)')
    manifest = inputs.json(SCAN_04 / 'terminal_accel_fix_manifest.json', 'AC1 fix manifest')
    new_files, old_files = new['installed_files'], old['installed_files']
    differing = sorted(p for p in set(new_files) | set(old_files) if new_files.get(p) != old_files.get(p))
    changed = [{'path': c['path'], 'reference_sha256': c['reference_sha256'], 'candidate_sha256': c['candidate_sha256'],
                'lines': [op['candidate_lines'] for op in c['opcodes']]} for c in compare['changed_files']]
    passed = (compare.get('exactly_one_file_one_line') is True and build.get('passed') is True
              and new.get('source_matches') is True)
    return {'status': 'pass' if passed else 'fail', 'exactly_one_file_one_line': compare.get('exactly_one_file_one_line'),
            'changed_files': changed, 'build_passed': build.get('passed'), 'image_id': build.get('image_id'),
            'installed_files': len(new_files), 'install_paths_differing_from_scan_03': differing,
            'fix_manifest_keys': sorted(manifest)}


def verdict_table(criteria, suite, ac1, series, result_md_exists, sampled_limit):
    acc = suite['acceptance']
    control = suite['validity_control']
    follow = acc['AC3']['follow_up_report_only']
    single = acc['AC3']['single_call']
    ac4 = acc['AC4']
    ev = {
        'AC0': '%s %s: %s' % (suite['run_id'], suite['validity'], '; '.join(
            '%s %s' % (c['start_id'], ', '.join('%s %d/%d' % (k, v, len(c['observed']))
                                                 for k, v in sorted(Counter(c['observed']).items())))
            for c in control['checks'])),
        'AC1': 'changed %s; build passed %s; install identity %d files, differing from scan_03: %s' % (
            '; '.join('%s line %s' % (c['path'], ', '.join(
                '%d' % a if a == b else '%d-%d' % (a, b) for a, b in c['lines'])) for c in ac1['changed_files']),
            ac1['build_passed'], ac1['installed_files'], ', '.join(ac1['install_paths_differing_from_scan_03']) or 'none'),
        'AC2': 'runs %d; original accepted %d (gate rejections %d); fixed accepted %d; fixed calls over %.1f m/s^2: %d of %d' % (
            acc['AC2']['runs_in_scope'], acc['AC2']['original_accepted'], acc['AC2']['original_acceleration_gate_rejections'],
            acc['AC2']['candidate_accepted'], sampled_limit, len(acc['AC2']['candidate_calls_over_sampled_limit']),
            acc['AC2']['candidate_accepted_calls_checked']),
        'AC3': 'fixed single-call max endpoint %.4f m (limit %.2f m, over limit %d); follow-up report only: original max %.4f m, fixed max %.4f m' % (
            single['max_endpoint_xy_m']['candidate'], acc['AC3']['limit_m'], len(single['candidate_over_limit']),
            follow['max_endpoint_xy_m']['original'], follow['max_endpoint_xy_m']['candidate']),
        'AC4': 'runs %d; fixed collision hits %d; counted fixed rejections %d; finding: %d original-build trajectories with collision samples' % (
            ac4['runs_in_scope'], len(ac4['candidate_collision_hits']),
            len(ac4['candidate_rejections_where_original_accepts_without_hit']),
            len(ac4['findings']['original_build_collision_hits'])),
        'AC5': 'groups %d; successes original %d, fixed %d; fixed-only failures %d' % (
            acc['AC5']['groups'], acc['AC5']['totals']['original'], acc['AC5']['totals']['candidate'],
            len(acc['AC5']['candidate_only_failures_requiring_explanation'])),
        'AC6': 'sequences %d; completed original %d, fixed %d' % (
            acc['AC6']['sequences'], acc['AC6']['completed']['original'], acc['AC6']['completed']['candidate']),
        'AC7': '%d of %d planned episodes counted, %d passed; one-sided %d %% lower bound %s; %s' % (
            series['counted_episodes'], series['planned_episodes'], series['passed_episodes'], round(CONFIDENCE * 100),
            'n/a' if series['success_lower_bound'] is None else '%.3f' % series['success_lower_bound'],
            'series ended' if series['series_ended'] else 'series not ended'),
        'AC8': 'RESULT.md %s; the claim boundary is judged by the lead' % ('present' if result_md_exists else 'not written'),
    }
    computed = {'AC0': control['status'], 'AC1': ac1['status'], 'AC7': series['status'], 'AC8': 'pending'}
    computed.update({k: acc[k]['status'] for k in ('AC2', 'AC3', 'AC4', 'AC5', 'AC6')})
    rows = []
    for item in criteria:
        value = computed.get(item['id'], 'unknown')
        if item['id'] in ('AC7', 'AC8'):
            status = value
        elif (value == 'pass') == item['checked']:
            status = value if value == 'pass' else 'fail'
        else:
            status = 'mismatch'
        rows.append({'id': item['id'], 'status': status, 'prd_checked': item['checked'], 'computed': value,
                     'requirement': item['requirement'], 'evidence': ev.get(item['id']),
                     'prd_evidence': item['prd_evidence']})
    return rows


# ---------------------------------------------------------------------------------------------
# Isaac runs.

def isaac_run_facts(run_dir, inputs, role):
    """Review verdict, poses, events and time series of one returned two-goal run."""
    run_dir = Path(run_dir)
    artifacts = run_dir / 'returned_artifacts'
    for name in ('run_request.json', 'inputs/pilot.json', 'source_env_hashes.json'):
        inputs.add(run_dir / name, role)
    for name in ('pilot_journal.json', 'runner_output/metrics.jsonl', 'runner_output/summary.json',
                 'artifact_hashes.json', 'result.json'):
        inputs.add(artifacts / name, role)
    if (run_dir / 'remote_only_artifacts.json').is_file():
        inputs.add(run_dir / 'remote_only_artifacts.json', role)
    review = rtg.review(run_dir)
    run_id = mwr.load_json(run_dir / 'run_request.json')['run_id']
    pilot = mwr.load_json(run_dir / 'inputs/pilot.json')
    summary = mwr.load_json(artifacts / 'runner_output/summary.json')
    result = mwr.load_json(artifacts / 'result.json')
    rows = load_metrics(artifacts / 'runner_output/metrics.jsonl')
    state = mwr.StateIndex(rows)
    parsed = mwr.extract_journal(mwr.load_json(artifacts / 'pilot_journal.json'), run_id, state)
    terminals = review['terminals']
    resume = next((p for p in review['plan_history'] if p.get('request_id') == run_id + '-goal-a-attempt-2'), None)
    goals = {g['goal_id']: g['ground_xyz_m'] for g in pilot['goals']}
    arrivals = {}
    for item, goal_id in zip(terminals[1:], ('goal-a', 'goal-b')):
        arrivals[goal_id] = {'present': item['present'], 'xy_error_m': item.get('target_xy_error_m'),
                             'base_xyz': item.get('base_xyz'), 'sim_time_s': item.get('sim_time_s')}
    points = {k: v['xyz'] for k, v in parsed['points'].items()}
    command = [math.hypot(r['admitted_command'][0], r['admitted_command'][1]) for r in rows]
    return {
        'run_id': run_id,
        'run_dir': rel(run_dir),
        'review_passed': review['passed'],
        'checks': review['checks'],
        'checks_passed': sum(1 for v in review['checks'].values() if v),
        'checks_total': len(review['checks']),
        'failed_checks': sorted(k for k, v in review['checks'].items() if not v),
        'cancel_terminal_xyz': terminals[0].get('base_xyz'),
        'cancel_terminal_sim_time_s': terminals[0].get('sim_time_s'),
        'measured_cancel_displacement_m': terminals[0].get('cancel_displacement_m'),
        'start_xyz': points.get('start'),
        'cancel_trigger_xyz': points.get('cancel'),
        'still_pose_xyz': points.get('stop'),
        'resume_plan_start_xyz': resume['request']['start_xyz_m'] if resume else None,
        'resume_plan_ok': bool(resume and resume.get('ok')),
        'arrivals': arrivals,
        'goals': goals,
        'goal_xy_tolerance_m': pilot['goal_xy_tolerance_m'],
        'max_nonfoot_force_n': review['max_nonfoot_force_n'],
        'contact_threshold_n': summary['contact_guard']['threshold_n'],
        'sim_seconds': review['sim_seconds'],
        'runner_wall_seconds': review['wall_seconds'],
        'gpu_peak_mib': (result.get('gpu_memory') or {}).get('peak_memory_used_mib'),
        'events': [{k: e.get(k) for k in ('key', 'label', 'sim_time_s', 'placement', 'cause', 'state_row_lag_s')}
                   for e in parsed['events']],
        'missing_events': parsed['missing'],
        'stop_windows': stop_windows(rows, terminals, pilot),
        'command_series': 'hypot(admitted_command[0], admitted_command[1]) from metrics.jsonl',
        '_series': {'sim': state.sim, 'speed': [float(r['horizontal_speed_mps']) for r in rows], 'command': command,
                    'force': [float(r['nonfoot_force_max_n']) for r in rows],
                    'x': [float(r['base_xyz'][0]) for r in rows], 'y': [float(r['base_xyz'][1]) for r in rows]},
    }


METRIC_KEYS = ('step', 'sim_time_s', 'state_sample_monotonic_ns', 'base_xyz', 'horizontal_speed_mps',
               'admitted_command', 'nonfoot_force_max_n', 'yaw_rate_radps', 'command_reason', 'command_stale')


def load_metrics(path):
    rows = []
    with Path(path).open() as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                missing = [k for k in METRIC_KEYS if k not in row]
                if missing:
                    raise ReportError('%s row lacks %s' % (path, missing))
                rows.append({k: row[k] for k in METRIC_KEYS})
    if not rows:
        raise ReportError('empty metrics: %s' % path)
    return rows


def stop_windows(rows, terminals, pilot):
    """The raw physics stillness window before each terminal, found with review_two_goal.instant_still.

    Same loop as review_two_goal.review(); a short window also reports the row that ended it and which of
    its values exceed the pilot.json stillness limits.
    """
    dwell = pilot['stop_dwell_sim_seconds']
    out = []
    for item in terminals:
        if not item.get('present'):
            continue
        limit_ns = item['terminal']['monotonic_s'] * 1e9
        before = [r for r in rows if r['state_sample_monotonic_ns'] <= limit_ns]
        window, breaker = [], None
        for row in reversed(before):
            if not rtg.instant_still(row, pilot):
                breaker = row
                break
            window.append(row)
            if window[0]['sim_time_s'] - window[-1]['sim_time_s'] >= dwell:
                break
        span = window[0]['sim_time_s'] - window[-1]['sim_time_s'] if window else 0.0
        record = {'request_id': item['request_id'], 'status': item['status'], 'span_s': rounded(span),
                  'required_s': dwell, 'passed': span >= dwell,
                  'start_s': rounded(window[-1]['sim_time_s'], 4) if window else None,
                  'end_s': rounded(window[0]['sim_time_s'], 4) if window else None,
                  'matches_review': close(span, item.get('raw_stop_span_sim_s'))}
        if breaker is not None and span < dwell:
            command = breaker['admitted_command']
            values = {'horizontal_speed_mps': breaker['horizontal_speed_mps'],
                      'yaw_rate_radps': breaker['yaw_rate_radps'],
                      'command_xy_norm': math.hypot(command[0], command[1]), 'command_yaw': command[2],
                      'command_reason': breaker['command_reason'], 'command_stale': breaker['command_stale']}
            over = []
            if abs(values['yaw_rate_radps']) > pilot['stop_yaw_rate_radps']:
                over.append('|yaw_rate_radps| %.4f > %g' % (abs(values['yaw_rate_radps']), pilot['stop_yaw_rate_radps']))
            if values['horizontal_speed_mps'] > pilot['stop_speed_mps']:
                over.append('horizontal_speed_mps %.4f > %g' % (values['horizontal_speed_mps'], pilot['stop_speed_mps']))
            if values['command_xy_norm'] > pilot['stop_command_norm'] or abs(values['command_yaw']) > pilot['stop_command_norm']:
                over.append('command above stop_command_norm %g' % pilot['stop_command_norm'])
            if breaker['command_stale']:
                over.append('command_stale')
            record['ended_by'] = {'sim_time_s': rounded(breaker['sim_time_s'], 4), 'values': values,
                                  'limits_exceeded': over or ['command_reason %r not accepted as still' % breaker['command_reason']]}
        out.append(record)
    return out


def close(a, b, tol=1e-9):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    return abs(float(a) - float(b)) <= tol


def episode_facts(entry, inputs, runs_root):
    record = {'episode': entry['episode'], 'run_id': entry.get('run_id'), 'outcome': entry.get('outcome'),
              'counted': entry.get('outcome') in COUNTED_OUTCOMES,
              'passed': COUNTED_OUTCOMES.get(entry.get('outcome')), 'ledger_line': entry['ledger_line'],
              'trigger_m': entry.get('cancel_displacement_m'), 'ledger': entry, 'facts': None, 'problems': []}
    run_dir = Path(runs_root) / entry['run_id'] if entry.get('run_id') else None
    if run_dir is None or not (run_dir / 'returned_artifacts').is_dir():
        if record['counted']:
            record['problems'].append('ledger episode has no returned run package')
        return record
    role = 'Isaac episode %d' % entry['episode']
    try:
        facts = isaac_run_facts(run_dir, inputs, role)
    except Exception as error:
        # A counted episode must be fully reviewable. An uncounted one (for example an execute failure that
        # returned a partial package) is listed for the lead instead of blocking the whole report.
        if record['counted']:
            raise
        record['problems'].append('uncounted run package is not reviewable: %r' % (error,))
        return record
    record['facts'] = facts
    problems = record['problems']
    stored = inputs.json(run_dir / 'review.json', role + ' stored review')
    if stored.get('checks') != facts['checks'] or stored.get('passed') != facts['review_passed']:
        problems.append('recomputed review differs from stored review.json')
    request = inputs.json(run_dir / 'run_request.json', role)
    verdict = inputs.json(run_dir / 'return_verdict.json', role + ' return verdict')
    record['host_run_wall_s'] = (verdict.get('host_wall_seconds') or {}).get('run')
    record['returned_hashes_match'] = verdict.get('returned_hashes_match')
    record['remote_only_accepted'] = verdict.get('remote_only_accepted')
    comparisons = {
        'trigger vs run_request.json cancel_displacement_m': (entry.get('cancel_displacement_m'), request.get('cancel_displacement_m')),
        'checks_passed': (entry.get('checks_passed'), facts['checks_passed']),
        'checks_total': (entry.get('checks_total'), facts['checks_total']),
        'cancel_stop_xyz vs review cancel terminal': (entry.get('cancel_stop_xyz'), facts['cancel_terminal_xyz']),
        'resume_plan_start_xyz': (entry.get('resume_plan_start_xyz'), facts['resume_plan_start_xyz']),
        'gpu_peak_mib vs result.json': (entry.get('gpu_peak_mib'), facts['gpu_peak_mib']),
    }
    for name, (a, b) in comparisons.items():
        if entry.get('outcome') in COUNTED_OUTCOMES and not close(a, b):
            problems.append('ledger %s %r != %r' % (name, a, b))
    video = run_dir / 'walk_review/walk_review.mp4'
    record['walk_video_source'] = video if video.is_file() else None
    if video.is_file():
        inputs.add(video, role + ' walk review video')
        if (run_dir / 'walk_review/walk_review.json').is_file():
            inputs.add(run_dir / 'walk_review/walk_review.json', role + ' walk review sidecar')
    elif record['counted']:
        problems.append('walk_review/walk_review.mp4 missing')
    return record


def stop_x(facts):
    """Still-confirmed pose, falling back to the resubmitted PCT request start."""
    if not facts:
        return None
    if facts.get('still_pose_xyz'):
        return facts['still_pose_xyz'][0]
    return facts['resume_plan_start_xyz'][0] if facts.get('resume_plan_start_xyz') else None


def episode_table(episodes, replay, band):
    rows = []
    for ep in episodes:
        facts = ep.get('facts') or {}
        arrivals = facts.get('arrivals') or {}
        run_id = ep.get('run_id')
        if replay is None:
            native = 'pending'
        elif run_id in replay['verdicts']:
            native = {BUILD_LABEL[b]: replay['verdicts'][run_id]['verdict'][b] for b in BUILDS}
            if replay['validity'] != 'VALID':
                native = 'replay %s (AC0 failed)' % replay['validity']
        else:
            native = 'not in replay %s' % replay['run_id']
        x = stop_x(facts)
        rows.append({
            'episode': ep['episode'],
            'run_id': run_id,
            'outcome': ep.get('outcome'),
            'counted': ep['counted'],
            'trigger_m': ep.get('trigger_m'),
            'measured_cancel_displacement_m': rounded(facts.get('measured_cancel_displacement_m')),
            'stop_x_m': rounded(x),
            'stop_x_source': 'post_stop_proof snapshot measured base_xyz (driver still-confirmed pose)',
            'cancel_terminal_x_m': rounded((facts.get('cancel_terminal_xyz') or [None])[0]),
            'resume_plan_start_x_m': rounded((facts.get('resume_plan_start_xyz') or [None])[0]),
            'stop_vs_original_failure_band': band_position(x, band),
            'band_rule': ('inside: between rejected sweep positions; edge: within half a sweep step of the band; '
                          'beyond_sweep: outside the swept x range, no native evidence'),
            'native_verdict_at_stop': native,
            'checks_passed': facts.get('checks_passed'),
            'checks_total': facts.get('checks_total'),
            'failed_checks': facts.get('failed_checks'),
            'failed_stop_windows': [w for w in facts.get('stop_windows', []) if not w['passed']],
            'arrival_xy_error_a_m': rounded((arrivals.get('goal-a') or {}).get('xy_error_m')),
            'arrival_xy_error_b_m': rounded((arrivals.get('goal-b') or {}).get('xy_error_m')),
            'max_nonfoot_force_n': facts.get('max_nonfoot_force_n'),
            'episode_wall_s': rounded(facts.get('runner_wall_seconds'), 3),
            'episode_wall_source': 'runner summary.json wall_seconds',
            'host_run_wall_s': rounded(ep.get('host_run_wall_s'), 3),
            'sim_s': rounded(facts.get('sim_seconds'), 3),
            'gpu_peak_mib': facts.get('gpu_peak_mib'),
            'walk_video': ep.get('walk_video'),
            'problems': ep.get('problems', []),
        })
    return rows


def link_video(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if os.path.samefile(source, target):
            return 'hardlink'
        target.unlink()
    try:
        os.link(source, target)
        return 'hardlink'
    except OSError:
        shutil.copy2(source, target)
        return 'copy'


# ---------------------------------------------------------------------------------------------
# Figures.

def new_figure(width, height):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    fig = Figure(figsize=(width, height), dpi=DPI)
    FigureCanvasAgg(fig)
    return fig


def save_figure(fig, path, outputs, panel, caption):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches='tight', pad_inches=0.12, metadata={'Software': None})
    width, height = struct.unpack('>II', path.read_bytes()[16:24])
    outputs.append({'kind': 'figure', 'panel': panel, 'path': rel(path), 'sha256': sha256_file(path),
                    'bytes': path.stat().st_size, 'width_px': width, 'height_px': height, 'caption': caption})


def mark_rejections(ax, xs, gate, color, reason, label=None):
    marker = 'x' if reason == GATE_REASON else '+'
    if xs:
        ax.plot(xs, [gate] * len(xs), linestyle='none', marker=marker, markersize=9, markeredgewidth=2.0,
                color=color, label=label, zorder=5)


def label_levels(xs, labels, data_per_inch, fontsize=8.0, marker_in=0.12):
    """Greedy levels so that a marker plus its right-hand label never overlaps another on the same level."""
    ends, levels = {}, []
    for x, label in zip(xs, labels):
        left = x - marker_in * data_per_inch
        right = x + (marker_in + 0.62 * fontsize / 72.0 * (len(label) + 1)) * data_per_inch
        level = 0
        while ends.get(level, -math.inf) > left:
            level += 1
        ends[level] = right
        levels.append(level)
    return levels


def plot_panel2(points, band, ticks, replay_points, gate, path, outputs):
    xs_all = [p['x'] for p in points] + [t['x'] for t in ticks if t['x'] is not None] + [r['x'] for r in replay_points]
    x0, x1 = min(xs_all) - 0.012, max(xs_all) + 0.012
    axis_width_in = FIG_W * (0.9 - 0.125)
    step = 0.26
    placed, base = {}, 0.0
    lane_ticks = []
    for lane_key in ('new', 'old'):
        group = sorted((t for t in ticks if t['lane'] == lane_key and t['x'] is not None), key=lambda t: t['x'])
        levels = label_levels([t['x'] for t in group], [t['label'] for t in group], (x1 - x0) / axis_width_in)
        placed[lane_key] = base
        lane_ticks += [(t, base + step * level) for t, level in zip(group, levels)]
        base += step * (max(levels, default=0) + 1) + 0.3
    lane_h = 0.35 * base / step + 0.3
    fig = new_figure(FIG_W, 4.9 + lane_h)
    grid = fig.add_gridspec(2, 1, height_ratios=[4.0, lane_h], hspace=0.07)
    ax = fig.add_subplot(grid[0])
    lane = fig.add_subplot(grid[1], sharex=ax)
    for seg in band['segments']:
        for axis in (ax, lane):
            axis.axvspan(seg['shade_from_x'], seg['shade_to_x'], color=BUILD_COLOR['original'], alpha=0.10, linewidth=0)
        ax.text((seg['shade_from_x'] + seg['shade_to_x']) / 2.0, 1.05,
                'original rejects every resume plan here\n(sweep x = %.2f to %.2f m)' % (
                    seg['first_rejected_x'], seg['last_rejected_x']),
                ha='center', va='center', fontsize=9, color='#8a3a00')
    ax.axhline(gate, linestyle='--', color='0.25', linewidth=1.1)
    ax.text(x1, gate + 0.02, 'SCAN acceleration gate %.1f m/s$^2$ ' % gate, ha='right', va='bottom', fontsize=9, color='0.25')
    sweep = [p for p in points if p['group'] == 'stop_position_sweep']
    recorded = [p for p in points if p['group'] != 'stop_position_sweep']
    for build in BUILDS:
        color = BUILD_COLOR[build]
        xs = [p['x'] for p in sweep]
        ys = [p['builds'][build]['max_acc'] if p['builds'][build]['accepted'] else float('nan') for p in sweep]
        ax.plot(xs, ys, marker='o', markersize=5, linewidth=1.3, color=color,
                label='%s, sweep: accepted' % BUILD_LABEL[build])
        acc = [p for p in recorded if p['builds'][build]['accepted']]
        ax.plot([p['x'] for p in acc], [p['builds'][build]['max_acc'] for p in acc], linestyle='none', marker='s',
                markersize=8, markerfacecolor='white', markeredgecolor=color, markeredgewidth=1.8,
                label='%s, recorded Sep 16 stop fixtures' % BUILD_LABEL[build])
        for reason in sorted({p['builds'][build]['reason'] for p in points if not p['builds'][build]['accepted']}):
            rejected = [p['x'] for p in points if not p['builds'][build]['accepted'] and p['builds'][build]['reason'] == reason]
            mark_rejections(ax, rejected, gate, color, reason,
                            label='%s: rejected (%s), drawn on the gate' % (BUILD_LABEL[build], reason.replace('_', ' ')))
    for item in replay_points:
        for build in BUILDS:
            entry = item['builds'].get(build)
            if not entry:
                continue
            y = entry['max_acc'] if entry['accepted'] else gate
            ax.plot([item['x']], [y], linestyle='none', marker='D', markersize=8,
                    markerfacecolor=BUILD_COLOR[build] if entry['accepted'] else 'white',
                    markeredgecolor='black', markeredgewidth=1.0, zorder=6)
    if replay_points:
        ax.plot([], [], linestyle='none', marker='D', markerfacecolor='0.6', markeredgecolor='black',
                label='native replay at an Isaac stop pose (hollow = rejected)')
    for passed in (True, False):
        marker, color, text = OUTCOME_STYLE[passed]
        ax.plot([], [], linestyle='none', marker=marker, color=color, markersize=8, label='lower strip: Isaac run ' + text)
    ax.set_xlim(x0, x1)
    top = max([gate] + [b['max_acc'] for p in points for b in p['builds'].values() if b['max_acc'] is not None])
    ax.set_ylim(0.0, top + 0.8)
    ax.set_ylabel('sampled max acceleration\nof the planned path (m/s$^2$)')
    ax.grid(axis='y', linewidth=0.4, alpha=0.5)
    ax.tick_params(labelbottom=False)
    ax.legend(loc='upper left', ncol=2, fontsize=8.5, handlelength=1.8, columnspacing=1.2)
    ax.set_title('Where the bug bites: plan acceleration against resume start x '
                 '(native suite, empty map, polynomial init, seed 0)', loc='left')
    for tick, y in lane_ticks:
        marker, color, _ = OUTCOME_STYLE[tick['passed']]
        lane.plot([tick['x']], [y], linestyle='none', marker=marker, markersize=8, color=color,
                  markerfacecolor=color if tick['passed'] is not None else 'white', markeredgecolor=color)
        lane.annotate(tick['label'], (tick['x'], y), xytext=(6, 0), textcoords='offset points', va='center',
                      fontsize=8, color='0.2')
    lane.set_yticks([placed['new'], placed['old']],
                    labels=['Sep 17 series\nfixed (scan_04)', 'Sep 16 runs\noriginal (scan_03)'])
    for key in ('new', 'old'):
        lane.axhline(placed[key] - 0.15, color='0.85', linewidth=0.8)
    lane.set_ylim(-0.3, base - 0.15)
    lane.spines['left'].set_visible(False)
    lane.tick_params(axis='y', length=0)
    lane.set_xlabel('resume start x in the world frame (m); Isaac stops at the still-confirmed pose')
    caption = ('Sampled maximum acceleration of the first returned plan against the resume start x. Crosses on the '
               'dashed gate line are gate rejections (no plan returned). The shaded band is the sweep range where '
               'the original build rejects every repeat. The lower strip marks Isaac stop positions.')
    save_figure(fig, path, outputs, '2', caption)


def start_label(start):
    if start['group'] == 'stop_position_sweep':
        return 'sweep x = %.2f' % start['start'][0]
    return '%s  x = %.3f' % (start['id'], start['start'][0])


def init_label(init):
    if init['random_poly']:
        return 'random s%d' % init['seed']
    return 'poly s%d #%d' % (init['seed'], init['repeat'] + 1)


def cell_state(row, max_collisions):
    if row['accepted']:
        call = first_call(row)
        return 'accepted_with_collision' if call and call['collision_samples'] > max_collisions else 'accepted'
    return GATE_REASON if row['reason'] == GATE_REASON else 'other_rejection'


def grid_data(report, fixtures, max_collisions):
    starts = [s['id'] for s in fixtures['starts']]
    inits = [i['id'] for i in fixtures['inits']]
    maps = [m['id'] for m in fixtures['maps']]
    grid = {}
    for row in report['rows']:
        if row['kind'] != 'single':
            continue
        grid[(row['map_id'], row['start_id'], row['init_id'], row['build'])] = cell_state(row, max_collisions)
    missing = [k for k in ((m, s, i, b) for m in maps for s in starts for i in inits for b in BUILDS) if k not in grid]
    if missing:
        raise ReportError('pass/fail grid is incomplete: %d cells missing, e.g. %s' % (len(missing), missing[:3]))
    counts = {m: {b: dict(Counter(grid[(m, s, i, b)] for s in starts for i in inits)) for b in BUILDS} for m in maps}
    return grid, counts


def plot_panel3(grid, counts, fixtures, path, outputs):
    import numpy as np
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    starts, inits, maps = fixtures['starts'], fixtures['inits'], fixtures['maps']
    states = list(STATE_COLOR)
    fig = new_figure(FIG_W, 8.2)
    axes = fig.subplots(1, len(maps), sharey=True)
    fig.subplots_adjust(left=0.25, right=0.995, top=0.86, bottom=0.2, wspace=0.06)
    cmap = ListedColormap([STATE_COLOR[s] for s in states])
    for ax, spec in zip(axes, maps):
        codes = np.zeros((len(starts), 2 * len(inits)))
        for r, start in enumerate(starts):
            for c, init in enumerate(inits):
                for h, build in enumerate(BUILDS):
                    codes[r, 2 * c + h] = states.index(grid[(spec['id'], start['id'], init['id'], build)])
        ax.imshow(codes, cmap=cmap, vmin=-0.5, vmax=len(states) - 0.5, aspect='auto', interpolation='nearest')
        for c in range(len(inits)):
            ax.axvline(2 * c + 0.5, color='white', linewidth=0.5)
            if c:
                ax.axvline(2 * c - 0.5, color='white', linewidth=2.4)
        for r in range(1, len(starts)):
            ax.axhline(r - 0.5, color='white', linewidth=1.4)
        ax.set_xticks([2 * c + 0.5 for c in range(len(inits))], labels=[init_label(i) for i in inits],
                      rotation=90, fontsize=8)
        ax.set_yticks(range(len(starts)), labels=[start_label(s) for s in starts], fontsize=8)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        name = spec['id'].replace('_', ' ') + ' map'
        if spec.get('lateral_center_offset_m') is not None:
            name += ', centre %.1f m left of route' % spec['lateral_center_offset_m']
        n = len(starts) * len(inits)
        accepted = {b: counts[spec['id']][b].get('accepted', 0) + counts[spec['id']][b].get('accepted_with_collision', 0)
                    for b in BUILDS}
        ax.set_title('%s\noriginal accepted %d/%d\nfixed accepted %d/%d' % (
            name, accepted['original'], n, accepted['candidate'], n), fontsize=9.5)
    handles = [Patch(facecolor=STATE_COLOR[s], label=STATE_LABEL[s]) for s in states]
    fig.legend(handles=handles, loc='lower center', ncol=4, bbox_to_anchor=(0.6, 0.0), fontsize=9)
    fig.text(0.6, 0.045, 'Each cell is one fixture run: left half original (scan_03), right half fixed (scan_04). '
             'Rows: resume and initial starts; columns: initializations.', ha='center', fontsize=9, color='0.25')
    fig.suptitle('First-call outcome of every single-call fixture run, by map', x=0.02, ha='left', fontsize=11)
    caption = ('Outcome of every single-call fixture run. Each cell is split into the original (left) and fixed (right) '
               'build. Colours: accepted, accepted with a collision sample, acceleration-gate rejection, other rejection.')
    save_figure(fig, path, outputs, '3', caption)


def endpoint_data(report):
    single = {b: [] for b in BUILDS}
    follow = {b: {} for b in BUILDS}
    for row in report['rows']:
        for call in row['calls']:
            if not call.get('success'):
                continue
            if row['kind'] == 'single':
                single[row['build']].append(call['endpoint_xy_m'])
            else:
                follow[row['build']].setdefault(call['call'], []).append(call['endpoint_xy_m'])
    return single, follow


def stats(values):
    if not values:
        return {'n': 0}
    ordered = sorted(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    return {'n': len(values), 'min': rounded(ordered[0]), 'median': rounded(median), 'max': rounded(ordered[-1])}


def plot_panel4(single, follow, limit, path, outputs):
    import numpy as np
    rng = np.random.RandomState(0)
    fig = new_figure(FIG_W, 5.0)
    ax = fig.add_subplot(1, 1, 1)
    positions = {('single', 'original'): 0.0, ('single', 'candidate'): 1.0,
                 ('follow', 'original'): 2.6, ('follow', 'candidate'): 3.6}
    ax.axvspan(2.05, 4.15, color='0.92', linewidth=0)
    ax.text(3.1, 0.99, 'follow-up replans: reported, not judged (D10)', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=9, color='0.3')
    ax.text(0.5, 0.99, 'single calls: judged by AC3', transform=ax.get_xaxis_transform(), ha='center', va='top',
            fontsize=9, color='0.3')
    ax.plot([-0.45, 1.45], [limit, limit], linestyle='--', color='0.2', linewidth=1.2)
    ax.text(1.47, limit, 'AC3 limit %.2f m' % limit, va='center', fontsize=9, color='0.2')
    ax.plot([2.15, 4.05], [limit, limit], linestyle=':', color='0.45', linewidth=1.0)
    for build in BUILDS:
        values = single[build]
        x = positions[('single', build)] + rng.uniform(-0.3, 0.3, len(values))
        ax.plot(x, values, linestyle='none', marker='o', markersize=3.2, alpha=0.45, color=BUILD_COLOR[build])
        ax.text(positions[('single', build)], -0.1, 'n = %d\nmax %.4f m' % (len(values), max(values)),
                transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=8.5)
        markers = {0: 'o', 1: 's', 2: '^'}
        count, top = 0, 0.0
        for call, values in sorted(follow[build].items()):
            x = positions[('follow', build)] + (call - 1) * 0.25 + rng.uniform(-0.08, 0.08, len(values))
            ax.plot(x, values, linestyle='none', marker=markers.get(call, 'D'), markersize=5, alpha=0.75,
                    markerfacecolor='none', markeredgecolor=BUILD_COLOR[build])
            count += len(values)
            top = max(top, max(values))
        if count:
            ax.text(positions[('follow', build)], -0.1, 'n = %d\nmax %.4f m' % (count, top),
                    transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=8.5)
    for call, marker in ((0, 'o'), (1, 's'), (2, '^')):
        ax.plot([], [], linestyle='none', marker=marker, markerfacecolor='none', markeredgecolor='0.3',
                label='follow-up call %d' % (call + 1))
    ax.legend(loc='upper left', bbox_to_anchor=(0.54, 0.93), fontsize=8.5)
    ax.set_xticks([positions[k] for k in sorted(positions, key=positions.get)],
                  labels=[BUILD_LABEL[b] for _, b in sorted(positions, key=positions.get)])
    ax.tick_params(axis='x', length=0, pad=4)
    ax.set_xlim(-0.55, 4.25)
    ax.set_ylim(0.0, max([limit] + [v for b in BUILDS for v in single[b]] +
                         [v for b in BUILDS for vs in follow[b].values() for v in vs]) * 1.22)
    ax.set_ylabel('endpoint XY distance to target (m)')
    ax.grid(axis='y', linewidth=0.4, alpha=0.5)
    ax.set_title('Endpoint distance of every accepted trajectory (native suite, all maps and initializations)', loc='left')
    fig.subplots_adjust(bottom=0.22)
    caption = ('Endpoint XY distance to the target for every accepted call. Single calls are judged against the '
               '0.05 m limit (AC3). Follow-up calls are shown for both builds but not judged (D10).')
    save_figure(fig, path, outputs, '4', caption)


def rect_distance(point, box):
    lo, hi = box['min'][:2], box['max'][:2]
    return mf.segment_rectangle_distance(tuple(point), tuple(point), lo, hi)


def box_voxel_range(box, res):
    """Voxel index range the suite harness marks: every voxel whose centre lies in the closed box.

    rebound_replan_suite.cpp mark_boxes: lo = ceil(min / res - 0.5), hi = floor(max / res - 0.5).
    """
    lo = [int(math.ceil(box['min'][k] / res - 0.5)) for k in range(3)]
    hi = [int(math.floor(box['max'][k] / res - 0.5)) for k in range(3)]
    return lo, hi


def inflated_cells(lo, hi, res, radius):
    """XY voxel indices of the inflated buffer: occupied voxels dilated by the offsets of
    grid_map.cpp rebuildInflationOffsets (offset norm strictly below double_cylinder_radius)."""
    steps = int(math.ceil(radius / res))
    offsets = [(dx, dy) for dx in range(-steps, steps + 1) for dy in range(-steps, steps + 1)
               if not math.sqrt((dx * res) ** 2 + (dy * res) ** 2) >= radius]
    return {(x + dx, y + dy) for x in range(lo[0], hi[0] + 1) for y in range(lo[1], hi[1] + 1) for dx, dy in offsets}


def voxel_of(point, res):
    """GridMap::posToIndex: floor(pos * resolution_inv)."""
    inv = 1.0 / res
    return (int(math.floor(point[0] * inv)), int(math.floor(point[1] * inv)))


def cells_distance(point, cells, res):
    """XY distance from a point to the union of voxel squares (0 inside)."""
    if voxel_of(point, res) in cells:
        return 0.0
    edge = [c for c in cells if any((c[0] + dx, c[1] + dy) not in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    return min(mf.segment_rectangle_distance(tuple(point), tuple(point), (c[0] * res, c[1] * res),
                                             ((c[0] + 1) * res, (c[1] + 1) * res)) for c in edge)


def path_case(label, entry, report_rows, boxes, planner, log_boxes):
    target = entry['target']
    res, radius, offset = planner['resolution_m'], planner['double_cylinder_radius_m'], planner['double_cylinder_offset_m']
    case = {'label': label, 'start': entry['start'], 'target': target, 'box': None, 'builds': {}}
    cells = None
    if entry['occupied_boxes']:
        box = boxes[entry['occupied_boxes']]['box']
        lo, hi = box_voxel_range(box, res)
        cells = inflated_cells(lo, hi, res, radius)
        logged = log_boxes[0] if log_boxes else {}
        case['box'] = {
            'min': box['min'], 'max': box['max'], 'voxel_index_min': lo, 'voxel_index_max': hi,
            'voxel_indices_match_log': [int(v) for v in logged.get('voxel_index_min', [])] == lo
            and [int(v) for v in logged.get('voxel_index_max', [])] == hi,
            'z_range_m': [lo[2] * res - planner['obstacles_inflation_z_down_m'],
                          (hi[2] + 1) * res + planner['obstacles_inflation_z_up_m']],
            'inflated_xy_voxels': len(cells), 'resolution_m': res, 'inflation_radius_m': radius,
            'rule': 'occupied voxels: harness mark_boxes; inflation: offsets with norm < radius (grid_map.cpp)',
            '_cells': cells, '_occupied': [(x, y) for x in range(lo[0], hi[0] + 1) for y in range(lo[1], hi[1] + 1)],
        }
    for build in BUILDS:
        row = report_rows[(label, build)]
        build_paths = entry['builds'].get(build, {}).get('paths', [])
        accepted = {c['call']: c for c in row['calls'] if c.get('success')}
        calls = []
        for item in build_paths:
            call = accepted.get(item['call'])
            xyz = item['xyz']
            xy = [p[:2] for p in xyz]
            record = {'call': item['call'], 'attempt': item['attempt'], 'samples': len(xy), 'dt_s': item['dt'],
                      'endpoint_xy_m': call['endpoint_xy_m'] if call else None,
                      'plotted_end_to_target_m': rounded(math.dist(xy[-1], target[:2])), '_xy': xy}
            if cells is not None:
                probes = []
                for a, b in zip(xy, xy[1:]):
                    yaw = math.atan2(b[1] - a[1], b[0] - a[0])
                    for sign in (1.0, -1.0):
                        probes.append((a[0] + sign * offset * math.cos(yaw), a[1] + sign * offset * math.sin(yaw)))
                z = [p[2] for p in xyz]
                record.update({
                    'probe_rule': 'centre +/- %.2f m along the heading of the next plotted segment '
                                  '(GridMap::getInflateOccupancy); plotted samples every %.2f s, the harness '
                                  'checks every 0.01 s' % (offset, item['dt']),
                    'plotted_probe_samples': len(probes),
                    'plotted_probe_samples_in_inflated_voxels': sum(voxel_of(p, res) in cells for p in probes),
                    'min_probe_to_inflated_voxels_m': rounded(min(cells_distance(p, cells, res) for p in probes)),
                    'min_centre_to_box_xy_m': rounded(min(rect_distance(p, case['box']) for p in xy)),
                    'path_z_within_inflated_z': case['box']['z_range_m'][0] <= min(z) and max(z) <= case['box']['z_range_m'][1],
                    'harness_collision_samples': call['collision_samples'] if call else None,
                })
            calls.append(record)
        case['builds'][build] = {'completed': row['completed'], 'reason': row['reason'], 'gate_value': row['gate_value'],
                                 'steps': row['steps'], 'paths': calls}
    return case


def plot_panel5(cases, planner, limit, path, outputs):
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Circle, Rectangle
    from matplotlib.font_manager import FontProperties
    from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
    res = planner['resolution_m']
    xs, ranges = [], []
    for case in cases:
        pts = [case['start'][:2], case['target'][:2]]
        pts += [p for b in case['builds'].values() for c in b['paths'] for p in c['_xy']]
        if case['box']:
            pts += [((x + dx) * res, (y + dy) * res) for x, y in case['box']['_cells'] for dx in (0, 1) for dy in (0, 1)]
        xs += [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # Box rows list their notes above the inflated voxels.
        ranges.append((min(ys) - 0.09, max(ys) + (0.2 if case['box'] else 0.09)))
    x0, x1 = min(xs) - 0.08, max(xs) + 0.08
    main_w, zoom_w, left, gap, top, row_gap = 7.6, 2.0, 0.75, 0.55, 0.55, 0.62
    scale = main_w / (x1 - x0)
    heights = [max((r[1] - r[0]) * scale, zoom_w) for r in ranges]
    fig_h = top + sum(heights) + row_gap * len(cases) + 0.2
    fw = left + main_w + gap + zoom_w + 0.3
    fig = new_figure(fw, fig_h)
    y_cursor = fig_h - top
    styles = {0: '-', 1: '--', 2: ':'}
    for case, (y0, y1), height in zip(cases, ranges, heights):
        y_cursor -= height
        # Same metres-per-inch in every row: widen the y range to the row height.
        centre, half = (y0 + y1) / 2.0, height / scale / 2.0
        ax = fig.add_axes([left / fw, y_cursor / fig_h, main_w / fw, height / fig_h])
        zoom = fig.add_axes([(left + main_w + gap) / fw, (y_cursor + height - zoom_w) / fig_h, zoom_w / fw, zoom_w / fig_h])
        y_cursor -= row_gap
        ax.set_xlim(x0, x1)
        ax.set_ylim(centre - half, centre + half)
        ax.set_aspect('equal', adjustable='box')
        tx, ty = case['target'][:2]
        zoom.set_xlim(tx - 0.07, tx + 0.07)
        zoom.set_ylim(ty - 0.07, ty + 0.07)
        zoom.set_aspect('equal', adjustable='box')
        box = case['box']
        if box:
            ax.add_collection(PatchCollection([Rectangle((x * res, y * res), res, res) for x, y in box['_cells']],
                                              facecolor='0.87', edgecolor='none', zorder=0))
            ax.add_collection(PatchCollection([Rectangle((x * res, y * res), res, res) for x, y in box['_occupied']],
                                              facecolor='0.5', edgecolor='none', zorder=1))
            lo, hi = box['min'], box['max']
            ax.add_patch(Rectangle((lo[0], lo[1]), hi[0] - lo[0], hi[1] - lo[1], fill=False, edgecolor='black',
                                   linewidth=0.8, zorder=2))
            ax.text(0.995, 0.02, 'black outline: box; dark grey: occupied voxels (%.2f m);\nlight grey: inflated voxels '
                    '(offsets with norm < %.2f m)' % (res, box['inflation_radius_m']), transform=ax.transAxes,
                    ha='right', va='bottom', fontsize=8.5, color='0.25')
        for axis in (ax, zoom):
            axis.plot([tx], [ty], marker='*', markersize=13, color='black', linestyle='none', zorder=6)
        zoom.add_patch(Circle((tx, ty), limit, fill=False, linestyle='--', edgecolor='0.3'))
        zoom.text(tx, ty - limit - 0.004, '%.2f m' % limit, ha='center', va='top', fontsize=8, color='0.3')
        ax.plot([case['start'][0]], [case['start'][1]], marker='s', markersize=7, color='0.3', linestyle='none', zorder=5)
        ax.annotate('start', (case['start'][0], case['start'][1]), xytext=(0, 7), textcoords='offset points',
                    ha='center', fontsize=8.5, color='0.3')
        ax.annotate('target', (tx, ty), xytext=(0, 8), textcoords='offset points', ha='center', fontsize=8.5)
        notes = []
        for build in BUILDS:
            info = case['builds'][build]
            for call in info['paths']:
                cx = [p[0] for p in call['_xy']]
                cy = [p[1] for p in call['_xy']]
                for axis in (ax, zoom):
                    axis.plot(cx, cy, linestyle=styles.get(call['call'], '-'), linewidth=1.8, color=BUILD_COLOR[build], zorder=4)
                    axis.plot([cx[-1]], [cy[-1]], marker='o', markersize=5, color=BUILD_COLOR[build], zorder=5)
                if len(info['paths']) > 1:
                    ax.plot([cx[0]], [cy[0]], marker='|', markersize=12, markeredgewidth=2, color=BUILD_COLOR[build], zorder=5)
                notes.append(('%s call %d ends %.4f m from the target' % (
                    BUILD_LABEL[build], call['call'] + 1, call['endpoint_xy_m']), BUILD_COLOR[build]))
                if 'min_probe_to_inflated_voxels_m' in call:
                    notes.append(('    collision probes (centre +/-%.2f m along heading): closest %.3f m from an inflated '
                                  'voxel; harness collision samples: %s' % (
                                      planner['double_cylinder_offset_m'], call['min_probe_to_inflated_voxels_m'],
                                      call['harness_collision_samples']), BUILD_COLOR[build]))
            if not info['paths']:
                reason = info['reason'].replace('_', ' ')
                if info['gate_value'] is not None:
                    reason += ' (%.3f > 1.5 m/s$^2$)' % info['gate_value']
                notes.append(('%s: no trajectory, rejected: %s' % (BUILD_LABEL[build], reason), BUILD_COLOR[build]))
        for i, (text, color) in enumerate(notes):
            if box:
                y, va = 0.97 - i * 0.17 / height, 'top'
            else:
                y, va = 0.02 + (len(notes) - 1 - i) * 0.17 / height, 'bottom'
            ax.text(0.005, y, text, transform=ax.transAxes, fontsize=8.5, color=color, va=va)
        ax.add_artist(AnchoredSizeBar(ax.transData, 0.25, '0.25 m', 'upper right', pad=0.4, frameon=False,
                                      size_vertical=0.004, fontproperties=FontProperties(size=8.5)))
        zoom.add_artist(AnchoredSizeBar(zoom.transData, 0.02, '2 cm', 'lower right', pad=0.3, frameon=False,
                                        size_vertical=0.0008, fontproperties=FontProperties(size=8)))
        ax.tick_params(labelsize=8)
        ax.set_ylabel('y (m)')
        zoom.set_xticks([])
        zoom.set_yticks([])
        for spine in zoom.spines.values():
            spine.set_visible(True)
            spine.set_color('0.6')
        zoom.set_title('zoom at target', fontsize=9)
        ax.set_title(case['title'], loc='left', fontsize=10)
    ax.set_xlabel('x (m), world frame; equal scale in every row')
    fig.text(left / fw, 1 - 0.12 / fig_h, 'Top-down paths of the three fixture runs with recorded samples '
             '(solid: call 1, dashed: call 2, dotted: call 3)', fontsize=11, va='top')
    caption = ('Top-down paths for the failing resume start (empty map), the same start with the near box, and a '
               'follow-up sequence. Only paths that a build returned are drawn. The box row shows the occupied and '
               'inflated voxels; the zoom shows the 0.05 m endpoint limit.')
    save_figure(fig, path, outputs, '5', caption)


def follow_up_data(report, fixtures):
    offsets = fixtures['follow_up']['offsets_s']
    sequences = []
    for row in sorted((r for r in report['rows'] if r['kind'] == 'follow_up'), key=lambda r: (r['start_x'], r['build'])):
        steps = []
        for step in row['steps']:
            call = next((c for c in row['calls'] if c.get('call') == step['call'] and c.get('success')), None)
            steps.append({'call': step['call'], 'accepted': step['accepted'], 'attempts': step['attempts'],
                          'failure_reasons': step['failure_reasons'], 'max_acc': call['max_acc'] if call else None})
        sequences.append({'label': row['label'], 'build': row['build'], 'start_x': row['start_x'],
                          'completed': row['completed'], 'steps': steps})
    return {'offsets_s': offsets, 'sequences': sequences}


def plot_panel6(data, gate, completed, path, outputs):
    fig = new_figure(FIG_W, 4.6)
    calls = sorted({s['call'] for seq in data['sequences'] for s in seq['steps']})
    axes = fig.subplots(1, len(calls), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.995, top=0.78, bottom=0.2, wspace=0.08)
    offsets = [0.0] + list(data['offsets_s'])
    top = gate
    for ax, call in zip(axes, calls):
        ax.axhline(gate, linestyle='--', color='0.25', linewidth=1.1)
        for build in BUILDS:
            seqs = [s for s in data['sequences'] if s['build'] == build]
            color = BUILD_COLOR[build]
            accepted = [(s['start_x'], s['steps'][call]['max_acc']) for s in seqs if s['steps'][call]['accepted']]
            top = max([top] + [v for _, v in accepted])
            ax.plot([a for a, _ in accepted], [v for _, v in accepted], linestyle='none',
                    marker='o' if build == 'original' else 's', markersize=6, color=color,
                    markerfacecolor=color if build == 'original' else 'none', markeredgewidth=1.5,
                    label='%s: accepted' % BUILD_LABEL[build])
            for reason in sorted({r for s in seqs if not s['steps'][call]['accepted'] for r in s['steps'][call]['failure_reasons'][-1:]}):
                xs = [s['start_x'] for s in seqs if not s['steps'][call]['accepted']
                      and s['steps'][call]['failure_reasons'][-1:] == [reason]]
                mark_rejections(ax, xs, gate, color, reason,
                                label='%s: rejected (%s)' % (BUILD_LABEL[build], reason.replace('_', ' ')))
        title = 'call %d' % (call + 1)
        title += ' (first plan)' if call == 0 else ' (+%.1f s after call %d)' % (offsets[call] - offsets[call - 1], call)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('sequence start x (m)')
        ax.grid(axis='y', linewidth=0.4, alpha=0.5)
    axes[0].set_ylabel('sampled max acceleration (m/s$^2$)')
    axes[0].set_ylim(0.0, top + 0.35)
    axes[-1].text(1.0, gate + 0.03, 'gate %.1f m/s$^2$' % gate, transform=axes[-1].get_yaxis_transform(),
                  ha='right', va='bottom', fontsize=8.5, color='0.25')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=3, bbox_to_anchor=(0.54, 0.92), fontsize=8.5)
    fig.suptitle('Follow-up replans in one planner instance (empty map, polynomial init, seed 0): '
                 'completed original %d/%d, fixed %d/%d' % (
                     completed['original'], completed['total'], completed['candidate'], completed['total']),
                 x=0.01, ha='left', fontsize=11)
    fig.text(0.5, 0.01, 'No marker: the sequence stopped at an earlier call.', ha='center', fontsize=8.5, color='0.3')
    caption = ('Sampled maximum acceleration of each accepted call in the 15 follow-up sequences. Crosses on the gate '
               'line are gate rejections. A sequence that stops early has no marker for later calls.')
    save_figure(fig, path, outputs, '6', caption)


def box_limits(xs, ys, pad, width_in, height_in):
    return mwr.equal_limits(min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad, width_in, height_in)


def plot_panel8(episodes, old_runs, band, path, outputs):
    from matplotlib.patches import Circle, Rectangle
    from matplotlib.font_manager import FontProperties
    from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
    shown = [e for e in episodes if e.get('facts')]
    reference = shown[0]['facts'] if shown else old_runs[0]['facts']
    tol = reference['goal_xy_tolerance_m']
    goals = reference['goals']
    left, width, top_h, zoom_h = 0.8, 9.9, 2.3, 3.0
    fig_h = 0.55 + top_h + 0.85 + zoom_h + 1.55
    fw = left + width + 0.3
    fig = new_figure(fw, fig_h)
    full = fig.add_axes([left / fw, (fig_h - 0.55 - top_h) / fig_h, width / fw, top_h / fig_h])
    zoom = fig.add_axes([left / fw, 1.55 / fig_h, width / fw, zoom_h / fig_h])
    xs, ys = [], []
    for item in shown + old_runs:
        xs += item['facts']['_series']['x']
        ys += item['facts']['_series']['y']
    xs += [g[0] + s * tol for g in goals.values() for s in (-1, 1)]
    ys += [g[1] + s * tol for g in goals.values() for s in (-1, 1)]
    fx, fy = box_limits(xs, ys, 0.12, width, top_h)
    full.set_xlim(*fx)
    full.set_ylim(*fy)
    zx, zy = [], []
    for item in shown + old_runs:
        for key in ('cancel_trigger_xyz', 'still_pose_xyz'):
            if item['facts'].get(key):
                zx.append(item['facts'][key][0])
                zy.append(item['facts'][key][1])
    for seg in band['segments']:
        zx += [seg['shade_from_x'], seg['shade_to_x']]
    zoom_x, zoom_y = box_limits(zx, zy, 0.02, width, zoom_h)
    zoom.set_xlim(*zoom_x)
    zoom.set_ylim(*zoom_y)
    for axis in (full, zoom):
        axis.set_aspect('equal', adjustable='box')
        axis.set_ylabel('y (m)')
        axis.grid(linewidth=0.4, alpha=0.35)
    full.add_patch(Rectangle((zoom_x[0], zoom_y[0]), zoom_x[1] - zoom_x[0], zoom_y[1] - zoom_y[0], fill=False,
                             edgecolor='0.4', linewidth=0.9))
    full.annotate('zoom below', (zoom_x[0], zoom_y[1]), xytext=(0, 3), textcoords='offset points', fontsize=8, color='0.35')
    for seg in band['segments']:
        zoom.axvspan(seg['shade_from_x'], seg['shade_to_x'], color=BUILD_COLOR['original'], alpha=0.10, linewidth=0)
        zoom.text((seg['shade_from_x'] + seg['shade_to_x']) / 2.0, 0.97,
                  'native sweep: original build rejects a resume plan from here', transform=zoom.get_xaxis_transform(),
                  ha='center', va='top', fontsize=8.5, color='#8a3a00')
    for goal_id, g in sorted(goals.items()):
        full.add_patch(Circle((g[0], g[1]), tol, fill=False, edgecolor='black', linewidth=1.1))
        full.plot([g[0]], [g[1]], marker='+', markersize=10, color='black')
        full.annotate('goal %s (r = %.2f m)' % (goal_id.replace('goal-', '').upper(), tol), (g[0], g[1] + tol),
                      xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8.5)
    for item in old_runs:
        s = item['facts']['_series']
        for axis in (full, zoom):
            axis.plot(s['x'], s['y'], color='0.6', linewidth=0.9, linestyle='--', zorder=1)
    stops = sorted((o for o in old_runs if o['facts'].get('still_pose_xyz')), key=lambda o: o['facts']['still_pose_xyz'][0])
    names = ['Sep 16 ' + o['label'] for o in stops]
    levels = label_levels([o['facts']['still_pose_xyz'][0] for o in stops], names, (zoom_x[1] - zoom_x[0]) / width,
                          marker_in=0.05)
    for item, name, level in zip(stops, names, levels):
        stop = item['facts']['still_pose_xyz']
        marker, _, _ = OUTCOME_STYLE[item['passed']]
        zoom.plot([stop[0]], [stop[1]], marker=marker, markersize=9, linestyle='none', color='0.45',
                  markerfacecolor='white' if item['passed'] else '0.45', zorder=3)
        zoom.annotate(name, (stop[0], stop[1]), xytext=(stop[0], 0.86 - 0.07 * level),
                      textcoords=zoom.get_xaxis_transform(), ha='left', va='center', fontsize=8, color='0.3',
                      arrowprops={'arrowstyle': '-', 'color': '0.65', 'linewidth': 0.6, 'shrinkA': 0, 'shrinkB': 4})
    for index, ep in enumerate(shown):
        facts = ep['facts']
        color = EPISODE_COLORS[index % len(EPISODE_COLORS)]
        s = facts['_series']
        for axis in (full, zoom):
            axis.plot(s['x'], s['y'], color=color, linewidth=1.5, zorder=4,
                      label='e%02d (%s, trigger %s m)' % (ep['episode'], OUTCOME_STYLE[ep['passed']][2], fmt(ep['trigger_m']))
                      if axis is full else None)
        if facts.get('start_xyz'):
            full.plot([facts['start_xyz'][0]], [facts['start_xyz'][1]], marker='s', markersize=6, color=color, zorder=5)
        for axis in (full, zoom):
            if facts.get('cancel_trigger_xyz'):
                axis.plot([facts['cancel_trigger_xyz'][0]], [facts['cancel_trigger_xyz'][1]], marker='X', markersize=9,
                          color=color, markeredgecolor='white', markeredgewidth=0.6, zorder=6)
            if facts.get('still_pose_xyz'):
                axis.plot([facts['still_pose_xyz'][0]], [facts['still_pose_xyz'][1]], marker='o', markersize=9,
                          markerfacecolor='none', markeredgecolor=color, markeredgewidth=1.8, zorder=6)
        for arrival in facts['arrivals'].values():
            if arrival.get('base_xyz'):
                full.plot([arrival['base_xyz'][0]], [arrival['base_xyz'][1]], marker='D', markersize=5,
                          color=color, zorder=6)
    for axis, bar in ((full, 0.5), (zoom, 0.05)):
        axis.add_artist(AnchoredSizeBar(axis.transData, bar, '%g m' % bar, 'lower right', pad=0.4, frameon=False,
                                        size_vertical=(axis.get_ylim()[1] - axis.get_ylim()[0]) / 150,
                                        fontproperties=FontProperties(size=8.5)))
    zoom.set_xlabel('x (m), world frame, equal scale')
    handles, labels = full.get_legend_handles_labels()
    extra = [
        (full.plot([], [], color='0.6', linestyle='--')[0], 'Sep 16 runs, original build (grey)'),
        (full.plot([], [], marker='s', linestyle='none', color='0.3')[0], 'start'),
        (full.plot([], [], marker='X', linestyle='none', color='0.3')[0], 'cancel sent'),
        (full.plot([], [], marker='o', linestyle='none', markerfacecolor='none', markeredgecolor='0.3')[0],
         'still-confirmed stop'),
        (full.plot([], [], marker='D', linestyle='none', color='0.3')[0], 'pose at arrival'),
        (full.plot([], [], marker='o', linestyle='none', color='0.45', markerfacecolor='white')[0],
         'Sep 16 stop, passed'),
        (full.plot([], [], marker='X', linestyle='none', color='0.45')[0], 'Sep 16 stop, failed'),
    ]
    fig.legend(handles + [h for h, _ in extra], labels + [t for _, t in extra], loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, 0.0), fontsize=8.5)
    full.set_title('Isaac robot paths (metrics.jsonl base_xyz): %d Sep 17 episode(s) with the fixed build, '
                   '%d Sep 16 runs in grey' % (len(shown), len(old_runs)), loc='left')
    caption = ('Top-down robot paths of the Sep 17 episodes with start, cancel and still-confirmed stop points and goal '
               'circles. The zoom shows the stop region, the native failure band and the Sep 16 stops.')
    save_figure(fig, path, outputs, '8', caption)


def plot_panel9(ep, path, outputs):
    facts = ep['facts']
    s = facts['_series']
    fig = new_figure(FIG_W, 4.9)
    grid = fig.add_gridspec(2, 1, height_ratios=[2.3, 1.0], hspace=0.12, top=0.74, bottom=0.12, left=0.08, right=0.99)
    ax = fig.add_subplot(grid[0])
    fx = fig.add_subplot(grid[1], sharex=ax)
    ax.plot(s['sim'], s['speed'], color='#0072B2', linewidth=1.3, label='measured horizontal speed')
    ax.plot(s['sim'], s['command'], color='#E69F00', linewidth=1.3, label='admitted command, horizontal norm')
    fx.plot(s['sim'], s['force'], color='black', linewidth=1.1, label='max non-foot contact force')
    fx.axhline(facts['contact_threshold_n'], linestyle='--', color='#CC79A7', linewidth=1.0,
               label='contact guard threshold %.0f N' % facts['contact_threshold_n'])
    t0, t1 = 0.0, s['sim'][-1]
    timeline = [e for e in facts['events'] if e['placement'] == 'timeline' and e['sim_time_s'] is not None]
    dwell = [e for e in timeline if e['key'] == 'still_dwell_start']
    still = [e for e in timeline if e['key'] == 'still_confirmed']
    if dwell and still:
        for axis in (ax, fx):
            axis.axvspan(dwell[0]['sim_time_s'], still[0]['sim_time_s'], color='#009E73', alpha=0.15, linewidth=0)
        ax.text((dwell[0]['sim_time_s'] + still[0]['sim_time_s']) / 2.0, 0.5, 'driver\nstill\ndwell',
                transform=ax.get_xaxis_transform(), ha='center', fontsize=8, color='#00694c')
    for window in facts['stop_windows']:
        if window['start_s'] is None:
            continue
        color = '#009E73' if window['passed'] else '#CC79A7'
        ax.plot([window['start_s'], window['end_s']], [0.03, 0.03], transform=ax.get_xaxis_transform(), color=color,
                linewidth=5, solid_capstyle='butt', zorder=6)
        if not window['passed']:
            ax.text((window['start_s'] + window['end_s']) / 2.0, 0.07, '%.2f s' % window['span_s'],
                    transform=ax.get_xaxis_transform(), ha='center', va='bottom', fontsize=8.5, color='#8e3b74',
                    bbox={'facecolor': 'white', 'alpha': 0.85, 'edgecolor': 'none', 'pad': 1})
    ax.plot([], [], color='#009E73', linewidth=5, label='review raw still window (>= required)')
    if any(not w['passed'] for w in facts['stop_windows']):
        ax.plot([], [], color='#CC79A7', linewidth=5, label='review raw still window (too short)')
    marked = [e for e in timeline if e['key'] != 'still_dwell_start']
    axis_pts = 0.91 * FIG_W * 72.0
    ends = {}
    for event in marked:
        bad = event['key'] == 'driver_error' or event['key'].startswith('terminal_')
        color = '#b00000' if bad else '0.25'
        for axis in (ax, fx):
            axis.axvline(event['sim_time_s'], color=color, linewidth=0.8, linestyle='--', alpha=0.8)
        x_pt = (event['sim_time_s'] - t0) / max(t1 - t0, 1e-9) * axis_pts
        row = 0
        while ends.get(row, -1e9) > x_pt:
            row += 1
        ends[row] = x_pt + 0.62 * 8.5 * (len(event['label']) + 1) + 4
        ax.text(event['sim_time_s'], 1.03 + 0.1 * row, ' ' + event['label'], transform=ax.get_xaxis_transform(),
                fontsize=8.5, color=color, ha='left', va='bottom')
    ax.set_xlim(t0, t1)
    ax.set_ylim(0.0, max(0.2, max(s['speed'] + s['command'])) * 1.35)
    fx.set_ylim(0.0, max(facts['contact_threshold_n'], max(s['force'])) * 1.35)
    ax.set_ylabel('speed (m/s)')
    fx.set_ylabel('force (N)')
    fx.set_xlabel('simulation time (s)')
    ax.tick_params(labelbottom=False)
    ax.legend(loc='upper right', ncol=2, fontsize=8.5)
    fx.legend(loc='upper right', ncol=2, fontsize=8.5)
    ax.set_ylim(0.0, max(0.2, max(s['speed'] + s['command'])) * 1.55)
    fx.text(0.005, 0.9, 'max %.1f N' % max(s['force']), transform=fx.transAxes, fontsize=8.5, va='top', color='0.3')
    for axis in (ax, fx):
        axis.grid(linewidth=0.4, alpha=0.35)
    notes = []
    if facts['missing_events']:
        notes.append('not recorded: ' + ', '.join(facts['missing_events']))
    outside = [e for e in facts['events'] if e['placement'] != 'timeline']
    if outside:
        notes.append('after the recorded state: ' + ', '.join(e['label'] for e in outside))
    if notes:
        fig.text(0.99, 0.005, ' | '.join(notes), ha='right', va='bottom', fontsize=8.5, color='#b00000')
    failed = []
    for window in facts['stop_windows']:
        if not window['passed']:
            text = '%s %s: raw still window %.2f s < %.2f s' % (
                window['request_id'][len(facts['run_id']) + 1:], window['status'], window['span_s'], window['required_s'])
            if window.get('ended_by'):
                text += ', ended at %.2f s by %s' % (window['ended_by']['sim_time_s'],
                                                     '; '.join(window['ended_by']['limits_exceeded']))
            failed.append(text)
    if facts['failed_checks']:
        fig.text(0.01, 0.935, 'failed checks: ' + ', '.join(c[len(facts['run_id']) + 1:] if c.startswith(facts['run_id'])
                                                            else c for c in facts['failed_checks'])
                 + ('\n' + '\n'.join(failed) if failed else ''), ha='left', va='top', fontsize=9, color='#8e3b74')
    verdict = '%s, %d/%d review checks' % (OUTCOME_STYLE[ep['passed']][2], facts['checks_passed'], facts['checks_total'])
    fig.suptitle('Episode %d (%s): cancel trigger %s m, %s' % (ep['episode'], facts['run_id'], fmt(ep['trigger_m']), verdict),
                 x=0.01, ha='left', fontsize=11, y=0.985)
    caption = ('Speed, admitted command and non-foot contact force against simulation time for episode %d, with the '
               'driver and backend events.' % ep['episode'])
    save_figure(fig, path, outputs, '9', caption)


# ---------------------------------------------------------------------------------------------
# Report assembly.

def check_output(output):
    output = Path(output).resolve()
    for root in READ_ONLY_ROOTS:
        root = root.resolve()
        if output == root or root in output.parents:
            raise ReportError('refusing to write into a read-only evidence tree: %s' % output)
    return output


def build_report(args):
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams.update(STYLE)
    output = check_output(args.output)
    inputs = InputLog()
    for name, path in CODE.items():
        inputs.add(path, 'code: ' + name)
    inputs.add(Path(__file__).resolve(), 'code: make_report')
    thresholds, thresholds_sha = an.load_thresholds()
    inputs.add(an.THRESHOLDS, 'frozen thresholds')
    inputs.add(an.PLAN, 'thresholds SHA-256 record')
    gate = thresholds['acceleration_gate_mps2']
    limit = thresholds['endpoint_xy_limit_m']
    suite, paths, fixtures = verified_native_run(args.suite_run, inputs, 'native suite')
    if suite['validity'] != 'VALID':
        raise ReportError('native suite %s is %s' % (suite['run_id'], suite['validity']))

    episodes_raw, ends = parse_ledger(inputs.add(args.ledger, 'Isaac series ledger'))
    runs_root = Path(args.runs_root)
    episodes = [episode_facts(e, inputs, runs_root) for e in episodes_raw]
    old_runs = []
    for label, run_dir in OLD_RUNS:
        facts = isaac_run_facts(run_dir, inputs, 'Sep 16 run ' + label)
        old_runs.append({'label': label, 'facts': facts, 'passed': facts['review_passed']})

    replay = None
    if args.stop_replay_run:
        rep, _, rep_fixtures = verified_native_run(args.stop_replay_run, inputs, 'stop-pose replay')
        run_ids = [e['run_id'] for e in episodes if e.get('run_id')] + [o['facts']['run_id'] for o in old_runs]
        replay = {'run_id': rep['run_id'], 'validity': rep['validity'], 'passed': rep['passed'],
                  'verdicts': replay_verdicts(rep, rep_fixtures, run_ids)}

    points = resume_outcomes(suite, fixtures)
    band = failure_band([p for p in points if p['group'] == 'stop_position_sweep'])
    planned_map = dict(ris.PLAN)
    for ep in episodes:
        planned_map.setdefault(ep['episode'], ep.get('trigger_m'))
    planned = [{'episode': k, 'trigger_m': planned_map[k]} for k in sorted(planned_map)]
    series = series_summary(episodes, ends, planned)
    criteria = parse_criteria(inputs.add(args.prd, 'PRD acceptance criteria').read_text())
    ac1 = ac1_facts(inputs)
    result_md = RESULT_MD.is_file()
    if result_md:
        inputs.add(RESULT_MD, 'RESULT.md (existence only)')
    verdicts = verdict_table(criteria, suite, ac1, series, result_md, thresholds['sampled_max_acc_limit_mps2'])

    figures_dir, videos_dir = output / 'figures', output / 'videos'
    before = {p.resolve() for d in (figures_dir, videos_dir) if d.is_dir() for p in d.iterdir() if p.suffix in ('.png', '.mp4')}
    outputs = []
    used_names = set()
    for ep in episodes:
        source = ep.get('walk_video_source')
        ep['walk_video'] = None
        if source is None:
            continue
        name = 'e%02d.mp4' % ep['episode']
        if name in used_names:
            name = 'e%02d_line%d.mp4' % (ep['episode'], ep['ledger_line'])
        used_names.add(name)
        target = videos_dir / name
        method = link_video(source, target)
        ep['walk_video'] = target.relative_to(output).as_posix()
        outputs.append({'kind': 'video', 'episode': ep['episode'], 'path': rel(target), 'sha256': sha256_file(target),
                        'bytes': target.stat().st_size, 'method': method, 'source': rel(source)})

    ticks = [{'lane': 'old', 'x': stop_x(o['facts']), 'passed': o['passed'], 'label': o['label']} for o in old_runs]
    ticks += [{'lane': 'new', 'x': stop_x(e['facts']), 'passed': e['passed'], 'label': 'e%02d' % e['episode']}
              for e in episodes if e.get('facts')]
    replay_points = []
    if replay and replay['validity'] == 'VALID':
        replay_points = [{'run_id': k, 'x': v['x'], 'builds': v['builds']} for k, v in sorted(replay['verdicts'].items())]
    plot_panel2(points, band, ticks, replay_points, gate, figures_dir / 'panel2_where_the_bug_bites.png', outputs)

    grid, grid_counts = grid_data(suite, fixtures, thresholds['max_collision_samples'])
    plot_panel3(grid, grid_counts, fixtures, figures_dir / 'panel3_pass_fail_grid.png', outputs)

    single, follow = endpoint_data(suite)
    plot_panel4(single, follow, limit, figures_dir / 'panel4_endpoint_distance.png', outputs)

    rows_by_key = {(r['label'], r['build']): r for r in suite['rows']}
    cases = []
    for label, entry in sorted(paths['runs'].items(), key=lambda kv: (bool(kv[1]['follow_up_offsets_s']),
                                                                      bool(kv[1]['occupied_boxes']))):
        log_boxes = []
        if entry['occupied_boxes']:
            log = inputs.add(args.suite_run / 'returned_artifacts/candidate' / (label + '.log'), 'panel 5 MAP_BOX line')
            log_boxes = an.parse_log(log.read_text(errors='replace'))['boxes']
        case = path_case(label, entry, rows_by_key, paths['boxes'], fixtures['planner_params'], log_boxes)
        row = rows_by_key[(label, 'candidate')]
        where = 'start x = %.3f' % entry['start'][0]
        if entry['follow_up_offsets_s']:
            case['title'] = 'Follow-up sequence from %s, empty map (calls at 0, +%s s)' % (
                where, ', +'.join('%g' % o for o in entry['follow_up_offsets_s']))
        elif entry['occupied_boxes']:
            case['title'] = '%s (%s), near box' % (row['start_id'], where)
        else:
            case['title'] = '%s (%s), empty map' % (row['start_id'], where)
        cases.append(case)
    plot_panel5(cases, fixtures['planner_params'], limit, figures_dir / 'panel5_top_down_paths.png', outputs)

    follow_data = follow_up_data(suite, fixtures)
    completed = dict(suite['acceptance']['AC6']['completed'], total=suite['acceptance']['AC6']['sequences'])
    plot_panel6(follow_data, gate, completed, figures_dir / 'panel6_follow_up_replans.png', outputs)

    plot_panel8(episodes, old_runs, band, figures_dir / 'panel8_isaac_top_down.png', outputs)
    for ep in episodes:
        if ep.get('facts'):
            plot_panel9(ep, figures_dir / ('panel9_timeline_e%02d.png' % ep['episode']), outputs)

    written = {Path(REPO / o['path']).resolve() for o in outputs}
    removed = []
    for stale in sorted(before - written):
        stale.unlink()
        removed.append(rel(stale))

    table = episode_table(episodes, replay, band)

    def public(facts):
        return {k: v for k, v in facts.items() if not k.startswith('_') and k != 'checks'} if facts else None

    old_summary = []
    for item in old_runs:
        facts = item['facts']
        fixture = next((s for s in fixtures['starts'] if (s.get('provenance') or {}).get('source_request_id')
                        == facts['run_id'] + '-goal-a-attempt-2'), None)
        old_summary.append(dict(public(facts), label=item['label'],
                                native_fixture=None if fixture is None else {
                                    'start_id': fixture['id'], 'start_x': fixture['start'][0],
                                    'equals_resume_plan_start_x': close(fixture['start'][0], facts['resume_plan_start_xyz'][0])}))
    data = {
        'schema': 'scan_fix_report_data_v1',
        'generated_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'generator': {'script': rel(Path(__file__).resolve()), 'sha256': sha256_file(Path(__file__).resolve()),
                      'python': sys.version.split()[0], 'matplotlib': matplotlib.__version__},
        'claim_boundary': {
            'status': 'pending: the lead states the AC8 boundary in RESULT.md',
            'native_suite': suite['claim'],
            'isaac_episodes': ('Known-map, simulator-truth continuous PCT/SCAN/V12 two-goal episodes on one flat route '
                               'with no placed obstacle; %d counted episode(s) so far; not a physical-robot, '
                               'language-navigation or SLAM result.' % series['counted_episodes']),
        },
        'native_suite': {
            'run_id': suite['run_id'], 'validity': suite['validity'], 'passed': suite['passed'],
            'thresholds_sha256': thresholds_sha, 'fixtures_sha256': suite['fixtures_sha256'],
            'verified': 'analyze_suite.analyze() result equals the stored comparison.json and paths.json',
            'integrity_passed': suite['integrity']['passed'], 'anomalies': len(suite['integrity']['anomalies']),
        },
        'stop_replay': None if replay is None else {k: v for k, v in replay.items()},
        'isaac_series': dict(series, ledger=rel(args.ledger)),
        'integrity_problems': [{'episode': e['episode'], 'run_id': e.get('run_id'), 'problems': e['problems']}
                               for e in episodes if e['problems']],
        'panels': {
            '1_verdicts': verdicts,
            '2_where_the_bug_bites': {
                'scope': 'single calls, empty map, polynomial init seed 0 (3 repeats); resume starts only '
                         '(provenance request attempt >= 2)',
                'y': 'max_acc of the accepted first call (harness: 1001 samples of the returned spline)',
                'gate_mps2': gate, 'points': points, 'failure_band': band,
                'isaac_ticks': ticks, 'replay_points': replay_points,
                'repeats_identical': all(b['repeats_identical'] for p in points for b in p['builds'].values()),
            },
            '3_pass_fail_grid': {
                'starts': [s['id'] for s in fixtures['starts']], 'inits': [i['id'] for i in fixtures['inits']],
                'maps': [m['id'] for m in fixtures['maps']], 'states': list(STATE_COLOR),
                'collision_rule': 'accepted first call with collision_samples > %d' % thresholds['max_collision_samples'],
                'counts': grid_counts,
            },
            '4_endpoint_distance': {
                'limit_m': limit,
                'single_call': {b: stats(v) for b, v in single.items()},
                'single_call_over_limit': {b: sum(1 for x in v if x > limit) for b, v in single.items()},
                'follow_up_report_only': {b: {'call %d' % (c + 1): stats(v) for c, v in sorted(calls.items())}
                                          for b, calls in follow.items()},
            },
            '5_top_down_paths': [dict({k: v for k, v in case.items() if k not in ('builds', 'box')},
                                      box=None if case['box'] is None else {
                                          k: v for k, v in case['box'].items() if not k.startswith('_')}, builds={
                b: dict({k: v for k, v in info.items() if k != 'paths'},
                        paths=[{k: v for k, v in c.items() if not k.startswith('_')} for c in info['paths']])
                for b, info in case['builds'].items()}) for case in cases],
            '6_follow_up_replans': dict(follow_data, completed=completed),
            '7_episode_table': table,
            '8_isaac_top_down': {
                'episodes': [{'episode': e['episode'], 'run_id': e.get('run_id'), 'start_xyz': (e['facts'] or {}).get('start_xyz'),
                              'cancel_trigger_xyz': (e['facts'] or {}).get('cancel_trigger_xyz'),
                              'still_pose_xyz': (e['facts'] or {}).get('still_pose_xyz'),
                              'arrivals': (e['facts'] or {}).get('arrivals')} for e in episodes],
                'goals': (episodes[0]['facts'] or {}).get('goals') if episodes and episodes[0].get('facts') else None,
                'goal_xy_tolerance_m': (episodes[0]['facts'] or {}).get('goal_xy_tolerance_m') if episodes and episodes[0].get('facts') else None,
                'sources': {'path': 'metrics.jsonl base_xyz',
                            'start': 'pilot_journal initial snapshot measured base_xyz',
                            'cancel': 'pilot_journal post_cancel trigger_snapshot measured base_xyz',
                            'stop': 'pilot_journal post_stop_proof snapshot measured base_xyz',
                            'goals': 'inputs/pilot.json'},
            },
            '9_timelines': [{'episode': e['episode'], 'run_id': e['facts']['run_id'], 'events': e['facts']['events'],
                             'missing_events': e['facts']['missing_events'],
                             'command_series': e['facts']['command_series']}
                            for e in episodes if e.get('facts')],
        },
        'sep16_runs': old_summary,
        'episodes': [dict({k: v for k, v in e.items() if k not in ('facts', 'ledger', 'walk_video_source')},
                          facts=public(e.get('facts'))) for e in episodes],
        'inputs': inputs.records(),
        'outputs': outputs,
        'removed_stale_outputs': removed,
        'report_data_sha256': 'not self-recorded; printed on stdout by make_report.py',
    }
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'report_data.json'
    target.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return data, target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--suite-run', type=Path, default=SUITE_RUN)
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    parser.add_argument('--runs-root', type=Path, default=ris.RUNS, help='directory holding the ledger run ids')
    parser.add_argument('--stop-replay-run', type=Path, default=None,
                        help='native replay run of the Isaac stop poses (implement.md C5); absent: verdicts pending')
    parser.add_argument('--prd', type=Path, default=PRD)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        data, target = build_report(args)
    except ReportError as error:
        print('make_report: refused: ' + str(error), file=sys.stderr)
        return 2
    series = data['isaac_series']
    print(json.dumps({
        'report_data': rel(target), 'report_data_sha256': sha256_file(target),
        'figures': len([o for o in data['outputs'] if o['kind'] == 'figure']),
        'videos': len([o for o in data['outputs'] if o['kind'] == 'video']),
        'verdicts': {v['id']: v['status'] for v in data['panels']['1_verdicts']},
        'episodes_counted': series['counted_episodes'], 'episodes_passed': series['passed_episodes'],
        'success_lower_bound': series['success_lower_bound'], 'series_status': series['status'],
        'integrity_problems': data['integrity_problems'],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
