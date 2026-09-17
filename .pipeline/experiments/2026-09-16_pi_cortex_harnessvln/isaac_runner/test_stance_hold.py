import ast
import math
import unittest
from pathlib import Path

import numpy as np

import stance_hold as sh

DT = 0.02
Q_STAND = np.tile(np.array([0.0, -0.8, 1.6]), 4)
BALANCED = np.array([30.0, 30.0, 30.0, 30.0])


class Loop:
    """Drive the hold like the runner: feed back last step's target and gains."""

    def __init__(self, mode="auto", **kwargs):
        self.hold = sh.StanceHold(mode, **kwargs)
        self.target = Q_STAND.copy()
        self.kp = np.full(12, sh.BASE_KP)
        self.kd = np.full(12, sh.BASE_KD)
        self.k = 0
        self.outputs = []

    def sample(self, now, **over):
        values = dict(
            now_s=now,
            command=np.zeros(3),
            joint_pos=Q_STAND + 0.01,
            joint_vel=np.zeros(12),
            policy_target=Q_STAND + 0.03,
            applied_target=self.target,
            applied_kp=self.kp,
            applied_kd=self.kd,
            linear_speed=0.02,
            angular_speed=0.05,
            tilt_deg=2.0,
            foot_forces=BALANCED,
        )
        values.update(over)
        return sh.HoldInput(**values)

    def step(self, now=None, **over):
        if now is None:
            now = self.k * DT
        out = self.hold.update(self.sample(now, **over))
        self.target, self.kp, self.kd = out.target, out.kp, out.kd
        self.k += 1
        self.outputs.append((now, out))
        return out

    def run(self, seconds, **over):
        out = None
        for _ in range(int(round(seconds / DT))):
            out = self.step(**over)
        return out

    def run_until(self, mode, limit_s=20.0, **over):
        for _ in range(int(round(limit_s / DT))):
            out = self.step(**over)
            if out.mode == mode:
                return out
        raise AssertionError("mode %s not reached; now %s (%s)" % (mode, self.hold.mode, self.hold.reason))

    def run_until_reason(self, reason, limit_s=20.0, **over):
        for _ in range(int(round(limit_s / DT))):
            out = self.step(**over)
            if out.reason == reason:
                return out
        raise AssertionError("reason %s not reached; now %s (%s)" % (reason, self.hold.mode, self.hold.reason))


class OffModeTests(unittest.TestCase):
    def test_off_returns_policy_target_and_v12_gains_without_state(self):
        loop = Loop("off")
        for k in range(200):
            policy = Q_STAND + 0.001 * k
            out = loop.step(policy_target=policy)
            np.testing.assert_array_equal(out.target, policy)
            np.testing.assert_array_equal(out.kp, np.full(12, 20.0))
            np.testing.assert_array_equal(out.kd, np.full(12, 0.5))
            self.assertTrue(out.policy_owns_joints)
            self.assertEqual(out.mode, "OFF")
        status = loop.hold.status()
        self.assertEqual(status["counters"]["updates"], 0)
        self.assertEqual(status["transitions"], [])
        self.assertEqual(status["mode"], "RL")

    def test_off_output_is_a_copy(self):
        hold = sh.StanceHold("off")
        policy = Q_STAND.copy()
        out = hold.update(Loop("off").sample(0.0, policy_target=policy))
        out.target[0] = 99.0
        self.assertEqual(policy[0], 0.0)

    def test_constructor_validation(self):
        with self.assertRaises(ValueError):
            sh.StanceHold("on")
        with self.assertRaises(ValueError):
            sh.StanceHold("auto", joint_lower=np.zeros(12))
        with self.assertRaises(ValueError):
            sh.StanceHold("auto", joint_lower=np.zeros(12), joint_upper=np.zeros(12))
        with self.assertRaises(ValueError):
            sh.StanceHold("auto", joint_lower=np.zeros(11), joint_upper=np.ones(11))


class EntryGateTests(unittest.TestCase):
    def test_entry_after_quarter_second_dwell(self):
        loop = Loop()
        first = loop.step()
        self.assertEqual(first.mode, "STAND_SETTLING")
        self.assertTrue(first.policy_owns_joints)
        np.testing.assert_array_equal(first.target, Q_STAND + 0.03)
        np.testing.assert_array_equal(first.kp, np.full(12, 20.0))
        out = loop.run_until("STAND_TRANSITION")
        entry_t = loop.outputs[-1][0]
        self.assertGreaterEqual(entry_t, sh.SETTLE_DWELL_S - 1e-9)
        self.assertLess(loop.outputs[-2][0], sh.SETTLE_DWELL_S - 1e-9)
        self.assertFalse(out.policy_owns_joints)
        # Before PRD D4 the entry step already carried Kp 60 / Kd 1. The entry gain
        # ramp starts at blend 0, so the entry step repeats the applied target and
        # the V12 gains; EntryRampTests cover the ramp itself.
        np.testing.assert_array_equal(out.target, Q_STAND + 0.03)
        np.testing.assert_array_equal(out.kp, np.full(12, 20.0))
        np.testing.assert_array_equal(out.kd, np.full(12, 0.5))
        self.assertEqual(out.reason, "quiet_four_contact_confirmed")
        entry = loop.hold.status()["last_entry"]
        self.assertEqual(entry["support_shares"], [0.5, 0.5, 0.5])
        self.assertEqual(entry["entry_ramp_s"], 0.5)
        self.assertIsNone(entry["entry_ramp_complete_t_s"])

    def test_each_gate_blocks_entry_and_names_itself(self):
        cases = [
            ("linear_speed", dict(linear_speed=0.1501)),
            ("angular_speed", dict(angular_speed=0.5001)),
            ("tilt", dict(tilt_deg=10.001)),
            ("four_contact", dict(foot_forces=np.array([30.0, 30.0, 9.99, 30.0]))),
        ]
        for name, over in cases:
            with self.subTest(gate=name):
                loop = Loop()
                out = loop.run(2.0, **over)
                self.assertEqual(out.mode, "STAND_SETTLING")
                self.assertTrue(out.policy_owns_joints)
                self.assertEqual(out.reason, "waiting_for_" + name)
                self.assertEqual(loop.hold.counters["entries"], 0)
                np.testing.assert_array_equal(out.kp, np.full(12, 20.0))

    def test_gate_boundaries_are_inclusive_like_mujoco(self):
        loop = Loop()
        out = loop.run_until("STAND_TRANSITION", linear_speed=0.15, angular_speed=0.5, tilt_deg=10.0,
                             foot_forces=np.array([10.0, 10.0, 10.0, 10.0]))
        self.assertEqual(out.mode, "STAND_TRANSITION")

    def test_nonzero_command_never_arms(self):
        loop = Loop()
        out = loop.run(2.0, command=np.array([0.0, 0.0, 0.0011]))
        self.assertEqual(out.mode, "RL")
        self.assertEqual(loop.hold.counters["settle_starts"], 0)
        out = loop.step(command=np.array([0.0, 0.001, 0.0]))
        self.assertEqual(out.mode, "STAND_SETTLING")

    def test_failing_gate_restarts_dwell(self):
        loop = Loop()
        loop.run(0.2)
        loop.step(linear_speed=0.2)
        self.assertEqual(loop.hold.mode, "STAND_SETTLING")
        restart = loop.k * DT
        out = loop.run_until("STAND_TRANSITION")
        self.assertGreaterEqual(loop.outputs[-1][0] - restart, sh.SETTLE_DWELL_S - 1e-9)
        self.assertEqual(out.mode, "STAND_TRANSITION")

    def test_unbalanced_support_blocks_entry(self):
        loop = Loop()
        out = loop.run(3.0, foot_forces=np.array([40.0, 10.0, 10.0, 40.0]))
        self.assertEqual(out.mode, "STAND_SETTLING")
        self.assertEqual(out.reason, "waiting_for_support_balance")
        self.assertGreater(loop.hold.counters["support_balance_blocks"], 0)
        self.assertEqual(loop.hold.counters["entries"], 0)
        self.assertTrue(out.policy_owns_joints)

    def test_balance_band_edges_and_dwell_mean(self):
        loop = Loop()
        # Just inside and just outside the band (front share 0.649 and 0.651).
        out = loop.run_until("STAND_TRANSITION", foot_forces=np.array([32.45, 32.45, 17.55, 17.55]))
        self.assertEqual(out.mode, "STAND_TRANSITION")
        loop = Loop()
        out = loop.run(2.0, foot_forces=np.array([17.45, 17.45, 32.55, 32.55]))
        self.assertEqual(out.reason, "waiting_for_support_balance")
        # Individual samples out of band, dwell mean in band (front shares 0.70 and 0.50).
        loop = Loop()
        for k in range(40):
            forces = np.array([35.0, 35.0, 15.0, 15.0]) if k % 2 == 0 else BALANCED
            out = loop.step(foot_forces=forces)
            if out.mode == "STAND_TRANSITION":
                break
        self.assertEqual(out.mode, "STAND_TRANSITION")
        self.assertAlmostEqual(loop.hold.status()["last_entry"]["support_shares"][0], 0.6, places=2)

    def test_settle_timeout_restarts_window_and_rl_keeps_control(self):
        loop = Loop()
        out = loop.run(21.0, foot_forces=np.array([30.0, 30.0, 5.0, 30.0]))
        self.assertEqual(out.mode, "STAND_SETTLING")
        self.assertTrue(out.policy_owns_joints)
        self.assertEqual(loop.hold.counters["settle_timeouts"], 2)
        out = loop.run_until("STAND_TRANSITION")
        self.assertEqual(out.mode, "STAND_TRANSITION")


class TorqueContinuityTests(unittest.TestCase):
    def test_seed_keeps_commanded_pd_torque_at_entry(self):
        rng = np.random.default_rng(7)
        loop = Loop()
        q = Q_STAND + rng.uniform(-0.05, 0.05, 12)
        policy = Q_STAND + rng.uniform(-0.2, 0.2, 12)
        before = None
        for _ in range(100):
            prev_target, prev_kp, prev_kd = loop.target.copy(), loop.kp.copy(), loop.kd.copy()
            out = loop.step(joint_pos=q, policy_target=policy)
            if out.mode == "STAND_TRANSITION":
                before = (prev_target, prev_kp, prev_kd)
                break
        self.assertIsNotNone(before)
        prev_target, prev_kp, prev_kd = before
        np.testing.assert_array_equal(prev_target, policy)
        qdot = np.zeros(12)
        tau_before = prev_kp * (prev_target - q) - prev_kd * qdot
        tau_after = out.kp * (out.target - q) - out.kd * qdot
        self.assertLessEqual(float(np.max(np.abs(tau_after - tau_before))), 1e-6)
        self.assertGreater(float(np.max(np.abs(tau_before))), 1.0)
        # With the entry ramp (PRD D4) the torque-matched seed is reached at the
        # end of the ramp instead of at the entry step; the torque stays matched.
        out = loop.run_until_reason("entry_gain_ramp_complete", joint_pos=q, policy_target=policy)
        np.testing.assert_allclose(out.target, q + (20.0 / 60.0) * (policy - q), atol=1e-12)
        np.testing.assert_array_equal(out.kp, np.full(12, 60.0))
        tau_after = out.kp * (out.target - q) - out.kd * qdot
        self.assertLessEqual(float(np.max(np.abs(tau_after - tau_before))), 1e-6)

    def test_damping_term_is_not_matched_like_mujoco(self):
        loop = Loop()
        qdot = np.full(12, 0.1)
        # Checked where the hold gains are reached (end of the entry ramp, PRD D4).
        out = loop.run_until_reason("entry_gain_ramp_complete", joint_vel=qdot)
        q = Q_STAND + 0.01
        tau_before = 20.0 * ((Q_STAND + 0.03) - q) - 0.5 * qdot
        tau_after = out.kp * (out.target - q) - out.kd * qdot
        np.testing.assert_allclose(tau_after - tau_before, -(1.0 - 0.5) * qdot, atol=1e-12)

    def test_joint_limits_clip_supervisor_targets_only(self):
        lower = Q_STAND - 0.005
        upper = Q_STAND + 0.005
        loop = Loop(joint_lower=lower, joint_upper=upper)
        first = loop.step()
        np.testing.assert_array_equal(first.target, Q_STAND + 0.03)
        out = loop.run_until("STAND_TRANSITION")
        np.testing.assert_array_equal(out.target, np.clip(out.target, lower, upper))
        self.assertTrue(np.all(out.target <= upper))


class EntryRampTests(unittest.TestCase):
    """Entry gain ramp at the start of STAND_TRANSITION (PRD D4, AC7 rerun)."""

    RAMP_STEPS = 25  # 0.5 s at the 20 ms control period

    def setUp(self):
        rng = np.random.default_rng(11)
        self.q0 = Q_STAND + rng.uniform(-0.05, 0.05, 12)
        self.policy = Q_STAND + rng.uniform(-0.2, 0.2, 12)
        # Keep every joint's entry error away from zero so relative checks are meaningful.
        self.policy = np.where(np.abs(self.policy - self.q0) < 0.02, self.q0 + 0.05, self.policy)

    def enter(self, kp0=None, kd0=None):
        """Settle at q0 with the policy target; return the loop, entry index and entry values."""
        loop = Loop()
        for _ in range(100):
            if kp0 is not None and loop.hold.mode == "STAND_SETTLING":
                # Non-uniform gains applied at entry, to check the per-joint rule.
                loop.kp, loop.kd = kp0.copy(), kd0.copy()
            prev = (loop.target.copy(), loop.kp.copy(), loop.kd.copy())
            out = loop.step(joint_pos=self.q0, policy_target=self.policy)
            if out.mode == "STAND_TRANSITION":
                return loop, len(loop.outputs) - 1, prev
        raise AssertionError("no entry")

    def ramp(self, loop, steps, drift=0.0):
        """Steps after entry; joint_pos moves so the ramp must use the frozen q0."""
        outs = []
        for k in range(1, steps + 1):
            outs.append(loop.step(joint_pos=self.q0 + drift * k, policy_target=self.policy - 0.1))
        return outs

    def test_constants(self):
        self.assertEqual(sh.ENTRY_RAMP_S, 0.5)
        self.assertLess(sh.ENTRY_RAMP_S, sh.TRANSITION_S)
        constants = sh.stance_hold_constants()
        self.assertEqual(constants["entry_ramp_s"], 0.5)
        self.assertEqual(constants["entry_ramp_blend"], "smoothstep")
        self.assertEqual(round(sh.ENTRY_RAMP_S / DT), self.RAMP_STEPS)

    def test_entry_step_repeats_previous_applied_target_and_gains(self):
        loop, index, (t0, kp0, kd0) = self.enter()
        out = loop.outputs[index][1]
        np.testing.assert_array_equal(t0, self.policy)
        np.testing.assert_array_equal(out.target, t0)
        np.testing.assert_array_equal(out.kp, kp0)
        np.testing.assert_array_equal(out.kd, kd0)
        self.assertFalse(out.policy_owns_joints)
        self.assertEqual(out.reason, "quiet_four_contact_confirmed")
        self.assertEqual(out.progress, 0.0)

    def test_stiffness_torque_on_q0_is_constant_at_every_ramp_step(self):
        kp0 = np.linspace(18.0, 22.0, 12)
        kd0 = np.linspace(0.4, 0.6, 12)
        loop, index, (t0, _kp, _kd) = self.enter(kp0, kd0)
        entry = loop.outputs[index][1]
        np.testing.assert_array_equal(entry.kp, kp0)
        reference = kp0 * (t0 - self.q0)
        self.assertGreater(float(np.min(np.abs(reference))), 0.3)
        outs = [entry] + self.ramp(loop, self.RAMP_STEPS, drift=0.002)
        for k, out in enumerate(outs):
            with self.subTest(step=k):
                self.assertEqual(out.mode, "STAND_TRANSITION")
                torque = out.kp * (out.target - self.q0)
                np.testing.assert_allclose(torque, reference, rtol=1e-9, atol=0.0)
                u = sh._stance_smoothstep(min(1.0, k * DT / sh.ENTRY_RAMP_S))
                np.testing.assert_allclose(out.kp, kp0 + (60.0 - kp0) * u, rtol=1e-12)
                np.testing.assert_allclose(out.kd, kd0 + (1.0 - kd0) * u, rtol=1e-12)
                expected_reason = ("quiet_four_contact_confirmed" if k == 0 else
                                   "entry_gain_ramp" if k < self.RAMP_STEPS else "entry_gain_ramp_complete")
                self.assertEqual(out.reason, expected_reason)
        self.assertGreater(float(np.max(np.abs(outs[-1].target - t0))), 0.01)

    def test_ramp_samples_at_quarter_and_half_ramp(self):
        loop, index, (t0, _kp, _kd) = self.enter()
        entry_t = loop.outputs[index][0]
        quarter = loop.step(now=entry_t + 0.125, joint_pos=self.q0, policy_target=self.policy)
        half = loop.step(now=entry_t + 0.25, joint_pos=self.q0, policy_target=self.policy)
        u = 0.25 * 0.25 * (3.0 - 0.5)  # smoothstep(0.25) = 0.15625
        np.testing.assert_allclose(quarter.kp, np.full(12, 20.0 + 40.0 * u), rtol=1e-12)
        np.testing.assert_allclose(quarter.target, self.q0 + (20.0 / (20.0 + 40.0 * u)) * (t0 - self.q0), rtol=1e-12)
        np.testing.assert_allclose(half.kp, np.full(12, 40.0), rtol=1e-12)
        np.testing.assert_allclose(half.kd, np.full(12, 0.75), rtol=1e-12)
        np.testing.assert_allclose(half.target, self.q0 + 0.5 * (t0 - self.q0), rtol=1e-12)
        self.assertAlmostEqual(half.progress, 0.25 / sh.TRANSITION_S)

    def test_ramp_ends_at_the_seed_and_hold_gains_then_fixed_stand_at_two_seconds(self):
        loop, index, (t0, kp0, _kd) = self.enter()
        entry_t = loop.outputs[index][0]
        outs = self.ramp(loop, self.RAMP_STEPS, drift=0.002)
        end = outs[-1]
        seed = self.q0 + (kp0 / np.full(12, 60.0)) * (t0 - self.q0)
        np.testing.assert_array_equal(end.target, seed)
        np.testing.assert_array_equal(end.kp, np.full(12, 60.0))
        np.testing.assert_array_equal(end.kd, np.full(12, 1.0))
        self.assertEqual(end.reason, "entry_gain_ramp_complete")
        self.assertLess(outs[-2].kp[0], 60.0)
        status = loop.hold.status()
        self.assertEqual(status["counters"]["entry_ramps_complete"], 1)
        entry = status["last_entry"]
        self.assertAlmostEqual(entry["entry_ramp_complete_t_s"], entry_t + sh.ENTRY_RAMP_S)
        self.assertEqual(entry["q0"], [float(v) for v in self.q0])
        self.assertEqual(entry["applied_target_t0"], [float(v) for v in t0])
        self.assertEqual((entry["kp0_mean"], entry["kd0_mean"]), (20.0, 0.5))
        self.assertAlmostEqual(entry["seed_minus_t0_max_abs"], float(np.max(np.abs(seed - t0))))
        self.assertAlmostEqual(entry["stiffness_torque_max_abs_nm"], float(np.max(np.abs(20.0 * (t0 - self.q0)))))
        out = loop.run_until("FIXED_STAND", joint_pos=self.q0, policy_target=self.policy)
        self.assertGreaterEqual(loop.outputs[-1][0] - entry_t, sh.TRANSITION_S - 1e-9)
        self.assertLess(loop.outputs[-2][0] - entry_t, sh.TRANSITION_S - 1e-9)
        np.testing.assert_array_equal(out.target, seed)
        np.testing.assert_array_equal(out.kp, np.full(12, 60.0))
        self.assertEqual(status["counters"]["entry_ramps_complete"], loop.hold.counters["entry_ramps_complete"])

    def test_gains_are_monotonic(self):
        loop, index, _prev = self.enter()
        outs = [loop.outputs[index][1]] + self.ramp(loop, 40)
        kps = np.array([o.kp for o in outs])
        kds = np.array([o.kd for o in outs])
        self.assertTrue(np.all(np.diff(kps, axis=0) >= 0.0))
        self.assertTrue(np.all(np.diff(kds, axis=0) >= 0.0))
        self.assertTrue(np.all(np.diff(kps[: self.RAMP_STEPS + 1], axis=0) > 0.0))
        np.testing.assert_array_equal(kps[self.RAMP_STEPS:], np.full((40 - self.RAMP_STEPS + 1, 12), 60.0))

    def test_delay_mismatch_is_bounded_at_control_step_resolution(self):
        """Lite3Actuator applies the previous step's target with the new gains.

        Over a delayed control step the stiffness torque on q0 is
        Kp_k * (target_{k-1} - q0); its relative error to Kp0 * (T0 - q0) is
        Kp_k / Kp_{k-1} - 1. The immediate step it replaces had 60 / 20 - 1 = 2.
        """
        loop, index, (t0, kp0, _kd) = self.enter()
        outs = [loop.outputs[index][1]] + self.ramp(loop, 60)
        reference = kp0 * (t0 - self.q0)
        previous = t0
        worst = 0.0
        for out in outs:
            mismatch = np.abs(out.kp * (previous - self.q0) - reference)
            self.assertTrue(np.all(mismatch <= 0.15 * np.abs(reference) + 1e-9), mismatch / np.abs(reference))
            worst = max(worst, float(np.max(mismatch / np.abs(reference))))
            previous = out.target
        # smoothstep over 25 steps: the largest step ratio is Kp_8 / Kp_7 - 1 = 0.0729.
        self.assertAlmostEqual(worst, 0.0729, delta=0.0005)

    def test_rejoin_during_the_ramp_blends_from_the_applied_ramp_values(self):
        loop, index, (t0, _kp, _kd) = self.enter()
        entry_t = loop.outputs[index][0]
        last = self.ramp(loop, 5)[-1]
        self.assertEqual(last.reason, "entry_gain_ramp")
        self.assertTrue(20.0 < float(last.kp[0]) < 60.0)
        ramp_target, ramp_kp, ramp_kd = last.target.copy(), last.kp.copy(), last.kd.copy()
        command = np.array([0.3, 0.0, 0.0])
        policy = Q_STAND - 0.1
        t_r = entry_t + 6 * DT
        out0 = loop.step(now=t_r, command=command, policy_target=policy)
        self.assertEqual((out0.mode, out0.reason), ("REJOIN", "new_command_rejoin"))
        np.testing.assert_array_equal(out0.target, ramp_target)
        np.testing.assert_array_equal(out0.kp, ramp_kp)
        np.testing.assert_array_equal(out0.kd, ramp_kd)
        mid = loop.step(now=t_r + 0.125, command=command, policy_target=policy)
        np.testing.assert_allclose(mid.target, 0.5 * ramp_target + 0.5 * policy, atol=1e-12)
        np.testing.assert_allclose(mid.kp, 0.5 * ramp_kp + 10.0, atol=1e-12)
        np.testing.assert_allclose(mid.kd, 0.5 * ramp_kd + 0.25, atol=1e-12)
        end = loop.step(now=t_r + 0.25, command=command, policy_target=policy)
        self.assertEqual((end.mode, end.reason), ("RL", "rejoin_complete"))
        np.testing.assert_array_equal(end.kp, np.full(12, 20.0))
        self.assertEqual(loop.hold.counters["entry_ramps_complete"], 0)
        self.assertIsNone(loop.hold.status()["last_entry"]["entry_ramp_complete_t_s"])
        # The next entry starts a fresh ramp from the V12 gains.
        loop.k = int(round((t_r + 0.25) / DT)) + 1
        out = loop.run_until("STAND_TRANSITION", joint_pos=self.q0, policy_target=self.policy)
        np.testing.assert_array_equal(out.kp, np.full(12, 20.0))
        np.testing.assert_array_equal(out.target, self.policy)
        out = loop.run_until_reason("entry_gain_ramp_complete", joint_pos=self.q0, policy_target=self.policy)
        np.testing.assert_array_equal(out.kp, np.full(12, 60.0))
        self.assertEqual(loop.hold.counters["entries"], 2)
        self.assertEqual(loop.hold.counters["entry_ramps_complete"], 1)

    def test_joint_limits_clip_every_ramp_target(self):
        lower = self.q0 - 0.01
        upper = self.q0 + 0.01
        loop = Loop(joint_lower=lower, joint_upper=upper)
        outs = []
        for _ in range(100):
            out = loop.step(joint_pos=self.q0, policy_target=self.policy)
            if out.mode == "STAND_TRANSITION" or outs:
                outs.append(out)
            if len(outs) > self.RAMP_STEPS:
                break
        self.assertEqual(len(outs), self.RAMP_STEPS + 1)
        for out in outs:
            np.testing.assert_array_equal(out.target, np.clip(out.target, lower, upper))


class TransitionAndRejoinTests(unittest.TestCase):
    def enter_fixed(self, loop):
        loop.run_until("STAND_TRANSITION")
        entry_t = loop.outputs[-1][0]
        # Torque-matched seed for the Loop defaults (q = Q_STAND + 0.01, previous
        # target = policy = Q_STAND + 0.03, Kp0 = 20); reached at the end of the ramp.
        q = Q_STAND + 0.01
        hold_target = q + (np.full(12, 20.0) / np.full(12, 60.0)) * ((Q_STAND + 0.03) - q)
        out = loop.run_until("FIXED_STAND")
        return entry_t, hold_target, out

    def test_transition_lasts_two_seconds_then_fixed_stand(self):
        loop = Loop()
        entry_t, hold_target, out = self.enter_fixed(loop)
        fixed_t = loop.outputs[-1][0]
        self.assertGreaterEqual(fixed_t - entry_t, sh.TRANSITION_S - 1e-9)
        self.assertLess(loop.outputs[-2][0] - entry_t, sh.TRANSITION_S - 1e-9)
        self.assertEqual(out.reason, "fixed_stand_active")
        transition = [(t, o) for t, o in loop.outputs if o.mode in ("STAND_TRANSITION", "FIXED_STAND")]
        # Before PRD D4 every output here was the seed at Kp 60. Now only outputs
        # at or after the 0.5 s entry ramp are; the ramp is checked in EntryRampTests.
        after_ramp = [o for t, o in transition if t - entry_t >= sh.ENTRY_RAMP_S - 1e-9]
        self.assertEqual(len(after_ramp), len(transition) - 25)
        for _t, item in transition:
            self.assertFalse(item.policy_owns_joints)
        for item in after_ramp:
            np.testing.assert_array_equal(item.target, hold_target)
            np.testing.assert_array_equal(item.kp, np.full(12, 60.0))
            np.testing.assert_array_equal(item.kd, np.full(12, 1.0))
        self.assertEqual(loop.hold.counters["fixed_stand"], 1)
        out = loop.run(5.0)
        self.assertEqual(out.mode, "FIXED_STAND")
        np.testing.assert_array_equal(out.target, hold_target)

    def test_nonzero_command_cancels_settling(self):
        loop = Loop()
        loop.run(0.1)
        out = loop.step(command=np.array([0.2, 0.0, 0.0]))
        self.assertEqual(out.mode, "RL")
        self.assertEqual(out.reason, "fixed_stand_cancelled:new_command")
        self.assertTrue(out.policy_owns_joints)
        self.assertEqual(loop.hold.counters["settle_cancels"], 1)
        out = loop.step()
        self.assertEqual(out.mode, "STAND_SETTLING")

    def check_rejoin(self, loop, start_mode):
        t_r = loop.outputs[-1][0] + DT
        hold_target = loop.target.copy()
        hold_kp, hold_kd = loop.kp.copy(), loop.kd.copy()
        self.assertEqual(loop.hold.mode, start_mode)
        policy = Q_STAND - 0.1
        command = np.array([0.3, 0.0, 0.0])
        out0 = loop.step(now=t_r, command=command, policy_target=policy)
        self.assertEqual(out0.mode, "REJOIN")
        self.assertEqual(out0.reason, "new_command_rejoin")
        np.testing.assert_array_equal(out0.target, hold_target)
        np.testing.assert_array_equal(out0.kp, hold_kp)
        np.testing.assert_array_equal(out0.kd, hold_kd)
        self.assertFalse(out0.policy_owns_joints)
        mid = loop.step(now=t_r + 0.125, command=command, policy_target=policy)
        self.assertEqual(mid.mode, "REJOIN")
        np.testing.assert_allclose(mid.target, 0.5 * hold_target + 0.5 * policy, atol=1e-12)
        np.testing.assert_allclose(mid.kp, np.full(12, 40.0), atol=1e-12)
        np.testing.assert_allclose(mid.kd, np.full(12, 0.75), atol=1e-12)
        self.assertAlmostEqual(mid.progress, 0.5)
        end = loop.step(now=t_r + 0.25, command=command, policy_target=policy)
        self.assertEqual(end.mode, "RL")
        self.assertEqual(end.reason, "rejoin_complete")
        self.assertTrue(end.policy_owns_joints)
        np.testing.assert_array_equal(end.target, policy)
        np.testing.assert_array_equal(end.kp, np.full(12, 20.0))
        np.testing.assert_array_equal(end.kd, np.full(12, 0.5))
        self.assertEqual(loop.hold.counters["rejoin_complete"], 1)

    def test_rejoin_from_fixed_stand_blends_target_and_gains(self):
        loop = Loop()
        self.enter_fixed(loop)
        self.check_rejoin(loop, "FIXED_STAND")

    def test_rejoin_from_transition(self):
        loop = Loop()
        loop.run_until("STAND_TRANSITION")
        loop.run(0.5)
        self.check_rejoin(loop, "STAND_TRANSITION")

    def test_rejoin_finishes_when_command_returns_to_zero_then_rearms(self):
        loop = Loop()
        self.enter_fixed(loop)
        out = loop.step(command=np.array([0.2, 0.0, 0.0]))
        self.assertEqual(out.mode, "REJOIN")
        out = loop.step()
        self.assertEqual(out.mode, "REJOIN")
        out = loop.run_until("RL")
        self.assertEqual(out.reason, "rejoin_complete")
        out = loop.step()
        self.assertEqual(out.mode, "STAND_SETTLING")

    def test_rejoin_blend_is_monotonic_smoothstep(self):
        loop = Loop()
        self.enter_fixed(loop)
        kps = []
        command = np.array([0.0, 0.2, 0.0])
        while True:
            out = loop.step(command=command)
            kps.append(float(out.kp[0]))
            if out.mode == "RL":
                break
        self.assertEqual(kps[0], 60.0)
        self.assertEqual(kps[-1], 20.0)
        self.assertTrue(all(b <= a for a, b in zip(kps, kps[1:])))
        # Entry output (blend 0), 12 blended outputs, then the RL output at +0.26 s.
        self.assertEqual(len(kps), math.ceil(sh.REJOIN_S / DT) + 1)


class DisturbanceTests(unittest.TestCase):
    def fixed(self):
        loop = Loop()
        loop.run_until("FIXED_STAND")
        return loop

    def test_contact_loss_exits_after_persistence_then_lockout(self):
        loop = self.fixed()
        lost = np.array([30.0, 30.0, 1.0, 30.0])
        start = loop.k * DT
        exit_t = None
        for _ in range(30):
            out = loop.step(foot_forces=lost)
            now = loop.outputs[-1][0]
            if out.mode == "RL":
                exit_t = now
                break
            self.assertEqual(out.mode, "FIXED_STAND")
            self.assertLess(now - start, sh.DISTURBANCE_DWELL_S - 1e-9)
        self.assertIsNotNone(exit_t)
        self.assertGreaterEqual(exit_t - start, sh.DISTURBANCE_DWELL_S - 1e-9)
        self.assertEqual(out.reason, "fixed_stand_disturbance:four_contact")
        self.assertTrue(out.policy_owns_joints)
        np.testing.assert_array_equal(out.kp, np.full(12, 20.0))
        self.assertEqual(loop.hold.counters["disturbance_exits"], 1)
        rearm_t = None
        for _ in range(60):
            out = loop.step()
            now = loop.outputs[-1][0]
            if out.mode != "RL":
                rearm_t = now
                break
        self.assertIsNotNone(rearm_t)
        self.assertEqual(out.mode, "STAND_SETTLING")
        self.assertGreaterEqual(rearm_t - exit_t, sh.REENTRY_LOCKOUT_S - 1e-9)
        self.assertLess(rearm_t - exit_t, sh.REENTRY_LOCKOUT_S + DT + 1e-9)

    def test_short_disturbance_resets_and_reason_change_restarts_timer(self):
        loop = self.fixed()
        loop.run(0.2, linear_speed=0.2)
        loop.step()
        loop.run(0.2, tilt_deg=11.0)
        out = loop.run(0.2, angular_speed=0.6)
        self.assertEqual(out.mode, "FIXED_STAND")
        # Samples at +0.20, +0.22, +0.24 s after the first angular sample stay in the hold.
        out = loop.run(0.06, angular_speed=0.6)
        self.assertEqual(out.mode, "FIXED_STAND")
        out = loop.step(angular_speed=0.6)
        self.assertEqual(out.mode, "RL")
        self.assertEqual(out.reason, "fixed_stand_disturbance:angular_speed")

    def test_each_disturbance_kind_exits(self):
        for name, over in [("linear_speed", dict(linear_speed=0.16)), ("angular_speed", dict(angular_speed=0.51)),
                           ("tilt", dict(tilt_deg=10.5)), ("four_contact", dict(foot_forces=np.array([0.0, 30, 30, 30])))]:
            with self.subTest(kind=name):
                loop = self.fixed()
                out = loop.run(0.3, **over)
                self.assertEqual(out.reason, "fixed_stand_disturbance:" + name)

    def test_transition_is_not_disturbance_checked(self):
        loop = Loop()
        loop.run_until("STAND_TRANSITION")
        out = loop.run(1.0, foot_forces=np.array([30.0, 30.0, 0.0, 30.0]))
        self.assertEqual(out.mode, "STAND_TRANSITION")


class FailClosedTests(unittest.TestCase):
    def test_nonfinite_or_malformed_input_latches_failure(self):
        cases = [
            dict(joint_pos=np.full(12, math.nan)),
            dict(policy_target=np.full(12, math.inf)),
            dict(linear_speed=math.nan),
            dict(tilt_deg=math.inf),
            dict(foot_forces=np.array([1.0, 2.0, math.nan, 3.0])),
            dict(command=np.array([0.0, 0.0])),
            dict(applied_kp=np.full(11, 20.0)),
            dict(applied_kp=np.full(12, -1.0)),
            dict(applied_kd=np.full(12, -0.1)),
            dict(now_s=True),
            dict(angular_speed="fast"),
        ]
        for over in cases:
            with self.subTest(case=sorted(over)):
                loop = Loop()
                loop.run(0.1)
                with self.assertRaises(sh.StanceHoldError):
                    loop.step(**over)
                with self.assertRaisesRegex(sh.StanceHoldError, "already failed"):
                    loop.step()
                self.assertIsNotNone(loop.hold.status()["failure"])

    def test_time_must_not_go_backwards(self):
        loop = Loop()
        loop.step(now=1.0)
        with self.assertRaisesRegex(sh.StanceHoldError, "backwards"):
            loop.step(now=0.5)


class RecordTests(unittest.TestCase):
    def test_status_records_transitions_counters_and_mode_time(self):
        loop = Loop()
        loop.run_until("FIXED_STAND")
        loop.run(1.0)
        loop.step(command=np.array([0.2, 0.0, 0.0]))
        loop.run_until("RL", command=np.array([0.2, 0.0, 0.0]))
        status = loop.hold.status()
        self.assertEqual([(t["from"], t["to"]) for t in status["transitions"]], [
            ("RL", "STAND_SETTLING"), ("STAND_SETTLING", "STAND_TRANSITION"),
            ("STAND_TRANSITION", "FIXED_STAND"), ("FIXED_STAND", "REJOIN"), ("REJOIN", "RL")])
        self.assertEqual(status["transition_counts"]["FIXED_STAND->REJOIN"], 1)
        self.assertAlmostEqual(status["mode_time_s"]["STAND_TRANSITION"], 2.0, places=6)
        # 0.25 s is not a multiple of the 0.02 s control period: REJOIN ends at +0.26 s.
        self.assertAlmostEqual(status["mode_time_s"]["REJOIN"], 0.26, places=6)
        self.assertAlmostEqual(sum(status["mode_time_s"].values()), loop.outputs[-1][0], places=6)
        self.assertEqual(status["constants"]["hold_kp"], 60.0)

    def test_module_imports_only_stdlib_and_numpy(self):
        tree = ast.parse(Path(sh.__file__).read_text(encoding="utf-8"), feature_version=(3, 8))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        self.assertEqual(names, {"math", "typing", "numpy"})


if __name__ == "__main__":
    unittest.main()
