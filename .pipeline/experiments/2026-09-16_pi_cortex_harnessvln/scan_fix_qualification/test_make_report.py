import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('test_' + name, str(HERE / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mr = load('make_report')


def upper_tail(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


class BinomialBoundTest(unittest.TestCase):
    def test_design_values(self):
        self.assertAlmostEqual(mr.binomial_lower_bound(8, 8), 0.688, places=3)
        self.assertAlmostEqual(mr.binomial_lower_bound(7, 8), 0.529, places=3)
        self.assertAlmostEqual(mr.binomial_lower_bound(6, 8), 0.400, places=3)

    def test_edges(self):
        self.assertIsNone(mr.binomial_lower_bound(0, 0))
        self.assertEqual(mr.binomial_lower_bound(0, 8), 0.0)
        self.assertAlmostEqual(mr.binomial_lower_bound(1, 1), 0.05, places=12)
        with self.assertRaises(ValueError):
            mr.binomial_lower_bound(9, 8)

    def test_bound_solves_the_tail_equation(self):
        for k, n in ((5, 7), (6, 7), (3, 8), (1, 5)):
            bound = mr.binomial_lower_bound(k, n)
            self.assertAlmostEqual(upper_tail(k, n, bound), 0.05, places=9)


class LedgerTest(unittest.TestCase):
    def write(self, text):
        handle = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_series_end_and_blank_lines_are_not_episodes(self):
        path = self.write('\n'.join([
            json.dumps({'episode': 1, 'run_id': 'r1', 'outcome': 'passed'}),
            '',
            json.dumps({'episode': 2, 'run_id': 'r2', 'outcome': 'review_failed'}),
            json.dumps({'series_end_utc': '2026-09-17T10:00:00Z', 'host_after': {'ok': True}}),
        ]) + '\n')
        episodes, ends = mr.parse_ledger(path)
        self.assertEqual([e['episode'] for e in episodes], [1, 2])
        self.assertEqual([e['ledger_line'] for e in episodes], [1, 3])
        self.assertEqual(len(ends), 1)
        self.assertEqual(ends[0]['ledger_line'], 4)

    def test_bad_lines_are_refused(self):
        with self.assertRaises(mr.ReportError):
            mr.parse_ledger(self.write('{"episode": 1}\nnot json\n'))
        with self.assertRaises(mr.ReportError):
            mr.parse_ledger(self.write('{"run_id": "r1", "outcome": "passed"}\n'))


def episode(index, outcome, problems=()):
    return {'episode': index, 'run_id': 'r%d' % index, 'outcome': outcome, 'ledger_line': index,
            'problems': list(problems)}


PLANNED = [{'episode': i, 'trigger_m': 0.4} for i in range(1, 9)]


class SeriesSummaryTest(unittest.TestCase):
    def test_running_series_counts_and_bound(self):
        summary = mr.series_summary([episode(1, 'passed'), episode(2, 'host_not_idle')], [], PLANNED)
        self.assertEqual(summary['status'], 'in_progress')
        self.assertEqual((summary['counted_episodes'], summary['passed_episodes']), (1, 1))
        self.assertAlmostEqual(summary['success_lower_bound'], 0.05, places=4)
        self.assertEqual([u['outcome'] for u in summary['uncounted']], ['host_not_idle'])

    def test_failure_and_completion(self):
        eight = [episode(i, 'passed') for i in range(1, 9)]
        self.assertEqual(mr.series_summary(eight, [{'ledger_line': 9}], PLANNED)['status'], 'pass')
        self.assertEqual(mr.series_summary(eight, [], PLANNED)['status'], 'in_progress')
        failed = eight[:2] + [episode(3, 'review_failed')]
        summary = mr.series_summary(failed, [], PLANNED)
        self.assertEqual(summary['status'], 'fail')
        self.assertEqual(summary['failed_episodes'], 1)
        self.assertEqual(mr.series_summary(eight[:3], [{'ledger_line': 4}], PLANNED)['status'], 'incomplete')

    def test_integrity_problem_needs_review(self):
        summary = mr.series_summary([episode(1, 'passed', ['recomputed review differs'])], [], PLANNED)
        self.assertEqual(summary['status'], 'needs_review')


SWEEP = [(-1.20, 'accepted'), (-1.19, 'acceleration_gate'), (-1.18, 'acceleration_gate'),
         (-1.17, 'acceleration_gate'), (-1.16, 'accepted')]


def sweep_points():
    return [{'x': x, 'group': 'stop_position_sweep',
             'builds': {'original': {'reasons': {reason: 3}}, 'candidate': {'reasons': {'accepted': 3}}}}
            for x, reason in SWEEP]


class FailureBandTest(unittest.TestCase):
    def test_band_edges_and_positions(self):
        band = mr.failure_band(sweep_points())
        self.assertEqual(len(band['segments']), 1)
        segment = band['segments'][0]
        self.assertEqual((segment['first_rejected_x'], segment['last_rejected_x']), (-1.19, -1.17))
        self.assertAlmostEqual(segment['shade_from_x'], -1.195)
        self.assertAlmostEqual(segment['shade_to_x'], -1.165)
        self.assertEqual(mr.band_position(-1.18, band), 'inside')
        self.assertEqual(mr.band_position(-1.167, band), 'edge')
        self.assertEqual(mr.band_position(-1.162, band), 'outside')
        self.assertEqual(mr.band_position(-1.10, band), 'beyond_sweep')
        self.assertEqual(band['sweep_range_x'], [-1.20, -1.16])
        self.assertIsNone(mr.band_position(None, band))

    def test_mixed_repeats_are_not_in_the_band(self):
        points = sweep_points()
        points[2]['builds']['original']['reasons'] = {'acceleration_gate': 2, 'accepted': 1}
        band = mr.failure_band(points)
        self.assertEqual([(s['first_rejected_x'], s['last_rejected_x']) for s in band['segments']],
                         [(-1.19, -1.19), (-1.17, -1.17)])


def replay_report(run_id):
    rows = []
    for build, reason in (('original', 'acceleration_gate'), ('candidate', 'accepted')):
        for repeat in range(3):
            accepted = reason == 'accepted'
            rows.append({'kind': 'single', 'map_id': 'empty', 'random_poly': False, 'build': build,
                         'start_id': run_id + '__goal_a_attempt_2', 'repeat': repeat, 'accepted': accepted,
                         'reason': reason, 'gate_value': None if accepted else 1.55,
                         'calls': [{'call': 0, 'success': accepted, 'max_acc': 0.59 if accepted else None,
                                    'endpoint_xy_m': 0.03 if accepted else None}]})
    fixtures = {'starts': [{'id': run_id + '__goal_a_attempt_2', 'group': 'recorded_isaac_stop',
                            'start': [-1.13, -4.5, 1.86],
                            'provenance': {'source_run': run_id, 'source_request_id': run_id + '-goal-a-attempt-2'}}]}
    return {'rows': rows}, fixtures


def table_episode(run_id='two_goal_x_scanfix_e01'):
    facts = {'still_pose_xyz': [-1.1375, -4.50, 1.86], 'cancel_terminal_xyz': [-1.134, -4.50, 1.86],
             'resume_plan_start_xyz': [-1.1375, -4.50, 1.51], 'measured_cancel_displacement_m': 0.417,
             'checks_passed': 41, 'checks_total': 41, 'failed_checks': [], 'stop_windows': [],
             'arrivals': {'goal-a': {'xy_error_m': 0.186}, 'goal-b': {'xy_error_m': 0.187}},
             'max_nonfoot_force_n': 0.0, 'runner_wall_seconds': 22.1, 'sim_seconds': 16.4, 'gpu_peak_mib': 7136.0}
    return {'episode': 1, 'run_id': run_id, 'outcome': 'passed', 'counted': True, 'trigger_m': 0.4,
            'facts': facts, 'host_run_wall_s': 128.9, 'walk_video': 'videos/e01.mp4', 'problems': []}


class ReplayAndTableTest(unittest.TestCase):
    def test_verdicts_are_keyed_by_run_id(self):
        report, fixtures = replay_report('two_goal_x_scanfix_e01')
        verdicts = mr.replay_verdicts(report, fixtures, ['two_goal_x_scanfix_e01', 'other_run'])
        self.assertEqual(set(verdicts), {'two_goal_x_scanfix_e01'})
        self.assertEqual(verdicts['two_goal_x_scanfix_e01']['verdict'],
                         {'original': 'acceleration_gate 3/3', 'candidate': 'accepted 3/3'})

    def test_pending_without_a_replay_run(self):
        band = mr.failure_band(sweep_points())
        row = mr.episode_table([table_episode()], None, band)[0]
        self.assertEqual(row['native_verdict_at_stop'], 'pending')
        self.assertEqual(row['stop_x_m'], -1.1375)
        self.assertEqual(row['cancel_terminal_x_m'], -1.134)
        self.assertEqual((row['checks_passed'], row['checks_total']), (41, 41))
        self.assertEqual(row['walk_video'], 'videos/e01.mp4')

    def test_replay_verdict_and_invalid_replay(self):
        report, fixtures = replay_report('two_goal_x_scanfix_e01')
        verdicts = mr.replay_verdicts(report, fixtures, ['two_goal_x_scanfix_e01'])
        replay = {'run_id': 'native_replay_1', 'validity': 'VALID', 'verdicts': verdicts}
        row = mr.episode_table([table_episode()], replay, mr.failure_band(sweep_points()))[0]
        self.assertEqual(row['native_verdict_at_stop'], {'original (scan_03)': 'acceleration_gate 3/3',
                                                         'fixed (scan_04)': 'accepted 3/3'})
        replay['validity'] = 'INVALID'
        row = mr.episode_table([table_episode()], replay, mr.failure_band(sweep_points()))[0]
        self.assertEqual(row['native_verdict_at_stop'], 'replay INVALID (AC0 failed)')
        row = mr.episode_table([table_episode('another_run')], dict(replay, validity='VALID'),
                               mr.failure_band(sweep_points()))[0]
        self.assertEqual(row['native_verdict_at_stop'], 'not in replay native_replay_1')


class PartialPackageTest(unittest.TestCase):
    def test_uncounted_partial_package_is_listed_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'r9' / 'returned_artifacts').mkdir(parents=True)
            entry = {'episode': 9, 'run_id': 'r9', 'outcome': 'execute_failed', 'ledger_line': 10,
                     'cancel_displacement_m': 0.4}
            record = mr.episode_facts(entry, mr.InputLog(), tmp)
            self.assertIsNone(record['facts'])
            self.assertFalse(record['counted'])
            self.assertEqual(len(record['problems']), 1)
            self.assertIn('not reviewable', record['problems'][0])
            summary = mr.series_summary([record], [], PLANNED)
            self.assertEqual(summary['uncounted'][0]['outcome'], 'execute_failed')
            self.assertEqual(summary['status'], 'needs_review')
            row = mr.episode_table([dict(record, walk_video=None)], None, mr.failure_band(sweep_points()))[0]
            self.assertIsNone(row['stop_x_m'])

    def test_counted_partial_package_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'r9' / 'returned_artifacts').mkdir(parents=True)
            entry = {'episode': 9, 'run_id': 'r9', 'outcome': 'review_failed', 'ledger_line': 10}
            with self.assertRaises(mr.ReportError):
                mr.episode_facts(entry, mr.InputLog(), tmp)


class CriteriaTest(unittest.TestCase):
    def test_multiline_checkboxes(self):
        text = '\n'.join([
            '## Acceptance Criteria',
            '',
            '- [x] AC0 Validity control: the original build must reproduce',
            '      the recorded failure. Passed in `run_a` (2026-09-17).',
            '- [ ] AC7 Isaac: every approved episode passes',
            '      the 41 checks.',
            '',
            '## Out of Scope',
            '- [x] not a criterion',
        ])
        items = mr.parse_criteria(text)
        self.assertEqual([(i['id'], i['checked']) for i in items], [('AC0', True), ('AC7', False)])
        self.assertEqual(items[0]['requirement'], 'Validity control: the original build must reproduce the recorded failure.')
        self.assertEqual(items[0]['prd_evidence'], 'Passed in `run_a` (2026-09-17).')
        self.assertIsNone(items[1]['prd_evidence'])
        self.assertTrue(items[1]['requirement'].endswith('the 41 checks.'))

    def test_real_prd_lists_ac0_to_ac8(self):
        if not mr.PRD.is_file():
            self.skipTest('task PRD absent')
        ids = [i['id'] for i in mr.parse_criteria(mr.PRD.read_text())]
        self.assertEqual(ids, ['AC%d' % i for i in range(9)])


class VoxelTest(unittest.TestCase):
    def test_box_voxels_match_the_recorded_harness_line(self):
        box = {'min': [-0.54614, -4.342744, 1.0], 'max': [-0.24614, -4.042744, 3.0]}
        self.assertEqual(mr.box_voxel_range(box, 0.05), ([-11, -87, 20], [-6, -82, 59]))

    def test_inflation_offsets_are_strictly_inside_the_radius(self):
        cells = mr.inflated_cells([0, 0, 0], [0, 0, 0], 0.05, 0.25)
        self.assertIn((4, 0), cells)
        self.assertIn((3, 3), cells)
        self.assertNotIn((5, 0), cells)
        self.assertNotIn((4, 3), cells)
        self.assertEqual(len(cells), sum(1 for x in range(-5, 6) for y in range(-5, 6) if x * x + y * y < 25))
        self.assertEqual(mr.voxel_of((-0.001, 0.049), 0.05), (-1, 0))
        self.assertEqual(mr.cells_distance((0.02, 0.02), {(0, 0)}, 0.05), 0.0)
        self.assertAlmostEqual(mr.cells_distance((0.08, 0.02), {(0, 0)}, 0.05), 0.03)


class OutputGuardTest(unittest.TestCase):
    def test_refuses_evidence_trees(self):
        with self.assertRaises(mr.ReportError):
            mr.check_output(mr.EXP / 'isaac_runner/two_goal_runs/some_run/report')
        with self.assertRaises(mr.ReportError):
            mr.check_output(mr.HERE / 'runs')
        self.assertEqual(mr.check_output(mr.OUTPUT), mr.OUTPUT.resolve())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class EndToEndTest(unittest.TestCase):
    def test_real_inputs_into_a_temporary_directory(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest('matplotlib unavailable')
        needed = [mr.SUITE_RUN / 'comparison.json', mr.LEDGER] + [run for _, run in mr.OLD_RUNS]
        if not all(Path(p).exists() for p in needed):
            self.skipTest('real report inputs absent')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'report'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mr.main(['--output', str(output)]), 0)
            data = json.loads((output / 'report_data.json').read_text())
            episodes, _ = mr.parse_ledger(mr.LEDGER)
            table = data['panels']['7_episode_table']
            self.assertGreaterEqual(len(table), 1)
            self.assertLessEqual(len(table), len(episodes))
            self.assertEqual([r['episode'] for r in table], [e['episode'] for e in episodes[:len(table)]])
            self.assertTrue(all(r['native_verdict_at_stop'] == 'pending' for r in table))
            self.assertIsNone(data['stop_replay'])
            verdicts = {v['id']: v['status'] for v in data['panels']['1_verdicts']}
            self.assertEqual([verdicts['AC%d' % i] for i in range(7)], ['pass'] * 7)
            self.assertEqual(verdicts['AC8'], 'pending')
            series = data['isaac_series']
            counted = [r for r in table if r['counted']]
            self.assertEqual(series['counted_episodes'], len(counted))
            self.assertEqual(series['passed_episodes'], sum(r['outcome'] == 'passed' for r in counted))
            self.assertEqual(series['success_lower_bound'],
                             round(mr.binomial_lower_bound(series['passed_episodes'], len(counted)), 4))
            figures = [o for o in data['outputs'] if o['kind'] == 'figure']
            self.assertEqual(sorted({o['panel'] for o in figures}), ['2', '3', '4', '5', '6', '8', '9'])
            for item in data['outputs']:
                self.assertEqual(sha256(item['path']), item['sha256'])
            for item in [o for o in data['outputs'] if o['kind'] == 'video']:
                source = mr.REPO / item['source']
                self.assertEqual(sha256(source), item['sha256'])
            self.assertTrue(all(len(i['sha256']) == 64 for i in data['inputs']))
            read = {i['path'] for i in data['inputs']}
            self.assertIn(mr.rel(mr.LEDGER), read)
            self.assertIn(mr.rel(mr.SUITE_RUN / 'comparison.json'), read)
            self.assertFalse(any('clouds.jsonl' in p or 'third_person_master.mp4' in p for p in read))
            band = data['panels']['2_where_the_bug_bites']['failure_band']['segments']
            self.assertEqual([(s['first_rejected_x'], s['last_rejected_x']) for s in band], [(-1.19, -1.11)])
            old = {r['label']: r for r in data['sep16_runs']}
            self.assertTrue(old['actual4']['review_passed'])
            self.assertFalse(any(old[k]['review_passed'] for k in ('display off', 'RViz', 'RViz GPU')))
            self.assertTrue(all(r['native_fixture'] is None or r['native_fixture']['equals_resume_plan_start_x']
                                for r in old.values()))


if __name__ == '__main__':
    unittest.main()
