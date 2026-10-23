import math
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from audit import Reader, analyze, main_band, project, pure_sign, yaw_intervals


def row(t, command=(0., 0., 0.), xy=(0., 0.), velocity=(0., 0.), yaw=0., number=None):
    return dict(t=t, c=list(command), p=list(xy), v=list(velocity), wz=.4, yaw=yaw,
                mode='RL', row=number if number is not None else int(t * 50) + 1)


class AuditTests(unittest.TestCase):
    def test_historical_source_identity_required(self):
        with tempfile.TemporaryDirectory() as directory:
            data = b'{"test": 3}\n'
            (Path(directory) / 'input.json').write_bytes(data)
            expected = {'input.json': {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}}
            self.assertEqual(Reader(directory, expected).consume('input.json'), {'test': 3})
            (Path(directory) / 'input.json').write_text('{"test": 4}\n')
            reader = Reader(directory, expected)
            with self.assertRaises(ValueError):
                reader.consume('input.json')
            self.assertFalse(reader.sources['input.json']['matches_historical'])

    def test_telemetry_projection_and_nonfinite_refusal(self):
        source = dict(physics_time_s=1., effective_command=[.1, 0, .3], stance_mode='RL',
                      body_sensor=dict(position=[1, 2, 3], linear_world=[.1, .2, .3],
                                       angular_world=[0, 0, .4], quaternion=[1, 0, 0, 0]))
        self.assertEqual(project(source, 9)['row'], 9)
        source['body_sensor']['linear_world'][0] = math.nan
        with self.assertRaises(ValueError):
            project(source, 9)

    def test_exact_boundaries_do_not_round(self):
        self.assertEqual([main_band(x) for x in [0, 1e-15, math.nextafter(.2, 0), .2, math.nextafter(.2, 1)]],
                         ['zero', 'below_0p2', 'below_0p2', 'exact_0p2', 'above_0p2'])

    def test_duration_weighting_and_inclusive_overlap(self):
        rows = [row(0, (.1, 0, 0), velocity=(.08, 0)), row(1, (.2, 0, 0), velocity=(.1, 0)),
                row(4, (.4, 0, 0), velocity=(.3, 0)), row(6)]
        r = analyze(rows, (0, 0), 0)
        self.assertAlmostEqual(r['low_inclusive_share'], 4 / 6)
        self.assertAlmostEqual(r['high_inclusive_share'], 5 / 6)
        self.assertAlmostEqual(sum(b['duration_s'] for b in r['bands'].values()), 6)
        self.assertAlmostEqual(r['bands']['below_0p2']['axis_tracking_ratio'], .8)
        self.assertAlmostEqual(r['bands']['exact_0p2']['duration_s'], 3)
        self.assertAlmostEqual(sum(b['duration_s'] for b in r['fine_bands'].values()), 6)

    def test_command_axis_rotation_and_opposite_motion(self):
        r = analyze([row(0, (.1, 0, 0), velocity=(.03, -.08), yaw=math.pi / 2), row(2)], (0, 0), 0)
        b = r['bands']['below_0p2']
        self.assertAlmostEqual(b['axis_tracking_ratio'], -.8)
        self.assertAlmostEqual(b['mean_transverse_mps'], .03)
        self.assertAlmostEqual(b['mean_body_speed_mps'], math.hypot(.03, .08))

    def test_ratio_of_integrals_not_mean_of_ratios(self):
        r = analyze([row(0, (.05, 0, 0), velocity=(.05, 0)), row(1, (.15, 0, 0), velocity=(0, 0)), row(4)], (0, 0), 0)
        self.assertAlmostEqual(r['bands']['below_0p2']['axis_tracking_ratio'], .1)

    def test_factory_zeros_excluded_and_fallback_clipped(self):
        rows = [row(0, xy=(2, 0)), row(2, (.3, 0, 0), xy=(2, 0)), row(8, xy=(2, 0)), row(12, xy=(2, 0))]
        r = analyze(rows, (0, 0), 2)
        self.assertEqual(r['window_kind'], 'fallback_before_first_zero')
        self.assertEqual(r['start_s'], 2)
        self.assertEqual(r['first_post_goal_zero_s'], 8)

    def test_circle_precedes_fallback_and_keeps_later_exit(self):
        rows = [row(0, xy=(1, 0)), row(10, xy=(.25, 0)), row(12, xy=(2, 0))]
        r = analyze(rows, (0, 0), 0)
        self.assertEqual((r['window_kind'], r['start_s'], r['end_s']), ('goal_circle', 10, 12))

    def test_no_navigation_or_window_is_unavailable(self):
        self.assertEqual(analyze([row(0)], (0, 0), None)['status'], 'unavailable')
        self.assertEqual(analyze([row(0, (.3, 0, 0), xy=(2, 0)), row(1, (.3, 0, 0), xy=(2, 0))], (0, 0), 0)['reason'],
                         'no_circle_entry_or_post_goal_zero')

    def test_invalid_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze([row(1), row(1)], (0, 0), 0)

    def test_residual_translation_is_not_pure_yaw(self):
        self.assertEqual(pure_sign(row(0, (1e-15, 0, .6))), 0)
        self.assertEqual(pure_sign(row(0, (0, 0, .6))), 1)
        self.assertEqual(pure_sign(row(0, (0, 0, 1e-10))), 0)

    def test_pure_yaw_sign_split_and_endpoint_drift(self):
        rows = [row(0, (0, 0, .3)), row(1, (0, 0, .6), xy=(.1, 0)),
                row(2, (0, 0, -.6), xy=(.2, 0)), row(3, xy=(.25, 0))]
        r = yaw_intervals(rows, 0, 3)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]['duration_s'], 2)
        self.assertAlmostEqual(r[0]['mean_command_yaw_radps'], .45)
        self.assertAlmostEqual(r[0]['max_xy_displacement_cm'], 20)
        self.assertAlmostEqual(r[1]['max_xy_displacement_cm'], 5)
        self.assertFalse(r[1]['right_censored'])

    def test_clipping_censoring_and_wrapped_heading(self):
        rows = [row(0, (0, 0, .6), yaw=3.), row(2, (0, 0, .6), xy=(.2, 0), yaw=-3.),
                row(4, (0, 0, .6), xy=(.4, 0), yaw=-2.8)]
        r = yaw_intervals(rows, 1, 4)[0]
        self.assertTrue(r['left_censored'])
        self.assertTrue(r['right_censored'])
        self.assertTrue(r['interpolated_boundary'])
        self.assertAlmostEqual(r['max_xy_displacement_cm'], 30)
        self.assertAlmostEqual(r['heading_change_rad'], (2 * math.pi - 6) / 2 + .2)

    def test_zero_duration_and_no_yaw_missingness(self):
        r = analyze([row(0)], (0, 0), 0)
        self.assertEqual(r['status'], 'zero_duration')
        self.assertIsNone(r['low_inclusive_share'])
        self.assertIsNone(r['pure_yaw_max_displacement_cm'])
        p = yaw_intervals([row(0, (0, 0, .6))], 0, 0)[0]
        self.assertEqual(p['duration_s'], 0)
        self.assertIsNone(p['mean_command_yaw_radps'])


if __name__ == '__main__':
    unittest.main()
