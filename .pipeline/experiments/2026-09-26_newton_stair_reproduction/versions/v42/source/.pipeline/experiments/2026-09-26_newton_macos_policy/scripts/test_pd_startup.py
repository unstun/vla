"""Independent spline, measured-entry, and legacy physics regressions."""
import json
import os
from pathlib import Path
import types
import unittest
import importlib.util

import numpy as np
from scipy.interpolate import CubicHermiteSpline
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
from lite3_newton import BASE, Lite3Newton, Q0, check_golden_policy
from pd_startup import PDStartup, SdkSpline


class StartupTests(unittest.TestCase):
    def test_navigation_driver_requires_an_explicit_completed_startup(self):
        path = BASE.parent / "2026-09-26_newton_stair_reproduction/scripts/pd_geometry_driver.py"
        spec = importlib.util.spec_from_file_location("pd_driver_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        good = {"startup_mode": "pd_stand", "phase": "policy", "navigation_ready": True,
                "policy_observation_valid": True}
        self.assertTrue(module.startup_ready({"control": good}))
        self.assertFalse(module.startup_ready({}))
        for field, value in [("phase", "handoff"), ("phase", "settle"), ("startup_mode", "policy"),
                             ("navigation_ready", False), ("policy_observation_valid", False)]:
            self.assertFalse(module.startup_ready({"control": {**good, field: value}}))

    def test_sdk_matches_independent_scipy_hermite_and_endpoint_clamp(self):
        sdk = SdkSpline()
        for initial, goal, duration in [(-1.3, -.8, 1.5), (.3, -.2, 1.), (2.7, 1.6, 1.5)]:
            reference = CubicHermiteSpline([0., duration], [initial, goal], [0., 0.])
            for t in np.r_[np.linspace(0., duration, 41), duration + .2]:
                actual, velocity = sdk.sample(np.array(initial), np.array(goal), t, duration)
                expected = reference(min(t, duration))
                expected_velocity = (reference(min(t + .001, duration)) - expected) / .001
                self.assertAlmostEqual(float(actual), float(expected), places=6)
                self.assertAlmostEqual(float(velocity), float(expected_velocity), places=6)

    def test_spline_rejects_invalid_boundary(self):
        sdk = SdkSpline()
        for initial, goal, t, duration in [(0., 1., -1., 1.), (0., 1., 0., 0.), (0., np.nan, 0., 1.)]:
            with self.assertRaises(ValueError):
                sdk.sample(np.array(initial), np.array(goal), t, duration)

    def test_stability_must_be_continuous_and_not_just_elapsed_time(self):
        startup = PDStartup(Q0)
        args = (Q0, np.zeros(12), .30, 1., 0., 0.)
        for t in [1., 2., 3.5, 3.6, 4.0]:
            startup.advance(t, *args)
        self.assertEqual(startup.phase, "settle")
        startup.advance(4.05, Q0, np.ones(12), .30, 1., 0., 0.)
        for t in [4.1, 4.4, 4.58]:
            startup.advance(t, *args)
        self.assertEqual(startup.phase, "settle")
        startup.advance(4.62, *args)
        self.assertEqual(startup.phase, "handoff")
        self.assertFalse(startup.ready)
        startup.advance(4.9, *args)
        self.assertTrue(startup.ready)

    def test_low_body_bad_posture_and_timeout_cannot_release_policy(self):
        startup = PDStartup(Q0)
        for t in [1., 2., 3.5, 4., 5., 6., 7.]:
            startup.advance(t, Q0, np.zeros(12), .12, .8, 0., 0.)
        self.assertFalse(startup.ready)
        with self.assertRaises(TimeoutError):
            startup.advance(8., Q0, np.zeros(12), .12, .8, 0., 0.)

    def test_handoff_interpolates_pd_torque_without_initial_jump(self):
        startup = PDStartup(Q0)
        startup.phase, startup.entered = "handoff", 4.
        target = Q0 + np.linspace(-.2, .2, 12, dtype=np.float32)
        q, qd = Q0 + .02, np.full(12, .1)
        for elapsed, alpha in [(0., 0.), (.125, .5), (.25, 1.)]:
            desired, velocity, kp, kd = startup.motor_command(4. + elapsed, target)
            actual = kp * (desired - q) + kd * (velocity - qd)
            expected = (1.-alpha) * (80.*(Q0-q)-.7*qd) + alpha * (20.*(target-q)-.5*qd)
            np.testing.assert_allclose(actual, expected, atol=1e-5)

    def test_unknown_mode_rejected_before_simulator_creation(self):
        with self.assertRaises(ValueError):
            Lite3Newton(startup_mode="invalid")

    def test_legacy_motor_loop_matches_archived_implementation(self):
        old = types.ModuleType("legacy_lite3_newton")
        old.__file__ = str(BASE / "scripts/lite3_newton.py")
        path = BASE.parent / "2026-09-26_newton_stair_reproduction/repairs/2026-09-27_pd_startup/before/lite3_newton.py"
        exec(compile(path.read_text(), str(path), "exec"), old.__dict__)
        expected, actual = old.Lite3Newton(), Lite3Newton()
        for i in range(100):
            command = (0., 0., 0.) if i < 60 else (.15, .02, .05)
            expected.step(command)
            actual.step(command)
            np.testing.assert_array_equal(actual.state.joint_q.numpy(), expected.state.joint_q.numpy())
            np.testing.assert_array_equal(actual.torque, expected.torque)
        self.assertTrue(check_golden_policy()["passed"])


if __name__ == "__main__":
    out = Path(os.environ["NEWTON_RUN_DIR"])
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests))
    (out / "result.json").write_text(json.dumps({"tests": result.testsRun, "passed": result.wasSuccessful(),
        "failures": len(result.failures), "errors": len(result.errors)}, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
