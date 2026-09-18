#!/usr/bin/env python3
"""AC3, AC5, AC7 and AC8 metrics for Isaac runner stance-hold runs.

Reads only returned run files (`metrics.jsonl`, `summary.json`, optional
`stance_hold_setup.json` and `scripted_walk_setup.json`) and the frozen
`stance_hold_thresholds.json`.

    analyze_stance_hold.py stand --on RUN --off RUN --output OUT.json
    analyze_stance_hold.py run RUN [RUN ...] --output OUT.json
    analyze_stance_hold.py walk --off RUN --on RUN [--on RUN ...] --output OUT.json

RUN is a run package (with returned_artifacts/runner_output) or a
runner_output directory. `stand` gives the AC3 verdict for the hold-on
stand_probe run, the hold-off baseline over the same simulation window, and
AC5 and AC7 for both. `run` gives AC5, AC7 and a stance summary for any run,
such as a two-goal episode. AC7 (entry smoothness, PRD D4) applies to hold-on
runs only and is "not_applicable" for the others. Rows without stance fields
are reported as "hold off / no stance fields".

AC7 window (PRD D7, a post-result amendment made after the C2 result): when
the thresholds set `ac7_entry.end_at_restart`, each entry window also ends at
the restart row (the first row after the entry whose stance_mode is neither
STAND_TRANSITION nor FIXED_STAND), which is excluded. The AC7 `verdict` uses
that rule; `as_frozen_before_results` gives the verdict with the full window as
frozen before the results. In each entry window the top-level maxima and checks
are the full window, as before, and `amended` holds the truncated window. AC8 b
and the D5 selection use the full window.

`walk` (PRD D5) takes scripted_walk runs: one hold-off baseline and one or
more hold-on entry damping variants. It gives AC8 (a-d) for each hold-on run,
AC5 and AC7 for every run, per-stop and per-start numbers for every run (the
baseline without thresholds), and the D5 selection. Its exit code is 0 only
when the selection rule picks a variant.

Claim boundary: simulation-only metrics of recorded runs; not a real-robot or
deployment result, and not a substitute for review_two_goal.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable, List, Optional

HERE = Path(__file__).resolve().parent
DEFAULT_THRESHOLDS = HERE / "stance_hold_thresholds.json"
# SHA-256 of stance_hold_thresholds.json with the PRD D7 AC7 amendment (the entry
# window also ends at a restart). D7 is a post-result change: it was made after
# the C2 two-goal result was known. A different file is refused unless
# --allow-unfrozen-thresholds.
FROZEN_THRESHOLDS_SHA256 = "34c15fe6fabd6bf90f34456371e363fc3e4ed813a2570a96a80760f6c5a8e049"
# Superseded frozen files, kept byte-for-byte for the reports that used them.
# They are refused like any other file.
SUPERSEDED_THRESHOLDS = {
    "0be59927aa18ad97cc6dfc01a3179867ce84e71e712286ee971a485a5238a29d":
        "stance_hold_thresholds_history/stance_hold_thresholds_0be59927.json (AC7 before the PRD D7 "
        "amendment, full 1.0 s entry window; used by the D6 walk report walk_d6_20260917T181650Z and the C2 "
        "series report series_d6_20260918)",
    "fb8f9204c18e0b400ae2b7a2abc22bb052526538ff9713689759f15bff897c66":
        "stance_hold_thresholds_history/stance_hold_thresholds_fb8f9204.json (AC3/AC5 only, used by C1 "
        "stand_20260917T125239Z)",
    "12373448a8aee02534b529c69189bc5155bbe13cb0d17b632d260b075e075da5":
        "stance_hold_thresholds_history/stance_hold_thresholds_12373448.json (AC3/AC5/AC7, used by the C1b "
        "report stand_20260917T132323Z_hold_auto_ramp)",
    "683a8ca6d9d26fe4c45af22fc449c1c05525fde9eb0fb3dc4125c4f2831b43b8":
        "stance_hold_thresholds_history/stance_hold_thresholds_683a8ca6.json (AC3/AC5/AC7/AC8 before the "
        "PRD D6 wording, used by the C1d walk report walk_ab_20260917T145650Z)",
}
SCRIPTED_WALK_CASE = "scripted_walk"
NO_STANCE = "hold off / no stance fields"
# Runner statuses of a stand that ran to its end: the worker's finish request was
# honoured, or the full --duration-seconds elapsed before the finish dwell ended.
COMPLETED_STAND_STATUSES = ("EXTERNAL_EPISODE_FINISHED", "DURATION_REACHED")
CLAIM_BOUNDARY = (
    "Simulation-only metrics of recorded Isaac runs (V12 in Isaac, one flat Building route). "
    "Not a real-robot or deployment result."
)


class AnalysisError(RuntimeError):
    """A required input is missing or malformed."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_thresholds(path: Path, allow_unfrozen: bool = False) -> dict:
    path = Path(path)
    digest = sha256_file(path)
    frozen = digest == FROZEN_THRESHOLDS_SHA256
    if not frozen and not allow_unfrozen:
        superseded = SUPERSEDED_THRESHOLDS.get(digest)
        raise AnalysisError(
            "thresholds %s have SHA-256 %s, not the frozen %s%s" % (
                path, digest, FROZEN_THRESHOLDS_SHA256,
                "" if superseded is None else "; it is the superseded " + superseded)
        )
    values = json.loads(path.read_text(encoding="utf-8"))
    return {"path": str(path), "sha256": digest, "frozen": frozen, "values": values}


def resolve_output_dir(run: Path) -> Path:
    run = Path(run)
    for candidate in (run, run / "returned_artifacts/runner_output", run / "artifacts/runner_output"):
        if (candidate / "metrics.jsonl").is_file():
            return candidate
    raise AnalysisError("no metrics.jsonl under %s" % run)


def load_rows(path: Path) -> List[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AnalysisError("metrics.jsonl line %d is not JSON: %s" % (number, exc))
    if not rows:
        raise AnalysisError("metrics.jsonl is empty: %s" % path)
    for key in ("step", "sim_time_s", "base_xyz", "base_rpy_rad", "horizontal_speed_mps", "yaw_rate_radps",
                "admitted_command", "foot_force_norms"):
        if any(key not in row for row in rows):
            raise AnalysisError("metrics.jsonl rows lack %s: %s" % (key, path))
    return rows


def load_run(run: Path) -> dict:
    out = resolve_output_dir(run)
    metrics = out / "metrics.jsonl"
    rows = load_rows(metrics)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    setup_path = out / "stance_hold_setup.json"
    setup = json.loads(setup_path.read_text(encoding="utf-8")) if setup_path.is_file() else None
    script_path = out / "scripted_walk_setup.json"
    script_setup = json.loads(script_path.read_text(encoding="utf-8")) if script_path.is_file() else None
    inputs = {"metrics": {"path": str(metrics), "sha256": sha256_file(metrics)}}
    for name, path in (("summary", summary_path), ("stance_hold_setup", setup_path),
                       ("scripted_walk_setup", script_path)):
        if path.is_file():
            inputs[name] = {"path": str(path), "sha256": sha256_file(path)}
    return {"run": str(run), "output_dir": str(out), "rows": rows, "summary": summary, "setup": setup,
            "script_setup": script_setup, "inputs": inputs}


def has_stance(rows: List[dict]) -> bool:
    return any("stance_mode" in row for row in rows)


def stance_fields(rows: List[dict]):
    """Sorted stance modes present, or the no-stance label for legacy rows."""
    return sorted({str(row["stance_mode"]) for row in rows if "stance_mode" in row}) or NO_STANCE


def modes(rows: List[dict]) -> List[str]:
    return [str(row.get("stance_mode", "")) for row in rows]


def entry_indices(rows: List[dict]) -> List[int]:
    """Row index of the first STAND_TRANSITION row of each hold entry."""
    labels = modes(rows)
    return [index for index in range(len(rows))
            if labels[index] == "STAND_TRANSITION" and (index == 0 or labels[index - 1] != "STAND_TRANSITION")]


def hold_on(run: dict) -> bool:
    """A run with the stance hold in auto mode, by summary or by row."""
    stance_summary = (run["summary"] or {}).get("stance_hold") or {}
    return stance_summary.get("mode") == "auto" or any(row.get("stance_hold") == "auto" for row in run["rows"])


def step_dt(rows: List[dict]) -> float:
    if len(rows) < 2:
        return 0.02
    gaps = sorted(b["sim_time_s"] - a["sim_time_s"] for a, b in zip(rows, rows[1:]))
    return float(gaps[len(gaps) // 2])


def zero_command(row: dict, limit: float) -> bool:
    return max(abs(float(v)) for v in row["admitted_command"]) <= limit


def count_nonfinite(value) -> int:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return 0
    if isinstance(value, (int, float)):
        return 0 if math.isfinite(float(value)) else 1
    if isinstance(value, dict):
        return sum(count_nonfinite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(count_nonfinite(item) for item in value)
    return 0


def segments(rows: List[dict]) -> List[dict]:
    """Contiguous stance modes with their row ranges and simulation span."""
    labels = modes(rows)
    result = []
    start = 0
    dt = step_dt(rows)
    for index in range(1, len(rows) + 1):
        if index == len(rows) or labels[index] != labels[start]:
            result.append({
                "mode": labels[start],
                "first_row": start,
                "last_row": index - 1,
                "start_s": rows[start]["sim_time_s"] - dt,
                "end_s": rows[index - 1]["sim_time_s"],
                "reason_at_start": rows[start].get("stance_reason"),
            })
            start = index
    return result


def check(value, limit, ok: Optional[bool]) -> dict:
    return {"value": value, "limit": limit, "pass": ok}


def window_metrics(rows: List[dict], clip_field: str = "torque_clip_joint_count") -> dict:
    """Stillness metrics over a list of rows."""
    if not rows:
        return {"rows": 0}
    x0, y0 = rows[0]["base_xyz"][:2]
    clip_known = all(clip_field in row for row in rows)
    return {
        "rows": len(rows),
        "start_s": rows[0]["sim_time_s"],
        "end_s": rows[-1]["sim_time_s"],
        "min_foot_force_n": min(min(float(v) for v in row["foot_force_norms"]) for row in rows),
        "planar_drift_m": max(math.hypot(row["base_xyz"][0] - x0, row["base_xyz"][1] - y0) for row in rows),
        "max_horizontal_speed_mps": max(float(row["horizontal_speed_mps"]) for row in rows),
        "max_abs_yaw_rate_radps": max(abs(float(row["yaw_rate_radps"])) for row in rows),
        "max_abs_roll_deg": max(abs(math.degrees(float(row["base_rpy_rad"][0]))) for row in rows),
        "max_abs_pitch_deg": max(abs(math.degrees(float(row["base_rpy_rad"][1]))) for row in rows),
        "torque_clip_steps": sum(1 for row in rows if row.get(clip_field, 0) > 0) if clip_known else None,
        "max_applied_torque_ratio": (
            max(float(row["applied_torque_max_ratio"]) for row in rows)
            if all("applied_torque_max_ratio" in row for row in rows) else None
        ),
        "nonfinite_values": sum(count_nonfinite(row) for row in rows),
    }


def time_to_fixed(rows: List[dict], zero_limit: float) -> Optional[dict]:
    labels = modes(rows)
    if "FIXED_STAND" not in labels:
        return None
    first = labels.index("FIXED_STAND")
    start = first
    while start > 0 and zero_command(rows[start - 1], zero_limit):
        start -= 1
    zero_start = rows[start - 1]["sim_time_s"] if start > 0 else 0.0
    return {
        "zero_command_start_s": zero_start,
        "first_fixed_stand_s": rows[first]["sim_time_s"],
        "seconds": rows[first]["sim_time_s"] - zero_start,
        "rule": "zero-command interval starts at the sim time before its first row (0 for row 0)",
    }


def ac3(on: dict, off: dict, thresholds: dict) -> dict:
    limits = thresholds["values"]["ac3_stand"]
    zero_limit = float(thresholds["values"]["definitions"]["zero_command_max_abs"])
    rows = on["rows"]
    problems = []
    summary = on["summary"] or {}
    if on["summary"] is None:
        problems.append("hold-on run has no summary.json")
    elif summary.get("status") not in COMPLETED_STAND_STATUSES:
        # A stand that ended early (NONFINITE, TERMINATED, WALL_TIMEOUT, ...) must not
        # pass on the FIXED_STAND rows it recorded before stopping.
        problems.append("hold-on run status is %s, not one of %s"
                        % (summary.get("status"), list(COMPLETED_STAND_STATUSES)))
    if (summary.get("stance_hold") or {}).get("failure") is not None:
        problems.append("hold-on run recorded a stance hold failure: %s"
                        % (summary.get("stance_hold") or {}).get("failure"))
    if summary.get("case") not in (None, "stand_probe"):
        problems.append("hold-on run case is %s, not stand_probe" % summary.get("case"))
    if not has_stance(rows):
        problems.append("hold-on run has no stance fields")
    if (summary.get("stance_hold") or {}).get("mode") not in (None, "auto"):
        problems.append("hold-on run summary stance_hold mode is %s" % (summary.get("stance_hold") or {}).get("mode"))
    if any(row.get("stance_hold") not in (None, "auto") for row in rows):
        problems.append("hold-on run rows are not stance_hold auto")
    fixed = [row for row in rows if row.get("stance_mode") == "FIXED_STAND"]
    metrics = window_metrics(fixed)
    ttf = time_to_fixed(rows, zero_limit)
    checks = {}
    if fixed:
        checks = {
            "four_feet_above_min_force": check(metrics["min_foot_force_n"], limits["min_foot_force_exclusive_n"],
                                               metrics["min_foot_force_n"] > limits["min_foot_force_exclusive_n"]),
            "planar_drift": check(metrics["planar_drift_m"], limits["max_planar_drift_m"],
                                  metrics["planar_drift_m"] <= limits["max_planar_drift_m"]),
            "horizontal_speed": check(metrics["max_horizontal_speed_mps"], limits["max_horizontal_speed_mps"],
                                      metrics["max_horizontal_speed_mps"] <= limits["max_horizontal_speed_mps"]),
            "yaw_rate": check(metrics["max_abs_yaw_rate_radps"], limits["max_abs_yaw_rate_radps"],
                              metrics["max_abs_yaw_rate_radps"] <= limits["max_abs_yaw_rate_radps"]),
            "roll": check(metrics["max_abs_roll_deg"], limits["max_abs_roll_deg"],
                          metrics["max_abs_roll_deg"] <= limits["max_abs_roll_deg"]),
            "pitch": check(metrics["max_abs_pitch_deg"], limits["max_abs_pitch_deg"],
                           metrics["max_abs_pitch_deg"] <= limits["max_abs_pitch_deg"]),
            "torque_clip_steps": check(
                metrics["torque_clip_steps"], limits["max_torque_clip_steps"],
                None if metrics["torque_clip_steps"] is None
                else metrics["torque_clip_steps"] <= limits["max_torque_clip_steps"]),
            "nonfinite_values": check(metrics["nonfinite_values"], limits["max_nonfinite_values"],
                                      metrics["nonfinite_values"] <= limits["max_nonfinite_values"]),
            "time_to_fixed_stand": check(ttf["seconds"], limits["max_time_to_fixed_stand_s"],
                                         ttf["seconds"] <= limits["max_time_to_fixed_stand_s"]),
        }
    else:
        problems.append("FIXED_STAND was never reached")
    for name, item in checks.items():
        if item["pass"] is None:
            problems.append("%s is not evaluable (field missing)" % name)
        elif not item["pass"]:
            problems.append("%s %s exceeds %s" % (name, item["value"], item["limit"]))
    fixed_segments = [s for s in segments(rows) if s["mode"] == "FIXED_STAND"]
    baseline_rows = []
    if fixed:
        t0, t1 = fixed[0]["sim_time_s"], fixed[-1]["sim_time_s"]
        baseline_rows = [row for row in off["rows"] if t0 - 1e-9 <= row["sim_time_s"] <= t1 + 1e-9]
    return {
        "verdict": "pass" if not problems else "fail",
        "problems": problems,
        "checks": checks,
        "fixed_stand": dict(metrics, seconds=len(fixed) * step_dt(rows), segments=len(fixed_segments),
                            exits=[s["reason_at_start"] for s in segments(rows)
                                   if s["first_row"] > 0 and modes(rows)[s["first_row"] - 1] == "FIXED_STAND"]),
        "time_to_fixed_stand": ttf,
        "run_status": summary.get("status"),
        "baseline_off": {
            "note": "no thresholds; same simulation window as the hold-on FIXED_STAND rows",
            "run_status": (off["summary"] or {}).get("status"),
            "stance_fields": stance_fields(off["rows"]),
            "window": window_metrics(baseline_rows),
            "whole_run": window_metrics(off["rows"]),
        },
    }


def ac5(run: dict, thresholds: dict) -> dict:
    limits = thresholds["values"]["ac5_transitions"]
    rows = run["rows"]
    summary = run["summary"] or {}
    nonfoot_rows = max(max(float(row.get("nonfoot_force_max_n", 0.0)),
                           float(row.get("nonfoot_force_substep_max_n", 0.0))) for row in rows)
    nonfoot_summary = summary.get("max_nonfoot_force_n")
    nonfoot = max(nonfoot_rows, float(nonfoot_summary or 0.0))
    events = len(summary.get("nonfoot_contact_events_over_threshold") or [])
    problems = []
    if nonfoot >= limits["max_nonfoot_force_exclusive_n"] or events:
        problems.append("non-foot force %.3f N (events %d) reaches the %.1f N guard"
                        % (nonfoot, events, limits["max_nonfoot_force_exclusive_n"]))
    entries = entry_indices(rows)
    entry_rows = sorted({i for index in entries for i in (index, index + 1) if i < len(rows)})
    rejoin_segments = [s for s in segments(rows) if s["mode"] == "REJOIN"]
    rejoin_rows = sorted({i for s in rejoin_segments for i in range(s["first_row"], s["last_row"] + 3) if i < len(rows)})
    rejoin_only = [rows[i] for s in rejoin_segments for i in range(s["first_row"], s["last_row"] + 1)]
    window = sorted(set(entry_rows) | set(rejoin_rows))
    clip_known = all("torque_clip_joint_count" in rows[i] for i in window)
    clip_steps = [rows[i]["step"] for i in window if rows[i].get("torque_clip_joint_count", 0) > 0]
    estimated = [rows[i]["step"] for i in window
                 if float(rows[i].get("delayed_target_torque_max_ratio_estimate", 0.0)) >= 1.0]
    rejoin_roll = max((abs(math.degrees(float(r["base_rpy_rad"][0]))) for r in rejoin_only), default=None)
    rejoin_pitch = max((abs(math.degrees(float(r["base_rpy_rad"][1]))) for r in rejoin_only), default=None)
    if rejoin_roll is not None and rejoin_roll > limits["max_abs_roll_deg_during_rejoin"]:
        problems.append("roll %.3f deg during REJOIN exceeds %.1f" % (rejoin_roll, limits["max_abs_roll_deg_during_rejoin"]))
    if rejoin_pitch is not None and rejoin_pitch > limits["max_abs_pitch_deg_during_rejoin"]:
        problems.append("pitch %.3f deg during REJOIN exceeds %.1f" % (rejoin_pitch, limits["max_abs_pitch_deg_during_rejoin"]))
    if window and not clip_known:
        problems.append("torque clip fields are missing at entry or rejoin steps")
    elif len(clip_steps) > limits["max_torque_clip_steps_at_entry_or_rejoin"]:
        problems.append("torque clip at entry or rejoin steps %s" % clip_steps)
    stance_summary = summary.get("stance_hold") or {}
    fsm = stance_summary.get("fsm") or {}
    lags = None
    if run["setup"] and run["setup"].get("inspection"):
        lags = {name: item.get("position_delay_time_lags")
                for name, item in run["setup"]["inspection"].get("actuators", {}).items()}
    return {
        "verdict": "pass" if not problems else "fail",
        "problems": problems,
        "stance_fields": stance_fields(rows),
        "stance_hold_mode": stance_summary.get("mode") or (rows[0].get("stance_hold") if has_stance(rows) else None),
        "summary_status": summary.get("status"),
        "stance_failure": stance_summary.get("failure"),
        "max_nonfoot_force_n": nonfoot,
        "nonfoot_events_over_threshold": events,
        "entries": [{"step": rows[i]["step"], "sim_time_s": rows[i]["sim_time_s"]} for i in entries],
        "rejoins": [{"first_step": rows[s["first_row"]]["step"], "start_s": s["start_s"], "end_s": s["end_s"],
                     "rows": s["last_row"] - s["first_row"] + 1} for s in rejoin_segments],
        "entry_or_rejoin_steps": [rows[i]["step"] for i in window],
        "torque_clip_steps_at_entry_or_rejoin": clip_steps if clip_known else None,
        "delayed_target_estimated_clip_steps": estimated,
        "delayed_target_note": (
            "rows where Kp_next * (previous target - q) - Kd_next * qd reaches the effort limit; a model estimate of "
            "the substeps that still use the delayed previous target, reported but not an acceptance check"
        ),
        "max_abs_roll_deg_during_rejoin": rejoin_roll,
        "max_abs_pitch_deg_during_rejoin": rejoin_pitch,
        "segments": [{k: s[k] for k in ("mode", "start_s", "end_s", "reason_at_start")} for s in segments(rows)]
        if has_stance(rows) else [],
        "mode_time_s": fsm.get("mode_time_s"),
        "fsm_counters": fsm.get("counters"),
        "position_delay_time_lags": lags,
        "gain_writes": stance_summary.get("gain_writes"),
    }


# Stance modes that keep an AC7 entry window open under the PRD D7 amendment.
HOLD_MODES = ("STAND_TRANSITION", "FIXED_STAND")
AC7_FULL_WINDOW_RULE = ("rows with sim_time_s in [t0, t0 + window_s] (window_tolerance_s at the end), "
                        "t0 = entry row sim_time_s")
AC7_AMENDED_WINDOW_RULE = (
    "PRD D7 post-result amendment (Dr Sun, 2026-09-18, made after the C2 result was known): "
    + AC7_FULL_WINDOW_RULE + ", ending before the restart row, the first row after the entry row whose "
    "stance_mode is neither STAND_TRANSITION nor FIXED_STAND; the restart row and every later row are excluded. "
    "Per entry window, the top-level maxima and checks are the full window and 'amended' is the truncated window; "
    "as_frozen_before_results gives the verdict with the full window"
)


def entry_window_stats(part: List[dict], yaw_limit: float, vertical_limit: float):
    """|yaw rate| and |vertical speed| maxima and checks over the rows of one entry window.

    Returns the statistics and the steps whose base_linear_velocity_world is missing.
    """
    yaw = [abs(float(row["yaw_rate_radps"])) for row in part]
    velocities = [row.get("base_linear_velocity_world") for row in part]
    missing = [row["step"] for row, value in zip(part, velocities)
               if not isinstance(value, (list, tuple)) or len(value) < 3]
    vertical = None if missing else [abs(float(value[2])) for value in velocities]
    max_yaw = max(yaw)
    max_vertical = None if vertical is None else max(vertical)
    yaw_pass = max_yaw <= yaw_limit
    vertical_pass = None if max_vertical is None else max_vertical <= vertical_limit
    stats = {
        "end_s": float(part[-1]["sim_time_s"]),
        "rows": len(part),
        "modes": sorted({str(row.get("stance_mode")) for row in part}),
        "max_abs_yaw_rate_radps": max_yaw,
        "max_abs_yaw_rate_step": part[yaw.index(max_yaw)]["step"],
        "max_abs_vertical_speed_mps": max_vertical,
        "max_abs_vertical_speed_step": None if vertical is None else part[vertical.index(max_vertical)]["step"],
        "yaw_rate": check(max_yaw, yaw_limit, yaw_pass),
        "vertical_speed": check(max_vertical, vertical_limit, vertical_pass),
    }
    return stats, missing


def entry_window_problems(entry_step, stats: dict, missing: List, yaw_limit: float, vertical_limit: float,
                          suffix: str = "") -> List[str]:
    problems = []
    if missing:
        problems.append("entry at step %s: vertical speed is not evaluable (base_linear_velocity_world "
                        "missing at steps %s)%s" % (entry_step, missing[:10], suffix))
    if not stats["yaw_rate"]["pass"]:
        problems.append("entry at step %s: |yaw rate| %.4f rad/s at step %s exceeds %.2f%s"
                        % (entry_step, stats["max_abs_yaw_rate_radps"], stats["max_abs_yaw_rate_step"], yaw_limit,
                           suffix))
    if stats["vertical_speed"]["pass"] is False:
        problems.append("entry at step %s: |vertical speed| %.4f m/s at step %s exceeds %.2f%s"
                        % (entry_step, stats["max_abs_vertical_speed_mps"], stats["max_abs_vertical_speed_step"],
                           vertical_limit, suffix))
    return problems


def ac7(run: dict, thresholds: dict) -> dict:
    """Entry smoothness (PRD D4): yaw rate and vertical body speed after each hold entry.

    With ac7_entry.end_at_restart (PRD D7, post-result) the verdict uses windows that end at the restart;
    as_frozen_before_results keeps the full-window verdict, which AC8 b uses.
    """
    limits = thresholds["values"]["ac7_entry"]
    rows = run["rows"]
    window_s = float(limits["window_s"])
    tolerance_s = float(limits["window_tolerance_s"])
    yaw_limit = float(limits["max_abs_yaw_rate_radps"])
    vertical_limit = float(limits["max_abs_vertical_speed_mps"])
    end_at_restart = bool(limits.get("end_at_restart", False))
    base = {
        "limits": {"window_s": window_s, "window_tolerance_s": tolerance_s, "max_abs_yaw_rate_radps": yaw_limit,
                   "max_abs_vertical_speed_mps": vertical_limit, "end_at_restart": end_at_restart},
        "stance_fields": stance_fields(rows),
        "verdict_rule": "amended_end_at_restart" if end_at_restart else "full_window",
        "window_rule": AC7_AMENDED_WINDOW_RULE if end_at_restart else AC7_FULL_WINDOW_RULE,
        "post_result_amendment": limits.get("amendment") if end_at_restart else None,
    }
    as_frozen_rule = AC7_FULL_WINDOW_RULE + "; the AC7 rule as frozen before the results; AC8 b uses this window"
    if not hold_on(run):
        base.update({"verdict": "not_applicable", "problems": [], "entry_windows": [],
                     "note": "not a stance_hold auto run",
                     "as_frozen_before_results": {"verdict": "not_applicable", "problems": [],
                                                  "window_rule": as_frozen_rule}})
        return base
    full_problems = []
    amended_problems = []
    windows = []
    for index in entry_indices(rows):
        t0 = float(rows[index]["sim_time_s"])
        part = []
        for row in rows[index:]:
            if float(row["sim_time_s"]) > t0 + window_s + tolerance_s:
                break
            part.append(row)
        entry_step = rows[index]["step"]
        stats, missing = entry_window_stats(part, yaw_limit, vertical_limit)
        window_complete = float(rows[-1]["sim_time_s"]) >= t0 + window_s - tolerance_s
        # Top-level fields: the full window, exactly as before the D7 amendment.
        window = dict(stats, entry_step=entry_step, start_s=t0, window_complete=window_complete)
        full_problems.extend(entry_window_problems(entry_step, stats, missing, yaw_limit, vertical_limit))
        if end_at_restart:
            restart = next((offset for offset in range(1, len(part))
                            if str(part[offset].get("stance_mode")) not in HOLD_MODES), None)
            kept = part if restart is None else part[:restart]
            amended, amended_missing = entry_window_stats(kept, yaw_limit, vertical_limit)
            amended.update({
                "window_end": "window_s" if restart is None else "restart",
                "restart_step": None if restart is None else part[restart]["step"],
                "restart_s": None if restart is None else float(part[restart]["sim_time_s"]),
                "restart_mode": None if restart is None else str(part[restart].get("stance_mode")),
                "window_complete": window_complete if restart is None else True,
            })
            window["amended"] = amended
            suffix = "" if restart is None else " (window ends before the restart at step %s)" % amended["restart_step"]
            amended_problems.extend(entry_window_problems(entry_step, amended, amended_missing, yaw_limit,
                                                          vertical_limit, suffix))
        windows.append(window)
    as_frozen = {"verdict": "pass" if not full_problems else "fail", "problems": full_problems,
                 "window_rule": as_frozen_rule}
    problems = amended_problems if end_at_restart else full_problems
    base.update({
        "verdict": "pass" if not problems else "fail",
        "problems": problems,
        "entry_windows": windows,
        "note": None if windows else "hold-on run without an entry; no window to check",
        "windows_ended_at_restart": (sum(1 for w in windows if w["amended"]["window_end"] == "restart")
                                     if end_at_restart else None),
        "as_frozen_before_results": as_frozen,
    })
    return base


def ac7_ok(result: dict) -> bool:
    return result["verdict"] in ("pass", "not_applicable")


def zero_command_intervals(run: dict, thresholds: dict) -> List[dict]:
    """Each zero-command interval with its hold timing (AC4 report helper)."""
    rows = run["rows"]
    zero_limit = float(thresholds["values"]["definitions"]["zero_command_max_abs"])
    result = []
    index = 0
    while index < len(rows):
        if not zero_command(rows[index], zero_limit):
            index += 1
            continue
        start = index
        while index < len(rows) and zero_command(rows[index], zero_limit):
            index += 1
        part = rows[start:index]
        labels = modes(part)
        begin = rows[start - 1]["sim_time_s"] if start > 0 else 0.0
        fixed = [row for row in part if row.get("stance_mode") == "FIXED_STAND"]
        result.append({
            "start_s": begin,
            "end_s": part[-1]["sim_time_s"],
            "first_transition_s": next((r["sim_time_s"] for r, m in zip(part, labels) if m == "STAND_TRANSITION"), None),
            "first_fixed_stand_s": fixed[0]["sim_time_s"] if fixed else None,
            "time_to_fixed_stand_s": fixed[0]["sim_time_s"] - begin if fixed else None,
            "fixed_stand_max_abs_yaw_rate_radps": (
                max(abs(float(r["yaw_rate_radps"])) for r in fixed) if fixed else None),
            "max_abs_yaw_rate_radps": max(abs(float(r["yaw_rate_radps"])) for r in part),
        })
    return result


def write_output(path: Optional[Path], payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    path = Path(path)
    if path.exists():
        raise AnalysisError("refusing to overwrite " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def base_payload(thresholds: dict) -> dict:
    return {
        "schema_version": 1,
        "tool": {"path": str(Path(__file__).resolve()), "sha256": sha256_file(Path(__file__).resolve())},
        "thresholds": {k: thresholds[k] for k in ("path", "sha256", "frozen")},
        "claim_boundary": CLAIM_BOUNDARY,
    }


def analyze_stand(on_path: Path, off_path: Path, thresholds: dict) -> dict:
    on, off = load_run(on_path), load_run(off_path)
    payload = base_payload(thresholds)
    payload.update({
        "kind": "stand",
        "inputs": {"on": on["inputs"], "off": off["inputs"]},
        "ac3": ac3(on, off, thresholds),
        "ac5": {"on": ac5(on, thresholds), "off": ac5(off, thresholds)},
        "ac7": {"on": ac7(on, thresholds), "off": ac7(off, thresholds)},
    })
    return json_safe(payload)


def analyze_runs(paths: Iterable[Path], thresholds: dict) -> dict:
    payload = base_payload(thresholds)
    payload["kind"] = "runs"
    payload["runs"] = []
    for path in paths:
        run = load_run(path)
        payload["runs"].append({
            "run": run["run"],
            "inputs": run["inputs"],
            "ac5": ac5(run, thresholds),
            "ac7": ac7(run, thresholds),
            "zero_command_intervals": zero_command_intervals(run, thresholds),
        })
    return json_safe(payload)


# ---- AC8 scripted walk (PRD D5) ------------------------------------------------
def xy_distance(a: dict, b: dict) -> float:
    return math.hypot(float(b["base_xyz"][0]) - float(a["base_xyz"][0]),
                      float(b["base_xyz"][1]) - float(a["base_xyz"][1]))


def path_length(rows: List[dict]) -> float:
    return sum(xy_distance(a, b) for a, b in zip(rows, rows[1:]))


def entry_kd_variant(run: dict) -> Optional[str]:
    stance = (run["summary"] or {}).get("stance_hold") or {}
    for value in (stance.get("entry_kd"), (stance.get("fsm") or {}).get("entry_kd"),
                  (run["setup"] or {}).get("entry_kd")):
        if value is not None:
            return str(value)
    return None


def run_script_sha256(run: dict) -> Optional[str]:
    for record in (run["script_setup"], (run["summary"] or {}).get("scripted_walk")):
        sha = ((record or {}).get("command_script") or {}).get("sha256")
        if sha is not None:
            return str(sha)
    return None


def command_phases(rows: List[dict], zero_limit: float) -> List[dict]:
    """Contiguous zero / non-zero admitted-command row runs with their command step time."""
    result = []
    start = 0
    for index in range(1, len(rows) + 1):
        if index == len(rows) or zero_command(rows[index], zero_limit) != zero_command(rows[start], zero_limit):
            result.append({
                "zero": zero_command(rows[start], zero_limit),
                "first_row": start,
                "last_row": index - 1,
                "command_step_s": float(rows[start - 1]["sim_time_s"]) if start > 0 else 0.0,
                "command": [float(v) for v in rows[start]["admitted_command"]],
                "distinct_commands": sorted({tuple(float(v) for v in row["admitted_command"])
                                             for row in rows[start:index]}),
                "script_segments": sorted({row["script_segment"] for row in rows[start:index]
                                           if row.get("script_segment") is not None}),
            })
            start = index
    return result


def match_phases(run: dict, thresholds: dict) -> dict:
    """Map recorded command phases to the frozen script phases; list every mismatch."""
    limits = thresholds["values"]["ac8_walk"]
    zero_limit = float(thresholds["values"]["definitions"]["zero_command_max_abs"])
    rows = run["rows"]
    expected = limits["phases"]
    tolerance = float(limits["command_step_tolerance_s"])
    window_tolerance = float(limits["window_tolerance_s"])
    finish_s = float(limits["finish_request_s"])
    found = command_phases(rows, zero_limit)
    problems = []
    pattern = [item["zero"] for item in found]
    wanted = [max(abs(float(v)) for v in item["command"]) <= zero_limit for item in expected]
    if pattern != wanted:
        problems.append("recorded command phases %s (zero=True) do not match the script phases %s"
                        % (pattern, wanted))
    matched = []
    for index, (item, phase) in enumerate(zip(found, expected)):
        record = dict(item, index=index, label=phase["label"], nominal_start_s=float(phase["start_s"]),
                      nominal_end_s=float(phase["end_s"]))
        if index > 0 and abs(item["command_step_s"] - float(phase["start_s"])) > tolerance:
            problems.append("phase %s command step at %.4f s is not within %.3f s of the script's %.3f s"
                            % (phase["label"], item["command_step_s"], tolerance, phase["start_s"]))
        if item["zero"] == wanted[index] and not item["zero"]:
            for command in item["distinct_commands"]:
                if any(abs(a - float(b)) > 1e-6 for a, b in zip(command, phase["command"])):
                    problems.append("phase %s command %s differs from the script's %s"
                                    % (phase["label"], list(command), phase["command"]))
        if item["script_segments"] and item["script_segments"] != [index]:
            problems.append("phase %s rows carry script_segment %s, expected [%d]"
                            % (phase["label"], item["script_segments"], index))
        last = item["last_row"]
        if index == len(expected) - 1:
            # The last zero phase ends at the finish request; later rows are post-finish.
            last = item["first_row"] - 1
            for row_index in range(item["first_row"], item["last_row"] + 1):
                if float(rows[row_index]["sim_time_s"]) <= finish_s + window_tolerance:
                    last = row_index
            record["post_finish_rows"] = item["last_row"] - last
            if float(rows[item["last_row"]]["sim_time_s"]) < finish_s - window_tolerance:
                problems.append("run ended at %.3f s, before the finish request at %.1f s"
                                % (rows[item["last_row"]]["sim_time_s"], finish_s))
        record["phase_last_row"] = last
        matched.append(record)
    if len(found) < len(expected):
        problems.append("run has %d command phases, the script has %d" % (len(found), len(expected)))
    return {"phases": matched, "problems": problems, "recorded_phase_count": len(found)}


def still_row(row: dict, reporting: dict) -> bool:
    return (float(row["horizontal_speed_mps"]) <= float(reporting["still_max_horizontal_speed_mps"])
            and abs(float(row["yaw_rate_radps"])) <= float(reporting["still_max_abs_yaw_rate_radps"]))


def zero_phase_report(rows: List[dict], phase: dict, thresholds: dict, hold: bool) -> dict:
    limits = thresholds["values"]["ac8_walk"]
    reporting = limits["reporting"]
    tolerance = float(limits["window_tolerance_s"])
    part = rows[phase["first_row"]: phase["phase_last_row"] + 1]
    t_c = phase["command_step_s"]
    reference = rows[phase["first_row"] - 1] if phase["first_row"] > 0 else rows[0]
    report = {
        "phase": phase["label"],
        "index": phase["index"],
        "nominal_start_s": phase["nominal_start_s"],
        "nominal_end_s": phase["nominal_end_s"],
        "command_step_s": t_c,
        "rows": len(part),
    }
    if not part:
        report["note"] = "no rows in the phase"
        return report
    end_s = float(part[-1]["sim_time_s"])
    duration = float(reporting["still_duration_s"])
    still_start = None
    still_found = None
    for row in part:
        if still_row(row, reporting):
            if still_start is None:
                still_start = float(row["sim_time_s"])
            if float(row["sim_time_s"]) - still_start >= duration - tolerance:
                still_found = still_start
                break
        else:
            still_start = None
    labels = modes(part)
    fixed = [row for row in part if row.get("stance_mode") == "FIXED_STAND"]
    transition = next((row for row, mode in zip(part, labels) if mode == "STAND_TRANSITION"), None)
    tail = [row for row in part if float(row["sim_time_s"]) >= end_s - float(reporting["phase_tail_s"]) - tolerance]
    exits = sum(1 for a, b in zip(labels, labels[1:]) if a == "FIXED_STAND" and b != "FIXED_STAND")
    report.update({
        "end_s": end_s,
        "time_to_still_s": None if still_found is None else still_found - t_c,
        "still_confirmed_s": None if still_found is None else still_found + duration,
        "first_transition_s": None if transition is None else float(transition["sim_time_s"]),
        "first_fixed_stand_s": float(fixed[0]["sim_time_s"]) if fixed else None,
        "time_to_fixed_stand_s": (float(fixed[0]["sim_time_s"]) - t_c) if fixed else None,
        "fixed_stand_reached": bool(fixed) if hold else None,
        "fixed_stand_exits_in_phase": exits if hold else None,
        "mode_at_end": labels[-1] or None,
        "tail": {
            "start_s": float(tail[0]["sim_time_s"]),
            "end_s": float(tail[-1]["sim_time_s"]),
            "rows": len(tail),
            "max_abs_yaw_rate_radps": max(abs(float(row["yaw_rate_radps"])) for row in tail),
            "max_horizontal_speed_mps": max(float(row["horizontal_speed_mps"]) for row in tail),
            "planar_drift_m": max(xy_distance(tail[0], row) for row in tail),
        },
        "displacement_in_phase_m": xy_distance(reference, part[-1]),
    })
    return report


def start_report(run: dict, phase: dict, thresholds: dict) -> dict:
    limits = thresholds["values"]["ac8_walk"]
    window = limits["c_start"]
    tolerance = float(limits["window_tolerance_s"])
    rows = run["rows"]
    t_c = phase["command_step_s"]
    reference = rows[phase["first_row"] - 1] if phase["first_row"] > 0 else rows[0]
    part = [row for row in rows[phase["first_row"]:]
            if float(row["sim_time_s"]) <= t_c + float(window["window_s"]) + tolerance]
    report = {
        "phase": phase["label"],
        "index": phase["index"],
        "nominal_start_s": phase["nominal_start_s"],
        "command_step_s": t_c,
        "command": phase["command"],
        "window_rows": len(part),
    }
    if not part:
        report["note"] = "no rows after the command step"
        return report
    velocities = [row.get("base_linear_velocity_world") for row in part]
    vertical_known = all(isinstance(v, (list, tuple)) and len(v) >= 3 for v in velocities)
    nonfoot = max(max(float(row.get("nonfoot_force_max_n", 0.0)), float(row.get("nonfoot_force_substep_max_n", 0.0)))
                  for row in part)
    end = float(part[-1]["sim_time_s"])
    events = [event for event in ((run["summary"] or {}).get("nonfoot_contact_events_over_threshold") or [])
              if isinstance(event, dict) and t_c < float(event.get("sim_time_s", -1.0)) <= end + tolerance]
    walk = rows[phase["first_row"]: phase["last_row"] + 1]
    report.update({
        "window_start_s": float(part[0]["sim_time_s"]),
        "window_end_s": end,
        "window_complete": end >= t_c + float(window["window_s"]) - tolerance,
        "modes": sorted({str(row.get("stance_mode")) for row in part}),
        "max_abs_pitch_deg": max(abs(math.degrees(float(row["base_rpy_rad"][1]))) for row in part),
        "max_abs_roll_deg": max(abs(math.degrees(float(row["base_rpy_rad"][0]))) for row in part),
        "max_abs_vertical_speed_mps": (max(abs(float(v[2])) for v in velocities) if vertical_known else None),
        "min_base_height_change_m": min(float(row["base_xyz"][2]) for row in part) - float(reference["base_xyz"][2]),
        "max_nonfoot_force_n": nonfoot,
        "nonfoot_events_in_window": len(events),
        "walk_phase_end_s": float(walk[-1]["sim_time_s"]),
        "walk_phase_distance_m": xy_distance(reference, walk[-1]),
        "walk_phase_path_m": path_length([reference] + walk),
    })
    return report


def walk_report(run: dict, thresholds: dict) -> dict:
    """Per-stop and per-start numbers and structural problems for one scripted-walk run."""
    matched = match_phases(run, thresholds)
    hold = hold_on(run)
    rows = run["rows"]
    zero_phases = [zero_phase_report(rows, phase, thresholds, hold) for phase in matched["phases"] if phase["zero"]]
    starts = [start_report(run, phase, thresholds) for phase in matched["phases"] if not phase["zero"]]
    return {
        "run": run["run"],
        "inputs": run["inputs"],
        "hold_on": hold,
        "stance_fields": stance_fields(rows),
        "entry_kd": entry_kd_variant(run) if hold else None,
        "status": (run["summary"] or {}).get("status"),
        "case": (run["summary"] or {}).get("case"),
        "command_script_sha256": run_script_sha256(run),
        "phase_problems": matched["problems"],
        "recorded_phase_count": matched["recorded_phase_count"],
        "zero_phases": zero_phases,
        "starts": starts,
        "planar_travel_m": xy_distance(rows[0], rows[-1]),
        "path_length_m": path_length(rows),
        "first_row_s": float(rows[0]["sim_time_s"]),
        "last_row_s": float(rows[-1]["sim_time_s"]),
    }


def run_integrity_problems(run: dict, thresholds: dict) -> List[str]:
    """AC8 d without the travel comparison; also the hold-off baseline validity."""
    limits = thresholds["values"]["ac8_walk"]
    rule = limits["d_run"]
    summary = run["summary"]
    problems = []
    if summary is None:
        return ["run has no summary.json"]
    if summary.get("status") not in rule["completed_statuses"]:
        problems.append("run status is %s, not one of %s" % (summary.get("status"), rule["completed_statuses"]))
    if summary.get("case") != rule["case"]:
        problems.append("run case is %s, not %s" % (summary.get("case"), rule["case"]))
    for key in rule["zero_event_counters"]:
        value = summary.get(key)
        if value is None:
            problems.append("summary %s is missing (not evaluable)" % key)
        elif value != 0:
            problems.append("summary %s is %s" % (key, value))
    if summary.get("case_failed") is not False:
        problems.append("summary case_failed is %s" % summary.get("case_failed"))
    guard = summary.get("contact_guard")
    if not isinstance(guard, dict) or guard.get("failed") is not False:
        problems.append("contact guard failed or not recorded: %s"
                        % (None if not isinstance(guard, dict) else guard.get("failure")))
    if (summary.get("stance_hold") or {}).get("failure") is not None:
        problems.append("stance hold failure: %s" % (summary.get("stance_hold") or {}).get("failure"))
    nonfinite = sum(count_nonfinite(row) for row in run["rows"])
    if nonfinite:
        problems.append("metrics.jsonl has %d non-finite values" % nonfinite)
    sha = run_script_sha256(run)
    if sha != limits["command_script"]["sha256"]:
        problems.append("command script SHA-256 %s is not the frozen %s" % (sha, limits["command_script"]["sha256"]))
    return problems


def ac8(on: dict, on_report: dict, off_report: dict, thresholds: dict, ac7_result: dict) -> dict:
    limits = thresholds["values"]["ac8_walk"]
    start_limits = limits["c_start"]
    problems = []
    if not on_report["hold_on"]:
        problems.append("not a stance_hold auto run")
    problems.extend(on_report["phase_problems"])

    a_checks = []
    for phase in on_report["zero_phases"]:
        ok = phase.get("first_fixed_stand_s") is not None
        a_checks.append({"phase": phase["phase"], "time_to_fixed_stand_s": phase.get("time_to_fixed_stand_s"),
                         "deadline_s": phase.get("end_s"), "pass": ok})
        if not ok:
            problems.append("a: phase %s did not reach FIXED_STAND before %s s" % (phase["phase"], phase.get("end_s")))
    if len(on_report["zero_phases"]) != sum(1 for p in limits["phases"] if not any(p["command"])):
        problems.append("a: not every zero phase was recorded")

    # AC8 b keeps the literal full 1.0 s window; the PRD D7 restart amendment applies to AC7 only.
    full = ac7_result["as_frozen_before_results"]
    b = {"verdict": full["verdict"], "entry_windows": len(ac7_result["entry_windows"]),
         "problems": full["problems"],
         "window_rule": "full window: " + AC7_FULL_WINDOW_RULE + " (ac8_walk.b_entry_windows; not the D7 restart rule)"}
    if full["verdict"] != "pass":
        problems.extend("b: " + item for item in (full["problems"] or ["AC7 verdict " + full["verdict"]]))

    c_checks = []
    off_starts = off_report["starts"]
    for position, start in enumerate(on_report["starts"]):
        off_start = off_starts[position] if position < len(off_starts) else None
        item = {"phase": start["phase"], "problems": []}
        if "max_abs_pitch_deg" not in start:
            item["problems"].append("no rows after the command step")
        else:
            if not start["window_complete"]:
                item["problems"].append("start window is incomplete (ends at %.3f s)" % start["window_end_s"])
            if (start["max_nonfoot_force_n"] >= start_limits["max_nonfoot_force_exclusive_n"]
                    or start["nonfoot_events_in_window"]):
                item["problems"].append("non-foot force %.3f N (events %d) reaches %.1f N" % (
                    start["max_nonfoot_force_n"], start["nonfoot_events_in_window"],
                    start_limits["max_nonfoot_force_exclusive_n"]))
            if start["max_abs_roll_deg"] > start_limits["max_abs_roll_deg"]:
                item["problems"].append("|roll| %.3f deg exceeds %.1f" % (start["max_abs_roll_deg"],
                                                                          start_limits["max_abs_roll_deg"]))
            if start["max_abs_pitch_deg"] > start_limits["max_abs_pitch_deg"]:
                item["problems"].append("|pitch| %.3f deg exceeds %.1f" % (start["max_abs_pitch_deg"],
                                                                           start_limits["max_abs_pitch_deg"]))
            if off_start is None or "max_abs_pitch_deg" not in off_start:
                item["pitch_excess_over_off_deg"] = None
                item["problems"].append("hold-off start %d is missing; pitch excess not evaluable" % position)
            else:
                excess = start["max_abs_pitch_deg"] - off_start["max_abs_pitch_deg"]
                item["pitch_excess_over_off_deg"] = excess
                if excess > start_limits["max_abs_pitch_excess_over_off_deg"]:
                    item["problems"].append("|pitch| %.3f deg is %.3f deg above the hold-off %.3f deg (limit %.1f)" % (
                        start["max_abs_pitch_deg"], excess, off_start["max_abs_pitch_deg"],
                        start_limits["max_abs_pitch_excess_over_off_deg"]))
        item["pass"] = not item["problems"]
        c_checks.append(item)
        problems.extend("c: start %s: %s" % (start["phase"], text) for text in item["problems"])

    d_problems = run_integrity_problems(on, thresholds)
    off_travel = off_report["planar_travel_m"]
    bound = float(limits["d_run"]["max_planar_travel_relative_difference"])
    relative = None if off_travel <= 0.0 else abs(on_report["planar_travel_m"] - off_travel) / off_travel
    if relative is None:
        d_problems.append("hold-off planar travel is zero; the travel comparison is not evaluable")
    elif relative > bound:
        d_problems.append("planar travel %.4f m differs from the hold-off %.4f m by %.1f %% (limit %.0f %%)" % (
            on_report["planar_travel_m"], off_travel, 100.0 * relative, 100.0 * bound))
    problems.extend("d: " + text for text in d_problems)
    return {
        "verdict": "pass" if not problems else "fail",
        "problems": problems,
        "a_fixed_stand": a_checks,
        "b_entry_windows": b,
        "c_starts": c_checks,
        "d_run": {"problems": d_problems, "planar_travel_m": on_report["planar_travel_m"],
                  "off_planar_travel_m": off_travel, "relative_difference": relative, "limit": bound},
    }


def max_entry_yaw(ac7_result: dict) -> Optional[float]:
    """D5 selection value: the largest full-window |yaw rate| over all entry windows (not the D7 amended window)."""
    values = [window["max_abs_yaw_rate_radps"] for window in ac7_result["entry_windows"]]
    return max(values) if values else None


def analyze_walk(off_path: Path, on_paths: Iterable[Path], thresholds: dict) -> dict:
    if "ac8_walk" not in thresholds["values"]:
        raise AnalysisError("thresholds have no ac8_walk section")
    off = load_run(off_path)
    if hold_on(off):
        raise AnalysisError("--off run %s is a stance_hold auto run" % off_path)
    off_report = walk_report(off, thresholds)
    baseline_problems = list(off_report["phase_problems"]) + run_integrity_problems(off, thresholds)
    off_report.update({
        "role": "off",
        "note": "hold-off baseline; numbers are reported without thresholds",
        "baseline_problems": baseline_problems,
        "ac5": ac5(off, thresholds),
        "ac7": ac7(off, thresholds),
    })
    runs = [off_report]
    candidates = []
    for path in on_paths:
        on = load_run(path)
        report = walk_report(on, thresholds)
        ac7_result = ac7(on, thresholds)
        ac5_result = ac5(on, thresholds)
        report.update({
            "role": "on",
            "ac5": ac5_result,
            "ac7": ac7_result,
            "ac8": ac8(on, report, off_report, thresholds, ac7_result),
            "max_entry_window_abs_yaw_rate_radps": max_entry_yaw(ac7_result),
        })
        runs.append(report)
        candidates.append({
            "run": report["run"],
            "entry_kd": report["entry_kd"],
            "ac5": ac5_result["verdict"],
            "ac8": report["ac8"]["verdict"],
            "max_entry_window_abs_yaw_rate_radps": report["max_entry_window_abs_yaw_rate_radps"],
            "eligible": (ac5_result["verdict"] == "pass" and report["ac8"]["verdict"] == "pass"
                         and report["max_entry_window_abs_yaw_rate_radps"] is not None),
        })
    selected = None
    note = None
    eligible = [item for item in candidates if item["eligible"]]
    if baseline_problems:
        note = "no selection: the hold-off baseline is not valid (%s)" % "; ".join(baseline_problems)
    elif not eligible:
        note = "no selection: no hold-on run passes AC5 and AC8; report and stop (PRD D5)"
    else:
        best = min(item["max_entry_window_abs_yaw_rate_radps"] for item in eligible)
        selected = next(item for item in eligible if item["max_entry_window_abs_yaw_rate_radps"] == best)
        ties = [item["run"] for item in eligible if item["max_entry_window_abs_yaw_rate_radps"] == best]
        note = None if len(ties) == 1 else "tie between %s; the earlier --on argument is selected" % ties
    payload = base_payload(thresholds)
    payload.update({
        "kind": "walk",
        "runs": runs,
        "selection": {
            "rule": thresholds["values"]["ac8_walk"]["selection"]["rule"],
            "candidates": candidates,
            "selected": selected,
            "note": note,
        },
    })
    return json_safe(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--allow-unfrozen-thresholds", action="store_true", default=False)
    sub = parser.add_subparsers(dest="command", required=True)
    stand = sub.add_parser("stand", help="AC3 stand A/B plus AC5 and AC7")
    stand.add_argument("--on", type=Path, required=True, help="--stance-hold auto stand_probe run")
    stand.add_argument("--off", type=Path, required=True, help="--stance-hold off stand_probe baseline run")
    stand.add_argument("--output", type=Path, default=None)
    runs = sub.add_parser("run", help="AC5, AC7 and hold timing for any run")
    runs.add_argument("runs", type=Path, nargs="+")
    runs.add_argument("--output", type=Path, default=None)
    walk = sub.add_parser("walk", help="AC8 scripted walk (PRD D5) with AC5, AC7 and the variant selection")
    walk.add_argument("--off", type=Path, required=True, help="--stance-hold off scripted_walk baseline run")
    walk.add_argument("--on", type=Path, action="append", required=True,
                      help="--stance-hold auto scripted_walk run; repeat for each entry damping variant")
    walk.add_argument("--output", type=Path, default=None)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        thresholds = load_thresholds(args.thresholds, args.allow_unfrozen_thresholds)
        if args.command == "stand":
            payload = analyze_stand(args.on, args.off, thresholds)
            ok = (payload["ac3"]["verdict"] == "pass" and payload["ac5"]["on"]["verdict"] == "pass"
                  and payload["ac7"]["on"]["verdict"] == "pass")
        elif args.command == "walk":
            payload = analyze_walk(args.off, args.on, thresholds)
            ok = payload["selection"]["selected"] is not None
        else:
            payload = analyze_runs(args.runs, thresholds)
            ok = all(item["ac5"]["verdict"] == "pass" and ac7_ok(item["ac7"]) for item in payload["runs"])
        write_output(args.output, payload)
    except AnalysisError as exc:
        raise SystemExit("stance hold analysis refused: %s" % exc)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
