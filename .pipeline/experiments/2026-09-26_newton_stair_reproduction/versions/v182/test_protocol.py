import unittest
from protocol import CONDITIONS, schedule


class ProtocolTests(unittest.TestCase):
    def test_all_conditions_have_two_ten_second_zero_windows(self):
        for attempt in range(1, 7):
            rows = list(schedule(attempt))
            for phase in ("stop1", "stop2"):
                chosen = [r for r in rows if r["phase"] == phase]
                self.assertEqual(len(chosen), 500)
                self.assertTrue(all(r["command"] == [0., 0., 0.] for r in chosen))
            self.assertEqual(len([r for r in rows if r["phase"] == "walk2"]), 150)

    def test_continuous_sequence_and_declared_speeds(self):
        for attempt, (speed, _) in enumerate(CONDITIONS, 1):
            rows = list(schedule(attempt))
            self.assertEqual([r["index"] for r in rows], list(range(len(rows))))
            self.assertTrue(all(r["command"] == [speed, 0., 0.] for r in rows if r["phase"].startswith("walk")))

    def test_invalid_attempt_or_timing_rejected(self):
        for a in (0, 7):
            with self.assertRaises(ValueError):
                list(schedule(a))
        with self.assertRaises(ValueError):
            list(schedule(1, .07))


if __name__ == "__main__":
    unittest.main()
