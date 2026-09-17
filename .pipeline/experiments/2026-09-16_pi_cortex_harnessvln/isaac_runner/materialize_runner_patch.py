#!/usr/bin/env python3
"""Materialize the P2B external-episode Building runner patch.

The frozen reference runner is not edited in place. This helper verifies the
known source hash, applies exact anchor replacements to a copy, and writes a
unified diff plus source-hash record for review.

Three anchor groups are applied in order: the external-episode anchors
(`_replacements`), the stance-hold anchors (`_stance_hold_replacements`), which
insert `stance_hold.py` verbatim and default to `--stance-hold off`, and the
scripted-walk anchors (`_scripted_walk_replacements`, PRD D5), which insert
`command_script.py` verbatim and add the `scripted_walk` case, the camera
heading mode and the stance-hold entry damping variants. Every D5 default
(`--camera-heading-mode body`, `--stance-entry-kd ramp`, no command script)
keeps the previous control and camera path.

The PRD D6 crossfade variants (`--stance-entry-kd xfade1s|xfade2s`) and their
landing grace live in `stance_hold.py`; the CLI choices come from its
`STANCE_ENTRY_KD_MODES`. The runner passes episode sim time as the hold's
`now_s`, which is the time base of the grace.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
STANCE_HOLD_MODULE = HERE / "stance_hold.py"
STANCE_HOLD_MODULE_REL = (
    ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py"
)
STANCE_BODY_BEGIN = "# >>> stance_hold runner body begin\n"
STANCE_BODY_END = "# <<< stance_hold runner body end\n"
COMMAND_SCRIPT_MODULE = HERE / "command_script.py"
COMMAND_SCRIPT_MODULE_REL = (
    ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/command_script.py"
)
COMMAND_SCRIPT_BODY_BEGIN = "# >>> command_script runner body begin\n"
COMMAND_SCRIPT_BODY_END = "# <<< command_script runner body end\n"
# Patched runner executed by the actual4 package and the scan_04 fix series
# (external-episode anchors only). Applying only those anchors must still give
# exactly these bytes, so every other difference is a stance-hold anchor.
EXTERNAL_ONLY_PATCHED_SHA256 = (
    "e215a6014bf15dc22a3261cb97c3435252b83ce2bde2f042375ae313493470f3"
)
SOURCE_REL = (
    "references/upstream/2026-09-16_lite3_isaac_harness_backend/"
    "source/machine-dog-nav/integration/lite3_sim_bridge/lite3_sim_bridge/"
    "run_pct_scan_building.py"
)
EXPECTED_SOURCE_SHA256 = (
    "1490dc85146ce7ea71f05c4f5520639da1a342a13e9dfcd8ce0ba04f21c8a76b"
)
DEFAULT_PATCH_REL = (
    ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/"
    "runner_external_episode.patch"
)
DEFAULT_HASHES_REL = (
    ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/"
    "source_hashes.json"
)


EXTERNAL_HELPER_SOURCE = '''

def write_json_atomic(path: Path, payload) -> None:
    """Write compact JSON through a same-directory atomic rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    tmp.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\\n",
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
'''


# Runner-side glue for the stance hold. It reads Isaac objects through duck-typed
# tensor methods only (detach/cpu/numpy/new_tensor/tolist), so tests can drive it
# with CPU tensors and fake articulation objects.
STANCE_HOLD_RUNNER_SOURCE = r'''

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


def _stance_hold_setup(mode, env, robot, wrapped, output_dir, entry_kd=STANCE_ENTRY_KD_DEFAULT):
    """Record the control contract; auto mode also validates it and builds the hold."""
    if mode not in STANCE_HOLD_MODES:
        raise AdapterFailure("unsupported --stance-hold value: %r" % (mode,))
    if entry_kd not in STANCE_ENTRY_KD_MODES:
        raise AdapterFailure("unsupported --stance-entry-kd value: %r" % (entry_kd,))
    record = {
        "schema_version": 1,
        "mode": mode,
        "entry_kd": entry_kd,
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
        "entry_kd": entry_kd,
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
                               joint_count=len(ids), entry_kd=entry_kd),
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
        "entry_kd": runtime["entry_kd"],
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
'''


# Runner-side glue for PRD D5: the scripted_walk case, the camera heading mode
# and the entry damping option. It uses only names that the frozen runner or the
# inserted modules define (AdapterFailure, sha256, write_json, shutil, Path).
SCRIPTED_WALK_RUNNER_SOURCE = r'''

# ---- scripted walk, camera heading, entry damping (materialize_runner_patch.py, PRD D5) ----
CAMERA_HEADING_MODES = ("body", "initial")
CAMERA_HEADING_DEFAULT = "body"


def _scripted_walk_limits(args):
    """The runner's own command limits; a script outside them is refused, never clamped."""
    return {
        "max_vx": args.max_vx,
        "max_vy": args.max_vy,
        "max_wz": args.max_wz,
        "max_horizontal_norm": args.max_horizontal_norm,
    }


def _scripted_walk_validate_args(args):
    """Pre-Isaac checks of the D5 flags; raises ValueError (CommandScriptError is one)."""
    if args.stance_entry_kd not in STANCE_ENTRY_KD_MODES:
        raise ValueError("unsupported --stance-entry-kd value: %r" % (args.stance_entry_kd,))
    if args.stance_hold != "auto" and args.stance_entry_kd != STANCE_ENTRY_KD_DEFAULT:
        raise ValueError("--stance-entry-kd %s applies only with --stance-hold auto" % args.stance_entry_kd)
    if args.camera_heading_mode not in CAMERA_HEADING_MODES:
        raise ValueError("unsupported --camera-heading-mode value: %r" % (args.camera_heading_mode,))
    if args.case == SCRIPTED_WALK_CASE:
        if args.command_script is None:
            raise ValueError("--case %s requires --command-script" % SCRIPTED_WALK_CASE)
        load_command_script(args.command_script, _scripted_walk_limits(args))
    elif args.command_script is not None:
        raise ValueError("--command-script is valid only with --case %s" % SCRIPTED_WALK_CASE)


def _scripted_walk_setup(args, scope):
    """Load the command script, bind it to the frozen scope and record it. None for other cases."""
    if args.case != SCRIPTED_WALK_CASE:
        if args.command_script is not None:
            raise AdapterFailure("--command-script is valid only with --case %s" % SCRIPTED_WALK_CASE)
        return None
    if args.command_script is None:
        raise AdapterFailure("--case %s requires --command-script" % SCRIPTED_WALK_CASE)
    try:
        loaded = load_command_script(args.command_script, _scripted_walk_limits(args))
    except CommandScriptError as exc:
        raise AdapterFailure("command script is invalid: %s" % exc)
    expected = scope.get("command_script_sha256")
    if expected != loaded["sha256"]:
        raise AdapterFailure("command script SHA-256 %s differs from the frozen scope command_script_sha256 %r"
                             % (loaded["sha256"], expected))
    output = Path(args.output)
    copy = output / "command_script.json"
    shutil.copyfile(str(args.command_script), str(copy))
    if sha256(copy) != loaded["sha256"]:
        raise AdapterFailure("command script changed while it was copied into the run output")
    record = {
        "schema_version": 1,
        "case": args.case,
        "command_script": {
            "source_path": str(Path(args.command_script).resolve()),
            "copy": copy.name,
            "sha256": loaded["sha256"],
            "bytes": loaded["bytes"],
        },
        "scope_command_script_sha256": expected,
        "script": loaded["script"],
        "module": {
            "path": COMMAND_SCRIPT_SOURCE_REL,
            "sha256": COMMAND_SCRIPT_SOURCE_SHA256,
            "body_sha256": COMMAND_SCRIPT_BODY_SHA256,
        },
        "selection_rule": (
            "segment i applies from the first control step whose loop-top sim_time "
            "(Isaac time minus run_clock.simulation_origin_s, before wrapped.step) is at least "
            "t_start_s - %g s; metrics.jsonl rows record it as script_segment" % COMMAND_SCRIPT_TIME_EPS_S
        ),
        "command_path": (
            "the scripted command replaces the TCP command where stand_probe zeroes it, before the unchanged "
            "admission norm check; base_velocity term.commands, the post-step command parity and policy "
            "observation checks, metrics admitted_command, current_command.json applied/admitted command, "
            "the stance hold and the external finish dwell all use it; the TCP snapshot is still read and "
            "recorded as raw_command and command_stale/reason"
        ),
    }
    write_json(output / "scripted_walk_setup.json", record)
    loaded["record"] = record
    return loaded


def _scripted_walk_summary(scripted_walk):
    if scripted_walk is None:
        return None
    return dict(scripted_walk["record"])


def _camera_view_yaw(mode, latched_yaw, body_yaw):
    """Yaw for the follow camera's heading/side vectors and the latched initial yaw.

    body: the current body yaw, unchanged (the previous camera path).
    initial: the body yaw of the first captured frame, latched for the whole run,
    so the camera translates with the robot but does not turn with its body twist.
    """
    if mode == "body":
        return body_yaw, latched_yaw
    if mode == "initial":
        if latched_yaw is None:
            latched_yaw = float(body_yaw)
        return latched_yaw, latched_yaw
    raise AdapterFailure("unsupported camera heading mode: %r" % (mode,))
'''


def load_marked_module(path: Path, begin: str, end: str) -> Dict[str, str]:
    """Return the marked body of a module that the materializer inserts verbatim, and its hashes."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError("%s must contain each body marker exactly once" % path.name)
    body = text.split(begin, 1)[1].split(end, 1)[0]
    tree = ast.parse(body, feature_version=(3, 8))
    if any(isinstance(node, ast.ImportFrom) and node.module == "__future__" for node in ast.walk(tree)):
        raise RuntimeError("%s body must not contain __future__ imports" % path.name)
    return {
        "path": str(path),
        "body": body,
        "sha256": sha256_text(text),
        "body_sha256": sha256_text(body),
    }


def load_stance_hold_module(path: Optional[Path] = None) -> Dict[str, str]:
    """Return the marked body of stance_hold.py and its hashes."""
    return load_marked_module(path or STANCE_HOLD_MODULE, STANCE_BODY_BEGIN, STANCE_BODY_END)


def load_command_script_module(path: Optional[Path] = None) -> Dict[str, str]:
    """Return the marked body of command_script.py and its hashes."""
    return load_marked_module(path or COMMAND_SCRIPT_MODULE, COMMAND_SCRIPT_BODY_BEGIN, COMMAND_SCRIPT_BODY_END)


def _replacements() -> List[Dict[str, str]]:
    return [
        {
            "name": "imports",
            "old": "import math\nimport shutil\nimport time\n",
            "new": "import math\nimport os\nimport re\nimport shutil\nimport sys\nimport time\n",
        },
        {
            "name": "atomic_helpers",
            "old": (
                "def write_json(path: Path, payload) -> None:\n"
                "    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + \"\\n\", encoding=\"utf-8\")\n"
            ),
            "new": (
                "def write_json(path: Path, payload) -> None:\n"
                "    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + \"\\n\", encoding=\"utf-8\")\n"
                + EXTERNAL_HELPER_SOURCE
            ),
        },
        {
            "name": "cli_external_args",
            "old": (
                "    parser.add_argument(\"--feedback-dropout-start-s\", type=float, default=-1.0)\n"
                "    parser.add_argument(\"--feedback-dropout-wall-s\", type=float, default=0.0)\n"
                "    parser.add_argument(\"--seed\", type=int, default=42)\n"
            ),
            "new": (
                "    parser.add_argument(\"--feedback-dropout-start-s\", type=float, default=-1.0)\n"
                "    parser.add_argument(\"--feedback-dropout-wall-s\", type=float, default=0.0)\n"
                "    parser.add_argument(\"--external-goal-mode\", action=\"store_true\", default=False,\n"
                "                        help=\"Disable only legacy fixed-goal auto-success termination and wait for an external backend finish request\")\n"
                "    parser.add_argument(\"--external-run-id\", default=None,\n"
                "                        help=\"Run identity shared with the external backend; required with --external-goal-mode\")\n"
                "    parser.add_argument(\"--external-control-dir\", type=Path, default=None,\n"
                "                        help=\"Directory for current_command.json and finish_request.json; defaults to OUTPUT/external_episode\")\n"
                "    parser.add_argument(\"--external-finish-stillness-seconds\", type=float, default=1.0)\n"
                "    parser.add_argument(\"--external-status-freshness-seconds\", type=float, default=2.0)\n"
                "    parser.add_argument(\"--seed\", type=int, default=42)\n"
            ),
        },
        {
            "name": "main_validation",
            "old": (
                "    args = build_parser().parse_args(argv)\n"
                "    if args.case == \"native_nominal\" and args.contact_policy != \"native_v12\":\n"
            ),
            "new": (
                "    args = build_parser().parse_args(argv)\n"
                "    _validate_external_goal_args(args)\n"
                "    if args.case == \"native_nominal\" and args.contact_policy != \"native_v12\":\n"
            ),
        },
        {
            "name": "external_control_dir_is_path",
            "old": (
                "    paths = {\"scene\", \"runtime\", \"checkpoint\", \"route_artifact\", \"scope\", \"output\",\n"
                "             \"execution_manifest\"}\n"
            ),
            "new": (
                "    paths = {\"scene\", \"runtime\", \"checkpoint\", \"route_artifact\", \"scope\", \"output\",\n"
                "             \"execution_manifest\", \"external_control_dir\"}\n"
            ),
        },
        {
            "name": "identity_external_contract",
            "old": (
                "        \"duration_seconds\": args.duration_seconds,\n"
                "        \"actor_obs_shape\": list(observation[\"policy\"].shape),\n"
                "    }\n"
            ),
            "new": (
                "        \"duration_seconds\": args.duration_seconds,\n"
                "        \"external_goal_mode\": bool(args.external_goal_mode),\n"
                "        \"external_goal_contract\": {\n"
                "            \"enabled\": bool(args.external_goal_mode),\n"
                "            \"run_id\": args.external_run_id,\n"
                "            \"control_dir\": (\n"
                "                str((args.external_control_dir or (args.output / \"external_episode\")).resolve())\n"
                "                if args.external_goal_mode else None\n"
                "            ),\n"
                "            \"status_snapshot\": \"current_command.json, atomically replaced by this runner\",\n"
                "            \"finish_request\": \"finish_request.json, written once by the external backend\",\n"
                "            \"finish_schema\": {\n"
                "                \"schema_version\": 1,\n"
                "                \"run_id\": \"same as --external-run-id\",\n"
                "                \"request_id\": \"backend unique id\",\n"
                "                \"observed_run_epoch_ns\": \"run_epoch_ns copied from current_command.json\",\n"
                "                \"requested_at_monotonic_ns\": \"same-host monotonic_ns when backend writes the request\",\n"
                "                \"backend_terminal_status\": \"FINISHED or FAILED\",\n"
                "            },\n"
                "            \"finish_stillness_seconds\": args.external_finish_stillness_seconds,\n"
                "            \"freshness_seconds\": args.external_status_freshness_seconds,\n"
                "            \"route_artifact_role\": (\n"
                "                \"spawn and legacy metric metadata only; it is not a command target in external-goal mode\"\n"
                "                if args.external_goal_mode else \"legacy fixed-goal metric and terminal target\"\n"
                "            ),\n"
                "        },\n"
                "        \"actor_obs_shape\": list(observation[\"policy\"].shape),\n"
                "    }\n"
            ),
        },
        {
            "name": "external_paths",
            "old": (
                "    run_epoch_ns = time.time_ns()\n"
                "    recorder = AsyncRecorder(max_pending=64) if args.async_recording else None\n"
                "    metrics_path = args.output / \"metrics.jsonl\"\n"
            ),
            "new": (
                "    run_epoch_ns = time.time_ns()\n"
                "    external_control_dir = None\n"
                "    external_status_path = None\n"
                "    external_finish_path = None\n"
                "    external_finish_window_start_s = None\n"
                "    external_finish_latched = None\n"
                "    external_finish_state = {\"last_check\": None, \"last_request\": None, \"final_reason\": None}\n"
                "    if args.external_goal_mode:\n"
                "        external_control_dir = args.external_control_dir or (args.output / \"external_episode\")\n"
                "        external_control_dir.mkdir(parents=True, exist_ok=True)\n"
                "        external_status_path = external_control_dir / \"current_command.json\"\n"
                "        external_finish_path = external_control_dir / \"finish_request.json\"\n"
                "        write_json(external_control_dir / \"contract.json\", identity[\"external_goal_contract\"])\n"
                "    recorder = AsyncRecorder(max_pending=64) if args.async_recording else None\n"
                "    metrics_path = args.output / \"metrics.jsonl\"\n"
            ),
        },
        {
            "name": "runtime_module_origin_identity",
            "old": (
                "    __import__(\"robot_lab.tasks\")\n"
                "\n"
                "    # ---- identity gates before anything physical happens -------------------\n"
            ),
            "new": (
                "    __import__(\"robot_lab.tasks\")\n"
                "    runtime_import_identity = _validate_runtime_module_origins(args.runtime)\n"
                "    write_json(args.output / \"runtime_import_identity.json\", runtime_import_identity)\n"
                "\n"
                "    # ---- identity gates before anything physical happens -------------------\n"
            ),
        },
        {
            "name": "step_finish_status_sentinel",
            "old": (
                "                sim_time = float(env.sim.current_time) - initial_sim_time\n"
                "                snapshot = command_server.snapshot(time.monotonic_ns())\n"
            ),
            "new": (
                "                sim_time = float(env.sim.current_time) - initial_sim_time\n"
                "                external_finish_ready_status = None\n"
                "                snapshot = command_server.snapshot(time.monotonic_ns())\n"
            ),
        },
        {
            "name": "current_command_snapshot",
            "old": (
                "                records.append(row)\n"
                "                metrics_file.write(json.dumps(row, sort_keys=True) + \"\\n\")\n"
            ),
            "new": (
                "                if args.external_goal_mode and external_status_path is not None:\n"
                "                    status_monotonic_ns = time.monotonic_ns()\n"
                "                    write_json_atomic(external_status_path, {\n"
                "                        \"schema_version\": 1,\n"
                "                        \"run_id\": args.external_run_id,\n"
                "                        \"run_epoch_ns\": run_epoch_ns,\n"
                "                        \"source\": \"run_pct_scan_building.py external-goal status snapshot\",\n"
                "                        \"output_dir\": str(args.output.resolve()),\n"
                "                        \"sim_step\": step,\n"
                "                        \"sim_time_s\": sim_time,\n"
                "                        \"wall_monotonic_s\": time.monotonic() - wall_start,\n"
                "                        \"wall_monotonic_ns\": status_monotonic_ns,\n"
                "                        \"sim_time_timestamp_ns\": int(float(env.sim.current_time) * 1.0e9),\n"
                "                        \"applied_command\": {\"vx\": command[0], \"vy\": command[1], \"wz\": command[2]},\n"
                "                        \"admitted_command\": {\"vx\": command[0], \"vy\": command[1], \"wz\": command[2]},\n"
                "                        \"raw_command\": {\n"
                "                            \"vx\": snapshot.command.vx,\n"
                "                            \"vy\": snapshot.command.vy,\n"
                "                            \"wz\": snapshot.command.wz,\n"
                "                        },\n"
                "                        \"command_sequence\": snapshot.sequence,\n"
                "                        \"command_stale\": snapshot.stale,\n"
                "                        \"command_reason\": snapshot.reason,\n"
                "                        \"command_source_timestamp_ns\": snapshot.source_timestamp_ns,\n"
                "                        \"command_watchdog_events\": snapshot.watchdog_events,\n"
                "                        \"command_sequence_gaps\": snapshot.sequence_gaps,\n"
                "                        \"measured\": {\n"
                "                            \"base_xyz\": [float(v) for v in position],\n"
                "                            \"base_quat_wxyz\": [qw, qx, qy, qz],\n"
                "                            \"horizontal_speed_mps\": horizontal_speed,\n"
                "                            \"yaw_rate_radps\": float(angular_world[2]),\n"
                "                            \"command_obs_error\": command_obs_error,\n"
                "                        },\n"
                "                        \"state_epoch\": {\n"
                "                            \"state_sequence\": state_sequence,\n"
                "                            \"telemetry_sequence\": telemetry_sequence,\n"
                "                        },\n"
                "                        \"freshness\": {\n"
                "                            \"writer_monotonic_ns\": status_monotonic_ns,\n"
                "                            \"max_reader_age_s\": args.external_status_freshness_seconds,\n"
                "                            \"atomic_replace\": True,\n"
                "                        },\n"
                "                        \"clock_domains\": {\n"
                "                            \"sim_time_s\": \"Isaac simulation time relative to run_clock.simulation_origin_s\",\n"
                "                            \"sim_time_timestamp_ns\": \"Isaac absolute simulation time in ns\",\n"
                "                            \"wall_monotonic_ns\": \"same-host Python time.monotonic_ns\",\n"
                "                            \"command_source_timestamp_ns\": \"same-host monotonic_ns from command sender when present\",\n"
                "                        },\n"
                "                    })\n"
                "\n"
                "                records.append(row)\n"
                "                metrics_file.write(json.dumps(row, sort_keys=True) + \"\\n\")\n"
            ),
        },
        {
            "name": "external_finish_logic",
            "old": (
                "                if terminal_ok:\n"
                "                    if terminal_window_start_s is None:\n"
                "                        terminal_window_start_s = sim_time\n"
                "                    elif (\n"
                "                        terminal_window_satisfied_s is None\n"
                "                        and sim_time - terminal_window_start_s >= args.terminal_window_seconds\n"
                "                    ):\n"
                "                        terminal_window_satisfied_s = sim_time\n"
                "                else:\n"
                "                    terminal_window_start_s = None\n"
            ),
            "new": (
                "                if terminal_ok:\n"
                "                    if terminal_window_start_s is None:\n"
                "                        terminal_window_start_s = sim_time\n"
                "                    elif (\n"
                "                        terminal_window_satisfied_s is None\n"
                "                        and sim_time - terminal_window_start_s >= args.terminal_window_seconds\n"
                "                    ):\n"
                "                        terminal_window_satisfied_s = sim_time\n"
                "                else:\n"
                "                    terminal_window_start_s = None\n"
                "\n"
                "                if args.external_goal_mode and external_finish_path is not None:\n"
                "                    if external_finish_latched is None:\n"
                "                        finish_check = _external_finish_request(\n"
                "                            external_finish_path,\n"
                "                            args.external_run_id,\n"
                "                            run_epoch_ns,\n"
                "                            time.monotonic_ns(),\n"
                "                            args.external_status_freshness_seconds,\n"
                "                        )\n"
                "                    else:\n"
                "                        finish_check = {\n"
                "                            \"requested\": True,\n"
                "                            \"reason\": \"latched\",\n"
                "                            \"status\": external_finish_latched[\"status\"],\n"
                "                            \"request\": external_finish_latched.get(\"request\"),\n"
                "                        }\n"
                "                    external_finish_state[\"last_check\"] = finish_check\n"
                "                    zero_applied = _external_zero_command(command, args.terminal_command_norm)\n"
                "                    still = (\n"
                "                        horizontal_speed <= args.terminal_speed_mps\n"
                "                        and abs(float(angular_world[2])) <= args.terminal_yaw_rate_radps\n"
                "                    )\n"
                "                    external_finish_latched, external_finish_window_start_s, external_finish_ready_status = _external_finish_step(\n"
                "                        external_finish_latched,\n"
                "                        finish_check,\n"
                "                        zero_applied,\n"
                "                        still,\n"
                "                        sim_time,\n"
                "                        args.external_finish_stillness_seconds,\n"
                "                    )\n"
                "                    if external_finish_latched is not None:\n"
                "                        external_finish_state[\"last_request\"] = _external_request_identity(external_finish_latched)\n"
                "                    if external_finish_ready_status is not None:\n"
                "                        external_finish_state[\"final_reason\"] = \"backend_terminal_and_measured_still\"\n"
            ),
        },
        {
            "name": "external_finish_after_safety",
            "old": (
                "                if (args.contact_policy != \"native_v12\"\n"
                "                        and robot.data.projected_gravity_b[0, 2].item() > -0.5):\n"
                "                    status = \"EXCESSIVE_TILT\"\n"
                "                    break\n"
                "                if (\n"
            ),
            "new": (
                "                if (args.contact_policy != \"native_v12\"\n"
                "                        and robot.data.projected_gravity_b[0, 2].item() > -0.5):\n"
                "                    status = \"EXCESSIVE_TILT\"\n"
                "                    break\n"
                "                if external_finish_ready_status is not None:\n"
                "                    status = external_finish_ready_status\n"
                "                    break\n"
                "                if (\n"
            ),
        },
        {
            "name": "disable_legacy_external_terminal",
            "old": (
                "                if (\n"
                "                    terminal_window_satisfied_s is not None\n"
                "                    and sim_time - terminal_window_satisfied_s > 0.5\n"
                "                ):\n"
                "                    status = \"GOAL_REACHED_AND_STOPPED\"\n"
                "                    break\n"
            ),
            "new": (
                "                if (\n"
                "                    not args.external_goal_mode\n"
                "                    and terminal_window_satisfied_s is not None\n"
                "                    and sim_time - terminal_window_satisfied_s > 0.5\n"
                "                ):\n"
                "                    status = \"GOAL_REACHED_AND_STOPPED\"\n"
                "                    break\n"
            ),
        },
        {
            "name": "summary_external_state",
            "old": (
                "            \"case_failed\": case_failure is not None,\n"
                "            \"contact_policy\": args.contact_policy,\n"
            ),
            "new": (
                "            \"external_goal_mode\": {\n"
                "                \"enabled\": bool(args.external_goal_mode),\n"
                "                \"run_id\": args.external_run_id,\n"
                "                \"control_dir\": str(external_control_dir) if external_control_dir is not None else None,\n"
                "                \"status_snapshot\": str(external_status_path) if external_status_path is not None else None,\n"
                "                \"finish_request\": str(external_finish_path) if external_finish_path is not None else None,\n"
                "                \"finish_window_start_s\": external_finish_window_start_s,\n"
                "                \"finish_state\": external_finish_state,\n"
                "                \"legacy_fixed_goal_auto_termination_disabled\": bool(args.external_goal_mode),\n"
                "                \"route_artifact_role\": (\n"
                "                    \"spawn and legacy metric metadata only\" if args.external_goal_mode else\n"
                "                    \"legacy fixed-goal metric and terminal target\"\n"
                "                ),\n"
                "            },\n"
                "            \"runtime_import_identity\": runtime_import_identity,\n"
                "            \"case_failed\": case_failure is not None,\n"
                "            \"contact_policy\": args.contact_policy,\n"
            ),
        },
        {
            "name": "external_exit_code",
            "old": (
                "    # A latched physical failure is a failed trial, not a completed one.\n"
                "    return trial_exit_code(status)\n"
            ),
            "new": (
                "    # A latched physical failure is a failed trial, not a completed one.\n"
                "    return _external_exit_code(status, trial_exit_code)\n"
            ),
        },
    ]


STANCE_HOLD_STEP_BRANCH = (
    "                if stance_hold_runtime[\"active\"]:\n"
    "                    try:\n"
    "                        previous_actions = _stance_hold_control_step(\n"
    "                            stance_hold_runtime, robot, contact, foot_ids, actions, command,\n"
    "                            float(env.sim.current_time) - initial_sim_time,\n"
    "                        )\n"
    "                    except StanceHoldError as exc:\n"
    "                        stance_hold_runtime[\"failure\"] = {\n"
    "                            \"type\": type(exc).__name__,\n"
    "                            \"message\": str(exc),\n"
    "                            \"step\": step,\n"
    "                        }\n"
    "                        status = \"NONFINITE\"\n"
    "                        break\n"
    "                else:\n"
    "                    previous_actions = actions\n"
)


def _stance_hold_replacements(module: Dict[str, str]) -> List[Dict[str, str]]:
    """Anchors applied after the external-episode group; `off` keeps today's step."""
    return [
        {
            "name": "stance_hold_module",
            "old": "\n\ndef _read_viewer_camera_intrinsics(stage, cam_prim_path: str, resolution) -> dict:\n",
            "new": (
                "\n\n# ---- stance hold state machine, inserted verbatim from stance_hold.py ------\n"
                "STANCE_HOLD_SOURCE_REL = %r\n"
                "STANCE_HOLD_SOURCE_SHA256 = %r\n"
                "STANCE_HOLD_BODY_SHA256 = %r\n"
                % (STANCE_HOLD_MODULE_REL, module["sha256"], module["body_sha256"])
                + module["body"]
                + STANCE_HOLD_RUNNER_SOURCE
                + "\n\ndef _read_viewer_camera_intrinsics(stage, cam_prim_path: str, resolution) -> dict:\n"
            ),
        },
        {
            "name": "cli_stance_hold",
            "old": (
                "    parser.add_argument(\"--seed\", type=int, default=42)\n"
                "    parser.add_argument(\"--device\", default=\"cuda:0\")\n"
            ),
            "new": (
                "    parser.add_argument(\"--stance-hold\", choices=STANCE_HOLD_MODES, default=\"off\",\n"
                "                        help=\"off: the V12 policy owns the joints at every step and no gain is written. \"\n"
                "                             \"auto: PD stance hold after an exactly zero command (stance_hold.py)\")\n"
                "    parser.add_argument(\"--seed\", type=int, default=42)\n"
                "    parser.add_argument(\"--device\", default=\"cuda:0\")\n"
            ),
        },
        {
            # AC3 of the stance-hold task is a 60 s stand; the frozen cap was 45 s.
            # Only the stand_probe case changes; every other case keeps its bound.
            "name": "stand_probe_duration_cap_60s",
            "old": "    maximum = {\"full_nominal\": 180.0, \"native_nominal\": 600.0}.get(case, 45.0)\n",
            "new": (
                "    maximum = {\"full_nominal\": 180.0, \"native_nominal\": 600.0,\n"
                "               \"stand_probe\": 60.0}.get(case, 45.0)\n"
            ),
        },
        {
            "name": "stance_hold_setup",
            "old": (
                "    nonfoot_ids = [index for index in range(len(contact.body_names)) if index not in foot_ids]\n"
                "    body_foot_ids, _ = robot.find_bodies(foot_names, preserve_order=True)\n"
            ),
            "new": (
                "    nonfoot_ids = [index for index in range(len(contact.body_names)) if index not in foot_ids]\n"
                "    body_foot_ids, _ = robot.find_bodies(foot_names, preserve_order=True)\n"
                "    # Off mode only reads and records the control contract; auto mode fails closed.\n"
                "    stance_hold_runtime = _stance_hold_setup(args.stance_hold, env, robot, wrapped, args.output)\n"
            ),
        },
        {
            "name": "stance_hold_step",
            "old": "                previous_actions = actions\n",
            "new": STANCE_HOLD_STEP_BRANCH,
        },
        {
            "name": "stance_hold_metrics_row",
            "old": (
                "                    \"goal_error_xy_m\": goal_error_xy,\n"
                "                    \"goal_layer_error_m\": goal_layer_error,\n"
                "                }\n"
            ),
            "new": (
                "                    \"goal_error_xy_m\": goal_error_xy,\n"
                "                    \"goal_layer_error_m\": goal_layer_error,\n"
                "                }\n"
                "                row.update(_stance_hold_row(stance_hold_runtime, robot))\n"
            ),
        },
        {
            "name": "stance_hold_summary",
            "old": "            \"runtime_import_identity\": runtime_import_identity,\n",
            "new": (
                "            \"stance_hold\": _stance_hold_summary(stance_hold_runtime),\n"
                "            \"runtime_import_identity\": runtime_import_identity,\n"
            ),
        },
    ]


SCRIPTED_WALK_COMMAND_BRANCH = (
    "                if args.case == \"stand_probe\":\n"
    "                    # A standing qualification probe never forwards motion.\n"
    "                    command = (0.0, 0.0, 0.0)\n"
    "                script_segment = None\n"
    "                if scripted_walk is not None:\n"
    "                    # PRD D5 scripted walk: the command script replaces the TCP command here,\n"
    "                    # before the unchanged admission norm check, the base_velocity write and\n"
    "                    # the post-step command parity checks.\n"
    "                    script_segment, command = command_script_at(scripted_walk[\"script\"], sim_time)\n"
)


def _scripted_walk_replacements(module: Dict[str, str]) -> List[Dict[str, str]]:
    """PRD D5 anchors, applied after the stance-hold group; every default keeps the previous path."""
    return [
        {
            "name": "scripted_walk_module",
            "old": "\n\ndef _read_viewer_camera_intrinsics(stage, cam_prim_path: str, resolution) -> dict:\n",
            "new": (
                "\n\n# ---- command scripts, inserted verbatim from command_script.py ------------\n"
                "COMMAND_SCRIPT_SOURCE_REL = %r\n"
                "COMMAND_SCRIPT_SOURCE_SHA256 = %r\n"
                "COMMAND_SCRIPT_BODY_SHA256 = %r\n"
                % (COMMAND_SCRIPT_MODULE_REL, module["sha256"], module["body_sha256"])
                + module["body"]
                + SCRIPTED_WALK_RUNNER_SOURCE
                + "\n\ndef _read_viewer_camera_intrinsics(stage, cam_prim_path: str, resolution) -> dict:\n"
            ),
        },
        {
            "name": "cases_scripted_walk",
            "old": "CASES = (\"stand_probe\", \"flat_nominal\", \"full_nominal\", \"native_nominal\")\n",
            "new": (
                "CASES = (\"stand_probe\", \"flat_nominal\", \"full_nominal\", \"native_nominal\",\n"
                "         \"scripted_walk\")\n"
            ),
        },
        {
            "name": "cli_camera_heading_mode",
            "old": "    parser.add_argument(\"--camera-look-down-m\", type=float, default=0.25)\n",
            "new": (
                "    parser.add_argument(\"--camera-look-down-m\", type=float, default=0.25)\n"
                "    parser.add_argument(\"--camera-heading-mode\", choices=CAMERA_HEADING_MODES, default=\"body\",\n"
                "                        help=\"body: heading and side vectors follow the body yaw (previous behaviour). \"\n"
                "                             \"initial: they keep the yaw of the first captured frame\")\n"
            ),
        },
        {
            "name": "cli_scripted_walk_entry_kd",
            "old": (
                "    parser.add_argument(\"--seed\", type=int, default=42)\n"
                "    parser.add_argument(\"--device\", default=\"cuda:0\")\n"
            ),
            "new": (
                "    parser.add_argument(\"--stance-entry-kd\", choices=STANCE_ENTRY_KD_MODES, default=\"ramp\",\n"
                "                        help=\"stance hold entry: ramp (Kd follows the Kp ramp), step1 \"\n"
                "                             \"(Kd 1 from entry), step2p5 (Kd 2.5 from entry, eased to 1 by FIXED_STAND), \"\n"
                "                             \"xfade1s or xfade2s (Kd 1 from entry, 1 s or 2 s crossfade from the policy PD \"\n"
                "                             \"law to the hold, arming after 1 s of sim time; PRD D6)\")\n"
                "    parser.add_argument(\"--command-script\", type=Path, default=None,\n"
                "                        help=\"JSON command script; required by and only valid with --case scripted_walk\")\n"
                "    parser.add_argument(\"--seed\", type=int, default=42)\n"
                "    parser.add_argument(\"--device\", default=\"cuda:0\")\n"
            ),
        },
        {
            # The script path is host-specific like the other inputs; its content is
            # bound through the frozen scope's command_script_sha256 instead.
            "name": "command_script_is_path",
            "old": "             \"execution_manifest\", \"external_control_dir\"}\n",
            "new": "             \"execution_manifest\", \"external_control_dir\", \"command_script\"}\n",
        },
        {
            # PRD D5 scripted walk runs up to 60 s like the stand_probe cap; no other case changes.
            "name": "scripted_walk_duration_cap_60s",
            "old": "               \"stand_probe\": 60.0}.get(case, 45.0)\n",
            "new": "               \"stand_probe\": 60.0, \"scripted_walk\": 60.0}.get(case, 45.0)\n",
        },
        {
            "name": "main_validation_scripted_walk",
            "old": "    _validate_external_goal_args(args)\n",
            "new": "    _validate_external_goal_args(args)\n    _scripted_walk_validate_args(args)\n",
        },
        {
            "name": "scripted_walk_setup",
            "old": "    frozen = scope[\"frozen_assets\"]\n",
            "new": (
                "    frozen = scope[\"frozen_assets\"]\n"
                "    # PRD D5: the command script is validated and bound to the frozen scope before physics.\n"
                "    scripted_walk = _scripted_walk_setup(args, scope)\n"
            ),
        },
        {
            "name": "stance_entry_kd_setup",
            "old": "    stance_hold_runtime = _stance_hold_setup(args.stance_hold, env, robot, wrapped, args.output)\n",
            "new": (
                "    stance_hold_runtime = _stance_hold_setup(args.stance_hold, env, robot, wrapped, args.output,\n"
                "                                             entry_kd=args.stance_entry_kd)\n"
            ),
        },
        {
            "name": "camera_heading_state",
            "old": "    camera_frame_index = 0\n    wall_start = time.monotonic()\n",
            "new": (
                "    camera_frame_index = 0\n"
                "    camera_heading_yaw = None\n"
                "    wall_start = time.monotonic()\n"
            ),
        },
        {
            "name": "scripted_walk_command",
            "old": (
                "                if args.case == \"stand_probe\":\n"
                "                    # A standing qualification probe never forwards motion.\n"
                "                    command = (0.0, 0.0, 0.0)\n"
            ),
            "new": SCRIPTED_WALK_COMMAND_BRANCH,
        },
        {
            "name": "scripted_walk_metrics_row",
            "old": "                row.update(_stance_hold_row(stance_hold_runtime, robot))\n",
            "new": (
                "                row.update(_stance_hold_row(stance_hold_runtime, robot))\n"
                "                if scripted_walk is not None:\n"
                "                    row[\"script_segment\"] = script_segment\n"
            ),
        },
        {
            "name": "camera_heading_view",
            "old": (
                "                if step % capture_stride == 0:\n"
                "                    heading = np.array([math.cos(yaw), math.sin(yaw), 0.0])\n"
                "                    side = np.array([-math.sin(yaw), math.cos(yaw), 0.0])\n"
            ),
            "new": (
                "                if step % capture_stride == 0:\n"
                "                    view_yaw, camera_heading_yaw = _camera_view_yaw(\n"
                "                        args.camera_heading_mode, camera_heading_yaw, yaw)\n"
                "                    heading = np.array([math.cos(view_yaw), math.sin(view_yaw), 0.0])\n"
                "                    side = np.array([-math.sin(view_yaw), math.cos(view_yaw), 0.0])\n"
            ),
        },
        {
            "name": "camera_heading_frame_row",
            "old": (
                "                        \"yaw_rad\": float(yaw),\n"
                "                    }) + \"\\n\")\n"
            ),
            "new": (
                "                        \"yaw_rad\": float(yaw),\n"
                "                        \"heading_mode\": args.camera_heading_mode,\n"
                "                        \"view_yaw_rad\": float(view_yaw),\n"
                "                    }) + \"\\n\")\n"
            ),
        },
        {
            "name": "camera_heading_summary",
            "old": (
                "                \"look_down_m\": args.camera_look_down_m,\n"
                "                \"capture_stride_steps\": capture_stride,\n"
            ),
            "new": (
                "                \"look_down_m\": args.camera_look_down_m,\n"
                "                \"heading_mode\": args.camera_heading_mode,\n"
                "                \"heading_yaw_rad\": camera_heading_yaw,\n"
                "                \"capture_stride_steps\": capture_stride,\n"
            ),
        },
        {
            "name": "scripted_walk_summary",
            "old": "            \"stance_hold\": _stance_hold_summary(stance_hold_runtime),\n",
            "new": (
                "            \"stance_hold\": _stance_hold_summary(stance_hold_runtime),\n"
                "            \"scripted_walk\": _scripted_walk_summary(scripted_walk),\n"
            ),
        },
    ]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _apply(result: str, items: List[Dict[str, str]]) -> str:
    for item in items:
        old = item["old"]
        count = result.count(old)
        if count != 1:
            raise RuntimeError(
                "replacement %s matched %d times, expected exactly 1" % (item["name"], count)
            )
        result = result.replace(old, item["new"], 1)
    return result


def apply_patch_text(source: str, include_stance_hold: bool = True,
                     stance_module: Optional[Dict[str, str]] = None,
                     include_scripted_walk: bool = True,
                     command_script_module: Optional[Dict[str, str]] = None) -> str:
    """Apply the anchor groups in order; the scripted-walk group needs the stance-hold group."""
    if include_scripted_walk and not include_stance_hold:
        raise ValueError("the scripted-walk anchors apply on top of the stance-hold anchors")
    result = _apply(source, _replacements())
    if include_stance_hold:
        result = _apply(result, _stance_hold_replacements(stance_module or load_stance_hold_module()))
    if include_scripted_walk:
        result = _apply(result, _scripted_walk_replacements(
            command_script_module or load_command_script_module()))
    return result


def _top_level_definitions(text: str) -> List[str]:
    names = []
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names.extend(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return names


def verify_patch(data: Dict[str, str]) -> Dict[str, object]:
    """Structural checks behind --check; raises when one fails."""
    names = _top_level_definitions(data["patched_text"])
    duplicates = sorted({name for name in names if names.count(name) > 1})
    compile(data["patched_text"], "run_pct_scan_building.py", "exec")
    checks = {
        "external_only_patched_sha256": data["external_only_sha256"],
        "external_only_matches_executed_runner": data["external_only_sha256"] == EXTERNAL_ONLY_PATCHED_SHA256,
        "duplicate_top_level_definitions": duplicates,
        "stance_step_branch_present": STANCE_HOLD_STEP_BRANCH in data["patched_text"],
        "default_stance_hold_off": "choices=STANCE_HOLD_MODES, default=\"off\"" in data["patched_text"],
        "scripted_walk_command_branch_present": SCRIPTED_WALK_COMMAND_BRANCH in data["patched_text"],
        "default_camera_heading_body": "choices=CAMERA_HEADING_MODES, default=\"body\"" in data["patched_text"],
        "default_stance_entry_kd_ramp": "choices=STANCE_ENTRY_KD_MODES, default=\"ramp\"" in data["patched_text"],
        "default_command_script_none": (
            "parser.add_argument(\"--command-script\", type=Path, default=None," in data["patched_text"]
        ),
        "patched_text_compiles": True,
    }
    failed = [
        key for key in ("external_only_matches_executed_runner", "stance_step_branch_present", "default_stance_hold_off",
                        "scripted_walk_command_branch_present", "default_camera_heading_body",
                        "default_stance_entry_kd_ramp", "default_command_script_none")
        if not checks[key]
    ]
    if duplicates:
        failed.append("duplicate_top_level_definitions")
    if failed:
        raise RuntimeError("patch verification failed: %s (%s)" % (failed, checks))
    return checks


def unified_diff(source: str, patched: str) -> str:
    return "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=SOURCE_REL,
            tofile="run_pct_scan_building.py.external_episode",
        )
    )


def load_and_patch(source_path: Path, allow_source_sha: bool = False) -> Dict[str, str]:
    source_text = source_path.read_text(encoding="utf-8")
    source_sha = sha256_text(source_text)
    if source_sha != EXPECTED_SOURCE_SHA256 and not allow_source_sha:
        raise RuntimeError(
            "source SHA-256 mismatch: got %s expected %s"
            % (source_sha, EXPECTED_SOURCE_SHA256)
        )
    stance_module = load_stance_hold_module()
    script_module = load_command_script_module()
    patched_text = apply_patch_text(source_text, stance_module=stance_module,
                                    command_script_module=script_module)
    external_only = apply_patch_text(source_text, include_stance_hold=False, include_scripted_walk=False)
    return {
        "source_text": source_text,
        "patched_text": patched_text,
        "source_sha256": source_sha,
        "patched_sha256": sha256_text(patched_text),
        "patch_text": unified_diff(source_text, patched_text),
        "external_only_sha256": sha256_text(external_only),
        "stance_hold_module": stance_module,
        "command_script_module": script_module,
    }


def write_outputs(args: argparse.Namespace) -> Dict[str, str]:
    source_path = Path(args.source or (REPO_ROOT / SOURCE_REL)).resolve()
    data = load_and_patch(source_path, allow_source_sha=args.allow_source_sha)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(data["patched_text"], encoding="utf-8")
    patch_path = Path(args.patch)
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(data["patch_text"], encoding="utf-8")
    hash_path = Path(args.hashes)
    hash_payload = {
        "schema_version": 1,
        "source_path": str(source_path),
        "source_rel": SOURCE_REL,
        "expected_source_sha256": EXPECTED_SOURCE_SHA256,
        "observed_source_sha256": data["source_sha256"],
        "patched_sha256": data["patched_sha256"],
        "patch_path": str(patch_path),
        "patch_sha256": sha256_file(patch_path),
        "materializer_sha256": sha256_file(Path(__file__)),
        "anchor_groups": {
            "external_episode": [item["name"] for item in _replacements()],
            "stance_hold": [item["name"] for item in _stance_hold_replacements(data["stance_hold_module"])],
            "scripted_walk": [item["name"] for item in _scripted_walk_replacements(data["command_script_module"])],
        },
        "external_only_patched_sha256": data["external_only_sha256"],
        "external_only_expected_sha256": EXTERNAL_ONLY_PATCHED_SHA256,
        "stance_hold_module": {
            "path": STANCE_HOLD_MODULE_REL,
            "sha256": data["stance_hold_module"]["sha256"],
            "body_sha256": data["stance_hold_module"]["body_sha256"],
        },
        "command_script_module": {
            "path": COMMAND_SCRIPT_MODULE_REL,
            "sha256": data["command_script_module"]["sha256"],
            "body_sha256": data["command_script_module"]["body_sha256"],
        },
        "stance_hold_default": "off",
        "stance_entry_kd_default": "ramp",
        "camera_heading_mode_default": "body",
        "command_script_default": None,
        "claim_boundary": (
            "Patch materialization only. Passing tests do not claim Isaac, ROS, "
            "PCT, SCAN, V12 policy, stance hold, scripted walk, or simulator success."
        ),
    }
    if args.check:
        hash_payload["verification"] = verify_patch(data)
    hash_path.write_text(json.dumps(hash_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hash_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--patch", type=Path, default=REPO_ROOT / DEFAULT_PATCH_REL)
    parser.add_argument("--hashes", type=Path, default=REPO_ROOT / DEFAULT_HASHES_REL)
    parser.add_argument("--allow-source-sha", action="store_true", default=False)
    parser.add_argument("--check", action="store_true", default=False)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = write_outputs(args)
    if args.check:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
