"""Bound SCAN's processed-scan age inside planning callbacks of v30_historical_full01.

Read-only over runs/v30_historical_full01. Uses the clock offset fitted by
timeline.py (timeline.json). Writes scan_age_bounds.json.

A planning callback is the run of scan.log lines from the first planning line
(A* goal search, route walk, optimizer or final check) to the FSM transition
out of GEN_NEW_TRAJ or REPLAN_TRAJ that closes it. The node runs one
single-threaded executor with no nested spin, so no scan is processed inside
such a callback.

- Exact ages: a `reactive_collision_blocked` line prints the processed scan's
  stamp; a later line of the same callback that prints `now=` gives its age at
  that moment. The stamp is matched to sensor_manifest.json to the nanosecond.
- Lower bounds: at a callback's end, or at a "robot is inside an obstacle"
  line, the processed scan is at most the newest scan published before the
  callback's first planning line. These use the clock mapping (median residual
  0.003 s, maximum 0.021 s).
- Preconditions of the other global blocks (missing processed scan, missing
  surface ground): "no sensor_pose" warnings, scan point counts, and how often
  each ground was published.
- Hold curves (six equal control points) published by SCAN versus the 3 s
  holds the controller received.
- For each "inside an obstacle" line, the XY distance of the optimized
  curve's start and goal (the `start:`/`goal:` lines after the preceding
  `[rebo replan]`) from the recorded body pose at the mapped time. The
  footprint reaches 0.53 m from the body (0.18 m offset + 0.35 m radius), and
  each query point sits 0.18 m from its control point, so the blind-zone
  waiver can reach a control point only within 0.71 m of the body.
- Live candidate at scan.log line 9434: distance of its colliding sample from
  the curve's start, and the 0.8 s look-ahead displacement at each of its 38
  samples (uniform steps up to the logged collision time).

Usage: python3 scan_age_bounds.py <experiment root> <audit dir>
"""
import bisect, json, re, statistics, sys
from pathlib import Path

base, audit = Path(sys.argv[1]), Path(sys.argv[2])
run = base / "runs/v30_historical_full01"
timeline = json.loads((audit / "timeline.json").read_text())
offset = timeline["summary"]["clock_mapping"]["offset_s"]
snap = [json.loads(l)["snapshot"] for l in (run / "applied_sent.jsonl").open()]
W = [(s["run_epoch_ns"] + s["wall_monotonic_ns"]) / 1e9 for s in snap]
S = [s["sim_time_s"] for s in snap]


def sim_at(wall):
    wall -= offset
    i = min(max(bisect.bisect_left(W, wall), 1), len(W) - 1)
    return S[i - 1] + (S[i] - S[i - 1]) * (wall - W[i - 1]) / (W[i] - W[i - 1])


manifest = json.loads((run / "sensor_manifest.json").read_text())
stamps = sorted(r["stamp_ns"] / 1e9 for r in manifest)
published = sorted((r["published_at_physics_s"], r["stamp_ns"] / 1e9) for r in manifest)


def exact_stamp(printed):
    s = min(stamps, key=lambda v: abs(v - printed))
    assert abs(s - printed) < 0.0006, printed
    return s


def newest_published_before(sim):
    return max(s for p, s in published if p <= sim)


TS = re.compile(r"^\[[A-Z]+\] \[([0-9]+\.[0-9]+)\]")
TRANSITION = re.compile(r"^\[([A-Z_0-9]+)\]: from (\w+) to (\w+)")
STAMP = re.compile(r"reactive_collision_blocked .* now=([0-9.]+) cloud_stamp=([0-9.]+)")
NOW = re.compile(r"now=([0-9.]+)")
PLANNING = ("Ran out of pool", "Unable to handle the initial", "reference_frontier", "[rebo replan]",
            "Failed in A-star", "A-star path search took", "reactive_stair_seed_search", "spline_curve_capture", "final_spline_rejected",
            "fixed_height_recovery", "[DEBUG-prefix-01]", "Target is occupied", "reference_prefix_proposal",
            "full_spline_sampled_clear", "final_plan_success")
lines = (run / "scan.log").read_text(errors="replace").splitlines()
segments, current, wall = [], [], None
for index, line in enumerate(lines, 1):
    m = TS.match(line)
    if m:
        wall = float(m.group(1))
    t = TRANSITION.match(line)
    if t:
        segments.append({"line": index, "source": t.group(1), "from": t.group(2), "lines": current})
        current = []
    else:
        current.append((index, wall, line))

pairs, ends, inside = [], [], []
for seg in segments:
    if seg["source"] != "FSM" or seg["from"] not in ("GEN_NEW_TRAJ", "REPLAN_TRAJ"):
        continue
    first = next((k for k, x in enumerate(seg["lines"]) if any(p in x[2] for p in PLANNING)), None)
    if first is None:
        continue
    body = seg["lines"][first:]
    walls = [w for _, w, text in body if w is not None and TS.match(text)]
    start_sim = sim_at(walls[0])
    newest = newest_published_before(start_sim)
    if walls[-1] > walls[0]:
        ends.append(round(sim_at(walls[-1]) - newest, 4))
    stamp = None
    for k, (index, w, text) in enumerate(body):
        m = STAMP.search(text)
        if m and stamp is None:
            stamp = (index, exact_stamp(float(m.group(2))))
        elif stamp and NOW.search(text):
            now = float(NOW.search(text).group(1))
            pairs.append({"stamp_line": stamp[0], "stamp_s": round(stamp[1], 9), "line": index,
                          "now_s": now, "age_s": round(now - stamp[1], 6)})
        if "robot is inside an obstacle" in text:
            sim = sim_at(w)
            inside.append({"line": index, "sim_s": round(sim, 4), "callback_closed_at": seg["line"], "state": seg["from"],
                           "terminal_point_in_obstacle": any("terminal point is in an obstacle" in x[2] for x in body[k:k + 3]),
                           "lower_bound_age_s": round(sim - newest, 4),
                           "mapped_age_from_printed_stamp_s": round(sim - stamp[1], 4) if stamp else None,
                           "printed_stamp_line": stamp[0] if stamp else None})

pose_warnings = sum("no sensor_pose" in l for l in lines)
tomogram_events = 0
holds, receipts, body_poses = [], [], []
with (run / "artifacts/reactive_observations.jsonl").open() as f:
    for line in f:
        record = json.loads(line)
        tomogram_events += record["event"] == "pct_tomogram"
        if record["event"] == "body_pose_observer" and record["clock_ns"] is not None:
            position = record["data"]["pose"]["pose"]["position"]
            body_poses.append((record["clock_ns"] / 1e9, position["x"], position["y"]))
        if record["event"] == "bspline":
            points = record["data"]["pos_pts"]
            if len(points) == 6 and all(p == points[0] for p in points):
                holds.append(record["data"]["traj_id"])
received = [(int(n), float(d)) for n, d in re.findall(r"Received trajectory (\d+), duration ([0-9.]+)s",
                                                          (run / "controller.log").read_text())]
received_ids = {n for n, _ in received}
cancel_lines = [i for i, l in enumerate(lines, 1) if l.startswith("[P2B_CANCEL]: from")]
surface_publications = sum("Published /pct_ground_surface" in l for l in (run / "pct_surface_ground.log").read_text().splitlines())

body_poses.sort()
body_times = [b[0] for b in body_poses]
NUMBER = re.compile(r"-?\d+\.?\d*(?:e-?\d+)?")
for r in inside:
    j = r["line"] - 1
    while "[rebo replan]" not in lines[j - 1]:
        j -= 1
    start = [float(v) for v in NUMBER.findall(lines[j].split("start:")[1].split(",")[0])]
    goal = [float(v) for v in NUMBER.findall(lines[j + 1].split("goal:")[1].split(",")[0])]
    _, bx, by = body_poses[max(0, bisect.bisect_right(body_times, r["sim_s"]) - 1)]
    r["start_from_body_xy_m"] = round(((start[0] - bx) ** 2 + (start[1] - by) ** 2) ** 0.5, 3)
    r["goal_from_body_xy_m"] = round(((goal[0] - bx) ** 2 + (goal[1] - by) ** 2) ** 0.5, 3)


def de_boor(controls, knots, u, degree=3):
    k = min(max(bisect.bisect_right(knots, u) - 1, degree), len(knots) - degree - 2)
    d = [list(controls[j + k - degree]) for j in range(degree + 1)]
    for r_ in range(1, degree + 1):
        for j in range(degree, r_ - 1, -1):
            a = (u - knots[j + k - degree]) / (knots[j + 1 + k - r_] - knots[j + k - degree])
            d[j] = [(1 - a) * x + a * y for x, y in zip(d[j - 1], d[j])]
    return d[degree]


candidate = next(c for c in json.loads((audit / "upper_corridor_hold/live_candidates.json").read_text()) if c["line"] == 9434)
knots = candidate["knots"]
u0, u1 = knots[3], knots[-4]
at = lambda t: de_boor(candidate["controls"], knots, min(u0 + t, u1))
xy = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
times = [candidate["logged_t"] * k / (candidate["logged_samples"] - 1) for k in range(candidate["logged_samples"])]
lookahead = [xy(at(t + 0.8), at(t)) for t in times]
line_9434 = {"collision_t_s": candidate["logged_t"], "samples": candidate["logged_samples"],
             "collision_from_start_xy_m": round(xy(at(candidate["logged_t"]), at(0.0)), 4),
             "lookahead_0p8s_displacement_m": {"min": round(min(lookahead), 3), "max": round(max(lookahead), 3)}}

terminal = [r for r in inside if r["terminal_point_in_obstacle"]]
record = {
    "exact_ages_within_one_callback": pairs,
    "exact_ages_over_0p25": [p for p in pairs if p["age_s"] > 0.25],
    "callback_end_lower_bound": {
        "callbacks": len(ends), "over_0p25": sum(v > 0.25 for v in ends),
        "over_0p25_plus_max_residual": sum(v > 0.25 + timeline["summary"]["clock_mapping"]["residual_max_s"] for v in ends),
        "median_s": statistics.median(ends), "max_s": max(ends)},
    "inside_obstacle": {
        "lines": len(inside), "with_terminal_point_in_obstacle": len(terminal),
        "lower_bound_over_0p25": sum(r["lower_bound_age_s"] > 0.25 for r in inside),
        "lower_bounds_with_terminal_s": sorted(r["lower_bound_age_s"] for r in terminal),
        "lower_bounds_without_terminal_s": sorted(r["lower_bound_age_s"] for r in inside if not r["terminal_point_in_obstacle"]),
        "mapped_ages_from_printed_stamp_s": [r["mapped_age_from_printed_stamp_s"] for r in inside
                                             if r["mapped_age_from_printed_stamp_s"] is not None],
        "with_terminal_goal_beyond_0p71_m": sum(r["goal_from_body_xy_m"] > 0.71 for r in terminal),
        "with_terminal_goal_beyond_0p71_min_m": min(r["goal_from_body_xy_m"] for r in terminal if r["goal_from_body_xy_m"] > 0.71),
        "with_terminal_goal_within_0p71_m": {r["line"]: r["goal_from_body_xy_m"] for r in terminal if r["goal_from_body_xy_m"] <= 0.71},
        "with_terminal_max_start_from_body_m": max(r["start_from_body_xy_m"] for r in terminal),
        "without_terminal_point": [r for r in inside if not r["terminal_point_in_obstacle"]],
        "rows": inside},
    "other_global_blocks": {"no_sensor_pose_warnings": pose_warnings,
                            "min_scan_points": min(r["sensor"]["point_count"] for r in manifest),
                            "navigation_ground_publications": tomogram_events,
                            "surface_ground_publications": surface_publications},
    "holds": {"published": len(holds), "received_3s": sum(abs(d - 3.0) < 1e-6 for _, d in received),
              "published_not_received": [h for h in holds if h not in received_ids],
              "last_received_trajectory": max(received_ids), "p2b_cancel_lines": cancel_lines},
    "live_candidate_line_9434": line_9434,
}
(audit / "scan_age_bounds.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: (v if k != "inside_obstacle" else {x: y for x, y in v.items() if x != "rows"})
                  for k, v in record.items()}, indent=2))
