import unittest

from lite3_sim_bridge.qualification_compare import summarize_metrics


class QualificationCompareTest(unittest.TestCase):
    def _row(self, segment, command, linear, angular, elapsed=1.0):
        return {
            "schedule_segment": segment,
            "schedule_segment_elapsed_seconds": elapsed,
            "applied_command": list(command),
            "sim_time_seconds": 0.0,
            "root_lin_vel_b": list(linear),
            "root_ang_vel_b": list(angular),
            "root_quat_wxyz": [1.0, 0.0, 0.0, 0.0],
            "root_pos_w": [0.0, 0.0, 0.35],
            "contact_count": 4,
            "nonfoot_contact_max_n": 0.0,
            "command_observation_max_error": 0.0,
            "actions": [0.1] * 12,
            "joint_position": [0.0, -0.8, 1.6] * 4,
            "finite": True,
            "done": False,
            "command_reason": "fresh",
        }

    def test_summarizes_schedule_response_and_support(self):
        rows = [
            self._row("settle_zero", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
            self._row("forward", (0.3, 0.0, 0.0), (0.2, 0.0, 0.0), (0.0, 0.0, 0.0)),
            self._row("lateral", (0.0, 0.18, 0.0), (0.0, 0.1, 0.0), (0.0, 0.0, 0.0)),
            self._row("yaw", (0.0, 0.0, 0.4), (0.0, 0.0, 0.0), (0.0, 0.0, 0.3)),
            self._row("watchdog_disconnect", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        ]
        for index, row in enumerate(rows):
            row["sim_time_seconds"] = index * 0.1
        rows[-1]["command_reason"] = "watchdog_timeout"
        summary = summarize_metrics(rows)
        self.assertEqual(summary["response_means"]["forward"], 0.2)
        self.assertEqual(summary["response_means"]["lateral"], 0.1)
        self.assertEqual(summary["response_means"]["yaw"], 0.3)
        self.assertEqual(summary["supported_contact_fraction"], 1.0)
        self.assertTrue(summary["watchdog_zero_observed"])
        self.assertFalse(summary["terminated"])

    def test_rejects_empty_metrics(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            summarize_metrics([])


if __name__ == "__main__":
    unittest.main()
