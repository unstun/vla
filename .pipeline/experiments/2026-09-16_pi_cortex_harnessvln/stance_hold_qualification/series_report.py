#!/usr/bin/env python3
"""AC4 report for the stance-hold two-goal series (task 09-17-isaac-runner-stance-hold).

AC4 asks for the pass count with its exact bound, the hold entries and exits, the time to hold, the max |yaw rate|
inside each review still window, and the rejoin transitions. This script adds no verdict of its own: the pass count
comes from the series ledger (the unchanged 41 review checks), AC5 / AC7 and the zero-command hold timing come from
`isaac_runner/analyze_stance_hold.py`, and the still window is the review's own rule (`review_two_goal.py`): the
rows sampled at or before the terminal, taken backwards until they span `stop_dwell_sim_seconds`. For a passing
dwell check that is exactly the review window; for a failing one it is the fixed-length window the check wanted.

A hold-off ledger (the SCAN fix series, same plan and build) can be given as a baseline; its runs have no stance
fields, so only the still windows and the pass count are reported for it.

AC7 is printed as two verdicts side by side, e.g. `AC7 pass (as frozen: FAIL)`: the first uses the loaded thresholds
(PRD D7: the entry window ends at a restart, a post-result change made after the C2 result), the second is the
full-window rule as frozen before the results (`ac7.as_frozen_before_results`).

    series_report.py --ledger hold_series/series_ledger.jsonl \
        --baseline-ledger ../scan_fix_qualification/isaac_series/series_ledger.jsonl --output OUT.json
"""
import argparse
import json
import math
from pathlib import Path

import sys

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / "isaac_runner"))
import analyze_stance_hold as hold  # noqa: E402  (path set above)

RUNS = EXP / "isaac_runner/two_goal_runs"
CONFIDENCE = 0.95
AC7_AMENDED_NOTE = (
    "AC7 verdict: PRD D7 rule, a post-result change made after the C2 result (the entry window ends at a restart); "
    "'as frozen' is the full-window rule frozen before the results"
)


def lower_bound(passed, total, confidence=CONFIDENCE):
    """One-sided Clopper-Pearson lower bound on the pass probability."""
    if passed == 0:
        return 0.0
    alpha = 1.0 - confidence

    def tail(p):  # P(X >= passed | total, p)
        return sum(math.comb(total, k) * p ** k * (1 - p) ** (total - k) for k in range(passed, total + 1))

    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if tail(mid) < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ledger_runs(path):
    """Ledger lines that name a run, in episode order (one line per episode in both series ledgers)."""
    items = []
    for line in Path(path).read_text().splitlines():
        record = json.loads(line)
        if record.get("run_id") and record.get("episode") is not None:
            items.append(record)
    return sorted(items, key=lambda r: r["episode"])


def still_windows(run_dir, run_id, rows):
    review = json.loads((run_dir / "review.json").read_text())
    pilot = json.loads((run_dir / "inputs/pilot.json").read_text())
    dwell = pilot["stop_dwell_sim_seconds"]
    result = []
    for item in review["terminals"]:
        terminal = item.get("terminal")
        if terminal is None:
            result.append({"goal": item["request_id"][len(run_id) + 1:], "present": False})
            continue
        before = [r for r in rows if r["state_sample_monotonic_ns"] <= terminal["monotonic_s"] * 1e9]
        window = []
        for row in reversed(before):
            window.append(row)
            if window[0]["sim_time_s"] - window[-1]["sim_time_s"] >= dwell:
                break
        if not window:  # no physics row at or before the terminal (the review fails raw_state_fresh)
            result.append({"goal": item["request_id"][len(run_id) + 1:], "status": item["status"], "present": True,
                           "samples": 0, "review_dwell_check": review["checks"].get(item["request_id"] + ":raw_physics_stop_dwell")})
            continue
        yaw = [abs(float(r["yaw_rate_radps"])) for r in window]
        peak = max(range(len(window)), key=lambda i: yaw[i])
        result.append({
            "goal": item["request_id"][len(run_id) + 1:],
            "status": item["status"],
            "terminal_sim_s": window[0]["sim_time_s"],
            "window_start_sim_s": window[-1]["sim_time_s"],
            "samples": len(window),
            "max_abs_yaw_rate_radps": yaw[peak],
            "max_abs_yaw_rate_at_sim_s": window[peak]["sim_time_s"],
            "yaw_limit_radps": pilot["stop_yaw_rate_radps"],
            "max_horizontal_speed_mps": max(float(r["horizontal_speed_mps"]) for r in window),
            "speed_limit_mps": pilot["stop_speed_mps"],
            "stance_modes": sorted({r.get("stance_mode", "none") for r in window}),
            "review_raw_stop_span_sim_s": item.get("raw_stop_span_sim_s"),
            "review_dwell_check": review["checks"].get(item["request_id"] + ":raw_physics_stop_dwell"),
            "target_xy_error_m": item.get("target_xy_error_m"),
        })
    return result


def exits(rows):
    """Each REJOIN segment with the mode it left and its sim-time span."""
    labels = hold.modes(rows)
    result = []
    index = 0
    while index < len(rows):
        if labels[index] != "REJOIN":
            index += 1
            continue
        start = index
        while index < len(rows) and labels[index] == "REJOIN":
            index += 1
        result.append({
            "start_s": rows[start]["sim_time_s"],
            "end_s": rows[index - 1]["sim_time_s"],
            "left_mode": labels[start - 1] if start > 0 else None,
            "rows": index - start,
        })
    return result


def direct_exits(rows):
    """Hold exits that skip REJOIN (FIXED_STAND disturbance exit straight to RL, stance_hold.py)."""
    labels = hold.modes(rows)
    return [{"at_s": rows[i]["sim_time_s"], "left_mode": labels[i - 1], "to_mode": labels[i],
             "reason": rows[i].get("stance_reason")}
            for i in range(1, len(rows))
            if labels[i - 1] in ("STAND_TRANSITION", "FIXED_STAND") and labels[i] == "RL"]


def episode_report(record, thresholds):
    run_dir = RUNS / record["run_id"]
    item = {
        "episode": record["episode"],
        "run_id": record["run_id"],
        "cancel_displacement_m": record["cancel_displacement_m"],
        "outcome": record["outcome"],
        "checks": "%s/%s" % (record.get("checks_passed"), record.get("checks_total")),
        "failed_checks": record.get("failed_checks"),
        "recovered_after_driver_interrupt": bool(record.get("recovered_after_driver_interrupt")),
    }
    try:
        run = hold.load_run(run_dir)
        rows = run["rows"]
        item["still_windows"] = still_windows(run_dir, record["run_id"], rows)
    except (OSError, ValueError, KeyError, hold.AnalysisError) as error:
        if record["outcome"] == "passed":
            raise  # a passed ledger line must have its returned, reviewed artifacts
        item["still_windows"] = []
        item["report_error"] = repr(error)  # e.g. a launcher failure left no returned run or review.json
        return item
    if hold.has_stance(rows) and hold.hold_on(run):
        ac7 = hold.ac7(run, thresholds)
        item.update({
            "stance_entry_kd": hold.entry_kd_variant(run),
            "ac5": hold.ac5(run, thresholds),
            "ac7": ac7,
            # ac7_ok follows the AC7 verdict under the loaded thresholds (the PRD D7 restart rule, a post-result
            # change); ac7_as_frozen_ok is the full-window rule as frozen before the results.
            "ac7_ok": hold.ac7_ok(ac7),
            "ac7_as_frozen_ok": hold.ac7_ok(ac7["as_frozen_before_results"]),
            "zero_command_intervals": hold.zero_command_intervals(run, thresholds),
            "exits": exits(rows),
            "mode_seconds": {m: round(sum(1 for x in hold.modes(rows) if x == m) * hold.step_dt(rows), 3)
                             for m in sorted(set(hold.modes(rows)))},
        })
        direct = direct_exits(rows)
        if direct:  # absent key when every exit went through REJOIN
            item["direct_exits"] = direct
    return item


def series(path, thresholds):
    records = ledger_runs(path)
    episodes = [episode_report(r, thresholds) for r in records]
    passed = sum(1 for r in records if r["outcome"] == "passed")
    windows = [w for e in episodes for w in e["still_windows"] if "max_abs_yaw_rate_radps" in w]
    return {
        "ledger": str(path),
        "passed": passed,
        "total": len(records),
        "one_sided_95_lower_bound": lower_bound(passed, len(records)),
        "bound_rule": "one-sided Clopper-Pearson, 95 %",
        "still_window_max_abs_yaw_rate_radps": max(w["max_abs_yaw_rate_radps"] for w in windows) if windows else None,
        "still_window_max_horizontal_speed_mps": max(w["max_horizontal_speed_mps"] for w in windows) if windows else None,
        "episodes": episodes,
    }


def fmt(value):
    return "n/a" if value is None else "%.4f" % value


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--baseline-ledger", type=Path, default=None)
    parser.add_argument("--thresholds", type=Path, default=hold.DEFAULT_THRESHOLDS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    thresholds = hold.load_thresholds(args.thresholds)
    amended = bool(thresholds["values"]["ac7_entry"].get("end_at_restart", False))
    report = {
        "purpose": __doc__.strip().splitlines()[0],
        "thresholds": {"path": str(args.thresholds), "sha256": hold.sha256_file(args.thresholds)},
        "ac7_rule": (AC7_AMENDED_NOTE if amended else "AC7 uses the full entry window as frozen before the results"),
        "hold": series(args.ledger, thresholds),
        "baseline": series(args.baseline_ledger, thresholds) if args.baseline_ledger else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(hold.json_safe(report), indent=2) + "\n")
    print(report["ac7_rule"])
    for name in ("hold", "baseline"):
        part = report[name]
        if part is None:
            continue
        print("%s: %d/%d passed, one-sided 95%% lower bound %.3f; still-window max |yaw| %s rad/s, max speed %s m/s"
              % (name, part["passed"], part["total"], part["one_sided_95_lower_bound"],
                 fmt(part["still_window_max_abs_yaw_rate_radps"]), fmt(part["still_window_max_horizontal_speed_mps"])))
        for episode in part["episodes"]:
            yaws = " ".join("%.4f" % w["max_abs_yaw_rate_radps"] for w in episode["still_windows"] if "max_abs_yaw_rate_radps" in w)
            extra = " report_error %s" % episode["report_error"] if "report_error" in episode else ""
            if "ac7" in episode:
                # Every hold entry (first STAND_TRANSITION row), not zero-command intervals with at least one entry.
                entries = len(episode["ac7"]["entry_windows"])
                exits_count = len(episode["exits"]) + len(episode.get("direct_exits", []))
                extra = " entries %d exits %d (rejoin %d) AC5 %s AC7 %s (as frozen: %s)" % (
                    entries, exits_count, len(episode["exits"]), episode["ac5"]["verdict"],
                    "pass" if episode["ac7_ok"] else "FAIL", "pass" if episode["ac7_as_frozen_ok"] else "FAIL")
            print("  e%02d %s %s still-window max |yaw| %s%s" % (episode["episode"], episode["checks"],
                                                               episode["outcome"], yaws, extra))


if __name__ == "__main__":
    main()
