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


mf = load('make_fixtures')
JOURNALS_PRESENT = all((mf.EXPERIMENT / returned / 'pilot_journal.json').is_file() for _, returned in mf.FAILED_DISPLAY_RUNS)
DIAGNOSIS_RUNS = {
    'two_goal_20260916T162236Z_p2b_actual4': mf.EXPERIMENT / 'isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4/returned_artifacts',
    'pointcloud_20260916T173400Z_rviz_gpu': mf.EXPERIMENT / 'pointcloud_display/runs/pointcloud_20260916T173400Z_rviz_gpu/returned_artifacts',
}


@pytest.fixture(scope='module')
def suite():
    return mf.generate()


def test_counts_match_the_plan(suite):
    doc, boxes = suite
    counts = doc['counts']
    assert counts['starts'] == 21 and counts['inits'] == 13 and counts['maps'] == 3
    assert counts['single_runs_per_build'] == 21 * 13 * 3 == 819
    assert counts['follow_up_runs_per_build'] == 15
    assert counts['process_runs_per_build'] == 834 and counts['process_runs_total_two_builds'] == 1668
    assert counts['follow_up_steps_per_build'] == 30
    assert len(boxes) == counts['box_files'] == 42
    assert sorted(r['label'] for r in doc['runs'] if r['dump_samples']) == sorted(mf.DUMP_RUN_LABELS)
    groups = [s['group'] for s in doc['starts']]
    assert groups.count('recorded_diagnosis') == 4
    assert groups.count('recorded_failed_stop') == 2
    assert groups.count('stop_position_sweep') == 15
    follow = [r for r in doc['runs'] if r['kind'] == 'follow_up']
    assert {r['start_group'] for r in follow} == {'stop_position_sweep'}
    assert all(r['map_id'] == 'empty' and r['init_id'] == 'poly_s0_r0' and r['follow_up_offsets_s'] == [0.3, 0.6]
               for r in follow)


def test_initializations(suite):
    doc, _ = suite
    inits = doc['inits']
    assert [i['id'] for i in inits[:3]] == ['poly_s0_r0', 'poly_s0_r1', 'poly_s0_r2']
    assert all(not i['random_poly'] and i['seed'] == 0 for i in inits[:3])
    assert [i['seed'] for i in inits[3:]] == list(range(10))
    assert all(i['random_poly'] and i['poly_init'] for i in inits[3:])


def test_generation_is_deterministic_and_matches_frozen_files(tmp_path):
    first = mf.write_outputs(tmp_path / 'a', *mf.generate())
    second = mf.write_outputs(tmp_path / 'b', *mf.generate())
    assert first == second
    for name, digest in first.items():
        frozen = HERE / 'fixtures' / name
        assert frozen.is_file(), name
        assert hashlib.sha256(frozen.read_bytes()).hexdigest() == digest, name


def test_every_start_has_provenance(suite):
    doc, _ = suite
    for start in doc['starts']:
        provenance = start['provenance']
        assert provenance['derivation'] and provenance['velocity_source']
        assert 'source_run' in provenance or 'base_source_run' in provenance
    failed = [s for s in doc['starts'] if s['group'] == 'recorded_failed_stop']
    for start in failed:
        artifacts = start['provenance']['source_artifacts']
        assert len(artifacts) == 2 and all(len(a['sha256']) == 64 for a in artifacts)
        assert start['provenance']['nominal_body_height_m'] == 0.35
    diagnosis = [s for s in doc['starts'] if s['group'] == 'recorded_diagnosis']
    assert all(s['provenance']['fixture_sha256'] == mf.DIAGNOSIS_CASES_SHA256 for s in diagnosis)
    assert doc['sources']['planner_yaml']['sha256'] == mf.PLANNER_YAML_SHA256


def test_sweep_poses(suite):
    doc, _ = suite
    base = next(s for s in doc['starts'] if s['id'] == 'failed_run_resume')
    sweep = [s for s in doc['starts'] if s['group'] == 'stop_position_sweep']
    assert [s['start'][0] for s in sweep] == [x / 100.0 for x in range(-120, -105)]
    assert sweep[0]['id'] == 'sweep_x_m1p20' and sweep[-1]['id'] == 'sweep_x_m1p06'
    assert all(s['start'][1:] == base['start'][1:] and s['target'] == base['target'] for s in sweep)


def test_recorded_failed_stop_poses(suite):
    doc, _ = suite
    starts = {s['id']: s for s in doc['starts']}
    assert starts['failed_off_resume']['start'][0] == pytest.approx(-1.1297621726989746)
    assert starts['failed_rviz_resume']['start'][0] == pytest.approx(-1.1488862037658691)
    assert starts['failed_off_resume']['start'][2] == 1.51266028881073 + 0.35
    assert starts['failed_off_resume']['target'] == starts['failed_run_resume']['target']


def test_box_geometry(suite):
    doc, boxes = suite
    geometry = doc['planner_params']
    lo_map = geometry['map_origin_m']
    hi_map = [o + s for o, s in zip(lo_map, geometry['map_size_m'])]
    for path, box_doc in boxes.items():
        box = box_doc['boxes'][0]
        derivation = box_doc['derivation']
        assert all(lo_map[k] < box['min'][k] < box['max'][k] < hi_map[k] for k in range(3))
        assert derivation['straight_route_to_box_xy_m'] > 0.0
        if path.endswith('__near_box.json'):
            assert derivation['straight_route_within_inflation_reach']
            assert 0.1 < derivation['straight_route_to_box_xy_m'] < 0.25
        else:
            assert not derivation['straight_route_within_inflation_reach']
            assert derivation['straight_route_to_box_xy_m'] > 0.8
        assert doc['boxes'][path]['sha256'] == hashlib.sha256(mf.dumps(box_doc).encode()).hexdigest()
    runs = [r for r in doc['runs'] if r['map_id'] != 'empty']
    assert all(r['occupied_boxes'] == 'boxes/%s__%s.json' % (r['start_id'], r['map_id']) for r in runs)


def test_segment_rectangle_distance():
    assert mf.segment_rectangle_distance((0, 0), (2, 0), (0.5, 0.3), (1.0, 0.6)) == pytest.approx(0.3)
    assert mf.segment_rectangle_distance((0, 0), (2, 0), (0.5, -0.1), (1.0, 0.6)) == 0.0
    assert mf.segment_rectangle_distance((0, 0), (2, 0), (3.0, 0.0), (4.0, 1.0)) == pytest.approx(1.0)


def stop_record(**overrides):
    record = {
        'source_run': 'run_x', 'source_request_id': 'run_x-goal-a-attempt-2',
        'start_ground_xyz_m': [-1.0, -4.5, 1.5], 'route_last_waypoint_m': [0.35, -4.48, 1.91],
        'nominal_body_height_m': 0.35, 'source_artifacts': [],
    }
    record.update(overrides)
    return record


def test_case_from_stop_record():
    case = mf.case_from_stop_record(stop_record(), 'x', 'recorded_isaac_stop')
    assert case['start'] == [-1.0, -4.5, 1.5 + 0.35]
    assert case['target'] == [0.35, -4.48, 1.91]
    assert case['start_velocity'] == case['start_acceleration'] == case['target_velocity'] == [0.0, 0.0, 0.0]
    with pytest.raises(mf.FixtureError):
        mf.case_from_stop_record(stop_record(nominal_body_height_m=float('nan')), 'x', 'g')
    with pytest.raises(mf.FixtureError):
        mf.case_from_stop_record(stop_record(start_ground_xyz_m=[1.0, 2.0]), 'x', 'g')


@pytest.mark.skipif(not all((d / 'pilot_journal.json').is_file() for d in DIAGNOSIS_RUNS.values()),
                    reason='local-only pilot journals are absent')
def test_journal_derivation_reproduces_diagnosis_cases():
    cases = {c['source_request_id']: c for c in json.loads(mf.DIAGNOSIS_CASES.read_text())['cases']}
    checked = 0
    for returned in DIAGNOSIS_RUNS.values():
        for record in mf.resume_records_from_run(returned, request_kind='all'):
            if record['source_request_id'] not in cases:
                continue
            expected = cases[record['source_request_id']]
            case = mf.case_from_stop_record(record, expected['id'], 'check')
            assert case['start'] == expected['start']
            assert case['target'] == expected['target']
            checked += 1
    assert checked == 4


@pytest.mark.skipif(not JOURNALS_PRESENT, reason='local-only pilot journals are absent')
def test_recorded_requests_match_journals():
    frozen = (HERE / 'fixtures/recorded_requests.json').read_text()
    assert mf.dumps(mf.recorded_requests_doc()) == frozen


def make_returned(tmp_path, journal_hash=None):
    returned = tmp_path / 'two_goal_x' / 'returned_artifacts'
    returned.mkdir(parents=True)
    entry = {
        'request_id': 'two_goal_x-goal-a-attempt-2', 'goal_id': 'goal-a', 'ok': True, 'route_id': 'pct:goal-a:1',
        'request': {'start_xyz_m': [-1.2, -4.5, 1.51], 'target_xyz_m': [0.39, -4.46, 1.56]},
        'waypoints_m': [[-1.1, -4.49, 1.91], [0.3546, -4.4868, 1.9105]],
        'z_semantics': 'lite3_body_reference_no_display_offset',
    }
    first = dict(entry, request_id='two_goal_x-goal-a-attempt-1')
    goal_b = dict(entry, request_id='two_goal_x-goal-b')
    journal = {'events': [{'event': 'state_poll', 'state': {'pct': {'plan_history': [first]}}},
                          {'event': 'state_poll', 'state': {'pct': {'plan_history': [first, entry, goal_b]}}}]}
    (returned / 'pilot_journal.json').write_text(json.dumps(journal))
    digest = journal_hash or hashlib.sha256((returned / 'pilot_journal.json').read_bytes()).hexdigest()
    (returned / 'artifact_hashes.json').write_text(json.dumps({'pilot_journal.json': digest}))
    (returned / 'resolved_backend_config.json').write_text(
        json.dumps({'resolved_config': {'map': {'nominal_body_height_m': 0.35}}}))
    return returned


def test_from_journals_builds_replay_fixture(tmp_path):
    returned = make_returned(tmp_path)
    doc, boxes = mf.from_journals([returned])
    assert boxes == {}
    control = ['successful_run_initial', 'successful_run_resume', 'failed_run_initial', 'failed_run_resume']
    assert [s['id'] for s in doc['starts']] == control + ['two_goal_x__goal_a_attempt_2']
    start = doc['starts'][-1]
    assert start['group'] == 'recorded_isaac_stop'
    assert start['start'] == [-1.2, -4.5, 1.51 + 0.35] and start['target'] == [0.3546, -4.4868, 1.9105]
    assert [r['init_id'] for r in doc['runs'][-3:]] == ['poly_s0_r0', 'poly_s0_r1', 'poly_s0_r2']
    assert len(doc['runs']) == 15 and {r['map_id'] for r in doc['runs']} == {'empty'}
    full, full_boxes = mf.from_journals([returned], full_matrix=True)
    assert len(full['runs']) == 5 * 39 and len(full_boxes) == 10
    everything, _ = mf.from_journals([returned], request_kind='all')
    assert len(everything['starts']) == 7
    hashes = mf.write_outputs(tmp_path / 'out', doc, boxes)
    assert (tmp_path / 'out/suite_cases.json').is_file() and set(hashes) == {'suite_cases.json'}


def test_from_journals_refuses_unverified_journal(tmp_path):
    returned = make_returned(tmp_path, journal_hash='0' * 64)
    with pytest.raises(mf.FixtureError):
        mf.from_journals([returned])


def test_write_outputs_refuses_to_overwrite_differing_files(tmp_path):
    doc, boxes = mf.from_journals([make_returned(tmp_path)])
    mf.write_outputs(tmp_path / 'out', doc, boxes)
    mf.write_outputs(tmp_path / 'out', doc, boxes)
    changed = dict(doc, purpose='changed')
    with pytest.raises(mf.FixtureError):
        mf.write_outputs(tmp_path / 'out', changed, boxes)
    mf.write_outputs(tmp_path / 'out', changed, boxes, force=True)


def test_generate_refuses_changed_inputs(tmp_path):
    cases = tmp_path / 'cases.json'
    cases.write_text(mf.DIAGNOSIS_CASES.read_text() + ' ')
    with pytest.raises(mf.FixtureError):
        mf.generate(cases_path=cases)
