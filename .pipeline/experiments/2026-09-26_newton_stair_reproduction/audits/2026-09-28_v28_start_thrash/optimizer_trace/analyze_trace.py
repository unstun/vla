"""Summarize VLA_TRACE replay logs: outcome per state and blocked-query classes.

Usage: python3 analyze_trace.py <run_dir> [<run_dir> ...]
Each run directory holds one sub-directory per replayed state with probe.log
and result.json. Writes <run_dir>/trace_summary.json.
"""
from pathlib import Path
import collections
import json
import re
import sys

NUMBER = r"(nan|-?[\d.]+)"
QUERY = re.compile(
    r"TRACE_Q reason=(\w+)(?: v=(\d+))? p=\(%s,%s,%s\) body=\(%s,%s,%s\) raw=(\d) occ=(\d) inside=(-?\d) "
    r"local=\(%s,%s,%s\) log_odds=%s inflate=(-?\d+)" % ((NUMBER,) * 10))
SUPPORT = re.compile(r"TRACE_SUPPORT reason=(\w+)(?: v=(\d+))?")
# Occupancy enum: Unknown=0, Free=1, Occupied=2. Verdict 6 = UnknownObstacle, 10 = WrongHeight.
OCCUPANCY = {"0": "unknown", "1": "free", "2": "occupied"}


def classify(match):
    reason, verdict, raw, occ, inside = match.group(1), match.group(2), match.group(9), match.group(10), match.group(11)
    local_z = float(match.group(14))
    if reason == "verdict" and verdict == "6" and raw == "0" and occ == "0":
        if inside == "0" and local_z > 0.07:
            return "unknown_above_trunk_band"
        if inside == "0":
            return "unknown_outside_footprint"
        return "unknown_other"
    if reason == "support":
        return "support_" + OCCUPANCY[raw] + ("_waived" if raw == "0" and occ == "1" else "")
    return "%s_v%s_%s" % (reason, verdict, OCCUPANCY.get(raw, raw))


def summarize(state_dir):
    lines = (state_dir / "probe.log").read_text(errors="replace").splitlines()
    result = json.loads((state_dir / "result.json").read_text())
    classes, supports, events = collections.Counter(), collections.Counter(), collections.Counter()
    decisive = []
    pending = []
    for line in lines:
        match = QUERY.match(line)
        if match:
            label = classify(match)
            classes[label] += 1
            pending.append(label)
            continue
        support = SUPPORT.match(line)
        if support:
            supports[support.group(1) + ("_v" + support.group(2) if support.group(2) else "")] += 1
            continue
        for key in ("TRACE_ASTAR_START occ=1", "TRACE_ASTAR_END occ=1", "TRACE_REFINE_POST", "TRACE_POST",
                    "A-star failed; aborting optimization", "A-star error", "Ran out of pool",
                    "This refined trajectory is unsafe", "final_spline_rejected", "reactive_stair_seed_search_failed",
                    "First three control points are in obstacles"):
            if key in line:
                events[key] += 1
                if key in ("TRACE_ASTAR_START occ=1", "TRACE_ASTAR_END occ=1", "TRACE_REFINE_POST", "TRACE_POST"):
                    decisive.append({"event": key, "blocked_by": sorted(set(pending))})
        if line.startswith("TRACE_ASTAR_ENDPOINTS") or line.startswith("TRACE_REFINE adjustment") or \
                line.startswith("[rebo replan]") or line.startswith("TRACE_INIT first"):
            pending = []
    decisive_counts = collections.Counter(
        "%s <- %s" % (item["event"], "+".join(item["blocked_by"]) or "none") for item in decisive)
    return {
        "final_body_z": result["start"][2], "continued": result["continued"],
        "accepted_xy_displacement_m": result["accepted_xy_displacement_m"],
        "boundary_pass": result["boundary_pass"], "full_clear": result["full_clear"],
        "blocked_query_classes": dict(classes.most_common()), "support_failures": dict(supports.most_common()),
        "events": dict(events.most_common()), "decisive_checks": dict(decisive_counts.most_common()),
    }


for argument in sys.argv[1:]:
    run = Path(argument).resolve()
    summary = {path.name: summarize(path) for path in sorted(run.iterdir())
               if path.is_dir() and (path / "result.json").exists() and (path / "probe.log").exists()}
    (run / "trace_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for name, item in summary.items():
        print("%-10s z=%.4f continued=%-5s accepted=%.4f decisive=%s" % (
            name, item["final_body_z"], item["continued"], item["accepted_xy_displacement_m"],
            json.dumps(item["decisive_checks"])))
