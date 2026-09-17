#!/usr/bin/env python3
"""PD stance hold state machine for the patched V12 Isaac Building runner.

Pure Python + NumPy; no Isaac, Torch or ROS import. `materialize_runner_patch.py`
inserts the text between the two body markers verbatim into the patched runner,
so the executed runner stays one hash-recorded file. Keep the body free of
`from __future__` imports and of Python syntax newer than 3.8.

Port of the stand path of `LocalMotionFSM` (RL -> STAND_SETTLING ->
STAND_TRANSITION -> FIXED_STAND -> REJOIN) from the read-only reference

    machine-dog/0_trials/2026-08-22/v17a28_mujoco_wasd/run_v17a28_mujoco_wasd.py
    (machine-dog commit fd751b8b, file SHA-256
    7f6a78323fc7f897cb85a614e4614daabfbe067dcd879c090421e5989a14d180; cited below as MJ)

with the whole-body torque-matched seed only. Not ported: the per-leg latch,
damping/passive/battery modes, boot-in-stand, explicit fixed_stand requests,
and the auto-stand delay knob (its default 0 s is used). Base gains are the V12
`Lite3ActuatorCfg` values instead of MuJoCo's KP/KD arrays.

Isaac-specific departure (PRD D4): STAND_TRANSITION starts with a 0.5 s entry
gain ramp instead of MJ's immediate switch to the hold gains. The V12
`Lite3Actuator` applies position targets a few physics substeps late but gains
at once, so an immediate Kp step multiplies the old target error (run
stand_20260917T125239Z_hold_auto hopped at entry). The ramp keeps the stiffness
torque on the entry joint positions constant at every control step.

Entry damping variants (PRD D5): `entry_kd="ramp"` (default) lets Kd follow the
Kp ramp; `"step1"` applies the hold Kd from the entry step on; `"step2p5"`
applies Kd 2.5 from the entry step and eases it to the hold Kd between the end
of the ramp and FIXED_STAND. Kd acts on measured joint velocity, which the
actuator does not delay. Kp and the target follow the ramp in every variant.

Task: .trellis/tasks/09-17-isaac-runner-stance-hold (design.md section 2).
"""

# >>> stance_hold runner body begin
import math
from typing import Dict

import numpy as np

STANCE_HOLD_MODES = ("off", "auto")
STANCE_HOLD_FSM_MODES = ("RL", "STAND_SETTLING", "STAND_TRANSITION", "FIXED_STAND", "REJOIN")
STANCE_HOLD_JOINT_COUNT = 12
STANCE_HOLD_FOOT_ORDER = ("FL", "FR", "HL", "HR")

# V12 Lite3ActuatorCfg "Hip"/"Knee": stiffness 20.0, damping 0.5 (robot_lab
# assets/deeprobotics.py LITE3_CFG_V12). Replaces MJ KP/KD (MJ:71-72).
BASE_KP = 20.0
BASE_KD = 0.5
# MJ FIXED_STAND_KP / FIXED_STAND_KD (MJ:119-120), MuJoCo-qualified hold gains.
HOLD_KP = 60.0
HOLD_KD = 1.0
# MJ HOLD_COMMAND_DEADBAND (MJ:109); compared with max |command| (MJ:1561, 1585).
COMMAND_DEADBAND = 1.0e-3
# MJ HOLD_LINEAR_SPEED_LIMIT / HOLD_ANGULAR_SPEED_LIMIT (MJ:110-111). Norms of
# the full 3-D base linear/angular velocity (MJ _hold_motion_metrics, MJ:2374-2396).
SETTLE_LINEAR_SPEED_MAX = 0.15
SETTLE_ANGULAR_SPEED_MAX = 0.5
# MJ HOLD_TILT_LIMIT_DEG (MJ:112): angle between body z and world z.
TILT_MAX_DEG = 10.0
# MJ FIXED_STAND_ENTRY_FORCE_N (MJ:152): every foot >= 10 N to enter.
ENTRY_FOOT_FORCE_N = 10.0
# MJ FIXED_STAND_DWELL_S (MJ:121).
SETTLE_DWELL_S = 0.25
# MJ FIXED_STAND_BALANCE_LOW/HIGH (MJ:159-160): dwell-mean front (FL+FR), left
# (FL+HL) and diagonal (FL+HR) shares of the total foot force (MJ:1660-1672).
BALANCE_LOW = 0.35
BALANCE_HIGH = 0.65
# MJ FIXED_STAND_TRANSITION_S / FIXED_STAND_REJOIN_S (MJ:127-128).
TRANSITION_S = 2.0
REJOIN_S = 0.25
# Not in MJ (MJ has no actuator delay). Isaac-specific, PRD D4 (Dr Sun,
# 2026-09-17): at the start of STAND_TRANSITION, Kp/Kd move from the gains
# applied at entry (Kp0, Kd0) to HOLD_KP/HOLD_KD along a smoothstep over this
# time, and the target moves so that Kp(t) * (target(t) - q0) = Kp0 * (T0 - q0),
# with q0 and T0 the joint positions and applied target at entry. The first
# transition step therefore repeats the applied target and gains, and the ramp
# ends at the torque-matched seed with the hold gains. It must end before
# TRANSITION_S.
ENTRY_RAMP_S = 0.5
# Entry damping variants (PRD D5, Dr Sun 2026-09-17). Kp and the target follow
# the entry ramp above in every variant; only Kd differs:
#   ramp    - Kd follows the Kp ramp from Kd0 to HOLD_KD (the PRD D4 behaviour);
#   step1   - Kd is HOLD_KD from the entry step on;
#   step2p5 - Kd is ENTRY_LANDING_KD from the entry step until ENTRY_RAMP_S, then
#             eases (smoothstep) to HOLD_KD at TRANSITION_S, where FIXED_STAND
#             starts with exactly HOLD_KD.
# Precedent for the raised damping: MJ BOOT_LANDING_KD = 2.5 over the
# FIXED_STAND_BOOT_GRACE_S = 1.0 s touchdown window (MJ:131-140, 1803), where
# the hold's own Kd 1 let the landing rock the stance. MJ steps back to Kd 1 at
# the end of its grace; the step2p5 variant eases instead.
STANCE_ENTRY_KD_MODES = ("ramp", "step1", "step2p5")
STANCE_ENTRY_KD_DEFAULT = "ramp"
ENTRY_LANDING_KD = 2.5
# MJ FIXED_STAND_CONTACT_THRESHOLD (MJ:130): hold needs every foot > 1 N.
HOLD_CONTACT_N = 1.0
# MJ FIXED_STAND_DISTURBANCE_DWELL_S (MJ:129) and HOLD_REENTRY_LOCKOUT_S (MJ:108).
DISTURBANCE_DWELL_S = 0.25
REENTRY_LOCKOUT_S = 0.5
# MJ FIXED_STAND_REQUEST_TIMEOUT_S (MJ:126). Auto mode restarts the wait window
# and RL keeps control (MJ:1603-1609).
SETTLE_TIMEOUT_S = 10.0
# MJ compares elapsed times with a 1e-9 s slack (MJ:1573, 1603, 1668, 1734, 1760, 1767).
STANCE_TIME_EPS = 1.0e-9
STANCE_TRANSITION_LOG_LIMIT = 2000


class StanceHoldError(RuntimeError):
    """Invalid hold input. The hold latches failed and the runner stops the case."""


def stance_hold_constants() -> Dict[str, object]:
    """Every constant that shapes the hold, for run records."""
    return {
        "base_kp": BASE_KP,
        "base_kd": BASE_KD,
        "hold_kp": HOLD_KP,
        "hold_kd": HOLD_KD,
        "command_deadband": COMMAND_DEADBAND,
        "settle_linear_speed_max_mps": SETTLE_LINEAR_SPEED_MAX,
        "settle_angular_speed_max_radps": SETTLE_ANGULAR_SPEED_MAX,
        "tilt_max_deg": TILT_MAX_DEG,
        "entry_foot_force_n": ENTRY_FOOT_FORCE_N,
        "settle_dwell_s": SETTLE_DWELL_S,
        "balance_band": [BALANCE_LOW, BALANCE_HIGH],
        "balance_shares": ["FL+FR", "FL+HL", "FL+HR"],
        "transition_s": TRANSITION_S,
        "rejoin_s": REJOIN_S,
        "rejoin_blend": "smoothstep",
        "hold_contact_n": HOLD_CONTACT_N,
        "disturbance_dwell_s": DISTURBANCE_DWELL_S,
        "reentry_lockout_s": REENTRY_LOCKOUT_S,
        "settle_timeout_s": SETTLE_TIMEOUT_S,
        "foot_order": list(STANCE_HOLD_FOOT_ORDER),
        "seed": "q + (applied_kp / HOLD_KP) * (applied_target - q)",
        "entry_ramp_s": ENTRY_RAMP_S,
        "entry_ramp_blend": "smoothstep",
        "entry_ramp_rule": (
            "u = smoothstep((t - t_entry) / entry_ramp_s); Kp = Kp0 + (HOLD_KP - Kp0) u; "
            "Kd = Kd0 + (HOLD_KD - Kd0) u; target = q0 + (Kp0 / Kp) (T0 - q0); "
            "q0, T0, Kp0, Kd0 = joint_pos, applied_target, applied_kp, applied_kd at entry (PRD D4)"
        ),
        "entry_kd_modes": {
            "ramp": "Kd follows the Kp ramp (entry_ramp_rule)",
            "step1": "Kd = HOLD_KD from the entry step on",
            "step2p5": (
                "Kd = entry_landing_kd from the entry step until entry_ramp_s, then "
                "entry_landing_kd + (HOLD_KD - entry_landing_kd) smoothstep((t - t_entry - entry_ramp_s) / "
                "(transition_s - entry_ramp_s)); exactly HOLD_KD from FIXED_STAND on"
            ),
            "precedent": "MJ BOOT_LANDING_KD 2.5 over FIXED_STAND_BOOT_GRACE_S 1.0 s (PRD D5)",
        },
        "entry_landing_kd": ENTRY_LANDING_KD,
        "reference": (
            "machine-dog 0_trials/2026-08-22/v17a28_mujoco_wasd/run_v17a28_mujoco_wasd.py "
            "LocalMotionFSM stand path (commit fd751b8b)"
        ),
    }


def _stance_progress(elapsed_s: float, duration_s: float) -> float:
    """MJ _motion_progress (MJ:1228-1230)."""
    return float(np.clip(elapsed_s / duration_s, 0.0, 1.0))


def _stance_smoothstep(progress: float) -> float:
    """MJ _motion_smoothstep (MJ:1233-1236)."""
    progress = float(np.clip(progress, 0.0, 1.0))
    return progress * progress * (3.0 - 2.0 * progress)


class HoldInput:
    """One control-step sample. Joint vectors use one consistent joint order.

    A plain class on purpose: the patched runner is loaded with `exec_module`
    under `from __future__ import annotations`, and dataclass field
    inspection then needs the module in `sys.modules`.
    """

    __slots__ = ("now_s", "command", "joint_pos", "joint_vel", "policy_target", "applied_target",
                 "applied_kp", "applied_kd", "linear_speed", "angular_speed", "tilt_deg", "foot_forces")

    def __init__(self, now_s, command, joint_pos, joint_vel, policy_target, applied_target,
                 applied_kp, applied_kd, linear_speed, angular_speed, tilt_deg, foot_forces):
        self.now_s = now_s
        self.command = command
        self.joint_pos = joint_pos
        self.joint_vel = joint_vel
        self.policy_target = policy_target
        self.applied_target = applied_target
        self.applied_kp = applied_kp
        self.applied_kd = applied_kd
        self.linear_speed = linear_speed
        self.angular_speed = angular_speed
        self.tilt_deg = tilt_deg
        self.foot_forces = foot_forces


class HoldOutput:
    """Joint target and gains for the next control step."""

    __slots__ = ("target", "kp", "kd", "policy_owns_joints", "mode", "reason", "progress")

    def __init__(self, target, kp, kd, policy_owns_joints, mode, reason, progress):
        self.target = target
        self.kp = kp
        self.kd = kd
        self.policy_owns_joints = policy_owns_joints
        self.mode = mode
        self.reason = reason
        self.progress = progress


def _stance_vector(name: str, value, size: int) -> np.ndarray:
    array = np.array(value, dtype=np.float64, copy=True)
    if array.shape != (size,):
        raise StanceHoldError("%s must have shape (%d,), got %s" % (name, size, array.shape))
    if not np.isfinite(array).all():
        raise StanceHoldError("%s is not finite" % name)
    return array


def _stance_scalar(name: str, value) -> float:
    if isinstance(value, bool):
        raise StanceHoldError("%s must be a number" % name)
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise StanceHoldError("%s must be a number" % name)
    if not math.isfinite(result):
        raise StanceHoldError("%s is not finite" % name)
    return result


class StanceHold:
    """Stand path of MJ LocalMotionFSM with automatic entry (MJ:1329-1821)."""

    def __init__(self, mode: str = "off", joint_lower=None, joint_upper=None,
                 joint_count: int = STANCE_HOLD_JOINT_COUNT,
                 entry_kd: str = STANCE_ENTRY_KD_DEFAULT) -> None:
        if mode not in STANCE_HOLD_MODES:
            raise ValueError("stance hold mode must be one of %s, got %r" % (STANCE_HOLD_MODES, mode))
        if entry_kd not in STANCE_ENTRY_KD_MODES:
            raise ValueError("entry_kd must be one of %s, got %r" % (STANCE_ENTRY_KD_MODES, entry_kd))
        self.entry_kd = entry_kd
        if (joint_lower is None) != (joint_upper is None):
            raise ValueError("joint_lower and joint_upper must be given together")
        self.setting = mode
        self.joint_count = int(joint_count)
        self._lower = None
        self._upper = None
        if joint_lower is not None:
            lower = np.array(joint_lower, dtype=np.float64, copy=True)
            upper = np.array(joint_upper, dtype=np.float64, copy=True)
            shape = (self.joint_count,)
            if lower.shape != shape or upper.shape != shape:
                raise ValueError("joint limits must have shape %s" % (shape,))
            if not (np.isfinite(lower).all() and np.isfinite(upper).all() and np.all(lower < upper)):
                raise ValueError("joint limits must be finite with lower < upper")
            self._lower, self._upper = lower, upper
        self._base_kp = np.full(self.joint_count, BASE_KP)
        self._base_kd = np.full(self.joint_count, BASE_KD)
        self._hold_kp = np.full(self.joint_count, HOLD_KP)
        self._hold_kd = np.full(self.joint_count, HOLD_KD)
        self._landing_kd = np.full(self.joint_count, ENTRY_LANDING_KD)
        self.reset()

    def reset(self) -> None:
        self.mode = "RL"
        self.reason = "reset"
        self.progress = 0.0
        self.failure = None
        self._phase_start = 0.0
        self._settle_started = None
        self._settle_split_sum = np.zeros(3)
        self._settle_split_count = 0
        self._settle_block_reason = "dwell"
        self._hold_target = None
        self._entry_q0 = None
        self._entry_target0 = None
        self._entry_kp0 = None
        self._entry_kd0 = None
        self._entry_ramp_done = False
        self._rejoin_target = None
        self._rejoin_kp = None
        self._rejoin_kd = None
        self._reentry_until = -math.inf
        self._disturbance_started = None
        self._disturbance_reason = None
        self._last_now = None
        self.transitions = []
        self.transitions_dropped = 0
        self.counters = {
            "updates": 0,
            "settle_starts": 0,
            "settle_cancels": 0,
            "settle_timeouts": 0,
            "support_balance_blocks": 0,
            "entries": 0,
            "entry_ramps_complete": 0,
            "fixed_stand": 0,
            "rejoins": 0,
            "rejoin_complete": 0,
            "disturbance_exits": 0,
        }
        self.mode_time_s = {name: 0.0 for name in STANCE_HOLD_FSM_MODES}
        self.last_entry = None

    # -- bookkeeping ---------------------------------------------------------
    def _set_mode(self, mode: str, reason: str, now: float) -> None:
        previous = self.mode
        self.mode = mode
        self.reason = reason
        if previous == mode:
            return
        if len(self.transitions) < STANCE_TRANSITION_LOG_LIMIT:
            self.transitions.append({"t_s": float(now), "from": previous, "to": mode, "reason": reason})
        else:
            self.transitions_dropped += 1

    def status(self) -> Dict[str, object]:
        pairs = {}
        for item in self.transitions:
            key = "%s->%s" % (item["from"], item["to"])
            pairs[key] = pairs.get(key, 0) + 1
        return {
            "setting": self.setting,
            "entry_kd": self.entry_kd,
            "mode": self.mode,
            "reason": self.reason,
            "progress": float(self.progress),
            "failure": self.failure,
            "counters": dict(self.counters),
            "mode_time_s": dict(self.mode_time_s),
            "transition_counts": pairs,
            "transitions": list(self.transitions),
            "transitions_dropped": self.transitions_dropped,
            "last_entry": None if self.last_entry is None else dict(self.last_entry),
            "joint_limits_applied": self._lower is not None,
            "constants": stance_hold_constants(),
        }

    def _fail(self, message: str) -> None:
        self.failure = message
        raise StanceHoldError(message)

    def _clip_target(self, target: np.ndarray) -> np.ndarray:
        # MJ _non_rl_motion_control clips every supervisor target (MJ:1223).
        if self._lower is None:
            return target
        return np.clip(target, self._lower, self._upper)

    def _entry_ramp(self, elapsed_s: float):
        """Target, Kp, Kd and blend of the entry gain ramp (PRD D4).

        The end points are returned exactly: blend 0 gives the applied target and
        gains at entry, blend 1 gives the torque-matched seed and the hold gains.
        """
        if elapsed_s + STANCE_TIME_EPS >= ENTRY_RAMP_S:
            return self._hold_target, self._hold_kp, self._hold_kd, 1.0
        blend = _stance_smoothstep(elapsed_s / ENTRY_RAMP_S)
        if blend <= 0.0:
            return self._entry_target0, self._entry_kp0, self._entry_kd0, 0.0
        kp = self._entry_kp0 + (self._hold_kp - self._entry_kp0) * blend
        kd = self._entry_kd0 + (self._hold_kd - self._entry_kd0) * blend
        # kp > 0: Kp0 >= 0 is validated, HOLD_KP > 0 and blend > 0.
        target = self._entry_q0 + (self._entry_kp0 / kp) * (self._entry_target0 - self._entry_q0)
        return target, kp, kd, blend

    def _entry_damping(self, elapsed_s: float, ramp_kd):
        """Kd during STAND_TRANSITION for the configured entry damping variant (PRD D5)."""
        if self.entry_kd == "ramp":
            return ramp_kd
        if self.entry_kd == "step1":
            return self._hold_kd
        if self.entry_kd == "step2p5":
            if elapsed_s + STANCE_TIME_EPS < ENTRY_RAMP_S:
                return self._landing_kd
            if elapsed_s + STANCE_TIME_EPS >= TRANSITION_S:
                return self._hold_kd
            blend = _stance_smoothstep((elapsed_s - ENTRY_RAMP_S) / (TRANSITION_S - ENTRY_RAMP_S))
            if blend <= 0.0:
                return self._landing_kd
            return self._landing_kd + (self._hold_kd - self._landing_kd) * blend
        self._fail("unhandled entry_kd variant: " + str(self.entry_kd))

    # -- update ----------------------------------------------------------------
    def update(self, x: HoldInput) -> HoldOutput:
        if self.setting == "off":
            # Stateless pass-through: exactly the policy target at V12 gains.
            return HoldOutput(
                target=np.array(x.policy_target, dtype=np.float64, copy=True),
                kp=self._base_kp.copy(),
                kd=self._base_kd.copy(),
                policy_owns_joints=True,
                mode="OFF",
                reason="stance_hold_off",
                progress=0.0,
            )
        if self.failure is not None:
            raise StanceHoldError("stance hold already failed: " + self.failure)
        n = self.joint_count
        try:
            now = _stance_scalar("now_s", x.now_s)
            command = _stance_vector("command", x.command, 3)
            joint_pos = _stance_vector("joint_pos", x.joint_pos, n)
            _stance_vector("joint_vel", x.joint_vel, n)
            policy_target = _stance_vector("policy_target", x.policy_target, n)
            applied_target = _stance_vector("applied_target", x.applied_target, n)
            applied_kp = _stance_vector("applied_kp", x.applied_kp, n)
            applied_kd = _stance_vector("applied_kd", x.applied_kd, n)
            linear_speed = _stance_scalar("linear_speed", x.linear_speed)
            angular_speed = _stance_scalar("angular_speed", x.angular_speed)
            tilt_deg = _stance_scalar("tilt_deg", x.tilt_deg)
            forces = _stance_vector("foot_forces", x.foot_forces, len(STANCE_HOLD_FOOT_ORDER))
        except StanceHoldError as exc:
            self._fail(str(exc))
        if bool(np.any(applied_kp < 0.0) or np.any(applied_kd < 0.0)):
            # The entry ramp divides by a blend of Kp0 and HOLD_KP.
            self._fail("applied_kp and applied_kd must not be negative")
        if self._last_now is not None and now < self._last_now - STANCE_TIME_EPS:
            self._fail("now_s went backwards: %.9f < %.9f" % (now, self._last_now))
        if self._last_now is not None:
            self.mode_time_s[self.mode] += now - self._last_now
        self._last_now = now
        self.counters["updates"] += 1
        zero_command = float(np.max(np.abs(command))) <= COMMAND_DEADBAND

        # Automatic arming with zero delay (MJ:1557-1581).
        if self.mode == "RL" and zero_command and now >= self._reentry_until:
            self._set_mode("STAND_SETTLING", "waiting_for_quiet_four_contact", now)
            self.progress = 0.0
            self._phase_start = now
            self._settle_started = None
            self.counters["settle_starts"] += 1

        if self.mode == "STAND_SETTLING":
            # Whole-body settle gate (MJ:1583-1708, per-leg latch path omitted).
            failure = None
            if not zero_command:
                failure = "new_command"
            elif linear_speed > SETTLE_LINEAR_SPEED_MAX:
                failure = "linear_speed"
            elif angular_speed > SETTLE_ANGULAR_SPEED_MAX:
                failure = "angular_speed"
            elif tilt_deg > TILT_MAX_DEG:
                failure = "tilt"
            elif not bool(np.all(forces >= ENTRY_FOOT_FORCE_N)):
                failure = "four_contact"
            if failure == "new_command":
                self._set_mode("RL", "fixed_stand_cancelled:new_command", now)
                self.progress = 0.0
                self._settle_started = None
                self.counters["settle_cancels"] += 1
            elif now - self._phase_start + STANCE_TIME_EPS >= SETTLE_TIMEOUT_S:
                # Auto mode: RL keeps control; restart the wait window (MJ:1603-1609).
                self._phase_start = now
                self.counters["settle_timeouts"] += 1
            elif failure is None:
                if self._settle_started is None:
                    self._settle_started = now
                    self._settle_split_sum = np.zeros(3)
                    self._settle_split_count = 0
                self._settle_split_sum += np.array([
                    forces[0] + forces[1],
                    forces[0] + forces[2],
                    forces[0] + forces[3],
                ]) / float(np.sum(forces))
                self._settle_split_count += 1
                dwell = now - self._settle_started
                self.progress = _stance_progress(dwell, SETTLE_DWELL_S)
                if dwell + STANCE_TIME_EPS >= SETTLE_DWELL_S:
                    splits = self._settle_split_sum / self._settle_split_count
                    if bool(np.any(splits < BALANCE_LOW) or np.any(splits > BALANCE_HIGH)):
                        self._settle_started = None
                        self._settle_block_reason = "support_balance"
                        self.progress = 0.0
                        self.reason = "waiting_for_support_balance"
                        self.counters["support_balance_blocks"] += 1
                    else:
                        # Torque-matched seed (MJ:1686-1703): the target offset that
                        # reproduces the applied PD stiffness torque at the hold gain.
                        self._hold_target = joint_pos + (applied_kp / self._hold_kp) * (
                            applied_target - joint_pos
                        )
                        # Entry gain ramp start point (PRD D4).
                        self._entry_q0 = joint_pos.copy()
                        self._entry_target0 = applied_target.copy()
                        self._entry_kp0 = applied_kp.copy()
                        self._entry_kd0 = applied_kd.copy()
                        self._entry_ramp_done = False
                        self._set_mode("STAND_TRANSITION", "quiet_four_contact_confirmed", now)
                        self.progress = 0.0
                        self._phase_start = now
                        self.counters["entries"] += 1
                        stiffness_torque = applied_kp * (applied_target - joint_pos)
                        self.last_entry = {
                            "t_s": now,
                            "support_shares": [float(v) for v in splits],
                            "dwell_samples": int(self._settle_split_count),
                            "foot_forces_n": [float(v) for v in forces],
                            "entry_ramp_s": ENTRY_RAMP_S,
                            "entry_ramp_complete_t_s": None,
                            "entry_kd": self.entry_kd,
                            "q0": [float(v) for v in joint_pos],
                            "applied_target_t0": [float(v) for v in applied_target],
                            "kp0_mean": float(np.mean(applied_kp)),
                            "kd0_mean": float(np.mean(applied_kd)),
                            "t0_minus_q0_max_abs": float(np.max(np.abs(applied_target - joint_pos))),
                            "seed_minus_t0_max_abs": float(np.max(np.abs(self._hold_target - applied_target))),
                            "stiffness_torque_max_abs_nm": float(np.max(np.abs(stiffness_torque))),
                        }
            else:
                self._settle_started = None
                self._settle_block_reason = failure
                self.progress = 0.0
                self.reason = "waiting_for_" + failure

        if self.mode == "FIXED_STAND" and zero_command:
            # Disturbance exit with persistence (MJ:1709-1746).
            disturbance = None
            if linear_speed > SETTLE_LINEAR_SPEED_MAX:
                disturbance = "linear_speed"
            elif angular_speed > SETTLE_ANGULAR_SPEED_MAX:
                disturbance = "angular_speed"
            elif tilt_deg > TILT_MAX_DEG:
                disturbance = "tilt"
            elif not bool(np.all(forces > HOLD_CONTACT_N)):
                disturbance = "four_contact"
            if disturbance is None:
                self._disturbance_started = None
                self._disturbance_reason = None
            else:
                if self._disturbance_reason != disturbance:
                    self._disturbance_started = now
                    self._disturbance_reason = disturbance
                if now - self._disturbance_started + STANCE_TIME_EPS >= DISTURBANCE_DWELL_S:
                    self._set_mode("RL", "fixed_stand_disturbance:" + disturbance, now)
                    self.progress = 0.0
                    self._reentry_until = now + REENTRY_LOCKOUT_S
                    self._disturbance_started = None
                    self._disturbance_reason = None
                    self.counters["disturbance_exits"] += 1

        if self.mode in ("STAND_TRANSITION", "FIXED_STAND") and not zero_command:
            # New command: blend back from what was actually applied (MJ:1747-1756).
            self._set_mode("REJOIN", "new_command_rejoin", now)
            self.progress = 0.0
            self._phase_start = now
            self._rejoin_target = applied_target.copy()
            self._rejoin_kp = applied_kp.copy()
            self._rejoin_kd = applied_kd.copy()
            # Deviation from MJ: clear the disturbance timer here too, so a stale
            # timer cannot skip the 0.25 s persistence in a later FIXED_STAND.
            self._disturbance_started = None
            self._disturbance_reason = None
            self.counters["rejoins"] += 1
        ramp = None
        if self.mode == "STAND_TRANSITION":
            elapsed = now - self._phase_start
            self.progress = _stance_progress(elapsed, TRANSITION_S)
            ramp = self._entry_ramp(elapsed)
            ramp = (ramp[0], ramp[1], self._entry_damping(elapsed, ramp[2]), ramp[3])
            # The entry step (blend 0) keeps the transition reason; later steps
            # name the ramp so metrics rows show when the hold gains are reached.
            if ramp[3] >= 1.0:
                self.reason = "entry_gain_ramp_complete"
                if not self._entry_ramp_done:
                    self._entry_ramp_done = True
                    self.counters["entry_ramps_complete"] += 1
                    if self.last_entry is not None:
                        self.last_entry["entry_ramp_complete_t_s"] = now
            elif ramp[3] > 0.0:
                self.reason = "entry_gain_ramp"
            if elapsed + STANCE_TIME_EPS >= TRANSITION_S:
                self._set_mode("FIXED_STAND", "fixed_stand_active", now)
                self.progress = 1.0
                self.counters["fixed_stand"] += 1
        if self.mode == "REJOIN":
            elapsed = now - self._phase_start
            self.progress = _stance_progress(elapsed, REJOIN_S)
            if elapsed + STANCE_TIME_EPS >= REJOIN_S:
                self._set_mode("RL", "rejoin_complete", now)
                self.progress = 1.0
                self.counters["rejoin_complete"] += 1

        if self.mode in ("RL", "STAND_SETTLING"):
            return self._output(policy_target, self._base_kp, self._base_kd, True)
        if self.mode == "STAND_TRANSITION":
            return self._output(self._clip_target(ramp[0]), ramp[1], ramp[2], False)
        if self.mode == "FIXED_STAND":
            return self._output(self._clip_target(self._hold_target), self._hold_kp, self._hold_kd, False)
        if self.mode == "REJOIN":
            blend = _stance_smoothstep(self.progress)
            return self._output(
                self._clip_target((1.0 - blend) * self._rejoin_target + blend * policy_target),
                (1.0 - blend) * self._rejoin_kp + blend * self._base_kp,
                (1.0 - blend) * self._rejoin_kd + blend * self._base_kd,
                False,
            )
        self._fail("unhandled stance hold mode: " + str(self.mode))

    def _output(self, target, kp, kd, owns: bool) -> HoldOutput:
        return HoldOutput(
            target=np.array(target, dtype=np.float64, copy=True),
            kp=np.array(kp, dtype=np.float64, copy=True),
            kd=np.array(kd, dtype=np.float64, copy=True),
            policy_owns_joints=bool(owns),
            mode=self.mode,
            reason=self.reason,
            progress=float(self.progress),
        )
# <<< stance_hold runner body end
