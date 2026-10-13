"""Absolute deadline, overrun and real native-clock regression checks."""
import unittest
from realtime_pacer import NativeClockPacer


class Clock:
    def __init__(self): self.now = 100.
    def __call__(self): return self.now
    def sleep(self, delay): self.now += delay


class PacerTests(unittest.TestCase):
    def test_absolute_clock_does_not_accumulate_policy_work(self):
        clock = Clock()
        pacer = NativeClockPacer(7., clock, clock.sleep)
        for i in range(1, 1001):
            clock.now += .0007
            pacer.wait(7. + i * .001)
        self.assertAlmostEqual(clock.now, 101.)
        self.assertAlmostEqual(pacer.snapshot(8.)["actual_rtf"], 1.)
        self.assertEqual(pacer.steps, 1000)

    def test_overrun_preserves_physics_and_original_anchor(self):
        clock = Clock()
        pacer = NativeClockPacer(0., clock, clock.sleep)
        clock.now += .04
        pacer.wait(.001)
        self.assertGreater(pacer.max_lag_s, .03)
        self.assertEqual(pacer.steps, 1)
        pacer.wait(.05)
        self.assertAlmostEqual(clock.now, 100.05)
        self.assertEqual(pacer.snapshot(.05)["dropped_physics_steps"], 0)

    def test_stale_rollback_and_nonfinite_clock_rejected(self):
        clock = Clock()
        pacer = NativeClockPacer(2., clock, clock.sleep)
        for native in (2., 1.9, float("nan"), float("inf")):
            with self.assertRaises(ValueError): pacer.wait(native)
        self.assertEqual(pacer.steps, 0)


if __name__ == "__main__": unittest.main()
