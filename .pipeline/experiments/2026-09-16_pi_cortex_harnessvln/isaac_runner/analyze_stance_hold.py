#!/usr/bin/env python3
"""AC3 and AC5 metrics for Isaac runner stance-hold runs.

Reads only returned run files (`metrics.jsonl`, `summary.json`, optional
`stance_hold_setup.json`) and the frozen `stance_hold_thresholds.json`.

    analyze_stance_hold.py stand --on RUN --off RUN --output OUT.json
    analyze_stance_hold.py run RUN [RUN ...] --output OUT.json

RUN is a run package (with returned_artifacts/runner_output) or a
runner_output directory. `stand` gives the AC3 verdict for the hold-on
stand_probe run, the hold-off baseline over the same simulation window, and
AC5 for both. `run` gives AC5 plus a stance summary for any run, such as a
two-goal episode. Rows without stance fields are reported as
"hold off / no stance fields".

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
# SHA-256 of stance_hold_thresholds.json as frozen before the first stance-hold
# Isaac run. A different file is refused unless --allow-unfrozen-thresholds.
FROZEN_THRESHOLDS_SHA256 = "fb8f9204c18e0b400ae2b7a2abc22bb052526538ff9713689759f15bff897c66"
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
        raise AnalysisError(
            "thresholds %s have SHA-256 %s, not the frozen %s" % (path, digest, FROZEN_THRESHOLDS_SHA256)
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
    inputs = {"metrics": {"path": str(metrics), "sha256": sha256_file(metrics)}}
    for name, path in (("summary", summary_path), ("stance_hold_setup", setup_path)):
        if path.is_file():
            inputs[name] = {"path": str(path), "sha256": sha256_file(path)}
    return {"run": str(run), "output_dir": str(out), "rows": rows, "summary": summary, "setup": setup,
            "inputs": inputs}


def has_stance(rows: List[dict]) -> bool:
    return any("stance_mode" in row for row in rows)


def stance_fields(rows: List[dict]):
    """Sorted stance modes present, or the no-stance label for legacy rows."""
    return sorted({str(row["stance_mode"]) for row in rows if "stance_mode" in row}) or NO_STANCE


def modes(rows: List[dict]) -> List[str]:
    return [str(row.get("stance_mode", "")) for row in rows]


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
    labels = modes(rows)
    nonfoot_rows = max(max(float(row.get("nonfoot_force_max_n", 0.0)),
                           float(row.get("nonfoot_force_substep_max_n", 0.0))) for row in rows)
    nonfoot_summary = summary.get("max_nonfoot_force_n")
    nonfoot = max(nonfoot_rows, float(nonfoot_summary or 0.0))
    events = len(summary.get("nonfoot_contact_events_over_threshold") or [])
    problems = []
    if nonfoot >= limits["max_nonfoot_force_exclusive_n"] or events:
        problems.append("non-foot force %.3f N (events %d) reaches the %.1f N guard"
                        % (nonfoot, events, limits["max_nonfoot_force_exclusive_n"]))
    entries = [index for index in range(len(rows))
               if labels[index] == "STAND_TRANSITION" and (index == 0 or labels[index - 1] != "STAND_TRANSITION")]
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
            "zero_command_intervals": zero_command_intervals(run, thresholds),
        })
    return json_safe(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--allow-unfrozen-thresholds", action="store_true", default=False)
    sub = parser.add_subparsers(dest="command", required=True)
    stand = sub.add_parser("stand", help="AC3 stand A/B plus AC5")
    stand.add_argument("--on", type=Path, required=True, help="--stance-hold auto stand_probe run")
    stand.add_argument("--off", type=Path, required=True, help="--stance-hold off stand_probe baseline run")
    stand.add_argument("--output", type=Path, default=None)
    runs = sub.add_parser("run", help="AC5 and hold timing for any run")
    runs.add_argument("runs", type=Path, nargs="+")
    runs.add_argument("--output", type=Path, default=None)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        thresholds = load_thresholds(args.thresholds, args.allow_unfrozen_thresholds)
        if args.command == "stand":
            payload = analyze_stand(args.on, args.off, thresholds)
            ok = payload["ac3"]["verdict"] == "pass" and payload["ac5"]["on"]["verdict"] == "pass"
        else:
            payload = analyze_runs(args.runs, thresholds)
            ok = all(item["ac5"]["verdict"] == "pass" for item in payload["runs"])
        write_output(args.output, payload)
    except AnalysisError as exc:
        raise SystemExit("stance hold analysis refused: %s" % exc)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
