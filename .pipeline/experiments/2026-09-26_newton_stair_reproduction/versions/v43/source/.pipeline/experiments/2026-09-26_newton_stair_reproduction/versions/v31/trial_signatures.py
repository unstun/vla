"""Count the stale-input signatures of the v30 stop diagnosis in one physical run's scan.log.

Usage: python3 trial_signatures.py <run dir> [<run dir> ...]; prints one JSON record per run.

Counts, from SCAN's own log lines only:
- emergency-stop transitions by source ([SAFETY], [INVALID_SPLINE_INPUT], ...);
- conflict stops with the conflict 0.000 s ahead ("Obstacle discovered; emergency stop in 0.000s");
- invalidations of the executing curve (remaining_spline_invalid) by status;
- final-curve rejections (final_spline_rejected) by status, and clear final checks;
- "The robot is inside an obstacle", and how many are followed by "terminal point is in an obstacle";
- "Target is occupied and no collision-free point was found" (whole route blocked);
- v31 input_refresh lines by site: messages applied, and the processed-scan and body-pose ages before and
  after the refresh (min, median, max), how many after-ages are negative (an input stamped ahead of the
  clock, which every freshness test reads as stale), how many exceed the 0.1 s pose and 0.25 s scan
  gates, and how many before-ages exceed them;
- failed takes ("input_refresh ... take from ... failed").
At the two timers (exec, safety) v31 logs only a stale input applied or a negative age, so their rows
are a selection; the four inner sites log every call.
"""
import collections, json, re, statistics, sys
from pathlib import Path

TRANSITION = re.compile(r"^\[([A-Z_0-9]+)\]: from (\w+) to (\w+)")
REFRESH = re.compile(r"input_refresh site=(\w+) sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+) fsm_odom=(-?\d+) "
                     r"cloud_age=([-0-9.]+)->([-0-9.]+) body_age=([-0-9.]+)->([-0-9.]+)")
GATES = {"cloud": 0.25, "body": 0.1}


def ages(values):
    return {"min": round(min(values), 4), "median": round(statistics.median(values), 4), "max": round(max(values), 4)}


def summarize(run):
    lines = (run / "scan.log").read_text(errors="replace").splitlines()
    stops, invalid, final, refresh = collections.Counter(), collections.Counter(), collections.Counter(), collections.defaultdict(list)
    inside = terminal = route_blocked = conflict_0s = clear = take_failures = 0
    for i, line in enumerate(lines):
        t = TRANSITION.match(line)
        if t and t.group(3) == "EMERGENCY_STOP":
            stops[f"{t.group(1)}:{t.group(2)}"] += 1
        conflict_0s += "Obstacle discovered; emergency stop in 0.000s" in line
        m = re.search(r"remaining_spline_invalid status=(\d+)", line)
        if m:
            invalid[m.group(1)] += 1
        m = re.search(r"final_spline_rejected status=(\d+)", line)
        if m:
            final[m.group(1)] += 1
        clear += "full_spline_sampled_clear" in line
        if "The robot is inside an obstacle" in line:
            inside += 1
            terminal += any("terminal point is in an obstacle" in x for x in lines[i + 1:i + 3])
        route_blocked += "Target is occupied and no collision-free point was found" in line
        take_failures += bool(re.search(r"input_refresh .*take from .* failed", line))
        m = REFRESH.search(line)
        if m:
            g = m.groups()
            refresh[g[0]].append({"applied": [int(x) for x in g[1:4]], "fsm_odom": int(g[4]),
                                  "cloud": (float(g[5]), float(g[6])), "body": (float(g[7]), float(g[8]))})
    sites = {}
    for site, rows in sorted(refresh.items()):
        entry = {"lines": len(rows),
                 "applied": {k: sum(r["applied"][i] for r in rows) for i, k in enumerate(("sensor_poses", "clouds", "body_poses"))},
                 "lines_applying_anything": sum(any(r["applied"]) for r in rows),
                 "fsm_odom_applied": sum(max(r["fsm_odom"], 0) for r in rows)}
        for kind, gate in GATES.items():
            before, after = [r[kind][0] for r in rows], [r[kind][1] for r in rows]
            entry[f"{kind}_age_before"] = ages(before)
            entry[f"{kind}_age_after"] = ages(after)
            entry[f"{kind}_after_negative"] = sum(x < 0 for x in after)
            entry[f"{kind}_before_over_gate"] = sum(x > gate for x in before)
            entry[f"{kind}_after_over_gate"] = sum(x > gate for x in after)
        sites[site] = entry
    return {"run": run.name, "scan_log_lines": len(lines), "emergency_stop_transitions": dict(stops),
            "conflict_stops_0s": conflict_0s, "executing_curve_invalidations": dict(invalid),
            "final_curve_rejections": dict(final), "final_curve_clear": clear,
            "inside_obstacle": inside, "inside_obstacle_then_terminal": terminal, "whole_route_blocked": route_blocked,
            "input_refresh_take_failures": take_failures, "input_refresh": sites}


for argument in sys.argv[1:]:
    print(json.dumps(summarize(Path(argument)), indent=2))
