#!/usr/bin/env python3
"""Evaluate PRD AC0 and AC2-AC6 from a returned native suite run.

AC0, the validity control, is evaluated first: if the original build does not reproduce the recorded
diagnosis pattern, the run is INVALID and no AC2-AC6 verdict is used. AC3 and AC4 follow the
2026-09-17 amendments (PRD decisions D8 and D10, thresholds.json "amendments"); follow-up endpoints are
reported without a verdict. Reads only the run package
(fixtures, manager identity, request) and returned files (logs, cases_result.json, artifact hashes).
Refuses to run unless thresholds.json matches the SHA-256 recorded in PLAN.md, the returned artifact
hashes match, and the run package matches its package_manifest.json. Integrity also requires the
thresholds hash recorded in request.json at preparation. Writes comparison.json, comparison.md and
paths.json into the run directory.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
RUNS = HERE / 'runs'
THRESHOLDS = HERE / 'thresholds.json'
PLAN = HERE / 'PLAN.md'
BUILDS = ('original', 'candidate')
ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
FIELD = re.compile(r'([A-Za-z_][A-Za-z0-9_.]*)=(\S*)')
PLAN_SHA = re.compile(r'`thresholds\.json` SHA-256: `([0-9a-f]{64})`')
GATE_WARN = re.compile(r'Dynamic feasibility failed: acceleration at t=(\S+) is (\S+) > (\S+)')
VEL_WARN = 'Dynamic feasibility failed: velocity'
METRICS = ('duration', 'max_acc', 'max_vel', 'endpoint_xy_m', 'endpoint_z_m', 'endpoint_xyz_m',
           'collision_samples', 'inflated_occupied_samples', 'out_of_map_samples', 'collision_checks')
SLIM_CALL = ('call', 'attempt', 'kind', 'poly_init', 'random_poly', 'success', 'reason', 'gate_value',
             'requested_offset_s', 'measured_offset_s')
SLIM_END = ('duration', 'max_acc', 'max_acc_t', 'endpoint_xy_m', 'endpoint_z_m', 'collision_samples',
            'inflated_occupied_samples', 'out_of_map_samples', 'collision_checks', 'start_offset_m')
MARKERS = ('SUITE_CALL_BEGIN', 'SUITE_CALL_END', 'SUITE_PATH', 'SUITE_IDENTITY', 'SUITE_SEQUENCE_END',
           'SUITE_FOLLOW_UP_SKIPPED', 'SUITE_INPUT', 'MAP_CONDITION', 'MAP_BOX', 'PARAMETERS',
           'CLOCK_CONDITION', 'REBOUND_REPLAN_RESULT', 'REBOUND_REPLAN_REPRO_ERROR')
CLAIM = ('Native planner-only A/B at the SCANPlannerManager boundary in the pinned Foxy image with '
         'recorded-pose fixtures and synthetic boxes; not an Isaac, controller, physical-robot or '
         'language-navigation result.')
# Source facts checked against p2b_execution/builds/scan_03/src on 2026-09-17.
BOUNDARY_NOTES = (
    'Follow-up offsets 0.3 s and 0.6 s are a stress schedule, not the live trigger. In EXEC_TRAJ the live FSM '
    'replans once the robot is 1.0 m from the current trajectory start (scan_replan_fsm.cpp:893, '
    'fsm.thresh_replan 1.0 in planner.yaml) or when checkCollisionCallback finds a collision '
    '(scan_replan_fsm.cpp:1083); new targets and routes also trigger a replan.',
    "SCAN's own collision checks cover only the first two thirds of a trajectory (bspline_optimizer.cpp:1017-1018 "
    'after rebound optimization, 1115-1116 after refinement), and reboundReplan has no final collision check '
    '(planner_manager.cpp:298 checks dynamic feasibility only). AC4 therefore samples every accepted trajectory '
    'independently over its full duration, every 0.01 s from t = 0.',
    "SCAN's acceleration gate (checkDynamicFeasibility) samples every max(0.01, min(0.05, duration/50)) s, i.e. "
    '0.05 s for durations of '
    '2.5 s or more, while t < duration + 1e-6 (planner_manager.cpp:460-464), so its last sample usually falls '
    "before the trajectory end. The harness maximum (1001 samples including t = duration) can therefore exceed "
    '1.5 m/s^2 for accepted original-build trajectories.',
)


class AnalysisRefused(RuntimeError):
    pass


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return text


def fields(text):
    out = {}
    for key, value in FIELD.findall(text):
        if value in ('true', 'false'):
            out[key] = value == 'true'
        elif re.fullmatch(r'-?\d+', value):
            out[key] = int(value)
        elif ',' in value and key not in ('points', 'follow_up_offsets', 'boxes_file', 'occupied_boxes', 'manager_cpp'):
            parts = value.split(',')
            out[key] = [number(p) for p in parts] if all(isinstance(number(p), float) for p in parts) else value
        else:
            out[key] = number(value)
    return out


def recorded_thresholds_sha256(plan_path=PLAN):
    matches = PLAN_SHA.findall(Path(plan_path).read_text())
    if len(matches) != 1:
        raise AnalysisRefused('PLAN.md must record exactly one thresholds.json SHA-256')
    return matches[0]


def load_thresholds(thresholds_path=THRESHOLDS, plan_path=PLAN):
    actual = sha256_file(thresholds_path)
    recorded = recorded_thresholds_sha256(plan_path)
    if actual != recorded:
        raise AnalysisRefused('thresholds.json sha256 %s differs from PLAN.md record %s' % (actual, recorded))
    return json.loads(Path(thresholds_path).read_text()), actual


# ---------------------------------------------------------------------------------------------
# Log parsing.

def classify(lines):
    text = '\n'.join(lines)
    gate = GATE_WARN.search(text)
    if gate:
        return 'acceleration_gate', {'gate_t': number(gate.group(1)), 'gate_value': number(gate.group(2)),
                                     'gate_limit': number(gate.group(3))}
    if VEL_WARN in text:
        return 'velocity_gate', {}
    if 'Close to goal' in text:
        return 'close_to_goal', {}
    if 'pseudo_arc_length is empty' in text:
        return 'previous_trajectory_empty', {}
    if 'first_optimize_step_success=0' in text:
        return 'rebound_optimization_failed', {}
    if 'This refined trajectory is unsafe' in text:
        return 'refinement_failed', {}
    return 'unclassified', {}


def parse_log(text):
    parsed = {'calls': [], 'paths': [], 'boxes': [], 'identity': None, 'parameters': None, 'map': None,
              'clock': None, 'sequence': None, 'skipped': [], 'errors': [], 'legacy_result': None}
    current = None
    for raw in ANSI.sub('', text).splitlines():
        marker = None
        for name in MARKERS:
            index = raw.find(name + ' ')
            if index < 0 and raw.endswith(name):
                index = len(raw) - len(name)
            if index >= 0:
                marker, body = name, raw[index + len(name):]
                break
        if marker == 'SUITE_CALL_BEGIN':
            if current is not None:
                parsed['calls'].append(unterminated(current))
            current = {'begin': fields(body), 'lines': []}
            continue
        if marker == 'SUITE_CALL_END' and current is not None:
            end = fields(body)
            reason, extra = ('accepted', {}) if end.get('success') else classify(current['lines'])
            call = dict(current['begin'])
            call.update({'end': end, 'success': bool(end.get('success')), 'reason': reason})
            call.update(extra)
            parsed['calls'].append(call)
            current = None
            continue
        if current is not None:
            current['lines'].append(raw)
        if marker == 'SUITE_PATH':
            record = fields(body.split(' points=')[0])
            points = body.split(' points=', 1)[1] if ' points=' in body else ''
            record['xyz'] = [[float(v) for v in p.split(',')] for p in points.split(';') if p]
            parsed['paths'].append(record)
        elif marker == 'SUITE_IDENTITY':
            parsed['identity'] = fields(body)
        elif marker == 'PARAMETERS':
            parsed['parameters'] = fields(body)
        elif marker == 'MAP_CONDITION':
            parsed['map'] = fields(body)
        elif marker == 'MAP_BOX':
            parsed['boxes'].append(fields(body))
        elif marker == 'CLOCK_CONDITION':
            parsed['clock'] = fields(body)
        elif marker == 'SUITE_SEQUENCE_END':
            parsed['sequence'] = fields(body)
        elif marker == 'SUITE_FOLLOW_UP_SKIPPED':
            parsed['skipped'].append(fields(body))
        elif marker == 'REBOUND_REPLAN_RESULT':
            parsed['legacy_result'] = fields(body).get('success')
        elif marker == 'REBOUND_REPLAN_REPRO_ERROR':
            parsed['errors'].append(body.strip())
    if current is not None:
        parsed['calls'].append(unterminated(current))
    return parsed


def unterminated(current):
    call = dict(current['begin'])
    call.update({'end': None, 'success': False, 'reason': 'no_end_marker'})
    return call


def slim(call):
    out = {k: call[k] for k in SLIM_CALL if k in call}
    if call.get('end') and call['success']:
        out.update({k: call['end'].get(k) for k in SLIM_END})
    return out


# ---------------------------------------------------------------------------------------------
# Run-level records.

PACKAGE_INPUTS = ('inputs/fixtures/suite_cases.json', 'managers/manager_identity.json', 'request.json')


def verify_package(run_dir):
    """The local run package is immutable: every manifest entry, and every package file read here, must match.

    The remote gate checked the executed copy against this same manifest, so a match binds the fixtures,
    manager identity and request used by this analysis to the files that actually ran.
    """
    manifest_path = run_dir / 'package_manifest.json'
    if not manifest_path.is_file():
        raise AnalysisRefused('run package has no package_manifest.json: %s' % run_dir)
    manifest = json.loads(manifest_path.read_text())
    unlisted = [p for p in PACKAGE_INPUTS if p not in manifest]
    changed = sorted(p for p, h in manifest.items()
                     if not (run_dir / p).is_file() or sha256_file(run_dir / p) != h)
    if unlisted or changed:
        raise AnalysisRefused('run package differs from its manifest (unlisted=%s changed=%s)' % (unlisted, changed[:10]))
    return len(manifest)


def load_run(run_dir):
    run_dir = Path(run_dir)
    returned = run_dir / 'returned_artifacts'
    expected = json.loads((returned / 'artifact_hashes.json').read_text())
    actual = {p.relative_to(returned).as_posix(): sha256_file(p) for p in sorted(returned.rglob('*'))
              if p.is_file() and p.name != 'artifact_hashes.json'}
    if expected != actual:
        missing = sorted(set(expected) ^ set(actual))[:10]
        changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])[:10]
        raise AnalysisRefused('returned artifact hashes do not match (differing=%s changed=%s)' % (missing, changed))
    verify_package(run_dir)
    fixtures = json.loads((run_dir / 'inputs/fixtures/suite_cases.json').read_text())
    managers = json.loads((run_dir / 'managers/manager_identity.json').read_text())
    result = json.loads((returned / 'result.json').read_text())
    return run_dir, returned, fixtures, managers, result, len(actual)


def step_summary(calls, offsets):
    steps = []
    for index in range(len(offsets) + 1):
        attempts = [c for c in calls if c.get('call') == index]
        accepted = next((c for c in attempts if c['success']), None)
        steps.append({'call': index, 'attempts': len(attempts), 'accepted': accepted is not None,
                      'accepted_attempt': accepted.get('attempt') if accepted else None,
                      'failure_reasons': [c['reason'] for c in attempts if not c['success']]})
    return steps


def build_rows(run_dir, returned, fixtures, managers, build, thresholds):
    by_label = {r['label']: r for r in json.loads((returned / build / 'cases_result.json').read_text())}
    records, anomalies = [], []
    expected_sha = managers[build]['sha256']
    limits = thresholds['expected_parameters']
    for run in fixtures['runs']:
        label = run['label']
        entry = by_label.get(label)
        log_path = returned / build / (label + '.log')
        if entry is None or not log_path.is_file():
            anomalies.append({'build': build, 'label': label, 'problem': 'missing case result or log'})
            continue
        parsed = parse_log(log_path.read_text(errors='replace'))
        code = entry['returncode']
        offsets = run.get('follow_up_offsets_s') or []
        steps = step_summary(parsed['calls'], offsets)
        first = next((c for c in parsed['calls'] if c.get('call') == 0), None)
        completed = all(s['accepted'] for s in steps)
        record = {
            'build': build, 'label': label, 'kind': run['kind'], 'start_id': run['start_id'],
            'start_group': run['start_group'], 'start_x': run['start'][0], 'map_id': run['map_id'],
            'init_id': run['init_id'], 'random_poly': run['random_poly'], 'seed': run['seed'],
            'repeat': run['repeat'], 'returncode': code, 'wall_seconds': entry['wall_seconds'],
            'accepted': bool(first and first['success']), 'reason': first['reason'] if first else 'no_call',
            'gate_value': first.get('gate_value') if first else None,
            'completed': completed, 'steps': steps, 'calls': parsed['calls'],
            'sequence': parsed['sequence'], 'skipped': parsed['skipped'],
        }
        problems = []
        identity = parsed['identity'] or {}
        if identity.get('manager_sha256') != expected_sha:
            problems.append('manager_sha256 %r != %s' % (identity.get('manager_sha256'), expected_sha))
        params = parsed['parameters'] or {}
        for key, value in limits.items():
            if params.get(key) != value:
                problems.append('parameter %s=%r expected %r' % (key, params.get(key), value))
        map_info = parsed['map'] or {}
        if run['occupied_boxes']:
            if map_info.get('boxes') != 1 or not map_info.get('occupied_voxels'):
                problems.append('box map condition missing')
            if not parsed['boxes'] or parsed['boxes'][0].get('center_inflated') != 1:
                problems.append('box centre not inflated')
        elif map_info.get('dynamics_only_empty_grid_no_clouds') is not True:
            problems.append('empty map condition missing')
        if code not in (0, 2):
            problems.append('returncode %s' % code)
        if parsed['errors']:
            problems.append('executable error: %s' % parsed['errors'][0])
        if code == 0 and not completed or code == 2 and completed:
            problems.append('returncode %s inconsistent with completed=%s' % (code, completed))
        if any(c['reason'] in ('no_end_marker', 'unclassified') for c in parsed['calls']):
            problems.append('call without end marker or unclassified rejection')
        for call in parsed['calls']:
            if call['success'] and not all(isinstance(call['end'].get(m), (int, float)) and
                                           math.isfinite(call['end'][m]) for m in METRICS):
                problems.append('call %s/%s has a missing or non-finite metric' % (call.get('call'), call.get('attempt')))
        if first is None:
            problems.append('no first call record')
        elif first['success'] != parsed['legacy_result']:
            problems.append('SUITE record disagrees with REBOUND_REPLAN_RESULT')
        if offsets:
            clock = parsed['clock'] or {}
            if clock.get('mode') != 'ros_time_override':
                problems.append('follow-up clock not overridden')
            relative = [offsets[0]] + [b - a for a, b in zip(offsets, offsets[1:])]
            for call in parsed['calls']:
                if call.get('call', 0) >= 1:
                    want = relative[call['call'] - 1]
                    if abs(call.get('requested_offset_s', -1) - want) > 1e-9 or \
                            abs(call.get('measured_offset_s', -1) - want) > thresholds['follow_up']['timing_tolerance_s']:
                        problems.append('follow-up %s timing %r/%r != %r' % (
                            call['call'], call.get('requested_offset_s'), call.get('measured_offset_s'), want))
        if problems:
            anomalies.append({'build': build, 'label': label, 'problems': problems})
        records.append(record)
        record['dump_samples'] = bool(run.get('dump_samples'))
        record['paths'] = parsed['paths'] if run.get('dump_samples') else []
    return records, anomalies


def accepted_calls(records):
    for record in records:
        for call in record['calls']:
            if call['success']:
                yield record, call


def call_endpoints(record):
    """Endpoint XY of the accepted attempt for each call index (None when that call was not accepted)."""
    out = []
    for step in record['steps']:
        accepted = next((c for c in record['calls'] if c.get('call') == step['call'] and c['success']), None)
        out.append(accepted['end']['endpoint_xy_m'] if accepted else None)
    return out


def collision_hits(record, max_collisions):
    return [{'build': record['build'], 'label': record['label'], 'start_id': record['start_id'],
             'map_id': record['map_id'], 'init_id': record['init_id'], 'call': call['call'],
             'attempt': call['attempt'], 'collision_samples': call['end']['collision_samples'],
             'inflated_occupied_samples': call['end']['inflated_occupied_samples'],
             'out_of_map_samples': call['end']['out_of_map_samples'],
             'first_collision_t': call['end'].get('first_collision_t'), 'duration': call['end']['duration']}
            for _, call in accepted_calls([record]) if call['end']['collision_samples'] > max_collisions]


def in_scope(record, scope):
    return (record['kind'] in scope['kinds'] and record['map_id'] in scope['map_ids']
            and record['random_poly'] in scope['random_poly'])


def status(failures, applicable=True, needs_explanation=()):
    if not applicable:
        return 'not_applicable'
    if failures:
        return 'fail'
    return 'needs_explanation' if needs_explanation else 'pass'


def key(record):
    return record['label']


def at_trajectory_end(end):
    """True when the sampled acceleration maximum lies at the last sample, t = duration."""
    t = end.get('max_acc_t')
    return isinstance(t, (int, float)) and abs(t - end['duration']) <= 1e-9


def validity_control(records, thresholds):
    """AC0: the original build must reproduce the recorded diagnosis accept/reject pattern."""
    control = thresholds['ac0']
    rows = [r for r in records if r['build'] == control['build'] and in_scope(r, control['scope'])]
    checks = []
    for expectation in control['expectations']:
        runs = sorted((r for r in rows if r['start_id'] == expectation['start_id']), key=lambda r: r['repeat'])
        outcomes = ['accepted' if r['accepted'] else r['reason'] for r in runs]
        passed = len(runs) == expectation['repeats'] and all(o == expectation['outcome'] for o in outcomes)
        checks.append({'start_id': expectation['start_id'], 'expected': expectation['outcome'],
                       'expected_repeats': expectation['repeats'], 'observed': outcomes,
                       'labels': [r['label'] for r in runs], 'passed': passed})
    reference = control['reference_gate_warning']
    values = [r['gate_value'] for r in rows if r['start_id'] == reference['start_id'] and r['gate_value'] is not None]
    return {
        'status': 'pass' if checks and all(c['passed'] for c in checks) else 'fail',
        'checks': checks,
        'reference_gate_value': reference['value'],
        'observed_gate_values': values,
        'gate_value_matches_reference': bool(values) and all(v == reference['value'] for v in values),
    }


def evaluate(records, thresholds):
    original = {key(r): r for r in records if r['build'] == 'original'}
    candidate = {key(r): r for r in records if r['build'] == 'candidate'}
    gate = thresholds['sampled_max_acc_limit_mps2']
    endpoint = thresholds['endpoint_xy_limit_m']
    max_collisions = thresholds['max_collision_samples']
    result = {}

    # AC2: fixtures on the empty map; candidate keeps every original acceptance and recovers every gate rejection.
    scope = thresholds['ac2']['scope']
    labels = sorted(k for k, r in original.items() if in_scope(r, scope) and k in candidate)
    failures = []
    for label in labels:
        o, c = original[label], candidate[label]
        if (o['accepted'] or o['reason'] == 'acceleration_gate') and not c['accepted']:
            failures.append({'label': label, 'original': o['reason'], 'candidate': c['reason']})
    over = [{'label': r['label'], 'call': call['call'], 'attempt': call['attempt'], 'max_acc': call['end']['max_acc'],
             'max_acc_t': call['end'].get('max_acc_t'), 'duration': call['end']['duration'],
             'at_trajectory_end': at_trajectory_end(call['end'])}
            for r, call in accepted_calls(candidate.values()) if call['end']['max_acc'] > gate]
    original_over = [call['end'] for _, call in accepted_calls(original.values()) if call['end']['max_acc'] > gate]
    result['AC2'] = {
        'status': status(failures + over, applicable=bool(labels)),
        'runs_in_scope': len(labels),
        'original_accepted': sum(original[k]['accepted'] for k in labels),
        'original_acceleration_gate_rejections': sum(original[k]['reason'] == 'acceleration_gate' for k in labels),
        'candidate_accepted': sum(candidate[k]['accepted'] for k in labels),
        'missing_candidate_acceptances': failures,
        'candidate_calls_over_sampled_limit': over,
        'candidate_accepted_calls_checked': sum(1 for _ in accepted_calls(candidate.values())),
        'original_calls_over_sampled_limit': len(original_over),
        'original_calls_over_sampled_limit_at_trajectory_end': sum(1 for end in original_over if at_trajectory_end(end)),
        'sampling_note': BOUNDARY_NOTES[2],
    }

    # AC3 (amended 2026-09-17, D8 then D10). Only single calls are judged: candidate endpoint XY within the
    # limit. Follow-up endpoints of both builds are reported without a verdict; AC6 judges follow-up completion.
    rules = thresholds['ac3']
    single_scope = rules['single_call']['scope']
    singles = {b: [r for r in v.values() if in_scope(r, single_scope)]
               for b, v in (('original', original), ('candidate', candidate))}
    far = [{'label': r['label'], 'call': call['call'], 'attempt': call['attempt'],
            'endpoint_xy_m': call['end']['endpoint_xy_m']}
           for r, call in accepted_calls(singles['candidate']) if call['end']['endpoint_xy_m'] > endpoint]
    single_distances = {b: [call['end']['endpoint_xy_m'] for _, call in accepted_calls(rows)]
                        for b, rows in singles.items()}
    follow_scope = rules['follow_up']['scope']
    sequences = sorted(k for k, r in original.items() if in_scope(r, follow_scope) and k in candidate)
    reported = [{'label': label,
                 'completed': {b: v[label]['completed'] for b, v in (('original', original), ('candidate', candidate))},
                 'endpoint_xy_m': {b: call_endpoints(v[label]) for b, v in (('original', original), ('candidate', candidate))}}
                for label in sequences]
    follow_distances = {b: [d for entry in reported for d in entry['endpoint_xy_m'][b] if d is not None]
                        for b in BUILDS}
    result['AC3'] = {
        'status': status(far, applicable=bool(single_distances['candidate'])),
        'limit_m': endpoint,
        'single_call': {
            'runs_in_scope': {b: len(rows) for b, rows in singles.items()},
            'accepted_calls': {b: len(d) for b, d in single_distances.items()},
            'max_endpoint_xy_m': {b: max(d) if d else None for b, d in single_distances.items()},
            'candidate_over_limit': far,
        },
        'follow_up_report_only': {
            'judged': False,
            'note': 'D10: follow-up endpoints are reported, not judged; AC6 judges completion, AC7 final position',
            'sequences': len(sequences),
            'completed': {b: sum(e['completed'][b] for e in reported) for b in BUILDS},
            'accepted_calls': {b: len(d) for b, d in follow_distances.items()},
            'calls_over_single_call_limit': {b: sum(d > endpoint for d in follow_distances[b]) for b in BUILDS},
            'max_endpoint_xy_m': {b: max(d) if d else None for b, d in follow_distances.items()},
            'sequences_reported': reported,
        },
    }

    # AC4 (amended 2026-09-17, D8): only candidate trajectories are judged. Original-build hits are a finding.
    scope = thresholds['ac4']['scope']
    box_labels = sorted(k for k, r in original.items() if in_scope(r, scope) and k in candidate)
    candidate_hits, original_hits, lost, not_counted = [], [], [], []
    for label in box_labels:
        o, c = original[label], candidate[label]
        candidate_hits += collision_hits(c, max_collisions)
        o_hits = collision_hits(o, max_collisions)
        original_hits += o_hits
        if o['accepted'] and not c['accepted']:
            entry = {'label': label, 'candidate': c['reason']}
            if o_hits:
                not_counted.append(dict(entry, original_collision_samples=sum(h['collision_samples'] for h in o_hits)))
            else:
                lost.append(entry)
    rejected = {b: sorted({k: v[k]['reason'] for k in box_labels if not v[k]['accepted']}.items())
                for b, v in (('original', original), ('candidate', candidate))}
    result['AC4'] = {
        'status': status(candidate_hits + lost, applicable=bool(box_labels)),
        'runs_in_scope': len(box_labels),
        'accepted_calls_checked': {b: sum(1 for _ in accepted_calls(v[k] for k in box_labels))
                                   for b, v in (('original', original), ('candidate', candidate))},
        'candidate_collision_hits': candidate_hits,
        'candidate_rejections_where_original_accepts_without_hit': lost,
        'candidate_rejections_where_original_accepts_with_hit_not_counted': not_counted,
        'rejections_reported': {b: [{'label': k, 'reason': v} for k, v in rows] for b, rows in rejected.items()},
        'findings': {
            'original_build_collision_hits': original_hits,
            'note': 'accepted original-build trajectories with collision samples; reported, they do not decide AC4',
        },
    }

    # AC5: random initialization; candidate successes >= original in every (start, map) group.
    scope = thresholds['ac5']['scope']
    groups = {}
    for label, o in original.items():
        if label in candidate and in_scope(o, scope):
            group = groups.setdefault('%s|%s' % (o['start_id'], o['map_id']), {'original': 0, 'candidate': 0, 'runs': 0})
            group['runs'] += 1
            group['original'] += o['accepted']
            group['candidate'] += candidate[label]['accepted']
    short = [dict(group=g, **v) for g, v in sorted(groups.items()) if v['candidate'] < v['original']]
    candidate_only = sorted(k for k, o in original.items()
                            if k in candidate and in_scope(o, scope) and o['accepted'] and not candidate[k]['accepted'])
    result['AC5'] = {
        'status': status(short, applicable=bool(groups), needs_explanation=candidate_only),
        'groups': len(groups),
        'groups_with_fewer_candidate_successes': short,
        'candidate_only_failures_requiring_explanation': [
            {'label': k, 'candidate_reason': candidate[k]['reason']} for k in candidate_only],
        'totals': {b: sum(g[b] for g in groups.values()) for b in BUILDS},
        'runs': sum(g['runs'] for g in groups.values()),
    }

    # AC6: follow-up sequences.
    scope = thresholds['ac6']['scope']
    sequences = sorted(k for k, r in original.items() if in_scope(r, scope) and k in candidate)
    failures = []
    for label in sequences:
        o, c = original[label], candidate[label]
        reasons = [reason for step in o['steps'] for reason in step['failure_reasons']]
        gate_only = not o['completed'] and bool(reasons) and all(r == 'acceleration_gate' for r in reasons)
        if (o['completed'] or gate_only) and not c['completed']:
            failures.append({'label': label, 'original_completed': o['completed'],
                             'original_failure_reasons': reasons, 'candidate_steps': c['steps']})
    result['AC6'] = {
        'status': status(failures, applicable=bool(sequences)),
        'sequences': len(sequences),
        'completed': {b: sum(v[k]['completed'] for k in sequences) for b, v in (('original', original), ('candidate', candidate))},
        'failures': failures,
        'max_acc_per_call': {
            label: {b: [max((call['end']['max_acc'] for call in v[label]['calls']
                             if call['success'] and call['call'] == i), default=None)
                        for i in range(len(v[label]['steps']))]
                    for b, v in (('original', original), ('candidate', candidate))}
            for label in sequences},
    }
    return result


def summary_table(records):
    groups = {}
    for record in records:
        init = 'random' if record['random_poly'] else 'poly_s0'
        name = (record['kind'], record['map_id'], init, record['build'])
        row = groups.setdefault(name, {'runs': 0, 'accepted': 0, 'acceleration_gate': 0, 'other_rejection': 0,
                                       'collision_accepted': 0, 'max_acc': 0.0, 'max_endpoint_xy_m': 0.0})
        row['runs'] += 1
        if record['kind'] == 'follow_up':
            ok = record['completed']
        else:
            ok = record['accepted']
        row['accepted'] += ok
        if not ok:
            reasons = [record['reason']] if record['kind'] == 'single' else \
                [r for step in record['steps'] for r in step['failure_reasons']] or [record['reason']]
            key_name = 'acceleration_gate' if 'acceleration_gate' in reasons else 'other_rejection'
            row[key_name] += 1
        for call in record['calls']:
            if call['success']:
                row['max_acc'] = max(row['max_acc'], call['end']['max_acc'])
                row['max_endpoint_xy_m'] = max(row['max_endpoint_xy_m'], call['end']['endpoint_xy_m'])
                if call['end']['collision_samples']:
                    row['collision_accepted'] += 1
    return [dict(kind=k[0], map=k[1], init=k[2], build=k[3], **v) for k, v in sorted(groups.items())]


def per_start(records):
    out = {}
    for record in records:
        if record['kind'] != 'single' or record['map_id'] != 'empty' or record['random_poly']:
            continue
        row = out.setdefault(record['start_id'], {'start_x': record['start_x']}).setdefault(
            record['build'], {'runs': 0, 'accepted': 0, 'reasons': {}, 'max_acc': [], 'gate_values': []})
        row['runs'] += 1
        row['accepted'] += record['accepted']
        row['reasons'][record['reason']] = row['reasons'].get(record['reason'], 0) + 1
        first = next((c for c in record['calls'] if c.get('call') == 0), None)
        if first and first['success']:
            row['max_acc'].append(first['end']['max_acc'])
        if record['gate_value'] is not None:
            row['gate_values'].append(record['gate_value'])
    return out


def markdown(report):
    lines = ['# Native suite comparison: %s' % report['run_id'], '',
             'Validity: **%s**. Overall passed: **%s** (integrity %s). Thresholds sha256 `%s`.' % (
                 report['validity'], report['passed'], report['integrity']['passed'], report['thresholds_sha256']), '',
             '| Criterion | Status | Key numbers |', '| --- | --- | --- |']
    control = report['validity_control']
    lines.append('| AC0 | %s | %s |' % (control['status'], '; '.join(
        '%s %s' % (c['start_id'], '/'.join(c['observed']) or 'missing') for c in control['checks'])))
    acceptance = report['acceptance']
    notes = {
        'AC2': 'runs %(runs_in_scope)s; original accepted %(original_accepted)s, gate rejections %(original_acceleration_gate_rejections)s; candidate accepted %(candidate_accepted)s',
        'AC3': ('single-call max endpoint XY m %(single_max)s (limit %(limit_m)s, candidate over %(single_over)s); '
                'follow-up report only: completed %(follow_completed)s, max endpoint XY m %(follow_max)s, '
                'calls over %(limit_m)s m %(follow_over)s'),
        'AC4': ('runs %(runs_in_scope)s; candidate hits %(candidate_hits)s; counted candidate rejections %(lost)s; '
                'not counted (original accepted with a hit) %(not_counted)s; finding: original-build hits %(original_hits)s'),
        'AC5': 'groups %(groups)s; totals %(totals)s; candidate-only failures %(only)s',
        'AC6': 'sequences %(sequences)s; completed %(completed)s',
    }
    for name in ('AC2', 'AC3', 'AC4', 'AC5', 'AC6'):
        row = dict(acceptance[name])
        try:
            if name == 'AC3':
                follow = row['follow_up_report_only']
                row.update(single_max=row['single_call']['max_endpoint_xy_m'],
                           single_over=len(row['single_call']['candidate_over_limit']),
                           follow_completed=follow['completed'], follow_max=follow['max_endpoint_xy_m'],
                           follow_over=follow['calls_over_single_call_limit'])
            if name == 'AC4':
                row.update(candidate_hits=len(row['candidate_collision_hits']),
                           lost=len(row['candidate_rejections_where_original_accepts_without_hit']),
                           not_counted=len(row['candidate_rejections_where_original_accepts_with_hit_not_counted']),
                           original_hits=len(row['findings']['original_build_collision_hits']))
            row.update(only=len(row.get('candidate_only_failures_requiring_explanation', [])))
            text = notes[name] % row
        except (KeyError, TypeError):
            text = ''
        lines.append('| %s | %s | %s |' % (name, row['status'], text))
    lines += ['', '| Kind | Map | Init | Build | Runs | Accepted | Gate rejections | Other rejections | Accepted with collision | Max acc (m/s^2) | Max endpoint XY (m) |',
              '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in report['summary']:
        lines.append('| %(kind)s | %(map)s | %(init)s | %(build)s | %(runs)d | %(accepted)d | %(acceleration_gate)d | '
                     '%(other_rejection)d | %(collision_accepted)d | %(max_acc).6f | %(max_endpoint_xy_m).6f |' % row)
    follow = report['follow_up_endpoints']
    lines += ['', '## Follow-up endpoints (report only, D10)', '',
              'Endpoint XY (m) of the accepted attempt per call; "-" when that call was not accepted.', '',
              '| Sequence | Original completed | Original calls 0/1/2 | Candidate completed | Candidate calls 0/1/2 |',
              '| --- | --- | --- | --- | --- |']
    lines += ['| %s | %s | %s | %s | %s |' % (
        e['label'], e['completed']['original'], ' / '.join('-' if d is None else '%.4f' % d for d in e['endpoint_xy_m']['original']),
        e['completed']['candidate'], ' / '.join('-' if d is None else '%.4f' % d for d in e['endpoint_xy_m']['candidate']))
        for e in follow]
    hits = report['findings']['original_build_collision_hits']
    lines += ['', '## Findings (not acceptance criteria)', '',
              'Accepted original-build trajectories with collision samples (AC4 scope): %d.%s' % (
                  len(hits), ' ' + report['findings']['note'] if report['findings'].get('note') else '')]
    if hits:
        lines += ['', '| Case | Init | Call | Collision samples | First collision t (s) | Duration (s) |',
                  '| --- | --- | ---: | ---: | ---: | ---: |']
        lines += ['| %s | %s | %s | %s | %s | %s |' % (
            h['label'], h['init_id'], h['call'], h['collision_samples'], h['first_collision_t'], h['duration'])
            for h in hits]
    lines += ['', 'Anomalies: %d. Claim boundary: %s' % (len(report['integrity']['anomalies']), report['claim']), '',
              'Boundary notes:', '']
    lines += ['- ' + note for note in report['boundary_notes']]
    lines.append('')
    return '\n'.join(lines)


def analyze(run_dir, thresholds_path=THRESHOLDS, plan_path=PLAN):
    thresholds, thresholds_sha = load_thresholds(thresholds_path, plan_path)
    run_dir, returned, fixtures, managers, result, artifact_count = load_run(run_dir)
    records, anomalies = [], []
    for build in BUILDS:
        rows, problems = build_rows(run_dir, returned, fixtures, managers, build, thresholds)
        records += rows
        anomalies += problems
    variants = result.get('variants', {})
    request = json.loads((run_dir / 'request.json').read_text())
    integrity = {
        'returned_hashes_match': True,
        'package_matches_manifest': True,
        'thresholds_sha256_matches_request': request.get('thresholds', {}).get('sha256') == thresholds_sha,
        'returned_artifacts': artifact_count,
        'source_gate_passed': bool(result.get('source_gate', {}).get('all_match')),
        'replay_completed': bool(result.get('replay_completed')),
        'sources_unchanged_after_run': bool(result.get('after_run')) and all(result['after_run'].values()),
        'owned_containers_absent': bool(result.get('owned_containers_absent')),
        'remote_error': result.get('error'),
        'executables_differ': len({variants.get(b, {}).get('executable_sha256') for b in BUILDS}) == 2,
        'manager_sources_one_line_diff': bool(managers.get('one_line_diff', {}).get('ok')),
        'runs_per_build': {b: sum(1 for r in records if r['build'] == b) for b in BUILDS},
        'expected_runs_per_build': len(fixtures['runs']),
        'anomalies': anomalies,
    }
    integrity['passed'] = (integrity['thresholds_sha256_matches_request']
                           and integrity['source_gate_passed'] and integrity['replay_completed']
                           and integrity['sources_unchanged_after_run'] and integrity['owned_containers_absent']
                           and not integrity['remote_error'] and integrity['executables_differ']
                           and integrity['manager_sources_one_line_diff'] and not anomalies
                           and all(v == len(fixtures['runs']) for v in integrity['runs_per_build'].values()))
    control = validity_control(records, thresholds)
    acceptance = evaluate(records, thresholds)
    valid = control['status'] == 'pass'
    findings = {'original_build_collision_hits': acceptance['AC4']['findings']['original_build_collision_hits'],
                'note': acceptance['AC4']['findings']['note'] if valid else
                'suite INVALID (AC0 failed); reported for diagnosis only'}
    follow_up_endpoints = acceptance['AC3']['follow_up_report_only']['sequences_reported']
    if not valid:
        for name, verdict in acceptance.items():
            acceptance[name] = {'status': 'not_evaluated', 'reason': 'AC0 validity control failed',
                                'computed_but_unused': verdict}
    passed = valid and integrity['passed'] and all(
        v['status'] in ('pass', 'not_applicable') for v in acceptance.values())
    report = {
        'schema': 'scan_fix_native_comparison_v1',
        'run_id': run_dir.name,
        'thresholds_sha256': thresholds_sha,
        'fixtures_sha256': sha256_file(run_dir / 'inputs/fixtures/suite_cases.json'),
        'fixtures_purpose': fixtures.get('purpose'),
        'validity': 'VALID' if valid else 'INVALID',
        'validity_control': control,
        'passed': passed,
        'integrity': integrity,
        'acceptance': acceptance,
        'findings': findings,
        'follow_up_endpoints': follow_up_endpoints,
        'summary': summary_table(records),
        'per_start_empty_poly': per_start(records),
        'rows': [dict({k: v for k, v in r.items() if k not in ('paths', 'calls', 'dump_samples')},
                      calls=[slim(c) for c in r['calls']]) for r in records],
        'claim': CLAIM,
        'boundary_notes': list(BOUNDARY_NOTES),
        'thresholds_amendments': thresholds.get('amendments', []),
    }
    paths = {
        'schema': 'scan_fix_native_paths_v1',
        'run_id': run_dir.name,
        'boxes': fixtures.get('boxes', {}),
        'runs': {},
    }
    runs_by_label = {r['label']: r for r in fixtures['runs']}
    for record in records:
        if not record['dump_samples']:
            continue
        run = runs_by_label[record['label']]
        entry = paths['runs'].setdefault(record['label'], {
            'start': run['start'], 'target': run['target'], 'occupied_boxes': run['occupied_boxes'],
            'follow_up_offsets_s': run['follow_up_offsets_s'], 'builds': {}})
        entry['builds'][record['build']] = {
            'completed': record['completed'],
            'steps': record['steps'],
            'paths': [{'call': p.get('call'), 'attempt': p.get('attempt'), 'dt': p.get('dt'), 'xyz': p['xyz']}
                      for p in record['paths']],
        }
    return report, paths


def default_run_dir():
    candidates = sorted(p for p in RUNS.glob('native_suite_*') if (p / 'returned_artifacts').is_dir()) if RUNS.is_dir() else []
    if len(candidates) != 1:
        raise AnalysisRefused('pass --run-dir; found %d returned native_suite_* runs' % len(candidates))
    return candidates[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=None)
    parser.add_argument('--thresholds', type=Path, default=THRESHOLDS)
    parser.add_argument('--plan', type=Path, default=PLAN)
    args = parser.parse_args(argv)
    try:
        run_dir = args.run_dir or default_run_dir()
        report, paths = analyze(run_dir, args.thresholds, args.plan)
    except AnalysisRefused as error:
        print('analyze_suite: refused: ' + str(error), file=sys.stderr)
        return 2
    run_dir = Path(run_dir)
    (run_dir / 'comparison.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    (run_dir / 'comparison.md').write_text(markdown(report))
    (run_dir / 'paths.json').write_text(json.dumps(paths, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'run_id': report['run_id'], 'validity': report['validity'], 'passed': report['passed'],
                      'integrity_passed': report['integrity']['passed'],
                      'acceptance': {k: v['status'] for k, v in report['acceptance'].items()}}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
