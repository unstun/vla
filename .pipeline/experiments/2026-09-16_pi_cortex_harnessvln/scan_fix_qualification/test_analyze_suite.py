import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(HERE / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


an = load('analyze_suite')
SHA = {'original': 'a' * 64, 'candidate': 'b' * 64}
HEADER = ('hit: 1.7346\nINPUT start=-1.142216802,-4.498657227,1.864306927\n'
          'SUITE_IDENTITY manager_cpp=/managers/{build}/planner_manager.cpp manager_sha256={sha}\n')
PARAMS = ('PARAMETERS manager.max_vel=1.000000000 manager.max_acc=0.500000000 manager.max_jerk=4.000000000 '
          'optimization.vel_tolerance=1.000000000 optimization.acc_tolerance=1.000000000 '
          'manager.feasibility_tolerance=0.500000000\n')
EMPTY = 'MAP_CONDITION dynamics_only_empty_grid_no_clouds=true note=GridMap_initialized_from_params_no_point_cloud_fed\n'
BOX = ('MAP_BOX index=0 id=s__near_box min=-0.5,-4.3,1 max=-0.2,-4.0,3 marked_voxels=1440 center_inflated=1\n'
       'MAP_CONDITION boxes=1 occupied_voxels=1440 boxes_file=/inputs/fixtures/boxes/s__near_box.json '
       'map_origin=-5,-5,0 map_size=10,10,5 resolution=0.050000000000000003 note=x\n')
GATE = ('[WARN] [1789.5] [scan_planner_node]: Dynamic feasibility failed: acceleration at t=3.500 is 1.567 > 1.500\n'
        '\x1b[34mThis refined trajectory is unsafe or dynamically infeasible. Skip publishing it.\n\x1b[0m')
REFINE = 'Need to reallocate time.\n\x1b[34mThis refined trajectory is unsafe or dynamically infeasible. Skip publishing it.\n\x1b[0m'
OPTIMIZE = 'first_optimize_step_success=0\n'


def ok(max_acc=0.59, endpoint=0.0355, collisions=0, out_of_map=0, duration=3.6, first_collision=None):
    if first_collision is None:
        first_collision = 1.25 if collisions else -1.0
    return {'max_acc': max_acc, 'endpoint': endpoint, 'collisions': collisions, 'out_of_map': out_of_map,
            'duration': duration, 'first_collision': first_collision}


def call_text(call, attempt, kind, outcome, poly=True, rand=False, requested=0.0, measured=None):
    measured = requested if measured is None else measured
    text = ('SUITE_CALL_BEGIN call=%d attempt=%d kind=%s poly_init=%s random_poly=%s clock_ns=0 '
            'requested_offset_s=%r measured_offset_s=%r start=-1.1,-4.5,1.86 start_vel=0,0,0 start_acc=0,0,0 '
            'target=0.35,-4.49,1.91 target_vel=0,0,0\n\n[rebo replan]: ----0\n' % (
                call, attempt, kind, str(poly).lower(), str(rand).lower(), requested, measured))
    if isinstance(outcome, dict):
        m = outcome
        occupied = m['collisions'] - m['out_of_map']
        text += ('SUITE_CALL_END call=%d attempt=%d kind=%s success=true clock_ns=0 traj_id=1 duration=%r '
                 'max_acc=%r max_acc_t=2.8 max_vel=0.74 end_acc=0.0006 end_vel=0.0057 end=0.319,-4.487,1.909 '
                 'endpoint_xy_m=%r endpoint_z_m=0.0011 endpoint_xyz_m=%r start_offset_m=0.02 '
                 'collision_samples=%d inflated_occupied_samples=%d out_of_map_samples=%d collision_checks=361 '
                 'first_collision_t=%r\n' % (call, attempt, kind, m['duration'], m['max_acc'], m['endpoint'],
                                             m['endpoint'], m['collisions'], occupied, m['out_of_map'],
                                             m['first_collision']))
        text += ('SUITE_PATH call=%d attempt=%d dt=0.050000000000000003 duration=%r '
                 'points=-1.1,-4.5,1.86;0.0,-4.49,1.9;0.319,-4.487,1.909\n' % (call, attempt, m['duration']))
    else:
        text += {'gate': GATE, 'refine': REFINE, 'optimize': OPTIMIZE}[outcome]
        text += 'SUITE_CALL_END call=%d attempt=%d kind=%s success=false clock_ns=0\n' % (call, attempt, kind)
    return text


def log_text(build, run, calls, sha=None, clock=None):
    """calls: list of (call, attempt, outcome[, requested, measured]) in order."""
    text = HEADER.format(build=build, sha=sha or SHA[build])
    text += BOX if run['occupied_boxes'] else EMPTY
    text += PARAMS
    offsets = run['follow_up_offsets_s']
    text += clock or ('CLOCK_CONDITION mode=ros_time_override use_sim_time=true override_enabled=true base_ns=100000000000\n'
                      if offsets else 'CLOCK_CONDITION mode=unmodified use_sim_time=true override_enabled=true now_ns=0\n')
    first = True
    accepted = {}
    for item in calls:
        call, attempt, outcome = item[:3]
        requested = item[3] if len(item) > 3 else 0.0
        measured = item[4] if len(item) > 4 else None
        chain = [(True, False), (False, False), (True, False), (True, True)][attempt + (1 if call else 0)] \
            if call else (run['poly_init'], run['random_poly'])
        text += call_text(call, attempt, 'initial' if call == 0 else 'follow_up', outcome, chain[0], chain[1],
                          requested, measured)
        if isinstance(outcome, dict):
            accepted[call] = True
        if first:
            text += 'REBOUND_REPLAN_RESULT success=%s\n' % str(isinstance(outcome, dict)).lower()
            first = False
    steps = [c for c in accepted if c >= 1]
    completed = 0 in accepted and len(steps) == len(offsets)
    text += 'SUITE_SEQUENCE_END steps_requested=%d steps_accepted=%d completed=%s stop_reason=x\ndes manager\n' % (
        len(offsets), len(steps), str(completed).lower())
    return text, (0 if completed else 2)


def fixture_run(label, map_id='empty', random_poly=False, kind='single', start_id='s', seed=0, repeat=0):
    return {
        'label': label, 'kind': kind, 'start_id': start_id, 'start_group': 'stop_position_sweep',
        'start': [-1.1, -4.5, 1.86], 'target': [0.35, -4.49, 1.91], 'map_id': map_id,
        'init_id': ('rand_s%d_r0' % seed) if random_poly else 'poly_s0_r%d' % repeat, 'repeat': repeat,
        'poly_init': True, 'random_poly': random_poly, 'seed': seed,
        'occupied_boxes': None if map_id == 'empty' else 'boxes/%s__%s.json' % (start_id, map_id),
        'follow_up_offsets_s': [0.3, 0.6] if kind == 'follow_up' else [], 'dump_samples': True,
    }


CONTROL = ('failed_run_resume', 'failed_run_initial', 'successful_run_initial', 'successful_run_resume')


def control_plan():
    """AC0 runs: the original rejects failed_run_resume at the gate 3/3 and accepts the others 3/3."""
    plan = {}
    for start_id in CONTROL:
        for repeat in range(3):
            label = '%s__empty__poly_s0_r%d' % (start_id, repeat)
            original = 'gate' if start_id == 'failed_run_resume' else ok()
            plan[label] = (fixture_run(label, start_id=start_id, repeat=repeat),
                           {'original': [(0, 0, original)], 'candidate': [(0, 0, ok())]})
    return plan


def passing_plan():
    """label -> (fixture run, {build: calls})."""
    follow_ok = [(0, 0, ok()), (1, 0, ok(), 0.3), (2, 0, ok(), 0.3)]
    return dict(control_plan(), **{
        's__empty__poly': (fixture_run('s__empty__poly'),
                           {'original': [(0, 0, 'gate')], 'candidate': [(0, 0, ok())]}),
        's__empty__rand0': (fixture_run('s__empty__rand0', random_poly=True),
                            {'original': [(0, 0, ok(0.8))], 'candidate': [(0, 0, ok(0.7))]}),
        's__near_box__poly': (fixture_run('s__near_box__poly', map_id='near_box'),
                              {'original': [(0, 0, 'refine')], 'candidate': [(0, 0, ok())]}),
        's__near_box__rand0': (fixture_run('s__near_box__rand0', map_id='near_box', random_poly=True),
                               {'original': [(0, 0, 'optimize')], 'candidate': [(0, 0, 'optimize')]}),
        's__empty__follow': (fixture_run('s__empty__follow', kind='follow_up'),
                             {'original': [(0, 0, 'gate')], 'candidate': follow_ok}),
        't__empty__follow': (fixture_run('t__empty__follow', kind='follow_up', start_id='t'),
                             {'original': follow_ok, 'candidate': follow_ok}),
    })


def build_run(root, plan, result_overrides=None, sha=None, one_line_diff=True, clock=None, thresholds_sha=None):
    run_dir = root / 'native_suite_test'
    (run_dir / 'inputs/fixtures').mkdir(parents=True)
    (run_dir / 'managers').mkdir()
    runs = [run for run, _ in plan.values()]
    (run_dir / 'inputs/fixtures/suite_cases.json').write_text(json.dumps(
        {'schema': 'scan_fix_suite_cases_v1', 'purpose': 'test', 'runs': runs, 'boxes': {}}))
    (run_dir / 'managers/manager_identity.json').write_text(json.dumps({
        'original': {'sha256': SHA['original']}, 'candidate': {'sha256': SHA['candidate']},
        'one_line_diff': {'ok': one_line_diff}}))
    recorded = thresholds_sha or hashlib.sha256((HERE / 'thresholds.json').read_bytes()).hexdigest()
    (run_dir / 'request.json').write_text(json.dumps({'run_id': 'native_suite_test',
                                                      'thresholds': {'sha256': recorded}}))
    package = {p.relative_to(run_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(run_dir.rglob('*')) if p.is_file()}
    (run_dir / 'package_manifest.json').write_text(json.dumps(package))
    returned = run_dir / 'returned_artifacts'
    for build in ('original', 'candidate'):
        (returned / build).mkdir(parents=True)
        results = []
        for label, (run, calls) in plan.items():
            text, code = log_text(build, run, calls[build], sha=(sha or {}).get((build, label)), clock=clock)
            (returned / build / (label + '.log')).write_text(text)
            results.append({'label': label, 'build': build, 'returncode': code, 'wall_seconds': 0.1, 'command': []})
        (returned / build / 'cases_result.json').write_text(json.dumps(results))
    result = {'source_gate': {'all_match': True}, 'replay_completed': True,
              'after_run': {'package_unchanged': True}, 'owned_containers_absent': True,
              'variants': {'original': {'executable_sha256': 'x'}, 'candidate': {'executable_sha256': 'y'}}}
    result.update(result_overrides or {})
    (returned / 'result.json').write_text(json.dumps(result))
    hashes = {p.relative_to(returned).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in returned.rglob('*') if p.is_file()}
    (returned / 'artifact_hashes.json').write_text(json.dumps(hashes))
    return run_dir


def analyze(tmp_path, plan, **kwargs):
    report, paths = an.analyze(build_run(tmp_path, plan, **kwargs))
    return report, paths


def test_passing_run(tmp_path):
    report, paths = analyze(tmp_path, passing_plan())
    assert report['integrity']['anomalies'] == []
    assert report['integrity']['passed']
    assert report['validity'] == 'VALID' and report['validity_control']['status'] == 'pass'
    assert report['validity_control']['gate_value_matches_reference']
    assert [c['observed'] for c in report['validity_control']['checks']] == [
        ['acceleration_gate'] * 3, ['accepted'] * 3, ['accepted'] * 3, ['accepted'] * 3]
    assert {k: v['status'] for k, v in report['acceptance'].items()} == {
        'AC2': 'pass', 'AC3': 'pass', 'AC4': 'pass', 'AC5': 'pass', 'AC6': 'pass'}
    assert report['passed']
    ac2 = report['acceptance']['AC2']
    assert ac2['original_acceleration_gate_rejections'] == 4 and ac2['candidate_accepted'] == 13
    ac4 = report['acceptance']['AC4']
    assert {r['reason'] for r in ac4['rejections_reported']['original']} == {'refinement_failed', 'rebound_optimization_failed'}
    assert report['acceptance']['AC6']['completed'] == {'original': 1, 'candidate': 2}
    assert report['acceptance']['AC6']['max_acc_per_call']['t__empty__follow']['candidate'] == [0.59, 0.59, 0.59]
    rows = {(r['build'], r['label']): r for r in report['rows']}
    assert rows[('original', 's__empty__poly')]['gate_value'] == 1.567
    dumped = paths['runs']['s__empty__follow']['builds']
    assert set(dumped) == {'candidate', 'original'}
    assert dumped['original']['paths'] == [] and not dumped['original']['completed']
    assert dumped['original']['steps'][0]['failure_reasons'] == ['acceleration_gate']
    assert [p['call'] for p in dumped['candidate']['paths']] == [0, 1, 2]
    assert dumped['candidate']['paths'][0]['xyz'][-1] == [0.319, -4.487, 1.909]


def test_ac2_fails_when_candidate_loses_an_acceptance(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__poly']
    plan['s__empty__poly'] = (run, {'original': [(0, 0, ok())], 'candidate': [(0, 0, 'optimize')]})
    report, _ = analyze(tmp_path, plan)
    assert report['acceptance']['AC2']['status'] == 'fail'
    assert not report['passed']


def test_ac2_fails_when_candidate_misses_a_gate_rejection(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__poly']
    plan['s__empty__poly'] = (run, {'original': [(0, 0, 'gate')], 'candidate': [(0, 0, 'gate')]})
    report, _ = analyze(tmp_path, plan)
    assert report['acceptance']['AC2']['missing_candidate_acceptances'][0]['candidate'] == 'acceleration_gate'
    assert report['acceptance']['AC2']['status'] == 'fail'


def test_ac2_fails_on_sampled_acceleration_anywhere(tmp_path):
    plan = passing_plan()
    run, calls = plan['t__empty__follow']
    calls = {'original': copy.deepcopy(calls['original']), 'candidate': copy.deepcopy(calls['candidate'])}
    calls['candidate'][2] = (2, 0, ok(max_acc=1.5000001), 0.3)
    plan['t__empty__follow'] = (run, calls)
    report, _ = analyze(tmp_path, plan)
    over = report['acceptance']['AC2']['candidate_calls_over_sampled_limit']
    assert over == [{'label': 't__empty__follow', 'call': 2, 'attempt': 0, 'max_acc': 1.5000001,
                     'max_acc_t': 2.8, 'duration': 3.6, 'at_trajectory_end': False}]
    assert report['acceptance']['AC2']['status'] == 'fail'


def test_ac2_reports_original_endpoint_maxima_without_failing(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__rand0']
    plan['s__empty__rand0'] = (run, {'original': [(0, 0, ok(max_acc=1.53, duration=2.8))],
                                     'candidate': [(0, 0, ok(0.7))]})
    report, _ = analyze(tmp_path, plan)
    ac2 = report['acceptance']['AC2']
    assert ac2['original_calls_over_sampled_limit'] == 1
    assert ac2['original_calls_over_sampled_limit_at_trajectory_end'] == 1
    assert 'checkDynamicFeasibility' in ac2['sampling_note']
    assert ac2['status'] == 'pass'


def test_ac3_fails_on_endpoint(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__near_box__poly']
    plan['s__near_box__poly'] = (run, {'original': [(0, 0, 'refine')], 'candidate': [(0, 0, ok(endpoint=0.0501))]})
    report, _ = analyze(tmp_path, plan)
    ac3 = report['acceptance']['AC3']
    assert ac3['status'] == 'fail'
    assert ac3['single_call']['max_endpoint_xy_m']['candidate'] == 0.0501
    assert ac3['single_call']['candidate_over_limit'] == [
        {'label': 's__near_box__poly', 'call': 0, 'attempt': 0, 'endpoint_xy_m': 0.0501}]
    assert ac3['follow_up_report_only']['judged'] is False


def test_ac3_single_call_at_the_limit_passes(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__near_box__poly']
    plan['s__near_box__poly'] = (run, {'original': [(0, 0, ok(endpoint=0.3))], 'candidate': [(0, 0, ok(endpoint=0.05))]})
    report, _ = analyze(tmp_path, plan)
    ac3 = report['acceptance']['AC3']
    assert ac3['status'] == 'pass' and ac3['single_call']['candidate_over_limit'] == []
    assert ac3['single_call']['max_endpoint_xy_m'] == {'original': 0.3, 'candidate': 0.05}


def follow_plan(original_ends, candidate_ends, label='t__empty__follow'):
    plan = passing_plan()
    run, _ = plan[label]
    calls = {}
    for build, ends in (('original', original_ends), ('candidate', candidate_ends)):
        calls[build] = [(i, 0, ok(endpoint=e), 0.0 if i == 0 else 0.3) if e is not None else (i, 0, 'gate', 0.3)
                        for i, e in enumerate(ends)]
    plan[label] = (run, calls)
    return plan


def test_ac3_follow_up_endpoints_are_reported_not_judged(tmp_path, capsys):
    # D10: follow-up endpoints over 0.05 m in either build do not fail AC3, and they appear in the report.
    plan = follow_plan([0.0355, 0.0785, 0.02], [0.0355, 0.0805, 0.3])
    run, calls = plan['s__empty__follow']
    plan['s__empty__follow'] = (run, dict(calls, original=[(0, 0, ok(endpoint=0.03)), (1, 0, ok(endpoint=0.12), 0.3),
                                                           (2, 0, 'gate', 0.3), (2, 1, 'gate', 0.3),
                                                           (2, 2, 'gate', 0.3)]))
    run_dir = build_run(tmp_path, plan)
    assert an.main(['--run-dir', str(run_dir)]) == 0
    capsys.readouterr()
    report = json.loads((run_dir / 'comparison.json').read_text())
    ac3 = report['acceptance']['AC3']
    assert ac3['status'] == 'pass' and report['passed']
    assert ac3['single_call']['candidate_over_limit'] == []
    follow = ac3['follow_up_report_only']
    assert follow['judged'] is False and follow['sequences'] == 2
    assert follow['completed'] == {'original': 1, 'candidate': 2}
    assert follow['calls_over_single_call_limit'] == {'original': 2, 'candidate': 2}
    assert follow['max_endpoint_xy_m'] == {'original': 0.12, 'candidate': 0.3}
    entries = {e['label']: e for e in follow['sequences_reported']}
    assert entries['t__empty__follow'] == {
        'label': 't__empty__follow', 'completed': {'original': True, 'candidate': True},
        'endpoint_xy_m': {'original': [0.0355, 0.0785, 0.02], 'candidate': [0.0355, 0.0805, 0.3]}}
    assert entries['s__empty__follow']['completed'] == {'original': False, 'candidate': True}
    assert entries['s__empty__follow']['endpoint_xy_m']['original'] == [0.03, 0.12, None]
    assert report['follow_up_endpoints'] == follow['sequences_reported']
    assert not any(k in json.dumps(ac3) for k in ('margin', 'non_inferior', 'over_original'))
    table = (run_dir / 'comparison.md').read_text()
    assert '## Follow-up endpoints (report only, D10)' in table
    assert '| t__empty__follow | True | 0.0355 / 0.0785 / 0.0200 | True | 0.0355 / 0.0805 / 0.3000 |' in table
    assert '| s__empty__follow | False | 0.0300 / 0.1200 / - | True | 0.0355 / 0.0355 / 0.0355 |' in table


def test_ac4_fails_on_a_candidate_collision(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__near_box__rand0']
    plan['s__near_box__rand0'] = (run, {'original': [(0, 0, 'optimize')],
                                        'candidate': [(0, 0, ok(collisions=2, out_of_map=1))]})
    report, _ = analyze(tmp_path, plan)
    ac4 = report['acceptance']['AC4']
    assert ac4['candidate_collision_hits'] == [{
        'build': 'candidate', 'label': 's__near_box__rand0', 'start_id': 's', 'map_id': 'near_box',
        'init_id': 'rand_s0_r0', 'call': 0, 'attempt': 0, 'collision_samples': 2, 'inflated_occupied_samples': 1,
        'out_of_map_samples': 1, 'first_collision_t': 1.25, 'duration': 3.6}]
    assert ac4['findings']['original_build_collision_hits'] == []
    assert ac4['status'] == 'fail' and not report['passed']


def test_ac4_original_only_collision_is_a_finding_not_a_failure(tmp_path, capsys):
    plan = passing_plan()
    run, _ = plan['s__near_box__rand0']
    plan['s__near_box__rand0'] = (run, {'original': [(0, 0, ok(collisions=9, duration=2.9, first_collision=0.61))],
                                        'candidate': [(0, 0, ok())]})
    run_dir = build_run(tmp_path, plan)
    assert an.main(['--run-dir', str(run_dir)]) == 0
    capsys.readouterr()
    report = json.loads((run_dir / 'comparison.json').read_text())
    ac4 = report['acceptance']['AC4']
    assert ac4['status'] == 'pass' and report['passed']
    assert ac4['candidate_collision_hits'] == []
    hit = {'build': 'original', 'label': 's__near_box__rand0', 'start_id': 's', 'map_id': 'near_box',
           'init_id': 'rand_s0_r0', 'call': 0, 'attempt': 0, 'collision_samples': 9, 'inflated_occupied_samples': 9,
           'out_of_map_samples': 0, 'first_collision_t': 0.61, 'duration': 2.9}
    assert ac4['findings']['original_build_collision_hits'] == [hit]
    assert report['findings']['original_build_collision_hits'] == [hit]
    table = (run_dir / 'comparison.md').read_text()
    assert '## Findings (not acceptance criteria)' in table
    assert '| s__near_box__rand0 | rand_s0_r0 | 0 | 9 | 0.61 | 2.9 |' in table
    assert 'finding: original-build hits 1' in table


def test_ac4_fails_when_candidate_rejects_what_original_accepts_without_a_hit(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__near_box__poly']
    plan['s__near_box__poly'] = (run, {'original': [(0, 0, ok())], 'candidate': [(0, 0, 'refine')]})
    report, _ = analyze(tmp_path, plan)
    ac4 = report['acceptance']['AC4']
    assert ac4['candidate_rejections_where_original_accepts_without_hit'] == [
        {'label': 's__near_box__poly', 'candidate': 'refinement_failed'}]
    assert ac4['candidate_rejections_where_original_accepts_with_hit_not_counted'] == []
    assert ac4['status'] == 'fail'


def test_ac4_candidate_rejection_is_not_counted_when_the_original_hit(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__near_box__poly']
    plan['s__near_box__poly'] = (run, {'original': [(0, 0, ok(collisions=3))], 'candidate': [(0, 0, 'refine')]})
    report, _ = analyze(tmp_path, plan)
    ac4 = report['acceptance']['AC4']
    assert ac4['candidate_rejections_where_original_accepts_without_hit'] == []
    assert ac4['candidate_rejections_where_original_accepts_with_hit_not_counted'] == [
        {'label': 's__near_box__poly', 'candidate': 'refinement_failed', 'original_collision_samples': 3}]
    assert {'label': 's__near_box__poly', 'reason': 'refinement_failed'} in ac4['rejections_reported']['candidate']
    assert len(ac4['findings']['original_build_collision_hits']) == 1
    assert ac4['status'] == 'pass'


def test_ac5_fails_when_a_group_loses_successes(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__rand0']
    plan['s__empty__rand0'] = (run, {'original': [(0, 0, ok())], 'candidate': [(0, 0, 'optimize')]})
    report, _ = analyze(tmp_path, plan)
    ac5 = report['acceptance']['AC5']
    assert ac5['status'] == 'fail'
    assert ac5['groups_with_fewer_candidate_successes'][0]['group'] == 's|empty'


def test_ac5_needs_explanation_for_candidate_only_failures(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__rand0']
    plan['s__empty__rand0'] = (run, {'original': [(0, 0, ok())], 'candidate': [(0, 0, 'optimize')]})
    other = fixture_run('s__empty__rand1', random_poly=True, seed=1)
    plan['s__empty__rand1'] = (other, {'original': [(0, 0, 'gate')], 'candidate': [(0, 0, ok())]})
    report, _ = analyze(tmp_path, plan)
    ac5 = report['acceptance']['AC5']
    assert ac5['groups_with_fewer_candidate_successes'] == []
    assert ac5['status'] == 'needs_explanation'
    assert ac5['candidate_only_failures_requiring_explanation'] == [
        {'label': 's__empty__rand0', 'candidate_reason': 'rebound_optimization_failed'}]
    assert not report['passed']


def test_ac6_fails_when_candidate_breaks_a_completed_sequence(tmp_path):
    plan = passing_plan()
    run, calls = plan['t__empty__follow']
    broken = [(0, 0, ok()), (1, 0, 'optimize', 0.3), (1, 1, 'refine', 0.3), (1, 2, 'refine', 0.3)]
    plan['t__empty__follow'] = (run, {'original': calls['original'], 'candidate': broken})
    report, _ = analyze(tmp_path, plan)
    ac6 = report['acceptance']['AC6']
    assert ac6['status'] == 'fail'
    steps = ac6['failures'][0]['candidate_steps']
    assert steps[1] == {'call': 1, 'attempts': 3, 'accepted': False, 'accepted_attempt': None,
                        'failure_reasons': ['rebound_optimization_failed', 'refinement_failed', 'refinement_failed']}


def test_ac6_requires_recovery_of_gate_only_failures(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__follow']
    gate_only = [(0, 0, ok()), (1, 0, ok(), 0.3), (2, 0, 'gate', 0.3), (2, 1, 'gate', 0.3), (2, 2, 'gate', 0.3)]
    plan['s__empty__follow'] = (run, {'original': gate_only, 'candidate': [(0, 0, ok()), (1, 0, ok(), 0.3),
                                                                          (2, 0, 'refine', 0.3)] + [
        (2, 1, 'refine', 0.3), (2, 2, 'refine', 0.3)]})
    report, _ = analyze(tmp_path, plan)
    assert report['acceptance']['AC6']['status'] == 'fail'
    assert report['acceptance']['AC6']['failures'][0]['original_failure_reasons'] == ['acceleration_gate'] * 3


def test_follow_up_timing_mismatch_is_an_integrity_failure(tmp_path):
    plan = passing_plan()
    run, calls = plan['t__empty__follow']
    late = [(0, 0, ok()), (1, 0, ok(), 0.3, 0.31), (2, 0, ok(), 0.3)]
    plan['t__empty__follow'] = (run, {'original': calls['original'], 'candidate': late})
    report, _ = analyze(tmp_path, plan)
    assert not report['integrity']['passed']
    assert any('timing' in p for a in report['integrity']['anomalies'] for p in a['problems'])
    assert not report['passed']


def test_manager_identity_mismatch_is_an_integrity_failure(tmp_path):
    report, _ = analyze(tmp_path, passing_plan(), sha={('candidate', 's__empty__poly'): SHA['original']})
    anomalies = report['integrity']['anomalies']
    assert anomalies[0]['label'] == 's__empty__poly' and 'manager_sha256' in anomalies[0]['problems'][0]
    assert not report['passed']


def test_non_finite_metric_is_an_integrity_failure(tmp_path):
    plan = passing_plan()
    run, _ = plan['s__empty__poly']
    plan['s__empty__poly'] = (run, {'original': [(0, 0, 'gate')], 'candidate': [(0, 0, ok(max_acc=float('nan')))]})
    report, _ = analyze(tmp_path, plan)
    assert any('non-finite' in p for a in report['integrity']['anomalies'] for p in a['problems'])
    assert not report['passed']


def test_remote_failures_fail_integrity(tmp_path):
    report, _ = analyze(tmp_path, passing_plan(), result_overrides={'owned_containers_absent': False})
    assert not report['integrity']['passed'] and not report['passed']


def test_returned_hash_mismatch_is_refused(tmp_path):
    run_dir = build_run(tmp_path, passing_plan())
    with (run_dir / 'returned_artifacts/candidate/s__empty__poly.log').open('a') as stream:
        stream.write('tampered\n')
    with pytest.raises(an.AnalysisRefused):
        an.analyze(run_dir)


def test_changed_run_package_is_refused(tmp_path):
    run_dir = build_run(tmp_path, passing_plan())
    path = run_dir / 'managers/manager_identity.json'
    identity = json.loads(path.read_text())
    identity['candidate']['sha256'] = SHA['original']
    path.write_text(json.dumps(identity))
    with pytest.raises(an.AnalysisRefused, match='manifest'):
        an.analyze(run_dir)


def test_run_package_without_manifest_or_listed_inputs_is_refused(tmp_path):
    run_dir = build_run(tmp_path, passing_plan())
    manifest = json.loads((run_dir / 'package_manifest.json').read_text())
    del manifest['inputs/fixtures/suite_cases.json']
    (run_dir / 'package_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(an.AnalysisRefused, match='unlisted'):
        an.analyze(run_dir)
    (run_dir / 'package_manifest.json').unlink()
    with pytest.raises(an.AnalysisRefused, match='package_manifest'):
        an.analyze(run_dir)


def test_thresholds_differing_from_the_request_fail_integrity(tmp_path):
    report, _ = analyze(tmp_path, passing_plan(), thresholds_sha='0' * 64)
    assert report['integrity']['thresholds_sha256_matches_request'] is False
    assert not report['integrity']['passed'] and not report['passed']
    assert len(report['fixtures_sha256']) == 64


def test_changed_thresholds_are_refused(tmp_path):
    changed = json.loads((HERE / 'thresholds.json').read_text())
    changed['endpoint_xy_limit_m'] = 0.06
    path = tmp_path / 'thresholds.json'
    path.write_text(json.dumps(changed))
    run_dir = build_run(tmp_path, passing_plan())
    with pytest.raises(an.AnalysisRefused):
        an.analyze(run_dir, thresholds_path=path)
    plan = tmp_path / 'PLAN.md'
    plan.write_text('no hash here\n')
    with pytest.raises(an.AnalysisRefused):
        an.load_thresholds(HERE / 'thresholds.json', plan)


def test_frozen_thresholds_match_prd_values():
    thresholds, digest = an.load_thresholds()
    assert thresholds['sampled_max_acc_limit_mps2'] == thresholds['acceleration_gate_mps2'] == 1.5
    assert thresholds['endpoint_xy_limit_m'] == 0.05
    assert thresholds['max_collision_samples'] == 0
    assert thresholds['ac3']['single_call']['scope']['kinds'] == ['single']
    assert thresholds['ac3']['follow_up']['judged'] is False and 'endpoint_margin_m' not in thresholds['ac3']['follow_up']
    d8, d10 = thresholds['amendments']
    assert d8['date'] == d10['date'] == '2026-09-17'
    assert d8['decision'].startswith('D8') and d10['decision'].startswith('D10')
    history = {'3cce793f0cdc83fffda510ff4df1eeed6495f8a9e2823faa25819bdc2b2d4c50': d8,
               '4c5f7eaf39944f88ea00a17df6211498e2dab3bfa6fb103f0962e7fa5d5cabbe': d10}
    for superseded, amendment in history.items():
        assert amendment['supersedes_sha256'] == superseded != digest
        copy_path = HERE / amendment['superseded_copy']
        assert hashlib.sha256(copy_path.read_bytes()).hexdigest() == superseded
    assert an.recorded_thresholds_sha256() == digest
    assert thresholds['expected_parameters']['manager.max_acc'] + thresholds['expected_parameters']['optimization.acc_tolerance'] == 1.5
    assert len(digest) == 64


def test_parse_log_handles_ansi_order_and_truncation():
    run = fixture_run('x')
    text, _ = log_text('original', run, [(0, 0, 'gate')])
    parsed = an.parse_log(text)
    assert parsed['calls'][0]['reason'] == 'acceleration_gate'
    assert parsed['calls'][0]['gate_value'] == 1.567 and parsed['legacy_result'] is False
    assert parsed['parameters']['manager.max_acc'] == 0.5
    truncated = text.split('SUITE_CALL_END')[0]
    assert an.parse_log(truncated)['calls'][0]['reason'] == 'no_end_marker'
    velocity = 'SUITE_CALL_BEGIN call=0 attempt=0\n[WARN] Dynamic feasibility failed: velocity at t=1 is 2 > 2\n' \
               'SUITE_CALL_END call=0 attempt=0 success=false\n'
    assert an.parse_log(velocity)['calls'][0]['reason'] == 'velocity_gate'
    unknown = 'SUITE_CALL_BEGIN call=0 attempt=0\nsomething\nSUITE_CALL_END call=0 attempt=0 success=false\n'
    assert an.parse_log(unknown)['calls'][0]['reason'] == 'unclassified'


def test_unclassified_rejection_is_an_integrity_failure(tmp_path):
    run_dir = build_run(tmp_path, passing_plan())
    path = run_dir / 'returned_artifacts/original/s__empty__poly.log'
    path.write_text(path.read_text().replace('[WARN]', '[INFO]').replace('Dynamic feasibility', 'Other')
                    .replace('This refined trajectory is unsafe', 'Unrelated'))
    returned = run_dir / 'returned_artifacts'
    hashes = {p.relative_to(returned).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in returned.rglob('*') if p.is_file() and p.name != 'artifact_hashes.json'}
    (returned / 'artifact_hashes.json').write_text(json.dumps(hashes))
    report, _ = an.analyze(run_dir)
    assert any('unclassified' in p for a in report['integrity']['anomalies'] for p in a['problems'])


def test_main_writes_outputs(tmp_path, capsys):
    run_dir = build_run(tmp_path, passing_plan())
    assert an.main(['--run-dir', str(run_dir)]) == 0
    report = json.loads((run_dir / 'comparison.json').read_text())
    assert report['passed'] and (run_dir / 'paths.json').is_file()
    table = (run_dir / 'comparison.md').read_text()
    assert '| AC2 | pass |' in table and '| follow_up | empty | poly_s0 | candidate | 2 | 2 |' in table
    assert 'scan_replan_fsm.cpp:893' in table and 'bspline_optimizer.cpp:1017-1018' in table
    assert 'planner_manager.cpp:460-464' in table
    assert report['boundary_notes'] == list(an.BOUNDARY_NOTES) and len(report['boundary_notes']) == 3
    assert [a['decision'][:3] for a in report['thresholds_amendments']] == ['D8 ', 'D10']
    assert json.loads(capsys.readouterr().out)['acceptance']['AC6'] == 'pass'
    changed = tmp_path / 'thresholds.json'
    changed.write_text('{}')
    assert an.main(['--run-dir', str(run_dir), '--thresholds', str(changed)]) == 2


def assert_invalid(report):
    assert report['validity'] == 'INVALID' and report['validity_control']['status'] == 'fail'
    assert {v['status'] for v in report['acceptance'].values()} == {'not_evaluated'}
    assert all('computed_but_unused' in v for v in report['acceptance'].values())
    assert not report['passed']


def test_control_fails_when_the_original_accepts_the_failed_resume(tmp_path):
    plan = passing_plan()
    run, calls = plan['failed_run_resume__empty__poly_s0_r1']
    plan['failed_run_resume__empty__poly_s0_r1'] = (run, dict(calls, original=[(0, 0, ok())]))
    report, _ = analyze(tmp_path, plan)
    assert_invalid(report)
    check = report['validity_control']['checks'][0]
    assert check['observed'] == ['acceleration_gate', 'accepted', 'acceleration_gate'] and not check['passed']


def test_control_fails_when_a_recorded_case_is_rejected(tmp_path):
    plan = passing_plan()
    run, calls = plan['successful_run_resume__empty__poly_s0_r2']
    plan['successful_run_resume__empty__poly_s0_r2'] = (run, dict(calls, original=[(0, 0, 'optimize')]))
    report, _ = analyze(tmp_path, plan)
    assert_invalid(report)
    assert report['validity_control']['checks'][3]['observed'][2] == 'rebound_optimization_failed'


def test_control_fails_when_the_rejection_is_not_the_gate(tmp_path):
    plan = passing_plan()
    run, calls = plan['failed_run_resume__empty__poly_s0_r0']
    plan['failed_run_resume__empty__poly_s0_r0'] = (run, dict(calls, original=[(0, 0, 'refine')]))
    report, _ = analyze(tmp_path, plan)
    assert_invalid(report)


def test_control_fails_when_control_runs_are_missing(tmp_path):
    plan = passing_plan()
    del plan['failed_run_initial__empty__poly_s0_r2']
    report, _ = analyze(tmp_path, plan)
    assert_invalid(report)
    assert report['validity_control']['checks'][1]['observed'] == ['accepted', 'accepted']
    plan = {k: v for k, v in passing_plan().items() if not k.startswith(CONTROL)}
    report, _ = analyze(tmp_path / 'none', plan)
    assert_invalid(report)


def test_invalid_suite_hides_passing_verdicts_in_outputs(tmp_path, capsys):
    plan = passing_plan()
    run, calls = plan['failed_run_resume__empty__poly_s0_r2']
    plan['failed_run_resume__empty__poly_s0_r2'] = (run, dict(calls, original=[(0, 0, ok())]))
    run_dir = build_run(tmp_path, plan)
    assert an.main(['--run-dir', str(run_dir)]) == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed['validity'] == 'INVALID' and set(printed['acceptance'].values()) == {'not_evaluated'}
    table = (run_dir / 'comparison.md').read_text()
    assert 'Validity: **INVALID**' in table and '| AC0 | fail |' in table and '| AC2 | not_evaluated |' in table
    assert '| AC2 | pass |' not in table
