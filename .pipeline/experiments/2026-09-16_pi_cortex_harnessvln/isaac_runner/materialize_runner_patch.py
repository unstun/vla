#!/usr/bin/env python3
"""Materialize the P2B external-episode Building runner patch.

The frozen reference runner is not edited in place. This helper verifies the
known source hash, applies exact anchor replacements to a copy, and writes a
unified diff plus source-hash record for review.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[4]
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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_patch_text(source: str) -> str:
    result = source
    for item in _replacements():
        old = item["old"]
        count = result.count(old)
        if count != 1:
            raise RuntimeError(
                "replacement %s matched %d times, expected exactly 1" % (item["name"], count)
            )
        result = result.replace(old, item["new"], 1)
    return result


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
    patched_text = apply_patch_text(source_text)
    return {
        "source_text": source_text,
        "patched_text": patched_text,
        "source_sha256": source_sha,
        "patched_sha256": sha256_text(patched_text),
        "patch_text": unified_diff(source_text, patched_text),
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
        "claim_boundary": (
            "Patch materialization only. Passing tests do not claim Isaac, ROS, "
            "PCT, SCAN, V12 policy, or simulator success."
        ),
    }
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
