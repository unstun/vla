"""Interface regression tests independent of the demonstration trajectory."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import numpy as np
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
from lite3_newton import Lite3Newton, check_golden_policy


class Lite3ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.robot = Lite3Newton()
        cls.q0 = cls.robot.model.joint_q.numpy().copy()
        cls.qd0 = cls.robot.model.joint_qd.numpy().copy()

    def setUp(self):
        self.robot.model.joint_q.assign(self.q0)
        self.robot.model.joint_qd.assign(self.qd0)
        self.robot.solver.reset(self.robot.state)
        self.robot.history.reset()
        self.robot.last_action.fill(0)

    def test_golden_policy_history_and_output(self):
        self.assertTrue(check_golden_policy()["passed"])

    def test_initial_state_is_synchronized_before_first_step(self):
        self.assertEqual(self.robot.solver.mj_data.time, 0.0)
        self.robot.infer((0., 0., 0.))
        np.testing.assert_allclose(self.robot.observation[:9], [0, 0, 0, 0, 0, -1, 0, 0, 0], atol=1e-7)
        self.assertLessEqual(self.robot.max_observation_mapping_error, 1e-4)

    def test_asymmetric_state_and_world_to_body_angular_velocity(self):
        q, qd = self.q0.copy(), self.qd0.copy()
        q[3:7] = [0, 0, math.sqrt(.5), math.sqrt(.5)]  # 90-degree yaw
        offsets = np.arange(1, 13, dtype=np.float32) * .01
        q[self.robot.q_indices] += offsets
        qd[3:6] = [.2, .4, .6]  # world -> body should be [.4, -.2, .6]
        qd[self.robot.qd_indices] = np.arange(1, 13, dtype=np.float32) * .05
        self.robot.model.joint_q.assign(q)
        self.robot.model.joint_qd.assign(qd)
        self.robot.solver.reset(self.robot.state)
        self.robot.infer((.5, 0., .4))
        obs = self.robot.observation
        np.testing.assert_allclose(obs[:9], [.1, -.05, .15, 0, 0, -1, .5, 0, .4], atol=2e-7)
        np.testing.assert_allclose(obs[9:21], offsets, atol=1e-7)
        np.testing.assert_allclose(obs[21:33], np.arange(1, 13) * .0025, atol=1e-7)
        self.assertLessEqual(self.robot.max_observation_mapping_error, 1e-4)

    def test_each_motor_targets_the_expected_joint(self):
        m = self.robot.solver.mj_model
        self.assertEqual(m.nu, 12)
        np.testing.assert_array_equal(m.actuator_trnid[:, 0], self.robot.mj_joints)
        np.testing.assert_allclose(m.actuator_gear[:, 0], 1)
        np.testing.assert_allclose(m.actuator_ctrlrange[:, 1], np.tile([24, 24, 36], 4))

    def test_invalid_command_rejected_before_history_update(self):
        for command in ((0., 0.), (float("nan"), 0., 0.), (0., float("inf"), 0.)):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.robot.infer(command)
            self.assertIsNone(self.robot.history.values)

    def test_runner_rejects_unsafe_run_identity_and_excessive_deadline(self):
        runner = Path(__file__).with_name("run_bounded.py")
        for args in (("--run-id", "../escape"), ("--run-id", "invalid_deadline", "--deadline", "601")):
            result = subprocess.run([sys.executable, str(runner), *args, "--", sys.executable, "-c", "pass"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    out = Path(os.environ["NEWTON_RUN_DIR"])
    shutil.copyfile(__file__, out / "executed_test_contracts.py")
    shutil.copyfile(Path(__file__).with_name("lite3_newton.py"), out / "executed_lite3_newton.py")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Lite3ContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (out / "result.json").write_text(json.dumps({"tests": result.testsRun,
                                                "failures": len(result.failures), "errors": len(result.errors),
                                                "passed": result.wasSuccessful()}, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
