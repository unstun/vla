import unittest

import numpy as np

from tic_vla_lite3.trajectory_adapter import AdapterConfig, TrajectoryAdapter


def path(y_end=0.0):
    return np.stack((np.linspace(0.0, 3.0, 30), np.linspace(0.0, y_end, 30)), axis=1)


class AdapterTest(unittest.TestCase):
    def test_straight_left_right_and_caps(self):
        straight = TrajectoryAdapter().adapt(path(), 1, 1.0, 1.0)
        left = TrajectoryAdapter().adapt(path(1.0), 1, 1.0, 1.0)
        right = TrajectoryAdapter().adapt(path(-1.0), 1, 1.0, 1.0)
        self.assertTrue(straight.valid)
        self.assertEqual(straight.vy_mps, 0.0)
        self.assertGreater(left.wz_radps, 0.0)
        self.assertLess(right.wz_radps, 0.0)
        for result in (straight, left, right):
            self.assertLessEqual(result.vx_mps, 0.30)
            self.assertLessEqual(abs(result.wz_radps), 0.20)

    def test_first_heading_filter_matches_upstream_initialization(self):
        adapter = TrajectoryAdapter(AdapterConfig(
            yaw_feedforward_gain=0.0, yaw_feedback_gain=0.8,
            wz_abs_max_radps=1.0))
        result = adapter.adapt(path(0.1), 1, 1.0, 1.0)
        points = path(0.1)
        segments = np.linalg.norm(np.diff(points, axis=0), axis=1)
        index = int(np.clip(np.searchsorted(
            np.concatenate(([0.0], np.cumsum(segments))), 1.0, side="left"),
                            2, 27))
        expected = 0.8 * np.arctan2(points[index, 1], points[index, 0])
        self.assertAlmostEqual(result.wz_radps, expected)

    def test_rejections_do_not_advance_sequence(self):
        adapter = TrajectoryAdapter()
        cases = [np.zeros((2, 2)), np.full((30, 2), np.nan), np.zeros((30, 2))]
        for sequence, value in enumerate(cases, 1):
            self.assertFalse(adapter.adapt(value, sequence, 1.0, 1.0).valid)
        self.assertTrue(adapter.adapt(path(), 1, 1.0, 1.0).valid)
        self.assertEqual(adapter.adapt(path(), 1, 1.0, 1.0).reason, "sequence")

    def test_stale_discontinuous_and_slew(self):
        adapter = TrajectoryAdapter(AdapterConfig(vx_slew_mps2=0.1, wz_slew_radps2=0.1))
        self.assertEqual(adapter.adapt(path(), 1, 0.0, 1.0).reason, "stale")
        broken = path(); broken[10] += 10.0
        self.assertEqual(adapter.adapt(broken, 1, 1.0, 1.0).reason, "discontinuity")
        first = adapter.adapt(path(), 1, 1.0, 1.0)
        second = adapter.adapt(path(2.0), 2, 1.1, 1.1)
        self.assertLessEqual(abs(second.wz_radps - first.wz_radps), 0.0100001)


if __name__ == "__main__":
    unittest.main()
