"""Building-specific PCT-to-SCAN-to-V12 closed loop on one platform segment.

This entry point owns nothing that the Office/Forest runner owns. It reuses the
pinned V12 loading, task contract capture, transport, dual-cloud conversion and
command-state helpers, and it builds the Building scene the same way the
PCT-only `run_dynamics.py` reference does. The differences from that reference
are deliberate and bounded:

  * navigation LiDAR is restored and retargeted at the Building USD terrain, so
    the planner consumes actual ray hits instead of an offline map;
  * the PCT lookahead follower is gone. Motion comes only from SCAN over TCP;
  * simulation time, body twist and scan identity are published so the planner
    and controller can run on simulation time with real velocity feedback.

Command ownership: `/planning/bspline` -> SCAN `closed_loop_controller` ->
`/quad_0/cmd_vel` -> `CMD_VEL_V1` -> V12 `base_velocity` -> policy -> PD/PhysX.
Nothing in this file generates a motion command.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
import traceback
from contextlib import ExitStack
from pathlib import Path

CASES = ("stand_probe", "flat_nominal", "full_nominal", "native_nominal")
GROUND_MESH_PRIM = "/World/ground"
TERRAIN_MESH_PRIM = "/World/ground/terrain/Mesh"
BUILDING_TRIANGLE_COUNT = 16448


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, payload) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_json_atomic(path: Path, payload) -> None:
    """Write compact JSON through a same-directory atomic rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    tmp.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(str(tmp), str(path))


def _module_origin(name: str) -> str:
    module = sys.modules.get(name)
    if module is None:
        return ""
    origin = getattr(module, "__file__", None)
    return "" if origin is None else str(Path(origin).resolve())


def _validate_runtime_module_origins(runtime: Path) -> dict:
    runtime = Path(runtime).resolve()
    expected = {
        "robot_lab": runtime / "source/robot_lab",
        "rsl_rl": runtime / "source/rsl_rl",
    }
    origins = {name: _module_origin(name) for name in expected}
    for name, root in expected.items():
        origin = origins.get(name) or ""
        root_text = str(root.resolve())
        if not origin.startswith(root_text + os.sep):
            raise AdapterFailure(f"{name} imported from unexpected path: {origin or '<missing>'}; expected under {root_text}")
    return {
        "robot_lab_file": origins["robot_lab"],
        "rsl_rl_file": origins["rsl_rl"],
        "expected_robot_lab_root": str(expected["robot_lab"].resolve()),
        "expected_rsl_rl_root": str(expected["rsl_rl"].resolve()),
        "python_executable": sys.executable,
    }


def _validate_external_goal_args(args) -> None:
    if not args.external_goal_mode:
        return
    if not args.external_run_id or not re.match(r"^[A-Za-z0-9_.:-]{1,128}$", args.external_run_id):
        raise ValueError("--external-goal-mode requires a stable --external-run-id")
    finite_nonnegative = (
        ("--external-finish-stillness-seconds", args.external_finish_stillness_seconds),
        ("--terminal-command-norm", args.terminal_command_norm),
        ("--terminal-speed-mps", args.terminal_speed_mps),
        ("--terminal-yaw-rate-radps", args.terminal_yaw_rate_radps),
    )
    for name, value in finite_nonnegative:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")
    if not isinstance(args.external_status_freshness_seconds, (int, float)) or isinstance(args.external_status_freshness_seconds, bool) or not math.isfinite(float(args.external_status_freshness_seconds)) or args.external_status_freshness_seconds <= 0.0:
        raise ValueError("--external-status-freshness-seconds must be finite and positive")


def _is_plain_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _external_exit_code(status: str, native_trial_exit_code) -> int:
    if status == "EXTERNAL_EPISODE_FINISHED":
        return 0
    if status == "EXTERNAL_EPISODE_FAILED":
        return 3
    return native_trial_exit_code(status)


def _external_finish_status(backend_status: str) -> str:
    if backend_status == "FINISHED":
        return "EXTERNAL_EPISODE_FINISHED"
    if backend_status == "FAILED":
        return "EXTERNAL_EPISODE_FAILED"
    return ""


def _external_zero_command(command, threshold: float) -> bool:
    return (
        math.hypot(float(command[0]), float(command[1])) <= float(threshold)
        and abs(float(command[2])) <= float(threshold)
    )


def _external_finish_step(latched: dict, finish_check: dict, zero_applied: bool,
                          still: bool, sim_time_s: float, dwell_seconds: float) -> tuple:
    """Latch one valid backend request, then wait on local command/stillness."""
    if latched is None:
        if not finish_check.get("requested"):
            return None, None, None
        latched = dict(finish_check)
        latched["latched_sim_time_s"] = sim_time_s
        latched["dwell_start_s"] = None
    if zero_applied and still:
        if latched.get("dwell_start_s") is None:
            latched["dwell_start_s"] = sim_time_s
        elif sim_time_s - float(latched["dwell_start_s"]) >= float(dwell_seconds):
            return latched, latched["dwell_start_s"], str(latched["status"])
    else:
        latched["dwell_start_s"] = None
    return latched, latched.get("dwell_start_s"), None


def _external_request_identity(check: dict) -> dict:
    request = check.get("request") if isinstance(check, dict) else None
    if not isinstance(request, dict):
        return {}
    return {
        "run_id": request.get("run_id"),
        "request_id": request.get("request_id"),
        "observed_run_epoch_ns": request.get("observed_run_epoch_ns"),
        "backend_terminal_status": request.get("backend_terminal_status"),
    }


def _external_finish_request(path: Path, run_id: str, run_epoch_ns: int,
                             now_monotonic_ns: int, max_age_s: float) -> dict:
    """Validate the backend's immutable finish request for this runner epoch."""
    path = Path(path)
    if not path.exists():
        return {"requested": False, "reason": "missing"}
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - evidence should preserve parse failure
        return {"requested": False, "reason": f"invalid_json:{type(exc).__name__}"}
    if not isinstance(request, dict):
        return {"requested": False, "reason": "request_not_object", "request": request}
    if request.get("schema_version") != 1:
        return {"requested": False, "reason": "unsupported_schema", "request": request}
    if request.get("run_id") != run_id:
        return {"requested": False, "reason": "run_id_mismatch", "request": request}
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        return {"requested": False, "reason": "invalid_request_id", "request": request}
    observed_epoch = request.get("observed_run_epoch_ns")
    if not _is_plain_int(observed_epoch):
        return {"requested": False, "reason": "invalid_observed_run_epoch_ns", "request": request}
    if not _is_plain_int(run_epoch_ns) or observed_epoch != run_epoch_ns:
        return {"requested": False, "reason": "run_epoch_mismatch", "request": request}
    requested_at = request.get("requested_at_monotonic_ns")
    if not _is_plain_int(requested_at):
        return {"requested": False, "reason": "missing_requested_at_monotonic_ns", "request": request}
    if not _is_plain_int(now_monotonic_ns):
        return {"requested": False, "reason": "invalid_now_monotonic_ns", "request": request}
    if not isinstance(max_age_s, (int, float)) or isinstance(max_age_s, bool) or not math.isfinite(float(max_age_s)) or max_age_s <= 0.0:
        return {"requested": False, "reason": "invalid_max_age_s", "request": request}
    age_s = (int(now_monotonic_ns) - int(requested_at)) / 1.0e9
    if age_s < -0.025:
        return {"requested": False, "reason": "finish_request_from_future", "request": request}
    if age_s > float(max_age_s):
        return {"requested": False, "reason": "finish_request_stale", "age_s": age_s, "request": request}
    terminal_status = _external_finish_status(request.get("backend_terminal_status"))
    if not terminal_status:
        return {"requested": False, "reason": "backend_not_terminal", "request": request}
    return {
        "requested": True,
        "status": terminal_status,
        "reason": "accepted",
        "age_s": age_s,
        "request": request,
    }


# ---- stance hold state machine, inserted verbatim from stance_hold.py ------
STANCE_HOLD_SOURCE_REL = '.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py'
STANCE_HOLD_SOURCE_SHA256 = '2d244efeea1708b02bc33243789464006af65bb32fc999463548d221d1bc3541'
STANCE_HOLD_BODY_SHA256 = '8dc51c1bfa726b8ae1316d80674912869168f08116d0f58763e2dbcd4b3831ba'
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
                 joint_count: int = STANCE_HOLD_JOINT_COUNT) -> None:
        if mode not in STANCE_HOLD_MODES:
            raise ValueError("stance hold mode must be one of %s, got %r" % (STANCE_HOLD_MODES, mode))
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
            "mode": self.mode,
            "reason": self.reason,
            "progress": float(self.progress),
            "failure": self.failure,
            "counters": dict(self.counters),
            "mode_time_s": dict(self.mode_time_s),
            "transition_counts": pairs,
            "transitions": list(self.transitions),
            "transitions_dropped": self.transitions_dropped,
            "last_entry": self.last_entry,
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
                        self._set_mode("STAND_TRANSITION", "quiet_four_contact_confirmed", now)
                        self.progress = 0.0
                        self._phase_start = now
                        self.counters["entries"] += 1
                        self.last_entry = {
                            "t_s": now,
                            "support_shares": [float(v) for v in splits],
                            "dwell_samples": int(self._settle_split_count),
                            "foot_forces_n": [float(v) for v in forces],
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
        if self.mode == "STAND_TRANSITION":
            elapsed = now - self._phase_start
            self.progress = _stance_progress(elapsed, TRANSITION_S)
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
        if self.mode in ("STAND_TRANSITION", "FIXED_STAND"):
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


# ---- stance hold runner integration (materialize_runner_patch.py) ----------
STANCE_HOLD_ACTION_TERM = "joint_pos"
STANCE_HOLD_ACTUATOR_GROUPS = ("Hip", "Knee")
STANCE_HOLD_ACTUATOR_CLASS = "Lite3Actuator"
STANCE_HOLD_ACTION_SCALE = 0.25
STANCE_HOLD_V12_DEFAULT_POS = (("_HipX_joint", 0.0), ("_HipY_joint", -0.8), ("_Knee_joint", 1.6))
STANCE_HOLD_VALUE_TOL = 1.0e-6
STANCE_HOLD_GAIN_READBACK_TOL = 1.0e-4
STANCE_HOLD_TORQUE_CLIP_TOL_NM = 1.0e-6


def _stance_hold_numpy(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.array(value, dtype=np.float64, copy=True)


def _stance_hold_env0(value, count):
    """Env-0 row of a per-env tensor, a vector or a scalar, as float64 (count,)."""
    array = _stance_hold_numpy(value)
    if array.ndim == 0:
        array = np.full(count, float(array))
    elif array.ndim >= 2:
        array = array[0]
    if array.shape != (count,):
        raise ValueError("expected %d values, got shape %s" % (count, array.shape))
    return array


def _stance_hold_indices(value, total):
    if isinstance(value, slice):
        return list(range(total))[value]
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]


def _stance_hold_optional(owner, name):
    if owner is None:
        return None
    try:
        return getattr(owner, name, None)
    except Exception:  # noqa: BLE001 - deprecated properties may raise; recorded as absent
        return None


def _stance_hold_physx_gains(robot):
    """Joint drive gains held by PhysX; explicit actuators require zero."""
    count = len(robot.joint_names)
    record = {}
    for key in ("joint_stiffness", "joint_damping"):
        value = _stance_hold_optional(robot.data, key)
        record["data_" + key] = None if value is None else _stance_hold_env0(value, count).tolist()
    view = _stance_hold_optional(robot, "root_physx_view")
    for key, method in (("view_dof_stiffnesses", "get_dof_stiffnesses"),
                        ("view_dof_dampings", "get_dof_dampings")):
        try:
            record[key] = _stance_hold_env0(getattr(view, method)(), count).tolist()
        except Exception as exc:  # noqa: BLE001 - optional API; recorded, not assumed
            record[key] = None
            record[key + "_error"] = "%s: %s" % (type(exc).__name__, exc)
    return record


def _stance_hold_physx_problems(physx):
    problems = []
    for key in ("data_joint_stiffness", "data_joint_damping", "view_dof_stiffnesses", "view_dof_dampings"):
        values = physx.get(key)
        if values is not None and max(abs(float(item)) for item in values) > STANCE_HOLD_VALUE_TOL:
            problems.append("PhysX joint drive %s is not zero: %s" % (key, values))
    return problems


def _stance_hold_inspect(env, robot, wrapped):
    """Read the V12 action term, actuators, limits and PhysX gains. Reads only."""
    names = [str(name) for name in robot.joint_names]
    total = len(names)
    term = env.action_manager.get_term(STANCE_HOLD_ACTION_TERM)
    action_ids = _stance_hold_indices(term._joint_ids, total)
    count = len(action_ids)
    offset = _stance_hold_env0(term._offset, count)
    scale = _stance_hold_env0(term._scale, count)
    clip = _stance_hold_optional(term, "_clip")
    default = _stance_hold_env0(robot.data.default_joint_pos, total)
    kp = np.full(total, np.nan)
    kd = np.full(total, np.nan)
    effort = np.full(total, np.nan)
    coverage = [0] * total
    groups = {}
    maps = []
    for group, actuator in robot.actuators.items():
        ids = _stance_hold_indices(actuator.joint_indices, total)
        stiffness = _stance_hold_env0(actuator.stiffness, len(ids))
        damping = _stance_hold_env0(actuator.damping, len(ids))
        limit = _stance_hold_env0(actuator.effort_limit, len(ids))
        buffer = _stance_hold_optional(actuator, "positions_delay_buffer")
        lags = _stance_hold_optional(buffer, "time_lags")
        cfg = _stance_hold_optional(actuator, "cfg")
        groups[str(group)] = {
            "class": type(actuator).__name__,
            "mro": [cls.__name__ for cls in type(actuator).__mro__],
            "joint_indices": ids,
            "joint_names": [names[index] for index in ids],
            "stiffness": stiffness.tolist(),
            "damping": damping.tolist(),
            "effort_limit": limit.tolist(),
            "gain_tensor_shape": [int(item) for item in actuator.stiffness.shape],
            "position_delay_time_lags": (
                None if lags is None else [int(item) for item in _stance_hold_numpy(lags).reshape(-1)]
            ),
            "min_delay": _stance_hold_optional(cfg, "min_delay"),
            "max_delay": _stance_hold_optional(cfg, "max_delay"),
        }
        maps.append((str(group), actuator, np.asarray(ids, dtype=np.int64)))
        for position, index in enumerate(ids):
            coverage[index] += 1
            kp[index] = stiffness[position]
            kd[index] = damping[position]
            effort[index] = limit[position]
    limits = None
    limits_source = None
    for key in ("joint_pos_limits", "joint_limits"):
        value = _stance_hold_optional(robot.data, key)
        if value is not None:
            limits = _stance_hold_numpy(value)
            if limits.ndim == 3:
                limits = limits[0]
            limits_source = "robot.data." + key
            break
    clip_actions = _stance_hold_optional(wrapped, "clip_actions")
    physx = _stance_hold_physx_gains(robot)
    record = {
        "joint_names": names,
        "action_term": {
            "name": STANCE_HOLD_ACTION_TERM,
            "class": type(term).__name__,
            "joint_ids": action_ids,
            "joint_names": [names[index] for index in action_ids] if max(action_ids, default=-1) < total else None,
            "offset": offset.tolist(),
            "scale": scale.tolist(),
            "clip": None if clip is None else _stance_hold_numpy(clip).tolist(),
        },
        "default_joint_pos": default.tolist(),
        "actuators": groups,
        "joint_coverage": coverage,
        "joint_pos_limits": None if limits is None else limits.tolist(),
        "joint_pos_limits_source": limits_source,
        "wrapper_clip_actions": clip_actions,
        "physx_gains_at_setup": physx,
    }
    return {
        "record": record, "names": names, "action_ids": np.asarray(action_ids, dtype=np.int64),
        "offset": offset, "scale": scale, "default": default, "kp": kp, "kd": kd, "effort": effort,
        "coverage": coverage, "groups": groups, "maps": maps, "limits": limits, "physx": physx,
        "clip_actions": clip_actions,
    }


def _stance_hold_validate(info):
    """Fail-closed preflight for --stance-hold auto; returns every problem found."""
    problems = []
    names = info["names"]
    total = len(names)
    if total != STANCE_HOLD_JOINT_COUNT:
        problems.append("articulation has %d joints, expected %d" % (total, STANCE_HOLD_JOINT_COUNT))
    ids = [int(item) for item in info["action_ids"]]
    permutation = len(ids) == total and sorted(ids) == list(range(total))
    if not permutation:
        problems.append("action term joints are not a permutation of the articulation joints: %s" % ids)
    if not np.all(np.abs(info["scale"] - STANCE_HOLD_ACTION_SCALE) <= STANCE_HOLD_VALUE_TOL):
        problems.append("action scale is not %s: %s" % (STANCE_HOLD_ACTION_SCALE, info["scale"].tolist()))
    if permutation and not np.all(np.abs(info["offset"] - info["default"][ids]) <= STANCE_HOLD_VALUE_TOL):
        problems.append("action offset is not the default joint position")
    for index, name in enumerate(names):
        expected = [value for suffix, value in STANCE_HOLD_V12_DEFAULT_POS if name.endswith(suffix)]
        if len(expected) != 1:
            problems.append("joint %s has no V12 default position rule" % name)
        elif abs(info["default"][index] - expected[0]) > STANCE_HOLD_VALUE_TOL:
            problems.append("default position of %s is %s, expected %s" % (name, info["default"][index], expected[0]))
    if set(info["groups"]) != set(STANCE_HOLD_ACTUATOR_GROUPS):
        problems.append("actuator groups are %s, expected %s" % (sorted(info["groups"]), list(STANCE_HOLD_ACTUATOR_GROUPS)))
    for group, item in sorted(info["groups"].items()):
        if item["class"] != STANCE_HOLD_ACTUATOR_CLASS:
            problems.append("actuator %s is %s, expected %s" % (group, item["class"], STANCE_HOLD_ACTUATOR_CLASS))
        if "DelayedPDActuator" not in item["mro"] or "ImplicitActuator" in item["mro"]:
            problems.append("actuator %s is not an explicit DelayedPDActuator: %s" % (group, item["mro"]))
        if item["gain_tensor_shape"] != [1, len(item["joint_indices"])]:
            problems.append("actuator %s gain tensor shape %s is not [1, %d]" % (
                group, item["gain_tensor_shape"], len(item["joint_indices"])))
        if max(abs(value - BASE_KP) for value in item["stiffness"]) > STANCE_HOLD_VALUE_TOL:
            problems.append("actuator %s stiffness %s is not %s" % (group, item["stiffness"], BASE_KP))
        if max(abs(value - BASE_KD) for value in item["damping"]) > STANCE_HOLD_VALUE_TOL:
            problems.append("actuator %s damping %s is not %s" % (group, item["damping"], BASE_KD))
    if info["coverage"] != [1] * total:
        problems.append("actuators do not cover every joint exactly once: %s" % info["coverage"])
    if not (np.isfinite(info["effort"]).all() and np.all(info["effort"] > 0.0)):
        problems.append("effort limits are not finite and positive: %s" % info["effort"].tolist())
    problems.extend(_stance_hold_physx_problems(info["physx"]))
    limits = info["limits"]
    if limits is None or limits.shape != (total, 2):
        problems.append("joint position limits are unavailable")
    elif not (np.isfinite(limits).all() and np.all(limits[:, 0] < limits[:, 1])):
        problems.append("joint position limits are not finite with lower < upper")
    clip = info["clip_actions"]
    if clip is not None and (isinstance(clip, bool) or not isinstance(clip, (int, float))
                             or not math.isfinite(float(clip)) or float(clip) <= 0.0):
        problems.append("wrapper clip_actions is not None or a positive number: %r" % (clip,))
    return problems


def _stance_hold_setup(mode, env, robot, wrapped, output_dir):
    """Record the control contract; auto mode also validates it and builds the hold."""
    if mode not in STANCE_HOLD_MODES:
        raise AdapterFailure("unsupported --stance-hold value: %r" % (mode,))
    record = {
        "schema_version": 1,
        "mode": mode,
        "module": {
            "path": STANCE_HOLD_SOURCE_REL,
            "sha256": STANCE_HOLD_SOURCE_SHA256,
            "body_sha256": STANCE_HOLD_BODY_SHA256,
        },
        "constants": stance_hold_constants(),
        "control_path": (
            "off: the V12 policy action goes to previous_actions unchanged and no gain is written"
            if mode == "off" else
            "auto: the applied joint target goes to wrapped.step as (target - offset) / scale, so the "
            "policy's last_action observation is the applied action; actuator Kp/Kd are written before "
            "the next step only when they change; the policy is evaluated every step"
        ),
        "joint_order": (
            "robot.joint_names (articulation order); the V12 action term order is mapped through "
            "its _joint_ids"
        ),
        "torque_clip_basis": (
            "robot.data.computed_torque vs robot.data.applied_torque read after the control step: "
            "the last physics substep only"
        ),
        "delayed_target_note": (
            "Lite3Actuator delays position targets by the recorded time lags (physics substeps) while "
            "stiffness and damping apply at once, so a gain change meets the previous step's target for "
            "that many substeps; metrics delayed_target_torque_max_ratio_estimate bounds that torque"
        ),
        "inspection": None,
        "inspection_error": None,
        "validation_problems": [],
    }
    runtime = {
        "mode": mode,
        "active": mode == "auto",
        "hold": None,
        "record": record,
        "failure": None,
        "effort_limit": None,
        "row": None,
        "row_error_count": 0,
        "row_last_error": None,
        "gain_writes": 0,
        "gain_readback_max_abs_error": 0.0,
        "physx_after_first_gain_write": None,
    }
    info = None
    try:
        info = _stance_hold_inspect(env, robot, wrapped)
        record["inspection"] = info["record"]
        if np.isfinite(info["effort"]).all() and np.all(info["effort"] > 0.0):
            runtime["effort_limit"] = info["effort"]
    except Exception as exc:  # noqa: BLE001 - off mode records only; auto mode fails below
        record["inspection_error"] = "%s: %s" % (type(exc).__name__, exc)
    if mode == "auto":
        if info is None:
            problems = ["inspection failed: %s" % record["inspection_error"]]
        else:
            problems = _stance_hold_validate(info)
        record["validation_problems"] = problems
        if problems:
            write_json(Path(output_dir) / "stance_hold_setup.json", record)
            raise AdapterFailure("stance hold preflight failed: " + "; ".join(problems))
        ids = info["action_ids"]
        initial_target = np.empty(len(ids))
        initial_target[ids] = info["offset"]
        limits = info["limits"]
        runtime.update({
            "hold": StanceHold("auto", joint_lower=limits[:, 0], joint_upper=limits[:, 1],
                               joint_count=len(ids)),
            "action_ids": ids,
            "action_offset": info["offset"],
            "action_scale": info["scale"],
            "clip_actions": None if info["clip_actions"] is None else float(info["clip_actions"]),
            "actuator_maps": info["maps"],
            # previous_actions starts at zero, so the first step applies the offset.
            "applied_target": initial_target,
            "applied_kp": info["kp"].copy(),
            "applied_kd": info["kd"].copy(),
        })
    write_json(Path(output_dir) / "stance_hold_setup.json", record)
    return runtime


def _stance_hold_write_gains(runtime, robot, kp, kd):
    """Write per-joint Kp/Kd into the explicit actuators, then read them back."""
    for _group, actuator, ids in runtime["actuator_maps"]:
        for key, values in (("stiffness", kp), ("damping", kd)):
            tensor = getattr(actuator, key)
            tensor[:] = tensor.new_tensor(values[ids])
    worst = 0.0
    for _group, actuator, ids in runtime["actuator_maps"]:
        for key, values in (("stiffness", kp), ("damping", kd)):
            got = _stance_hold_env0(getattr(actuator, key), len(ids))
            worst = max(worst, float(np.max(np.abs(got - values[ids]))))
    runtime["gain_writes"] += 1
    runtime["gain_readback_max_abs_error"] = max(runtime["gain_readback_max_abs_error"], worst)
    if worst > STANCE_HOLD_GAIN_READBACK_TOL:
        raise AdapterFailure("actuator gain read-back differs from the written value by %.6g" % worst)
    if runtime["physx_after_first_gain_write"] is None:
        physx = _stance_hold_physx_gains(robot)
        physx["problems"] = _stance_hold_physx_problems(physx)
        runtime["physx_after_first_gain_write"] = physx
        if physx["problems"]:
            raise AdapterFailure("PhysX joint drive gains are not zero after a stance gain write: "
                                 + "; ".join(physx["problems"]))


def _stance_hold_control_step(runtime, robot, contact, foot_ids, actions, command, now_s):
    """Run the hold after the policy; return the action for the next wrapped.step."""
    hold = runtime["hold"]
    ids = runtime["action_ids"]
    offset = runtime["action_offset"]
    scale = runtime["action_scale"]
    count = len(ids)
    action = _stance_hold_env0(actions, count)
    policy_target = np.empty(count)
    policy_target[ids] = offset + scale * action
    joint_pos = _stance_hold_env0(robot.data.joint_pos, count)
    joint_vel = _stance_hold_env0(robot.data.joint_vel, count)
    linear_speed = float(np.linalg.norm(_stance_hold_env0(robot.data.root_lin_vel_w, 3)))
    angular_speed = float(np.linalg.norm(_stance_hold_env0(robot.data.root_ang_vel_w, 3)))
    gravity_z = float(_stance_hold_env0(robot.data.projected_gravity_b, 3)[2])
    tilt_deg = (math.degrees(math.acos(min(1.0, max(-1.0, -gravity_z))))
                if math.isfinite(gravity_z) else float("nan"))
    foot_forces = np.linalg.norm(_stance_hold_numpy(contact.data.net_forces_w[0, foot_ids]), axis=-1)
    previous_target = runtime["applied_target"]
    out = hold.update(HoldInput(
        now_s=float(now_s),
        command=np.asarray(command, dtype=np.float64),
        joint_pos=joint_pos,
        joint_vel=joint_vel,
        policy_target=policy_target,
        applied_target=previous_target,
        applied_kp=runtime["applied_kp"],
        applied_kd=runtime["applied_kd"],
        linear_speed=linear_speed,
        angular_speed=angular_speed,
        tilt_deg=tilt_deg,
        foot_forces=foot_forces,
    ))
    if out.policy_owns_joints:
        applied_actions = actions
        applied_action = action
    else:
        applied_action = (out.target[ids] - offset) / scale
        if not np.isfinite(applied_action).all():
            raise StanceHoldError("stance hold produced a non-finite action")
        clip = runtime["clip_actions"]
        if clip is not None and float(np.max(np.abs(applied_action))) > clip:
            raise AdapterFailure("stance hold action exceeds the wrapper clip_actions bound %s" % clip)
        applied_actions = actions.new_tensor(applied_action).reshape(actions.shape)
    gains_changed = not (np.array_equal(out.kp, runtime["applied_kp"])
                         and np.array_equal(out.kd, runtime["applied_kd"]))
    if gains_changed:
        _stance_hold_write_gains(runtime, robot, out.kp, out.kd)
    delayed_torque = out.kp * (previous_target - joint_pos) - out.kd * joint_vel
    runtime["row"] = {
        "stance_mode": out.mode,
        "stance_reason": out.reason,
        "stance_progress": out.progress,
        "policy_owns_joints": bool(out.policy_owns_joints),
        "applied_kp_mean": float(np.mean(out.kp)),
        "applied_kd_mean": float(np.mean(out.kd)),
        "applied_target": [float(item) for item in out.target],
        "applied_target_minus_policy_max_abs": float(np.max(np.abs(out.target - policy_target))),
        "applied_action_max": float(np.max(np.abs(applied_action))),
        "stance_gains_written": bool(gains_changed),
        "delayed_target_torque_max_ratio_estimate": float(np.max(np.abs(delayed_torque) / runtime["effort_limit"])),
        "stance_linear_speed_mps": linear_speed,
        "stance_angular_speed_radps": angular_speed,
        "stance_tilt_deg": tilt_deg,
    }
    runtime["applied_target"] = out.target
    runtime["applied_kp"] = out.kp
    runtime["applied_kd"] = out.kd
    return applied_actions


def _stance_hold_row(runtime, robot):
    """Additive metrics fields. Recording errors are counted, never raised."""
    row = {"stance_hold": runtime["mode"]}
    if runtime["active"]:
        if runtime["row"] is not None:
            row.update(runtime["row"])
    else:
        row.update({"stance_mode": "OFF", "policy_owns_joints": True})
    effort = runtime["effort_limit"]
    if effort is None:
        return row
    try:
        applied = _stance_hold_env0(robot.data.applied_torque, len(effort))
        row["applied_torque_max_ratio"] = float(np.max(np.abs(applied) / effort))
        computed = _stance_hold_optional(robot.data, "computed_torque")
        if computed is not None:
            gap = np.abs(_stance_hold_env0(computed, len(effort)) - applied)
            row["torque_clip_joint_count"] = int(np.sum(gap > STANCE_HOLD_TORQUE_CLIP_TOL_NM))
            row["torque_clip_max_nm"] = float(np.max(gap))
    except Exception as exc:  # noqa: BLE001 - recording must not change the control path
        runtime["row_error_count"] += 1
        runtime["row_last_error"] = "%s: %s" % (type(exc).__name__, exc)
        row["stance_record_error"] = True
    return row


def _stance_hold_summary(runtime):
    return {
        "mode": runtime["mode"],
        "setup_record": "stance_hold_setup.json",
        "module_sha256": STANCE_HOLD_SOURCE_SHA256,
        "failure": runtime["failure"],
        "gain_writes": runtime["gain_writes"],
        "gain_readback_max_abs_error": runtime["gain_readback_max_abs_error"],
        "physx_after_first_gain_write": runtime["physx_after_first_gain_write"],
        "row_error_count": runtime["row_error_count"],
        "row_last_error": runtime["row_last_error"],
        "fsm": None if runtime["hold"] is None else runtime["hold"].status(),
    }


def _read_viewer_camera_intrinsics(stage, cam_prim_path: str, resolution) -> dict:
    """Read the recording camera's aperture so an overlay can be projected offline.

    Display-only. The horizontal aperture is authored on the prim; Omniverse fits
    the render product to the horizontal extent, so the vertical half-angle is
    derived from the render aspect rather than from the authored vertical
    aperture, which does not follow the requested resolution.
    """
    from pxr import UsdGeom

    prim = stage.GetPrimAtPath(cam_prim_path)
    if not prim or not prim.IsValid():
        raise AdapterFailure(f"recording camera prim is missing: {cam_prim_path}")
    camera = UsdGeom.Camera(prim)
    focal_length = camera.GetFocalLengthAttr().Get()
    horizontal_aperture = camera.GetHorizontalApertureAttr().Get()
    vertical_aperture = camera.GetVerticalApertureAttr().Get()
    if not focal_length or not horizontal_aperture:
        raise AdapterFailure(
            "recording camera has no usable focal length or horizontal aperture; "
            "refusing to guess a field of view for the overlay"
        )
    width, height = int(resolution[0]), int(resolution[1])
    half_horizontal = math.atan(float(horizontal_aperture) / (2.0 * float(focal_length)))
    return {
        "cam_prim_path": cam_prim_path,
        "render_width": width,
        "render_height": height,
        "focal_length": float(focal_length),
        "horizontal_aperture": float(horizontal_aperture),
        "authored_vertical_aperture": (
            None if vertical_aperture is None else float(vertical_aperture)
        ),
        "horizontal_fov_rad": 2.0 * half_horizontal,
        "aperture_fit": "horizontal",
        "source": "usd_camera_prim",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True, help="pinned building.usda")
    parser.add_argument("--runtime", type=Path, required=True, help="pinned V12 runtime root")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--route-artifact", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True, help="contracts/run_scope.json")
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new immutable run directory")
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--telemetry-host", default="127.0.0.1")
    parser.add_argument("--telemetry-port", type=int, default=46010)
    parser.add_argument("--command-host", default="127.0.0.1")
    parser.add_argument("--command-port", type=int, default=46011)
    parser.add_argument("--max-vx", type=float, default=0.30)
    parser.add_argument("--max-vy", type=float, default=0.30)
    parser.add_argument("--max-wz", type=float, default=0.8)
    parser.add_argument("--max-horizontal-norm", type=float, default=0.30)
    parser.add_argument("--speed-profile", choices=("conservative_0p3", "speed_1p0"), default="conservative_0p3")
    parser.add_argument("--robot-visual-style", choices=("native", "black_review"), default="native")
    parser.add_argument("--watchdog-seconds", type=float, default=0.25)
    parser.add_argument("--sensor-period", type=float, default=0.10)
    parser.add_argument("--sensor-translation", type=float, nargs=3,
                        default=(0.182399336, 0.0, 0.108541081))
    parser.add_argument("--sensor-pitch-degrees", type=float, default=15.0)
    parser.add_argument("--lidar-channels", type=int, default=16)
    parser.add_argument("--lidar-vertical-min", type=float, default=-7.0)
    parser.add_argument("--lidar-vertical-max", type=float, default=52.0)
    parser.add_argument("--lidar-horizontal-resolution", type=float, default=2.0)
    parser.add_argument("--lidar-min-range", type=float, default=0.10)
    parser.add_argument("--lidar-max-range", type=float, default=12.0)
    parser.add_argument("--terrain-filter-cell-size", type=float, default=0.30)
    parser.add_argument("--terrain-filter-height-threshold", type=float, default=0.12)
    parser.add_argument("--terrain-filter-neighbor-cells", type=int, default=1)
    parser.add_argument("--terrain-filter-minimum-neighbor-cells", type=int, default=1)
    parser.add_argument("--contact-force-threshold", type=float, default=5.0)
    parser.add_argument("--nonfoot-contact-threshold", type=float, default=5.0)
    parser.add_argument("--contact-policy", choices=("nonfoot_fatal", "native_v12"),
                        default="nonfoot_fatal",
                        help="native_v12 records non-foot contact without an added termination")
    parser.add_argument("--unfiltered-planner-cloud", action="store_true",
                        help="Send measured returns to the upstream map without the project terrain filter")
    parser.add_argument("--goal-tolerance-m", type=float, default=0.25)
    parser.add_argument("--terminal-window-seconds", type=float, default=2.0)
    parser.add_argument("--terminal-command-norm", type=float, default=0.01)
    parser.add_argument("--terminal-speed-mps", type=float, default=0.10)
    parser.add_argument("--terminal-yaw-rate-radps", type=float, default=0.15)
    parser.add_argument("--connection-ready-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--max-wall-seconds", type=float, default=900.0)
    parser.add_argument("--video-fps", type=float, default=12.5)
    # Capture stride in control steps. Offline three-view composition spends the
    # fixed delivery byte ceiling on fewer, sharper frames, so the default
    # halves the previous 25 fps capture. Recording rate only: nothing in
    # planning, control or termination reads this.
    parser.add_argument("--camera-capture-stride", type=int, default=4)
    # World-side follow camera. It only observes: no robot state is changed.
    # A lateral offset large enough to cross a corridor wall renders a
    # featureless view, so the default keeps the camera on the route centre.
    parser.add_argument("--camera-trail-m", type=float, default=2.0)
    parser.add_argument("--camera-lateral-m", type=float, default=0.0)
    parser.add_argument("--camera-height-m", type=float, default=0.55)
    parser.add_argument("--camera-look-ahead-m", type=float, default=0.6)
    parser.add_argument("--camera-look-down-m", type=float, default=0.25)
    parser.add_argument("--video-resolution", type=int, nargs=2, default=(1920, 1080))
    parser.add_argument("--cloud-record-stride", type=int, default=1)
    # Complete body state at every control step, independent of the point-cloud
    # batch. Off by default so a legacy scope reproduces byte for byte.
    parser.add_argument("--complete-body-state", dest="complete_body_state",
                        action="store_true", default=False)
    parser.add_argument("--no-complete-body-state", dest="complete_body_state",
                        action="store_false")
    # Priority telemetry sending and asynchronous recording. Both default off.
    parser.add_argument("--priority-telemetry", dest="priority_telemetry",
                        action="store_true", default=False)
    parser.add_argument("--no-priority-telemetry", dest="priority_telemetry",
                        action="store_false")
    parser.add_argument("--async-recording", dest="async_recording",
                        action="store_true", default=False)
    parser.add_argument("--no-async-recording", dest="async_recording",
                        action="store_false")
    parser.add_argument("--freeze-gc", dest="freeze_gc",
                        action="store_true", default=False)
    parser.add_argument("--no-freeze-gc", dest="freeze_gc", action="store_false")
    parser.add_argument("--feedback-dropout-start-s", type=float, default=-1.0)
    parser.add_argument("--feedback-dropout-wall-s", type=float, default=0.0)
    parser.add_argument("--external-goal-mode", action="store_true", default=False,
                        help="Disable only legacy fixed-goal auto-success termination and wait for an external backend finish request")
    parser.add_argument("--external-run-id", default=None,
                        help="Run identity shared with the external backend; required with --external-goal-mode")
    parser.add_argument("--external-control-dir", type=Path, default=None,
                        help="Directory for current_command.json and finish_request.json; defaults to OUTPUT/external_episode")
    parser.add_argument("--external-finish-stillness-seconds", type=float, default=1.0)
    parser.add_argument("--external-status-freshness-seconds", type=float, default=2.0)
    parser.add_argument("--stance-hold", choices=STANCE_HOLD_MODES, default="off",
                        help="off: the V12 policy owns the joints at every step and no gain is written. "
                             "auto: PD stance hold after an exactly zero command (stance_hold.py)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda:0")
    return parser


class AdapterFailure(RuntimeError):
    """Raised when a declared invariant of this run is violated."""


class TrialTermination(RuntimeError):
    """Raised instead of letting the environment silently auto-reset."""


def validate_motion_profile(args):
    cap = {"conservative_0p3": 0.30, "speed_1p0": 1.0}[args.speed_profile]
    limits = (args.max_vx, args.max_vy, args.max_horizontal_norm)
    if any(not math.isfinite(value) or value <= 0 or value > cap + 1e-12 for value in limits):
        raise ValueError(f"horizontal limits must be positive and at most {cap} m/s for {args.speed_profile}")
    if not math.isfinite(args.max_wz) or not 0 < args.max_wz <= 1.0 + 1e-12:
        raise ValueError("yaw limit must remain within the upstream controller's (0, 1.0] rad/s range")


def validate_run_duration(case, duration):
    """Long runs require their own case; old dispatch bounds stay unchanged."""
    maximum = {"full_nominal": 180.0, "native_nominal": 600.0,
               "stand_probe": 60.0}.get(case, 45.0)
    if case not in CASES or not math.isfinite(duration) or not 0 < duration <= maximum:
        raise ValueError(f"duration-seconds must be within (0, {maximum:g}] for {case}")


def route_scope(case, scope):
    """A full-course dispatch cannot accidentally inherit a platform scope."""
    if case in ("full_nominal", "native_nominal") and "full_route" not in scope:
        raise ValueError(f"{case} requires an explicit full_route scope")
    return scope["full_route"] if "full_route" in scope else scope["platform_segment"]


def execution_configuration(args):
    """Freeze every runner setting independently of host/artifact paths."""
    paths = {"scene", "runtime", "checkpoint", "route_artifact", "scope", "output",
             "execution_manifest", "external_control_dir"}
    # Round-trip normalizes argparse tuples and JSON lists identically.
    return json.loads(json.dumps({key: value for key, value in vars(args).items() if key not in paths}))


def verify_execution_inputs(args):
    """Check the frozen local-source manifest before initializing Isaac."""
    scope = json.loads(args.scope.read_text())
    if scope.get("execution_source_sha256") != sha256(__file__):
        raise AdapterFailure("runner source differs from frozen execution contract")
    if scope.get("execution_configuration") != execution_configuration(args):
        raise AdapterFailure("runner configuration differs from frozen execution contract")
    if scope.get("execution_manifest_sha256") != sha256(args.execution_manifest):
        raise AdapterFailure("execution manifest differs from frozen execution contract")
    manifest = json.loads(args.execution_manifest.read_text())
    root = Path(manifest["root"]).resolve()
    if not manifest.get("files"):
        raise AdapterFailure("empty execution source manifest")
    for entry in manifest["files"]:
        path = (root / entry["path"]).resolve()
        if root not in path.parents or sha256(path) != entry["sha256"]:
            raise AdapterFailure("execution source mismatch: " + entry["path"])


def main(argv=None) -> int:
    """Validate the request, start Isaac, then run the bounded trial.

    Argument parsing and the Isaac app launch live here rather than at module
    scope so the module stays importable: the run script imports it purely to
    prove which copy of this source the interpreter actually loaded.
    """
    args = build_parser().parse_args(argv)
    _validate_external_goal_args(args)
    if args.case == "native_nominal" and args.contact_policy != "native_v12":
        raise SystemExit("native_nominal records contact and preserves native V12 termination")
    from .feedback_dropout import FeedbackDropout
    dropout = FeedbackDropout(args.feedback_dropout_start_s, args.feedback_dropout_wall_s)
    if dropout.enabled and (not args.complete_body_state or args.case != "flat_nominal"):
        raise SystemExit("feedback dropout requires complete state and the flat_nominal case")
    validate_run_duration(args.case, args.duration_seconds)
    validate_motion_profile(args)
    verify_execution_inputs(args)
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, args.output / "executed_run_pct_scan_building.py")

    # Isaac requires the app launcher before any isaaclab module import.
    from isaaclab.app import AppLauncher

    app = AppLauncher(headless=True, enable_cameras=True, device=args.device).app
    try:
        status = _run(args)
    except Exception as exc:  # noqa: BLE001 - the failure must survive as evidence
        write_json(args.output / "runtime_error.json", {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })
        raise
    finally:
        app.close()
    return int(status)


def _run(args) -> int:
    import gymnasium as gym
    import imageio.v2 as imageio
    import numpy as np
    import torch
    from pxr import UsdGeom, UsdPhysics

    import isaaclab.sim as sim_utils
    from isaaclab.assets import AssetBaseCfg
    from isaaclab.sensors.ray_caster import MultiMeshRayCasterCfg
    from isaaclab.terrains import TerrainImporterCfg
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

    from lite3_sim_bridge import run_isaac_v12_fallback as v12
    from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
    from lite3_sim_bridge.contact_guard import (
        ContactHistoryError,
        SubstepContactMonitor,
        SubstepContactStop,
        required_substeps_for,
    )
    from lite3_sim_bridge.trial_events import TrialEvents, TrialStateMutation, trial_exit_code
    from lite3_sim_bridge.isaac_adapter_core import (
        canonical_config_sha256,
        mounted_sensor_pose,
        quaternion_wxyz_to_xyzw,
        split_geometry_cloud_points,
        world_hits_to_sensor_points,
    )
    from lite3_sim_bridge.protocol import (
        BodyStateV1,
        BodyStateV2,
        DualCloudSensorFrameV1,
        JointStateV1,
        MessageType,
        StatusFlag,
        StatusV1,
        encode_body_state_payload,
        encode_body_state_v2_payload,
        encode_dual_cloud_sensor_payload,
        encode_frame,
        encode_joint_state_payload,
        encode_status_payload,
        pack_xyz_points,
    )
    from lite3_sim_bridge.recording_load import AsyncRecorder
    from lite3_sim_bridge.transport import CommandReceiverServer, TelemetryPublisherServer

    v12._activate_vendored_rsl_rl(args.runtime / "source/rsl_rl")
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper  # noqa: E402

    __import__("robot_lab.tasks")
    runtime_import_identity = _validate_runtime_module_origins(args.runtime)
    write_json(args.output / "runtime_import_identity.json", runtime_import_identity)

    # ---- identity gates before anything physical happens -------------------
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    frozen = scope["frozen_assets"]
    if sha256(args.checkpoint) != v12.PINNED_CHECKPOINT_SHA256:
        raise AdapterFailure("checkpoint SHA-256 does not match the pinned V12 weights")
    if sha256(args.checkpoint) != frozen["checkpoint"]["sha256"]:
        raise AdapterFailure("checkpoint SHA-256 does not match the frozen run scope")
    if sha256(args.scene) != frozen["building_usda"]["sha256"]:
        raise AdapterFailure("Building USD SHA-256 does not match the frozen run scope")
    urdf_path = args.runtime / "resources/lite3/urdf/lite3.urdf"
    if sha256(urdf_path) != frozen["original_urdf"]["sha256"]:
        raise AdapterFailure("runtime URDF is not the pinned original V12 URDF")

    artifact = json.loads(args.route_artifact.read_text(encoding="utf-8"))
    route = np.asarray(artifact["points_xyz_m"], dtype=np.float64)
    if route.shape[1] != 3 or len(route) < 2 or not np.isfinite(route).all():
        raise AdapterFailure("route artifact geometry is unusable")
    segment = route_scope(args.case, scope)
    if artifact["semantics"] == "terrain_ground_xyz_m" and not artifact["body_height_applied"]:
        start_ground = route[0].copy()
        goal_ground = route[-1].copy()
        if not np.allclose(start_ground, segment["start_ground_xyz_m"], atol=1e-9):
            raise AdapterFailure("route artifact start disagrees with the frozen segment")
        if not np.allclose(goal_ground, segment["goal_ground_xyz_m"], atol=1e-9):
            raise AdapterFailure("route artifact goal disagrees with the frozen segment")
    elif artifact["semantics"] == "body_reference_xyz_m" and artifact["body_height_applied"]:
        # Native PCT body-reference samples are not physical ground heights.
        # Keep the requested spawn/goal independent; do not move the spawn to
        # the first optimizer sample or rewrite its Z against the scene mesh.
        start_ground = np.asarray(segment["start_ground_xyz_m"], dtype=np.float64)
        goal_ground = np.asarray(segment["goal_ground_xyz_m"], dtype=np.float64)
        if start_ground.shape != (3,) or goal_ground.shape != (3,) or not (
                np.isfinite(start_ground).all() and np.isfinite(goal_ground).all()):
            raise AdapterFailure("native route requires finite frozen physical endpoints")
    else:
        raise AdapterFailure("route representation and body-height declaration disagree")
    body_height = float(segment["nominal_body_height_m"])
    start_yaw = float(segment["start_tangent_yaw_radians"])

    # ---- scene, policy and sensor configuration ---------------------------
    cfg = load_cfg_from_registry(v12.DEFAULT_TASK, "env_cfg_entry_point")
    agent = load_cfg_from_registry(v12.DEFAULT_TASK, "rsl_rl_cfg_entry_point")
    contract = v12._capture_v12_task_contract(cfg)
    if contract["policy_observation_dimension"] != 450 or contract["action_dimension"] != 12:
        raise AdapterFailure("pinned V12 observation/action contract changed")

    helper_args = v12._parser().parse_args([
        "--output-dir", str(args.output),
        "--checkpoint", str(args.checkpoint),
        "--vendored-rsl-rl", str(args.runtime / "source/rsl_rl"),
        "--mode", "external",
        "--duration-seconds", str(args.duration_seconds),
        "--seed", str(args.seed),
        "--device", args.device,
        "--sensor-period", str(args.sensor_period),
        "--sensor-translation", *[str(value) for value in args.sensor_translation],
        "--sensor-pitch-degrees", str(args.sensor_pitch_degrees),
        "--lidar-channels", str(args.lidar_channels),
        "--lidar-vertical-min", str(args.lidar_vertical_min),
        "--lidar-vertical-max", str(args.lidar_vertical_max),
        "--lidar-horizontal-resolution", str(args.lidar_horizontal_resolution),
        "--lidar-min-range", str(args.lidar_min_range),
        "--lidar-max-range", str(args.lidar_max_range),
        "--max-vx", str(args.max_vx),
        "--max-vy", str(args.max_vy),
        "--max-wz", str(args.max_wz),
        "--watchdog-seconds", str(args.watchdog_seconds),
    ])
    # Reuse the pinned environment configuration path: zero command ranges, no
    # domain randomization, external-mode episode length, and the existing
    # navigation LiDAR construction with its audited mount transform.
    v12._configure_environment(cfg, helper_args)
    if cfg.scene.navigation_lidar is None:
        raise AdapterFailure("navigation LiDAR was not configured; real sensing is required")

    # Inspect each substep without changing the policy's contact history.
    # V12 privileged observations flatten (history_length + 1) * four feet;
    # increasing history from three to four changes checkpoint input shapes.
    contact_substeps = required_substeps_for(
        float(cfg.decimation) * float(cfg.sim.dt), float(cfg.sim.dt)
    )
    inherited_contact_history = int(cfg.scene.contact_forces.history_length)

    source_terrain = cfg.scene.terrain
    cfg.scene.terrain = TerrainImporterCfg(
        prim_path=GROUND_MESH_PRIM,
        terrain_type="usd",
        usd_path=str(args.scene.resolve()),
        terrain_generator=source_terrain.terrain_generator,
        physics_material=source_terrain.physics_material,
        env_spacing=1.0,
        use_terrain_origins=False,
        debug_vis=False,
    )
    cfg.scene.terrain.max_init_terrain_level = 0
    # The USD import places the Building triangles under /World/ground/terrain,
    # so the raycaster needs that merged mesh as an explicit target. Without it
    # the sensor silently reuses a terrain-only Warp mesh and sees nothing.
    cfg.scene.navigation_lidar.mesh_prim_paths = [
        GROUND_MESH_PRIM,
        MultiMeshRayCasterCfg.RaycastTargetCfg(
            prim_expr=f"{GROUND_MESH_PRIM}/terrain",
            merge_prim_meshes=True,
            track_mesh_transforms=False,
        ),
    ]
    # Diagnostic height scanners only; they never reach the 450-D actor input.
    for scan in (cfg.scene.height_scanner, cfg.scene.height_scanner_small):
        scan.offset.pos = (0.0, 0.0, 0.20)
        scan.mesh_prim_paths = [TERRAIN_MESH_PRIM]

    cfg.scene.robot.init_state.pos = (
        float(start_ground[0]), float(start_ground[1]), float(start_ground[2] + body_height)
    )
    cfg.scene.robot.init_state.rot = (
        math.cos(start_yaw / 2.0), 0.0, 0.0, math.sin(start_yaw / 2.0)
    )
    cfg.scene.sky_light = AssetBaseCfg(
        prim_path="/World/skyLight", spawn=sim_utils.DomeLightCfg(intensity=1100)
    )
    cfg.viewer.origin_type = "world"
    cfg.viewer.resolution = tuple(int(value) for value in args.video_resolution)
    cfg.viewer.eye = (float(start_ground[0] - 3.0), float(start_ground[1] + 1.5),
                      float(start_ground[2] + 2.0))
    cfg.viewer.lookat = (float(start_ground[0] + 1.0), float(start_ground[1]),
                         float(start_ground[2] + 0.3))
    agent.device = args.device
    agent.seed = helper_args.seed

    raw_env = gym.make(v12.DEFAULT_TASK, cfg=cfg, render_mode="rgb_array")
    env = raw_env.unwrapped
    wrapped = RslRlVecEnvWrapper(raw_env, clip_actions=agent.clip_actions)
    policy, policy_state, observation, policy_source = v12._load_inference_policy(
        wrapped, agent, args.checkpoint, agent.device
    )
    robot = env.scene["robot"]
    from .robot_visual import apply_robot_visual
    robot_visual = apply_robot_visual(env.sim.stage, args.robot_visual_style)
    write_json(args.output / "robot_visual_identity.json", robot_visual)
    # Display-only: the render product is built from cfg.viewer.cam_prim_path at
    # cfg.viewer.resolution, so an offline overlay must project with that exact
    # camera's aperture. Reading it here keeps the value measured rather than
    # assumed; a wrong field of view produces a plausible but false overlay, so
    # a missing attribute stops the run instead of falling back to a guess.
    camera_intrinsics = _read_viewer_camera_intrinsics(
        env.sim.stage, cfg.viewer.cam_prim_path, cfg.viewer.resolution
    )
    write_json(args.output / "camera_intrinsics.json", camera_intrinsics)
    contact = env.scene.sensors["contact_forces"]
    lidar = env.scene.sensors["navigation_lidar"]
    foot_ids, foot_names = contact.find_bodies(
        ["FL_FOOT", "FR_FOOT", "HL_FOOT", "HR_FOOT"], preserve_order=True
    )
    if len(foot_ids) != 4:
        raise AdapterFailure("expected four foot contact bodies")
    nonfoot_ids = [index for index in range(len(contact.body_names)) if index not in foot_ids]
    body_foot_ids, _ = robot.find_bodies(foot_names, preserve_order=True)
    # Off mode only reads and records the control contract; auto mode fails closed.
    stance_hold_runtime = _stance_hold_setup(args.stance_hold, env, robot, wrapped, args.output)

    # Contact data is consumed after every physics scene update below. History
    # ordering is no longer used to infer when the case should have stopped.
    contact.update(dt=0.0, force_recompute=True)
    contact_history = contact.data.net_forces_w_history

    stage = env.sim.stage
    collision_prims = [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if prim.HasAPI(UsdPhysics.CollisionAPI) and str(prim.GetPath()).startswith(GROUND_MESH_PRIM)
    ]
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(TERRAIN_MESH_PRIM))
    triangle_count = len(mesh.GetFaceVertexCountsAttr().Get()) if mesh else 0
    if triangle_count != BUILDING_TRIANGLE_COUNT:
        raise AdapterFailure(
            f"Building collision mesh has {triangle_count} triangles, expected "
            f"{BUILDING_TRIANGLE_COUNT}"
        )

    # Prove the raycaster actually loaded meshes rather than only being
    # configured. The warp mesh container is not a plain mapping, so it is
    # inspected defensively; the authoritative proof is the hit evidence below.
    configured_targets = [
        target if isinstance(target, str) else str(getattr(target, "prim_expr", target))
        for target in lidar.cfg.mesh_prim_paths
    ]
    loaded_mesh_count = None
    for attribute in ("_mesh_ids_wp", "meshes", "_meshes"):
        container = getattr(lidar, attribute, None)
        if container is None:
            continue
        try:
            loaded_mesh_count = int(len(container))
        except TypeError:
            continue
        if loaded_mesh_count:
            break
    resolved_target_prims = sorted(
        str(prim.GetPath())
        for prim in env.sim.stage.Traverse()
        if str(prim.GetPath()).startswith(f"{GROUND_MESH_PRIM}/terrain")
    )
    lidar.update(dt=0.0, force_recompute=True)
    first_hits = lidar.data.ray_hits_w[0]
    finite_first = torch.isfinite(first_hits).all(dim=-1)
    if int(finite_first.sum().item()) == 0:
        raise AdapterFailure("navigation LiDAR returned no finite hits on the Building mesh")
    first_origin, _ = mounted_sensor_pose(
        lidar.data.pos_w[0].detach().cpu().tolist(), lidar.data.quat_w[0].detach().cpu().tolist(),
        lidar.cfg.offset.pos, lidar.cfg.offset.rot)
    first_ranges = torch.linalg.vector_norm(
        first_hits[finite_first] - first_hits.new_tensor(first_origin).unsqueeze(0), dim=-1
    )
    non_ground_first = int(
        (first_hits[finite_first][:, 2] > float(start_ground[2]) + 0.25).sum().item()
    )
    if non_ground_first == 0:
        raise AdapterFailure("no non-ground LiDAR returns at the frozen start pose")

    limits = CommandLimits(
        args.max_vx, args.max_vy, args.max_wz,
        max_horizontal_norm=args.max_horizontal_norm,
    )
    state = LatestCommandState(
        limits,
        timeout_ns=int(args.watchdog_seconds * 1.0e9),
        max_source_age_ns=int(args.watchdog_seconds * 1.0e9),
        max_future_skew_ns=25_000_000,
    )
    command_server = CommandReceiverServer(state, args.command_host, args.command_port)
    telemetry_server = TelemetryPublisherServer(
        args.telemetry_host,
        args.telemetry_port,
        priority_send=args.priority_telemetry,
    )

    identity = {
        "claim": scope["claim"] if "full_route" in scope else (
            "Frozen PCT ground-route segment consumed by Foxy SCAN mode 3, with the "
            "existing SCAN trajectory controller driving V12 over TCP. Bounded "
            "simulation preflight on one same-level Building platform segment."
        ),
        "case": args.case,
        "task": v12.DEFAULT_TASK,
        "robot_visual": robot_visual,
        "v12_contract": contract,
        "checkpoint_sha256": sha256(args.checkpoint),
        "original_urdf_path": str(urdf_path),
        "original_urdf_sha256": sha256(urdf_path),
        "scene_path": str(args.scene.resolve()),
        "scene_sha256": sha256(args.scene),
        "route_artifact_path": str(args.route_artifact.resolve()),
        "route_artifact_sha256": sha256(args.route_artifact),
        "route_id": artifact["route_id"],
        "route_semantics": artifact["semantics"],
        "route_geometry_sha256": artifact["geometry_sha256"],
        "route_point_count": int(len(route)),
        "route_arc_length_xy_m": float(artifact["statistics"]["arc_length_xy_m"]),
        "scope_path": str(args.scope.resolve()),
        "scope_sha256": sha256(args.scope),
        "execution_source_sha256": sha256(__file__),
        "execution_manifest_sha256": sha256(args.execution_manifest),
        "execution_configuration": execution_configuration(args),
        "bridge_module_file": str(Path(v12.__file__).resolve()),
        "bridge_module_sha256": sha256(v12.__file__),
        "policy_source": str(policy_source),
        "source_commit": v12.PINNED_SOURCE_COMMIT,
        "spawn_xyz": list(cfg.scene.robot.init_state.pos),
        "spawn_quat_wxyz": list(cfg.scene.robot.init_state.rot),
        "spawn_yaw_radians": start_yaw,
        "nominal_body_height_m": body_height,
        "goal_ground_xyz_m": [float(value) for value in goal_ground],
        "joint_names": list(robot.joint_names),
        "body_names": list(robot.body_names),
        "contact_body_names": list(contact.body_names),
        "collision_prims": collision_prims,
        "terrain_triangle_count": triangle_count,
        "physics_dt": float(env.physics_dt),
        "policy_dt": float(env.step_dt),
        "contact_evidence": {
            "contact_policy": args.contact_policy,
            "nonfoot_threshold_n": args.nonfoot_contact_threshold,
            "required_substeps_per_control_period": contact_substeps,
            "inherited_contact_history_length": inherited_contact_history,
            "effective_contact_history_length": int(contact_history.shape[1]),
            "history_newest_first_verified": None,
            "acquisition": "after_each_physics_substep_scene_update",
            "vendored_torso_termination_preserved": True,
            "note": (
                "Every physics substep inside each control period is inspected. "
                + ("Non-foot contact is recorded without added termination. "
                   if args.contact_policy == "native_v12" else
                   "Non-foot contact at the threshold latches case failure. ")
                + "The vendored V12 TORSO-only 1 N termination remains unchanged."
            ),
        },
        "sensor_period_s": args.sensor_period,
        "lidar_prim_path": lidar.cfg.prim_path,
        "lidar_offset_pos": list(lidar.cfg.offset.pos),
        "lidar_offset_rot_wxyz": list(lidar.cfg.offset.rot),
        "lidar_ray_count": int(first_hits.shape[0]),
        "lidar_configured_targets": configured_targets,
        "lidar_loaded_mesh_count": loaded_mesh_count,
        "lidar_resolved_terrain_prims": resolved_target_prims,
        "lidar_first_scan_finite_hits": int(finite_first.sum().item()),
        "lidar_first_scan_non_ground_hits": non_ground_first,
        "lidar_first_scan_range_min_m": float(first_ranges.min().item()),
        "lidar_first_scan_range_max_m": float(first_ranges.max().item()),
        "command_limits": {
            "max_vx_mps": args.max_vx, "max_vy_mps": args.max_vy,
            "max_wz_radps": args.max_wz,
            "max_horizontal_norm_mps": args.max_horizontal_norm,
            "watchdog_seconds": args.watchdog_seconds,
        },
        "command_ownership": (
            "SCAN closed_loop_controller only. No PCT lookahead follower exists in "
            "this entry point; the route is a planner input, never a command source."
        ),
        "clock_domains": {
            "telemetry_timestamp": "Isaac simulation time in nanoseconds",
            "command_freshness": "local monotonic wall time at both ends",
        },
        "terrain_filter": {
            "enabled": not args.unfiltered_planner_cloud,
            "cell_size_m": args.terrain_filter_cell_size,
            "height_threshold_m": args.terrain_filter_height_threshold,
            "neighbor_cells": args.terrain_filter_neighbor_cells,
            "minimum_neighbor_cells": args.terrain_filter_minimum_neighbor_cells,
            "method": ("measured returns, frame/range conversion only"
                       if args.unfiltered_planner_cloud else
                       "split_geometry_cloud_points local same-level separation"),
        },
        "telemetry_port": args.telemetry_port,
        "command_port": args.command_port,
        "seed": helper_args.seed,
        "autoreset_allowed": False,
        "duration_seconds": args.duration_seconds,
        "external_goal_mode": bool(args.external_goal_mode),
        "external_goal_contract": {
            "enabled": bool(args.external_goal_mode),
            "run_id": args.external_run_id,
            "control_dir": (
                str((args.external_control_dir or (args.output / "external_episode")).resolve())
                if args.external_goal_mode else None
            ),
            "status_snapshot": "current_command.json, atomically replaced by this runner",
            "finish_request": "finish_request.json, written once by the external backend",
            "finish_schema": {
                "schema_version": 1,
                "run_id": "same as --external-run-id",
                "request_id": "backend unique id",
                "observed_run_epoch_ns": "run_epoch_ns copied from current_command.json",
                "requested_at_monotonic_ns": "same-host monotonic_ns when backend writes the request",
                "backend_terminal_status": "FINISHED or FAILED",
            },
            "finish_stillness_seconds": args.external_finish_stillness_seconds,
            "freshness_seconds": args.external_status_freshness_seconds,
            "route_artifact_role": (
                "spawn and legacy metric metadata only; it is not a command target in external-goal mode"
                if args.external_goal_mode else "legacy fixed-goal metric and terminal target"
            ),
        },
        "actor_obs_shape": list(observation["policy"].shape),
    }
    config_sha256 = canonical_config_sha256(identity)
    identity["config_sha256"] = config_sha256.hex()
    write_json(args.output / "runtime_identity.json", identity)

    events = TrialEvents()
    events.install(env, robot)

    video_path = args.output / "third_person_master.mp4"
    capture_stride = max(1, int(args.camera_capture_stride))
    # Real-time playback requires the container rate to match the capture rate.
    # A silent mismatch would make the delivered video a different length from
    # the episode it claims to show.
    capture_fps = 1.0 / (float(env.step_dt) * capture_stride)
    if abs(capture_fps - float(args.video_fps)) > 1e-6:
        raise AdapterFailure(
            f"--video-fps {args.video_fps} does not match the capture rate "
            f"{capture_fps} implied by step_dt {float(env.step_dt)} and stride "
            f"{capture_stride}"
        )
    writer = imageio.get_writer(
        str(video_path), fps=args.video_fps, codec="libx264", quality=8, macro_block_size=None
    )
    # One constant identity for this process. A consumer latches the first epoch
    # it sees, so a packet replayed from an earlier run can never be mistaken
    # for current state.
    run_epoch_ns = time.time_ns()
    external_control_dir = None
    external_status_path = None
    external_finish_path = None
    external_finish_window_start_s = None
    external_finish_latched = None
    external_finish_state = {"last_check": None, "last_request": None, "final_reason": None}
    if args.external_goal_mode:
        external_control_dir = args.external_control_dir or (args.output / "external_episode")
        external_control_dir.mkdir(parents=True, exist_ok=True)
        external_status_path = external_control_dir / "current_command.json"
        external_finish_path = external_control_dir / "finish_request.json"
        write_json(external_control_dir / "contract.json", identity["external_goal_contract"])
    recorder = AsyncRecorder(max_pending=64) if args.async_recording else None
    metrics_path = args.output / "metrics.jsonl"
    sensor_path = args.output / "sensor_metrics.jsonl"
    cloud_path = args.output / "clouds.jsonl"
    camera_frames_path = args.output / "camera_frames.jsonl"

    status = "DURATION_REACHED"
    records: list[dict] = []
    previous_actions = torch.zeros((1, 12), device=env.device)
    telemetry_sequence = 0
    state_sequence = 0
    complete_state_frames = 0
    complete_state_dropped = 0
    scan_index = 0
    dropped_frames = 0
    first_nonzero_command_s = None
    goal_reached_s = None
    terminal_window_start_s = None
    terminal_window_satisfied_s = None
    max_command_obs_error = 0.0
    nonfoot_events: list[dict] = []
    frame_luminance_std: list[float] = []
    camera_frame_index = 0
    wall_start = time.monotonic()

    command_server.start()
    telemetry_server.start()
    connection_deadline = time.monotonic() + args.connection_ready_timeout_seconds
    while time.monotonic() < connection_deadline:
        if (
            command_server.stats().accepted_connections > 0
            and telemetry_server.stats().accepted_connections > 0
        ):
            break
        time.sleep(0.01)
    else:
        raise AdapterFailure("Foxy bridge did not connect before the ready timeout")
    connected_wall_s = time.monotonic() - wall_start

    for _ in range(8):
        env.sim.render()

    initial_sim_time = float(env.sim.current_time)
    # F8: the run's absolute simulation origin is recorded rather than inferred
    # later from the first published plan. It is written to its own file so the
    # pre-run `runtime_identity.json` and the `config_sha256` computed over it
    # both stay exactly as transmitted.
    write_json(args.output / "run_clock.json", {
        "schema_version": 2,
        "simulation_origin_s": initial_sim_time,
        "simulation_origin_ns": int(round(initial_sim_time * 1.0e9)),
        "run_epoch_ns": run_epoch_ns,
        "complete_body_state": bool(args.complete_body_state),
        "complete_body_state_period_s": float(env.step_dt) if args.complete_body_state else None,
        "physics_dt_s": float(env.physics_dt),
        "policy_dt_s": float(env.step_dt),
        "semantics": (
            "metrics.jsonl sim_time_s = Isaac absolute simulation time - "
            "simulation_origin_s. Telemetry timestamp_ns, /clock and B-spline "
            "start stamps are absolute simulation time. The command freshness "
            "domain is local monotonic wall time at both ends and is never "
            "compared against either of these."
        ),
    })
    # Measured on `recovery_stand_probe01`: the control loop stalled ~266 ms
    # every 120 control steps, exactly periodically, and each stall crossed the
    # unchanged 0.25 s feedback deadline and stopped the robot. The period is a
    # fixed allocation count per step, which is a generation-2 collection over
    # Isaac's very large static heap. `gc.freeze()` moves everything allocated
    # during setup into the permanent generation so gen-2 stops rescanning it.
    # Automatic collection stays enabled; only what it has to walk changes. The
    # before/after counters are recorded so the effect is measured, not claimed.
    gc_before = gc.get_stats()
    gc_frozen = 0
    if args.freeze_gc:
        gc.collect()
        gc.freeze()
        gc_frozen = gc.get_freeze_count()
    from .feedback_dropout import FeedbackDropout
    dropout = FeedbackDropout(args.feedback_dropout_start_s, args.feedback_dropout_wall_s)
    case_failure = None
    contact_guard = SubstepContactMonitor(
        stop_on_contact=args.contact_policy == "nonfoot_fatal",
        read_forces=lambda: torch.linalg.vector_norm(
            contact.data.net_forces_w[0], dim=-1).detach().cpu().tolist(),
        clock=lambda: float(env.sim.current_time) - initial_sim_time,
        on_failure=state.latch_case_failure,
        required_substeps=contact_substeps,
        threshold_n=args.nonfoot_contact_threshold,
        nonfoot_indices=nonfoot_ids,
        body_names=list(contact.body_names),
        physics_dt_s=float(env.physics_dt),
    )
    contact_guard.install(env.scene)
    try:
        with metrics_path.open("w", encoding="utf-8") as metrics_file, \
                sensor_path.open("w", encoding="utf-8") as sensor_file, \
                cloud_path.open("w", encoding="utf-8") as cloud_file, \
                camera_frames_path.open("w", encoding="utf-8") as camera_frames_file, \
                ExitStack() as recording_cleanup:
            if recorder is not None:
                # This context exits before the files, including on a physics
                # exception. Pending cloud writes must still have open handles.
                recording_cleanup.callback(recorder.close, timeout_seconds=300.0)
            sensor_stride = max(1, int(round(args.sensor_period / float(env.step_dt))))
            total_steps = int(round(args.duration_seconds / float(env.step_dt)))
            for step in range(total_steps):
                if time.monotonic() - wall_start > args.max_wall_seconds:
                    status = "WALL_TIMEOUT"
                    break
                sim_time = float(env.sim.current_time) - initial_sim_time
                external_finish_ready_status = None
                snapshot = command_server.snapshot(time.monotonic_ns())
                command = (snapshot.command.vx, snapshot.command.vy, snapshot.command.wz)
                if args.case == "stand_probe":
                    # A standing qualification probe never forwards motion.
                    command = (0.0, 0.0, 0.0)
                horizontal_norm = math.hypot(command[0], command[1])
                if horizontal_norm > args.max_horizontal_norm + 1e-9:
                    raise AdapterFailure(
                        f"admitted horizontal command norm {horizontal_norm} exceeds the limit"
                    )
                if first_nonzero_command_s is None and max(abs(v) for v in command) > 1e-6:
                    first_nonzero_command_s = sim_time

                term = env.command_manager.get_term("base_velocity")
                term.commands[:, 0] = command[0]
                term.commands[:, 1] = command[1]
                term.commands[:, 2] = command[2]
                contact_guard.begin(step)
                try:
                    observation, _, dones, _ = wrapped.step(previous_actions)
                    contact_guard.end()
                except SubstepContactStop as exc:
                    case_failure = exc.failure
                    sim_time = float(env.sim.current_time) - initial_sim_time
                    position = robot.data.root_pos_w[0].detach().cpu().numpy().copy()
                    quaternion = robot.data.root_quat_w[0].detach().cpu().tolist()
                    # The guard raises from inside the scene update that already
                    # completed the offending substep, so the simulator state read
                    # here IS that substep's state. Reading tensors advances
                    # nothing; no step, render, reset or write is performed. The
                    # last guard sample is the force row that latched the failure.
                    fatal_state = {
                        "note": (
                            "Actual state at the latched fatal substep, read "
                            "without advancing physics. Not a later sample and "
                            "not an interpolation."
                        ),
                        "substep_sim_time_s": case_failure.substep_sim_time_s,
                        "joint_names": list(robot.joint_names),
                        "joint_pos": robot.data.joint_pos[0].detach().cpu().tolist(),
                        "joint_vel": robot.data.joint_vel[0].detach().cpu().tolist(),
                        "applied_torque": robot.data.applied_torque[0].detach().cpu().tolist(),
                        "base_linear_velocity_world": robot.data.root_lin_vel_w[0].detach().cpu().tolist(),
                        "base_angular_velocity_world": robot.data.root_ang_vel_w[0].detach().cpu().tolist(),
                        "base_linear_velocity_body": robot.data.root_lin_vel_b[0].detach().cpu().tolist(),
                        "base_angular_velocity_body": robot.data.root_ang_vel_b[0].detach().cpu().tolist(),
                        "gravity_b": robot.data.projected_gravity_b[0].detach().cpu().tolist(),
                        "foot_names": list(foot_names),
                        "foot_positions": robot.data.body_pos_w[0, body_foot_ids].detach().cpu().tolist(),
                        "contact_body_names": list(contact.body_names),
                        "contact_force_norms_at_fatal_substep": (
                            list(contact_guard.samples[-1]) if contact_guard.samples else None
                        ),
                        "contact_force_norms_post_update": torch.linalg.vector_norm(
                            contact.data.net_forces_w[0], dim=-1
                        ).detach().cpu().tolist(),
                        "substep_force_rows_this_control_step": [
                            list(sample) for sample in contact_guard.samples
                        ],
                    }
                    # A latched physical failure ends the trial. State and error
                    # evidence are preserved, no pose reset or retry happens,
                    # and the consumer is told through the existing status
                    # fields before the transport is closed.
                    status = "CASE_FAILED_NONFOOT_CONTACT"
                    metrics_file.flush()
                    write_json(args.output / "case_failure.json", {
                        "schema_version": 1,
                        "case": args.case,
                        "reason": "nonfoot_contact_above_threshold",
                        "termination_code": case_failure.termination_code,
                        "contact": case_failure.as_record(),
                        "guard": contact_guard.as_record(),
                        "sim_time_s": sim_time,
                        "physics_steps_after_failure": 0,
                        "contact_substeps_inspected": len(contact_guard.samples),
                        "base_xyz": position.tolist(),
                        "base_quat_wxyz": quaternion,
                        "fatal_substep_state": fatal_state,
                        "admitted_command_at_failure": list(command),
                        "command_state_reason": state.snapshot(
                            time.monotonic_ns()
                        ).reason,
                        "reset_performed": False,
                        "note": (
                            "The simulation case is latched failed. Command "
                            "admission is disabled for the rest of this process "
                            "and no further physics step is taken."
                        ),
                    })
                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.STATUS_V1,
                        telemetry_sequence,
                        int(float(env.sim.current_time) * 1.0e9),
                        encode_status_payload(StatusV1(
                            physics_hz=1.0 / float(env.physics_dt),
                            policy_hz=1.0 / float(env.step_dt),
                            sensor_hz=1.0 / args.sensor_period,
                            bridge_latency_ms=0.0,
                            contact_count=0,
                            dropped_frames=dropped_frames,
                            watchdog_events=snapshot.watchdog_events,
                            flags=int(StatusFlag.COLLISION) | int(StatusFlag.TERMINATED),
                            termination_code=case_failure.termination_code,
                        )),
                    )))
                    break

                except TrialStateMutation as exc:
                    status = "TERMINATED"
                    sim_time = float(env.sim.current_time) - initial_sim_time
                    write_json(args.output / "termination.json", {
                        "sim_time_s": sim_time,
                        "reason": str(exc),
                        "base_xyz": robot.data.root_pos_w[0].detach().cpu().tolist(),
                        "terms": env.termination_manager._term_dones.detach().cpu().tolist(),
                        "contact_body_names": list(contact.body_names),
                        "contact_force_rows": [list(row) for row in contact_guard.samples],
                        "guard": contact_guard.as_record(),
                    })
                    break
                policy_state.reset(dones)
                if bool(dones.any()):
                    status = "TERMINATED"
                    break
                actual_command = env.command_manager.get_command("base_velocity")
                expected_command = actual_command.new_tensor([command])
                if not torch.allclose(actual_command, expected_command, atol=1e-6, rtol=0.0):
                    raise AdapterFailure("V12 command drifted after the physics step")
                _, command_obs_error, _ = v12._policy_command_evidence(observation, command)
                max_command_obs_error = max(max_command_obs_error, command_obs_error)
                with torch.inference_mode():
                    actions = policy(observation)
                if tuple(actions.shape) != (1, 12):
                    raise AdapterFailure(f"V12 action shape {tuple(actions.shape)} != (1, 12)")
                if not torch.isfinite(actions).all() or not torch.isfinite(observation["policy"]).all():
                    status = "NONFINITE"
                    break
                if stance_hold_runtime["active"]:
                    try:
                        previous_actions = _stance_hold_control_step(
                            stance_hold_runtime, robot, contact, foot_ids, actions, command,
                            float(env.sim.current_time) - initial_sim_time,
                        )
                    except StanceHoldError as exc:
                        stance_hold_runtime["failure"] = {
                            "type": type(exc).__name__,
                            "message": str(exc),
                            "step": step,
                        }
                        status = "NONFINITE"
                        break
                else:
                    previous_actions = actions

                sim_time = float(env.sim.current_time) - initial_sim_time
                position = robot.data.root_pos_w[0].detach().cpu().numpy().copy()
                quaternion = robot.data.root_quat_w[0].detach().cpu().numpy()
                qw, qx, qy, qz = (float(value) for value in quaternion)
                yaw = math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
                roll = math.atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))
                pitch = math.asin(max(-1.0, min(1.0, 2 * (qw * qy - qz * qx))))
                linear_body = robot.data.root_lin_vel_b[0].detach().cpu().numpy()
                angular_body = robot.data.root_ang_vel_b[0].detach().cpu().numpy()
                linear_world = robot.data.root_lin_vel_w[0].detach().cpu().numpy()
                angular_world = robot.data.root_ang_vel_w[0].detach().cpu().numpy()
                forces = torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1)
                nonfoot_max = float(forces[nonfoot_ids].max().item()) if nonfoot_ids else 0.0
                nonfoot_substep_max = max(
                    (sample[index] for sample in contact_guard.samples for index in nonfoot_ids),
                    default=0.0,
                )
                horizontal_speed = float(math.hypot(linear_world[0], linear_world[1]))
                goal_error_xy = float(np.linalg.norm(position[:2] - goal_ground[:2]))
                goal_layer_error = float(
                    abs((position[2] - body_height) - goal_ground[2])
                )

                for substep_index, sample in enumerate(contact_guard.samples):
                    if not nonfoot_ids:
                        continue
                    body_index = max(nonfoot_ids, key=lambda index: sample[index])
                    if sample[body_index] >= args.nonfoot_contact_threshold:
                        nonfoot_events.append({
                            "sim_time_s": sim_time - (len(contact_guard.samples) - 1 - substep_index) * float(env.physics_dt),
                            "force_n": sample[body_index],
                            "body": contact.body_names[body_index],
                            "step": step,
                            "substep_index": substep_index,
                            "contact_policy": args.contact_policy,
                        })

                row = {
                    "step": step,
                    "sim_time_s": sim_time,
                    "monotonic_s": time.monotonic() - wall_start,
                    "base_xyz": position.tolist(),
                    "base_quat_wxyz": [qw, qx, qy, qz],
                    "base_rpy_rad": [roll, pitch, yaw],
                    "base_linear_velocity_body": linear_body.tolist(),
                    "base_angular_velocity_body": angular_body.tolist(),
                    "base_linear_velocity_world": linear_world.tolist(),
                    "base_angular_velocity_world": angular_world.tolist(),
                    "horizontal_speed_mps": horizontal_speed,
                    "yaw_rate_radps": float(angular_world[2]),
                    "raw_command": [snapshot.command.vx, snapshot.command.vy, snapshot.command.wz],
                    "admitted_command": list(command),
                    "command_horizontal_norm_mps": horizontal_norm,
                    "command_sequence": snapshot.sequence,
                    "command_stale": snapshot.stale,
                    "command_reason": snapshot.reason,
                    "command_watchdog_events": snapshot.watchdog_events,
                    "command_sequence_gaps": snapshot.sequence_gaps,
                    "command_obs_error": command_obs_error,
                    "joint_pos": robot.data.joint_pos[0].detach().cpu().tolist(),
                    "joint_vel": robot.data.joint_vel[0].detach().cpu().tolist(),
                    "applied_torque": robot.data.applied_torque[0].detach().cpu().tolist(),
                    "foot_force_norms": forces[foot_ids].detach().cpu().tolist(),
                    "nonfoot_force_max_n": nonfoot_max,
                    "nonfoot_force_substep_max_n": nonfoot_substep_max,
                    "contact_substeps_inspected": len(contact_guard.samples),
                    "substep_contact_force_norms_n": contact_guard.samples,
                    "foot_positions": robot.data.body_pos_w[0, body_foot_ids].detach().cpu().tolist(),
                    "action_max": float(actions.abs().max()),
                    "gravity_b": robot.data.projected_gravity_b[0].detach().cpu().tolist(),
                    "goal_error_xy_m": goal_error_xy,
                    "goal_layer_error_m": goal_layer_error,
                }
                row.update(_stance_hold_row(stance_hold_runtime, robot))
                # ---- complete body state, every control step ---------------
                # Position, orientation and both twist representations all come
                # from the physics update that has just completed, so a consumer
                # never has to pair a fresh velocity with an older pose. This is
                # deliberately outside the sensor-stride branch below: odometry
                # freshness must not inherit the point-cloud cadence.
                if args.complete_body_state:
                    state_sequence += 1
                    state_sample_ns = time.monotonic_ns()
                    withheld = dropout.suppress(sim_time, state_sample_ns, state_sequence)
                    row.update({"state_sequence": state_sequence,
                                "state_sample_monotonic_ns": state_sample_ns,
                                "state_withheld_by_probe": withheld})
                    if not withheld:
                        telemetry_sequence += 1
                    control_state_timestamp_ns = int(float(env.sim.current_time) * 1.0e9)
                    frame = encode_frame(
                        MessageType.BODY_STATE_V2,
                        telemetry_sequence,
                        control_state_timestamp_ns,
                        encode_body_state_v2_payload(BodyStateV2(
                            position_world=tuple(float(v) for v in position),
                            orientation_world_xyzw=quaternion_wxyz_to_xyzw(
                                [qw, qx, qy, qz]
                            ),
                            linear_velocity_world=tuple(float(v) for v in linear_world),
                            angular_velocity_world=tuple(float(v) for v in angular_world),
                            linear_velocity_body=tuple(float(v) for v in linear_body),
                            angular_velocity_body=tuple(float(v) for v in angular_body),
                            simulation_time_ns=control_state_timestamp_ns,
                            state_sequence=state_sequence,
                            run_epoch_ns=run_epoch_ns,
                        )),
                    )
                    if not withheld:
                        published = telemetry_server.publish(frame)
                        dropped_frames += int(not published)
                        complete_state_frames += 1
                        complete_state_dropped += int(not published)

                if args.external_goal_mode and external_status_path is not None:
                    status_monotonic_ns = time.monotonic_ns()
                    write_json_atomic(external_status_path, {
                        "schema_version": 1,
                        "run_id": args.external_run_id,
                        "run_epoch_ns": run_epoch_ns,
                        "source": "run_pct_scan_building.py external-goal status snapshot",
                        "output_dir": str(args.output.resolve()),
                        "sim_step": step,
                        "sim_time_s": sim_time,
                        "wall_monotonic_s": time.monotonic() - wall_start,
                        "wall_monotonic_ns": status_monotonic_ns,
                        "sim_time_timestamp_ns": int(float(env.sim.current_time) * 1.0e9),
                        "applied_command": {"vx": command[0], "vy": command[1], "wz": command[2]},
                        "admitted_command": {"vx": command[0], "vy": command[1], "wz": command[2]},
                        "raw_command": {
                            "vx": snapshot.command.vx,
                            "vy": snapshot.command.vy,
                            "wz": snapshot.command.wz,
                        },
                        "command_sequence": snapshot.sequence,
                        "command_stale": snapshot.stale,
                        "command_reason": snapshot.reason,
                        "command_source_timestamp_ns": snapshot.source_timestamp_ns,
                        "command_watchdog_events": snapshot.watchdog_events,
                        "command_sequence_gaps": snapshot.sequence_gaps,
                        "measured": {
                            "base_xyz": [float(v) for v in position],
                            "base_quat_wxyz": [qw, qx, qy, qz],
                            "horizontal_speed_mps": horizontal_speed,
                            "yaw_rate_radps": float(angular_world[2]),
                            "command_obs_error": command_obs_error,
                        },
                        "state_epoch": {
                            "state_sequence": state_sequence,
                            "telemetry_sequence": telemetry_sequence,
                        },
                        "freshness": {
                            "writer_monotonic_ns": status_monotonic_ns,
                            "max_reader_age_s": args.external_status_freshness_seconds,
                            "atomic_replace": True,
                        },
                        "clock_domains": {
                            "sim_time_s": "Isaac simulation time relative to run_clock.simulation_origin_s",
                            "sim_time_timestamp_ns": "Isaac absolute simulation time in ns",
                            "wall_monotonic_ns": "same-host Python time.monotonic_ns",
                            "command_source_timestamp_ns": "same-host monotonic_ns from command sender when present",
                        },
                    })

                records.append(row)
                metrics_file.write(json.dumps(row, sort_keys=True) + "\n")

                # ---- terminal-window bookkeeping (observation only) --------
                if goal_reached_s is None and goal_error_xy <= args.goal_tolerance_m:
                    goal_reached_s = sim_time
                terminal_ok = (
                    horizontal_norm <= args.terminal_command_norm
                    and abs(command[2]) <= args.terminal_command_norm
                    and horizontal_speed <= args.terminal_speed_mps
                    and abs(float(angular_world[2])) <= args.terminal_yaw_rate_radps
                    and goal_error_xy <= args.goal_tolerance_m
                )
                if terminal_ok:
                    if terminal_window_start_s is None:
                        terminal_window_start_s = sim_time
                    elif (
                        terminal_window_satisfied_s is None
                        and sim_time - terminal_window_start_s >= args.terminal_window_seconds
                    ):
                        terminal_window_satisfied_s = sim_time
                else:
                    terminal_window_start_s = None

                if args.external_goal_mode and external_finish_path is not None:
                    if external_finish_latched is None:
                        finish_check = _external_finish_request(
                            external_finish_path,
                            args.external_run_id,
                            run_epoch_ns,
                            time.monotonic_ns(),
                            args.external_status_freshness_seconds,
                        )
                    else:
                        finish_check = {
                            "requested": True,
                            "reason": "latched",
                            "status": external_finish_latched["status"],
                            "request": external_finish_latched.get("request"),
                        }
                    external_finish_state["last_check"] = finish_check
                    zero_applied = _external_zero_command(command, args.terminal_command_norm)
                    still = (
                        horizontal_speed <= args.terminal_speed_mps
                        and abs(float(angular_world[2])) <= args.terminal_yaw_rate_radps
                    )
                    external_finish_latched, external_finish_window_start_s, external_finish_ready_status = _external_finish_step(
                        external_finish_latched,
                        finish_check,
                        zero_applied,
                        still,
                        sim_time,
                        args.external_finish_stillness_seconds,
                    )
                    if external_finish_latched is not None:
                        external_finish_state["last_request"] = _external_request_identity(external_finish_latched)
                    if external_finish_ready_status is not None:
                        external_finish_state["final_reason"] = "backend_terminal_and_measured_still"

                # ---- sensing and telemetry --------------------------------
                if step % sensor_stride == 0:
                    lidar.update(dt=0.0, force_recompute=True)
                    hits = lidar.data.ray_hits_w[0]
                    sensor_position_values, sensor_quaternion_values = mounted_sensor_pose(
                        lidar.data.pos_w[0].detach().cpu().tolist(),
                        lidar.data.quat_w[0].detach().cpu().tolist(),
                        lidar.cfg.offset.pos, lidar.cfg.offset.rot)
                    sensor_position = hits.new_tensor(sensor_position_values)
                    timestamp_ns = int(float(env.sim.current_time) * 1.0e9)
                    world_hits = hits.detach().cpu().tolist()
                    if args.unfiltered_planner_cloud:
                        raw_points = world_hits_to_sensor_points(
                            world_hits, sensor_position_values, sensor_quaternion_values,
                            args.lidar_min_range, args.lidar_max_range,
                            minimum_world_z=None)
                        planner_points = raw_points
                        filter_stats = {
                            "input_hit_count": len(world_hits),
                            "finite_in_range_hit_count": len(raw_points),
                            "obstacle_hit_count": len(raw_points),
                            "filtered_ground_hit_count": 0,
                            "sparse_retained_hit_count": 0,
                            "terrain_filter_enabled": False,
                        }
                    else:
                        raw_points, planner_points, filter_stats = split_geometry_cloud_points(
                            world_hits,
                            sensor_position_values,
                            sensor_quaternion_values,
                            args.lidar_min_range,
                            args.lidar_max_range,
                            args.terrain_filter_cell_size,
                            args.terrain_filter_height_threshold,
                            args.terrain_filter_neighbor_cells,
                            args.terrain_filter_minimum_neighbor_cells,
                        )
                    raw_count, raw_bytes = pack_xyz_points(raw_points)
                    planner_count, planner_bytes = pack_xyz_points(planner_points)
                    scan_index += 1
                    finite = torch.isfinite(hits).all(dim=-1)
                    ranges = torch.linalg.vector_norm(
                        hits - sensor_position.unsqueeze(0), dim=-1
                    )
                    environment = finite & (ranges >= args.lidar_min_range)
                    sensor_row = {
                        "scan_id": scan_index,
                        "sim_time_s": sim_time,
                        "timestamp_ns": timestamp_ns,
                        "sensor_position": sensor_position_values,
                        "sensor_quaternion_wxyz": sensor_quaternion_values,
                        "body_position": position.tolist(),
                        "ray_count": int(hits.shape[0]),
                        "finite_hit_count": int(finite.sum().item()),
                        "environment_hit_count": int(environment.sum().item()),
                        "raw_point_count": raw_count,
                        "planner_point_count": planner_count,
                        "non_ground_hit_count": int(
                            (hits[finite][:, 2] > float(start_ground[2]) + 0.25).sum().item()
                        ),
                        "environment_range_min_m": (
                            float(ranges[environment].min().item())
                            if int(environment.sum().item()) else None
                        ),
                        "environment_range_max_m": (
                            float(ranges[environment].max().item())
                            if int(environment.sum().item()) else None
                        ),
                        "filter_stats": dict(filter_stats),
                    }
                    sensor_file.write(json.dumps(sensor_row, sort_keys=True) + "\n")
                    if scan_index % max(1, args.cloud_record_stride) == 0:
                        cloud_row = {
                            "scan_id": scan_index,
                            "sim_time_s": sim_time,
                            "sensor_position": sensor_position_values,
                            "sensor_quaternion_wxyz": sensor_quaternion_values,
                            "raw_points_sensor_frame": raw_points,
                            "planner_points_sensor_frame": planner_points,
                        }
                        # Serialising ~125 kB of points per scan is the second
                        # largest recording cost after encoding. It carries no
                        # ordering relationship to physics, so it is queued.
                        def _write_cloud(row=cloud_row, handle=cloud_file):
                            row["raw_points_sensor_frame"] = [
                                [round(float(v), 4) for v in point]
                                for point in row["raw_points_sensor_frame"]
                            ]
                            row["planner_points_sensor_frame"] = [
                                [round(float(v), 4) for v in point]
                                for point in row["planner_points_sensor_frame"]
                            ]
                            handle.write(json.dumps(row, sort_keys=True) + "\n")

                        if recorder is not None:
                            recorder.submit(_write_cloud)
                        else:
                            _write_cloud()

                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.SENSOR_FRAME_DUAL_CLOUD_V1,
                        telemetry_sequence,
                        timestamp_ns,
                        encode_dual_cloud_sensor_payload(DualCloudSensorFrameV1(
                            body_position=tuple(float(v) for v in position),
                            body_quaternion_xyzw=quaternion_wxyz_to_xyzw([qw, qx, qy, qz]),
                            sensor_position=tuple(float(v) for v in sensor_position_values),
                            sensor_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                sensor_quaternion_values
                            ),
                            config_sha256=config_sha256,
                            scan_id=scan_index,
                            raw_point_count=raw_count,
                            raw_points_xyz_f32_be=raw_bytes,
                            planner_point_count=planner_count,
                            planner_points_xyz_f32_be=planner_bytes,
                            filtered_ground_point_count=filter_stats["filtered_ground_hit_count"],
                            conservative_retained_point_count=filter_stats[
                                "sparse_retained_hit_count"
                            ],
                        )),
                    )))

                    # Legacy velocity-only state keeps the sensor cadence. It
                    # is superseded by BODY_STATE_V2 above, so it is emitted
                    # only when the complete channel is off; a legacy scope is
                    # then byte-identical to the previous runner.
                    if not args.complete_body_state:
                        state_sequence += 1
                        telemetry_sequence += 1
                        dropped_frames += int(not telemetry_server.publish(encode_frame(
                            MessageType.BODY_STATE_V1,
                            telemetry_sequence,
                            timestamp_ns,
                            encode_body_state_payload(BodyStateV1(
                                linear_velocity_world=tuple(
                                    float(v) for v in linear_world
                                ),
                                angular_velocity_world=tuple(
                                    float(v) for v in angular_world
                                ),
                                linear_velocity_body=tuple(
                                    float(v) for v in linear_body
                                ),
                                angular_velocity_body=tuple(
                                    float(v) for v in angular_body
                                ),
                                simulation_time_ns=timestamp_ns,
                                state_sequence=state_sequence,
                            )),
                        )))

                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.JOINT_STATE_V1,
                        telemetry_sequence,
                        timestamp_ns,
                        encode_joint_state_payload(JointStateV1(
                            names=tuple(str(name) for name in robot.joint_names),
                            positions=tuple(
                                float(v) for v in robot.data.joint_pos[0].detach().cpu().tolist()
                            ),
                            velocities=tuple(
                                float(v) for v in robot.data.joint_vel[0].detach().cpu().tolist()
                            ),
                        )),
                    )))

                    flags = 0
                    contact_count = int(
                        (forces[foot_ids] >= args.contact_force_threshold).sum().item()
                    )
                    if contact_count >= 2:
                        flags |= int(StatusFlag.CONTACT_SUPPORTED)
                    if nonfoot_max >= args.nonfoot_contact_threshold:
                        flags |= int(StatusFlag.COLLISION)
                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.STATUS_V1,
                        telemetry_sequence,
                        timestamp_ns,
                        encode_status_payload(StatusV1(
                            physics_hz=1.0 / float(env.physics_dt),
                            policy_hz=1.0 / float(env.step_dt),
                            sensor_hz=1.0 / args.sensor_period,
                            bridge_latency_ms=0.0 if snapshot.source_timestamp_ns is None else
                            max(0.0, (time.monotonic_ns() - snapshot.source_timestamp_ns) / 1.0e6),
                            contact_count=contact_count,
                            dropped_frames=dropped_frames,
                            watchdog_events=snapshot.watchdog_events,
                            flags=flags,
                            termination_code=0,
                        )),
                    )))

                # ---- third-person capture, world-side camera only ---------
                if step % capture_stride == 0:
                    heading = np.array([math.cos(yaw), math.sin(yaw), 0.0])
                    side = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
                    camera_eye = (
                        position
                        - args.camera_trail_m * heading
                        + args.camera_lateral_m * side
                        + np.array([0.0, 0.0, args.camera_height_m])
                    )
                    camera_target = (
                        position
                        + args.camera_look_ahead_m * heading
                        - np.array([0.0, 0.0, args.camera_look_down_m])
                    )
                    env.sim.set_camera_view(eye=camera_eye, target=camera_target)
                    # Isaac owns the rendering API, so render() stays on this
                    # thread. Only the H.264 encode and the contrast statistic
                    # are queued; frames therefore still reach the writer in
                    # capture order because the recorder is a single worker.
                    frame = raw_env.render()
                    # Display-only pose log, written on this thread in capture
                    # order so row N describes master frame N. Offline
                    # composition pairs each frame to telemetry by this
                    # simulation stamp instead of by wall time, and projects the
                    # overlay with this exact eye/target pair.
                    camera_frames_file.write(json.dumps({
                        "frame_index": camera_frame_index,
                        "step": step,
                        "sim_time_s": sim_time,
                        "eye_xyz": [float(v) for v in camera_eye],
                        "target_xyz": [float(v) for v in camera_target],
                        "up_axis": [0.0, 0.0, 1.0],
                        "base_xyz": [float(v) for v in position],
                        "yaw_rad": float(yaw),
                    }) + "\n")
                    camera_frame_index += 1

                    def _encode_frame(captured=frame):
                        writer.append_data(captured)
                        # A camera that ends up behind a wall renders a flat
                        # field. Record the per-frame contrast so an unusable
                        # capture is detected from the run's own evidence, not
                        # after delivery.
                        luminance = np.asarray(captured, dtype=np.float32)
                        if luminance.ndim == 3:
                            luminance = luminance[..., :3].mean(axis=2)
                        frame_luminance_std.append(float(luminance.std()))

                    if recorder is not None:
                        recorder.submit(_encode_frame)
                    else:
                        _encode_frame()

                if step % 100 == 0:
                    print(json.dumps({
                        "sim_time_s": round(sim_time, 2),
                        "xyz": [round(float(v), 3) for v in position],
                        "command": [round(float(v), 4) for v in command],
                        "goal_error_xy_m": round(goal_error_xy, 3),
                        "scan_id": scan_index,
                    }), flush=True)

                if (args.contact_policy != "native_v12"
                        and robot.data.projected_gravity_b[0, 2].item() > -0.5):
                    status = "EXCESSIVE_TILT"
                    break
                if external_finish_ready_status is not None:
                    status = external_finish_ready_status
                    break
                if (
                    not args.external_goal_mode
                    and terminal_window_satisfied_s is not None
                    and sim_time - terminal_window_satisfied_s > 0.5
                ):
                    status = "GOAL_REACHED_AND_STOPPED"
                    break
    finally:
        # Stop live command and telemetry transport before slow teardown. The
        # priority sender is drained first so queued state and status frames
        # are not lost at shutdown.
        telemetry_server.drain(timeout_seconds=5.0)
        transport_metrics = telemetry_server.queue_metrics()
        command_server.stop()
        telemetry_server.stop()
        # Every queued encode and evidence write is completed before the video
        # file is closed. A writer failure raises here rather than silently
        # truncating the record.
        # Wall-clock spacing of the control loop itself. This is the quantity
        # the 0.25 s feedback deadline is actually measured against, so it is
        # reported with percentiles rather than as a mean.
        control_loop_timing = None
        if len(records) > 1:
            spacing = sorted(
                later["monotonic_s"] - earlier["monotonic_s"]
                for earlier, later in zip(records, records[1:])
            )

            def _quantile(fraction):
                index = min(len(spacing) - 1, int(len(spacing) * fraction))
                return spacing[index]

            control_loop_timing = {
                "samples": len(spacing),
                "p50_s": _quantile(0.50),
                "p95_s": _quantile(0.95),
                "p99_s": _quantile(0.99),
                "max_s": spacing[-1],
                "over_freshness_deadline_count": sum(1 for value in spacing if value > 0.25),
                "freshness_deadline_s": 0.25,
            }
        recorder_metrics = None
        if recorder is not None:
            recorder.close(timeout_seconds=300.0)
            recorder_metrics = recorder.metrics()
        writer.close()
        summary = {
            "status": status,
            "case": args.case,
            "record_count": len(records),
            "sim_seconds": float(env.sim.current_time) - initial_sim_time,
            "recorded_control_seconds": len(records) * float(env.step_dt),
            "wall_seconds": time.monotonic() - wall_start,
            "bridge_connected_wall_s": connected_wall_s,
            "scan_count": scan_index,
            "telemetry_frames": telemetry_sequence,
            "dropped_telemetry_frames": dropped_frames,
            "complete_body_state": {
                "enabled": bool(args.complete_body_state),
                "frames_published": complete_state_frames,
                "frames_dropped": complete_state_dropped,
                "run_epoch_ns": run_epoch_ns,
                "last_state_sequence": state_sequence,
                "period_s": float(env.step_dt),
                "message": "BODY_STATE_V2 id 8, !19dQQQ, 176 bytes, network byte order",
            },
            "telemetry_transport": transport_metrics,
            "feedback_dropout": dropout.record(),
            "recording_load": recorder_metrics,
            "control_loop_timing": control_loop_timing,
            "garbage_collection": {
                "freeze_requested": bool(args.freeze_gc),
                "frozen_objects": gc_frozen,
                "collections_before": [entry["collections"] for entry in gc_before],
                "collections_after": [entry["collections"] for entry in gc.get_stats()],
            },
            "first_nonzero_command_s": first_nonzero_command_s,
            "goal_reached_s": goal_reached_s,
            "terminal_window_satisfied_s": terminal_window_satisfied_s,
            "maximum_command_obs_error": max_command_obs_error,
            "nonfoot_contact_events_over_threshold": nonfoot_events,
            "contact_guard": contact_guard.as_record(),
            "external_goal_mode": {
                "enabled": bool(args.external_goal_mode),
                "run_id": args.external_run_id,
                "control_dir": str(external_control_dir) if external_control_dir is not None else None,
                "status_snapshot": str(external_status_path) if external_status_path is not None else None,
                "finish_request": str(external_finish_path) if external_finish_path is not None else None,
                "finish_window_start_s": external_finish_window_start_s,
                "finish_state": external_finish_state,
                "legacy_fixed_goal_auto_termination_disabled": bool(args.external_goal_mode),
                "route_artifact_role": (
                    "spawn and legacy metric metadata only" if args.external_goal_mode else
                    "legacy fixed-goal metric and terminal target"
                ),
            },
            "stance_hold": _stance_hold_summary(stance_hold_runtime),
            "runtime_import_identity": runtime_import_identity,
            "case_failed": case_failure is not None,
            "contact_policy": args.contact_policy,
            "case_failure_reason": (
                "nonfoot_contact_above_threshold" if case_failure is not None else None
            ),
            "termination_code": (
                case_failure.termination_code if case_failure is not None else 0
            ),
            "command_watchdog_events": records[-1]["command_watchdog_events"] if records else None,
            "command_sequence_gaps": records[-1]["command_sequence_gaps"] if records else None,
            **events.as_record(),
            "claim": identity["claim"],
            "video_master": str(video_path),
            "camera": {
                "trail_m": args.camera_trail_m,
                "lateral_m": args.camera_lateral_m,
                "height_m": args.camera_height_m,
                "look_ahead_m": args.camera_look_ahead_m,
                "look_down_m": args.camera_look_down_m,
                "capture_stride_steps": capture_stride,
                "capture_fps": capture_fps,
                "pose_log": str(camera_frames_path),
                "pose_rows": camera_frame_index,
                "intrinsics": camera_intrinsics,
                "note": "world-side follow camera; observes only, changes no robot state",
            },
            "video_frame_contrast": {
                "frames": len(frame_luminance_std),
                "luminance_std_min": min(frame_luminance_std) if frame_luminance_std else None,
                "luminance_std_mean": (
                    sum(frame_luminance_std) / len(frame_luminance_std)
                    if frame_luminance_std
                    else None
                ),
                "featureless_frames_below_std_8": sum(
                    1 for value in frame_luminance_std if value < 8.0
                ),
            },
        }
        if records:
            positions = np.array([row["base_xyz"] for row in records])
            summary.update({
                "start_xyz": positions[0].tolist(),
                "end_xyz": positions[-1].tolist(),
                "travel_xy_m": float(
                    np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1).sum()
                ),
                "final_goal_error_xy_m": records[-1]["goal_error_xy_m"],
                "final_goal_layer_error_m": records[-1]["goal_layer_error_m"],
                "max_horizontal_speed_mps": max(r["horizontal_speed_mps"] for r in records),
                "max_abs_roll_deg": math.degrees(max(abs(r["base_rpy_rad"][0]) for r in records)),
                "max_abs_pitch_deg": math.degrees(max(abs(r["base_rpy_rad"][1]) for r in records)),
                # A fatal impact can occur before the enclosing control record
                # is completed. The substep guard includes that final impact.
                "max_nonfoot_force_n": contact_guard.as_record()["maximum_nonfoot_force_n"],
                "max_admitted_command_norm_mps": max(
                    r["command_horizontal_norm_mps"] for r in records
                ),
            })
        write_json(args.output / "summary.json", summary)
        print(json.dumps(summary, indent=2), flush=True)
        contact_guard.restore()
        events.restore()
        raw_env.close()
    # A latched physical failure is a failed trial, not a completed one.
    return _external_exit_code(status, trial_exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
