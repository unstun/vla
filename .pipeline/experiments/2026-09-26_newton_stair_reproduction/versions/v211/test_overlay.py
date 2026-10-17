import copy
import unittest
import numpy as np
from curve_overlay import Selection, sample_spline


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.data = dict(traj_id=1, order=3, start_time={'sec': 10, 'nanosec': 0},
                         pos_pts=[dict(x=float(i), y=0., z=.3) for i in range(4)],
                         knots=[float(i) for i in range(-3, 5)], emergency_stop=False)
        self.selection = Selection()

    def event(self, kind, data, wall=20., sim=10.):
        return dict(event=kind, data=copy.deepcopy(data), host_wall_s=wall, clock_ns=round(sim*1e9))

    def command(self, vx=1., wall=20., sim=10.):
        self.selection.consume(self.event('gated_command',
            dict(linear=dict(x=vx, y=0., z=0.), angular=dict(x=0., y=0., z=0.)), wall, sim))

    def curve(self, data=None, wall=20.):
        self.selection.consume(self.event('bspline', data or self.data, wall))

    def test_direct_spline_without_p2b_identity(self):
        self.curve(); self.command()
        self.assertEqual(self.selection.current(10.05, 20.05)['data']['traj_id'], 1)
        self.assertIsNone(self.selection.current(9.99, 20.05))
        self.assertIsNone(self.selection.current(10.05, 19.99))

    def test_latest_trajectory_replaces_prior_curve(self):
        self.curve(); self.command()
        data = dict(self.data, traj_id=2)
        self.curve(data)
        self.assertEqual(self.selection.current(10.05, 20.05)['data']['traj_id'], 2)
        self.assertEqual(set(self.selection.curves), {1, 2})

    def test_emergency_stop_clears_until_new_curve(self):
        self.curve(); self.command()
        self.curve(dict(self.data, traj_id=2, emergency_stop=True))
        self.assertIsNone(self.selection.current(10.05, 20.05))
        self.command()
        self.assertIsNone(self.selection.current(10.05, 20.05))
        self.curve(dict(self.data, traj_id=3))
        self.assertEqual(self.selection.current(10.05, 20.05)['data']['traj_id'], 3)

    def test_missing_or_stale_direct_command_hides_curve(self):
        self.curve()
        self.assertIsNone(self.selection.current(10.05, 20.05))
        self.command()
        self.assertIsNone(self.selection.current(10.05, 20.16))
        self.assertIsNone(self.selection.current(10.16, 20.05))

    def test_zero_command_with_active_tracking_window(self):
        self.curve(); self.command(vx=0.)
        self.assertIsNotNone(self.selection.current(10.05, 20.05))
        self.command(vx=0., wall=21.05, sim=11.05)
        self.assertIsNone(self.selection.current(11.05, 21.05))

    def test_nonzero_command_has_only_bounded_end_grace(self):
        self.curve(); self.command(wall=21.05, sim=11.05)
        self.assertIsNotNone(self.selection.current(11.05, 21.05))
        self.command(wall=21.16, sim=11.16)
        self.assertIsNone(self.selection.current(11.16, 21.16))

    def test_old_curve_wall_event_cannot_revive_with_fresh_commands(self):
        self.curve(); self.command(wall=24., sim=10.5)
        self.assertIsNone(self.selection.current(10.5, 24.))

    def test_future_command_is_not_tracking_evidence(self):
        self.curve(); self.command(wall=20.1, sim=10.1)
        self.assertIsNone(self.selection.current(10.05, 20.05))

    def test_route_is_causal_and_empty_route_replaces_prior(self):
        self.selection.consume(self.event('pct_route', dict(poses=[{'pose': 1}])))
        self.assertIsNone(self.selection.current_route(9.99, 20.05))
        self.assertIsNone(self.selection.current_route(10.05, 19.99))
        self.assertIsNotNone(self.selection.current_route(10.05, 20.05))
        self.selection.consume(self.event('pct_route', dict(poses=[])))
        self.assertEqual(self.selection.current_route(10.05, 20.05)['data']['poses'], [])

    def test_recorded_spline_has_expected_endpoints(self):
        points = sample_spline(self.data)
        np.testing.assert_allclose(points[[0, -1]], [[1, 0, .3], [2, 0, .3]], atol=1e-6)
        self.data['knots'][4] = self.data['knots'][3]
        with self.assertRaises(ValueError):
            sample_spline(self.data)


if __name__ == '__main__':
    unittest.main()
