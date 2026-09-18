import unittest

from lite3_sim_bridge.monitor_core import (
    AcceptanceAccumulator,
    TopicStats,
    should_record_periodic_event,
)


class MonitorCoreTest(unittest.TestCase):
    def test_periodic_evidence_rate_limit(self):
        self.assertTrue(should_record_periodic_event(0, 1_000_000_000, 100_000_000))
        self.assertFalse(
            should_record_periodic_event(1_000_000_000, 1_099_999_999, 100_000_000)
        )
        self.assertTrue(
            should_record_periodic_event(1_000_000_000, 1_100_000_000, 100_000_000)
        )
        with self.assertRaises(ValueError):
            should_record_periodic_event(0, 1, 0)

    def test_topic_rate_and_stamp_regression(self):
        stats = TopicStats()
        stats.observe(1_000_000_000, 100)
        stats.observe(1_500_000_000, 200)
        stats.observe(2_000_000_000, 200)
        summary = stats.summary()
        self.assertEqual(summary["count"], 3)
        self.assertAlmostEqual(summary["rate_hz"], 2.0)
        self.assertEqual(summary["nonincreasing_stamp_count"], 1)

    def test_accumulates_synchronized_closed_loop_topics(self):
        monitor = AcceptanceAccumulator()
        for index in range(3):
            stamp = 100 + index
            receipt = 1_000_000_000 + index * 100_000_000
            monitor.observe_body_pose(receipt, stamp, (float(index), 0.0, 0.3))
            monitor.observe_sensor_pose(receipt + 1, stamp)
            monitor.observe_cloud(receipt + 2, stamp, 20 + index)
        monitor.observe_command(2_000_000_000, (0.3, -0.1, 0.2))
        monitor.observe_command(2_020_000_000, (0.0, 0.0, 0.0))
        monitor.observe_bspline(2_000_000_000, 7)
        monitor.observe_bspline(2_100_000_000, 8)

        summary = monitor.summary()
        self.assertAlmostEqual(summary["path_length_m"], 2.0)
        self.assertEqual(summary["last_body_position"], (2.0, 0.0, 0.3))
        self.assertEqual(summary["max_abs_command"], [0.3, 0.1, 0.2])
        self.assertEqual(summary["nonzero_command_count"], 1)
        self.assertEqual(summary["cloud_points"]["minimum"], 20)
        self.assertEqual(summary["unique_trajectory_count"], 2)
        self.assertEqual(summary["synchronized_sensor_triplet_fraction"], 1.0)

    def test_rejects_nonfinite_or_invalid_samples(self):
        monitor = AcceptanceAccumulator()
        with self.assertRaises(ValueError):
            monitor.observe_body_pose(1, 1, (0.0, float("nan"), 0.0))
        with self.assertRaises(ValueError):
            monitor.observe_cloud(1, 1, -1)
        with self.assertRaises(ValueError):
            monitor.observe_command(1, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
