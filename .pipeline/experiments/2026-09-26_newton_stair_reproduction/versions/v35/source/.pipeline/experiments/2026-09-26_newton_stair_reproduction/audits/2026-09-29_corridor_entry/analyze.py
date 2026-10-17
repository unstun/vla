"""Summarize the corridor-entry replays and compare each with the live trial's first replan cycle at the stand.

For every state (v33_stand, v32_stand) and navigation ground (state = pinned; cells_fixed, entry_filled, both =
make_grounds.py counterfactuals) it reads result_<ground>.json and probe_<ground>.log:
- the attempts of the live-entry replay ([CE-LIVE-BEGIN] ... [CE-LIVE-END]): each "[rebo replan]" call with its goal
  and outcome, and, for a final-check rejection, where the logged first-collision time falls on the checked curve
  (the preceding "minimum_cruise_checked" capture, evaluated as versions/v32/corridor_entry_curves.py does, placed in
  the navigation grid);
- the headings at which the replan start and the measured body are free (yaw sweep), and which circle stage blocks
  the others;
- the first attempt's read-only rebound breakdown.
The live cycle is the same planFromCurrentTraj call in the trial's scan.log: from the stand's "[FSM]: from EXEC_TRAJ
to REPLAN_TRAJ" line to the next "[FSM]: from REPLAN_TRAJ to REPLAN_TRAJ" line.
Beside the event signature, each attempt's printed details are compared as text (review round 1, B1): the start and
target lines, every optimizer iteration count, every final-check rejection (status, time, duration), every
post-optimization duration, every A* pool index and every frontier time printed up to the next attempt (both the
reference_frontier lines and the frontier= field of the [DEBUG-prefix-01] lines; review round 2, R2-B4). Attempts are
numbered from 1 in the output.
Usage: python3 analyze.py   (writes summary.json)
"""
from pathlib import Path
import collections, json, math, re
import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
STATES = {"v33_stand": "v33_historical_full01", "v32_stand": "v32_historical_full01"}
GROUNDS = ("state", "cells_fixed", "entry_filled", "both")
X0, Y0, RES = -7.0953148, -8.3368109, 0.1   # navigation-grid origin (make_grounds.py; decodeReactiveGround)
REJECTED = re.compile(r"final_spline_rejected status=(\d+) t=([0-9.]+) duration=([0-9.]+)")
POOL = re.compile(r"Ran out of pool, index=(-?\d+) (-?\d+) (-?\d+)")


def evaluate(controls, knots, t):
    """Uniform cubic B-spline position at time t (time runs from knots[3] to knots[len(controls)])."""
    p, k = np.asarray(controls, dtype=float), np.asarray(knots, dtype=float)
    dt = k[4] - k[3]
    span = int(np.clip(np.floor((t - k[3]) / dt), 0, len(p) - 4))
    u = (t - k[3]) / dt - span
    basis = np.array([(1 - u) ** 3, 3 * u ** 3 - 6 * u ** 2 + 4, -3 * u ** 3 + 3 * u ** 2 + 3 * u + 1, u ** 3]) / 6
    return basis @ p[span:span + 4]


def attempts(lines):
    """Split a log section into rebound-replan attempts with a compact outcome."""
    out, cur, capture = [], None, None
    for line in lines:
        if line.startswith("[rebo replan]"):
            cur = {"goal": None, "events": []}
            out.append(cur)
            capture = None
            continue
        if cur is None:
            continue
        if line.startswith("goal:"):
            cur["goal"] = [round(float(v), 2) for v in line[5:].split(",")[0].split()]
        elif '"stage":"minimum_cruise_checked"' in line:
            capture = json.loads(line.split("spline_curve_capture ", 1)[1])
        elif "The robot is inside an obstacle" in line:
            cur["events"].append("inside")
        elif POOL.search(line):
            cur["events"].append("pool " + " ".join(POOL.search(line).groups()))
        elif "First three control points are in obstacles" in line:
            cur["events"].append("first_three")
        elif "Trajectory terminal point is in an obstacle" in line:
            cur["events"].append("terminal_in_obstacle")
        elif "0.2 second time limit exceeded" in line:
            cur["events"].append("astar_timeout")
        elif "reactive_stair_seed_search_failed" in line:
            cur["events"].append("seed_failed " + line.rsplit("status=", 1)[1].strip())
        elif "first_optimize_step_success=" in line:
            cur["events"].append("optimized " + line.rsplit("=", 1)[1].strip())
        elif REJECTED.search(line):
            status, t, duration = REJECTED.search(line).groups()
            event = {"rejected": int(status), "t": float(t), "duration": float(duration)}
            if capture:
                x, y, z = evaluate(capture["controls"], capture["knots"], capture["knots"][3] + float(t))
                event.update({"xyz": [round(x, 3), round(y, 3), round(z, 3)],
                              "nav_cell": [math.floor((x - X0) / RES), math.floor((y - Y0) / RES)]})
            cur["events"].append(event)
        elif "full_spline_sampled_clear" in line:
            cur["events"].append("final_clear")
        elif "Close to goal" in line:
            cur["events"].append("close_to_goal")
    return out


def signature(a):
    """Comparable outcome: rejected curves by status and cell, not by exact time."""
    ev = [e if isinstance(e, str) else f"rejected {e['rejected']} cell {tuple(e.get('nav_cell', []))}" for e in a["events"]]
    return {"goal": a["goal"], "events": ev}


def details(lines):
    """Per attempt, the printed values compared as text with the live cycle (review round 1, B1)."""
    out, cur = [], None
    for line in lines:
        if line.startswith("[rebo replan]"):
            cur = {"start": None, "goal": None, "iterations": [], "rejections": [], "post_opt_durations": [],
                   "pool": [], "frontier": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("start:"):
            cur["start"] = line.strip()
        elif line.startswith("goal:"):
            cur["goal"] = line.strip()
        m = re.search(r"iter(?:\(\+1\))?=(\d+)", line)
        if m:
            cur["iterations"].append(int(m.group(1)))
        m = REJECTED.search(line)
        if m:
            cur["rejections"].append(list(m.groups()))
        m = re.search(r"post_opt_time_adjustment iteration=\d+ ratio=[0-9.]+ duration=([0-9.]+)", line)
        if m:
            cur["post_opt_durations"].append(m.group(1))
        m = POOL.search(line)
        if m:
            cur["pool"].append(" ".join(m.groups()))
        m = re.search(r"reference_frontier time=([0-9.]+)", line) or re.search(r"\[DEBUG-prefix-01\] .*frontier=([0-9.]+)", line)
        if m:
            cur["frontier"].append(m.group(1))
    return out


def intervals(sweep):
    """Free heading intervals, in whole degrees, of a 360-entry sweep starting at -180."""
    free = [s["occ"] == 0 for s in sweep]
    runs, start = [], None
    for d in range(361):
        f = free[d % 360] if d < 360 else False
        if f and start is None:
            start = d
        if not f and start is not None:
            runs.append([start - 180, d - 1 - 180])
            start = None
    if len(runs) > 1 and runs[0][0] == -180 and runs[-1][1] == 179:   # wrap around +-180
        runs = [[runs[-1][0], runs[0][1] + 360]] + runs[1:-1]
    return runs


def blocking(sweep):
    counts = collections.Counter()
    for s in sweep:
        if s["occ"]:
            counts[f"front {s['front']} / rear {s['rear']}"] += 1
    return dict(counts.most_common())


summary = {}
for state, run in STATES.items():
    log = (E / "runs" / run / "scan.log").read_text(errors="replace").splitlines()
    manifest = json.loads((H / state / "inputs/input_manifest.json").read_text())
    stand = manifest["stand_line"] - 1
    assert "Local reference window complete" in log[stand]
    begin = next(i for i in range(stand, len(log)) if log[i].startswith("[FSM]: from EXEC_TRAJ to REPLAN_TRAJ"))
    end = next(i for i in range(begin + 1, len(log)) if log[i].startswith("[FSM]: from REPLAN_TRAJ to REPLAN_TRAJ"))
    live = [signature(a) for a in attempts(log[begin:end])]
    live_details = details(log[begin:end])
    summary[state] = {"live_cycle_lines": [begin + 1, end + 1], "live_cycle": live, "grounds": {}}
    for ground in GROUNDS:
        result_path = H / state / f"result_{ground}.json"
        code = (H / state / f"probe_{ground}_exit_code.txt").read_text().strip()
        entry = {"exit_code": int(code)}
        if result_path.exists():
            r = json.loads(result_path.read_text())
            text = (H / state / f"probe_{ground}.log").read_text(errors="replace").splitlines()
            b = next(i for i, l in enumerate(text) if l.startswith("[CE-LIVE-BEGIN]"))
            e = next(i for i, l in enumerate(text) if l.startswith("[CE-LIVE-END]"))
            replay = [signature(a) for a in attempts(text[b:e])]
            replay_details = details(text[b:e])
            detail_differences = [{"attempt": k + 1, **{f: [a[f], r[f]] for f in a if a[f] != r[f]}}
                                  for k, (a, r) in enumerate(zip(live_details, replay_details)) if a != r]
            att = r["attempt"]
            chain = []
            if att["first_new_collision"] >= 0:
                for j in range(att["first_new_collision"], -1, -1):
                    cp = att["control_points"][j]
                    q = cp["query"]
                    chain.append({"index": j, "xyz": [round(v, 4) for v in cp["xyz"]], "yaw_deg": round(math.degrees(q["yaw"]), 2),
                                  "occ": q["occ"], "front": q["front"]["stage"], "rear": q["rear"]["stage"],
                                  "front_centre": [round(v, 4) for v in q["front"]["center"]],
                                  "rear_centre": [round(v, 4) for v in q["rear"]["center"]]})
                    if q["occ"] == 0 and j < att["first_new_collision"]:
                        break
            entry.update({
                "clouds": r["clouds"], "start": r["start"], "body": r["body"], "body_yaw_deg": round(math.degrees(r["body_yaw"]), 2),
                "start_free_headings_deg": intervals(r["sweep_start"]), "start_blocking": blocking(r["sweep_start"]),
                "body_free_headings_deg": intervals(r["sweep_body"]), "body_blocking": blocking(r["sweep_body"]),
                "live_entry_ok": r["live"]["ok"], "live_entry_committed": r["live"]["committed"],
                "replay_cycle": replay,
                "replay_matches_live": ground == "state" and replay == live,
                "details_compared_with_live": ground == "state",
                "detail_differences_from_live": detail_differences if ground == "state" else None,
                "attempts_identical_in_detail": (sum(1 for a, r in zip(live_details, replay_details) if a == r)
                                                 if ground == "state" else None),
                "first_attempt": {k: att[k] for k in ("target_ok", "target", "frontier_s", "target_time_s", "ok",
                                                      "optimization_attempted", "size", "i_end", "first_new_collision",
                                                      "backward_free", "inside_replicated")},
                "first_attempt_chain": chain,
                "trajectory_first_occupied": att["trajectory_first_occupied"] and {
                    k: att["trajectory_first_occupied"][k] for k in ("t", "interval", "within_first_interval", "xyz")},
                "mismatches": {k: r[k] for k in ("circle_mismatches", "support_mismatches", "query_mismatches")}})
        summary[state]["grounds"][ground] = entry
(H / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
for state, s in summary.items():
    print(state, "live cycle", s["live_cycle_lines"])
    for g, e in s["grounds"].items():
        if "clouds" not in e:
            print(" ", g, "exit", e["exit_code"], "no result")
            continue
        print(" ", g, "exit", e["exit_code"], "live_ok", e["live_entry_ok"], "matches_live", e["replay_matches_live"],
              "identical_in_detail", e["attempts_identical_in_detail"],
              "start_free", e["start_free_headings_deg"], "inside_replicated", e["first_attempt"]["inside_replicated"],
              "mismatch", e["mismatches"])
