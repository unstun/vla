"""v34's navigation-progress analysis (PHYSICAL_RUN_PLAN.md, "What is recorded"), written before the trial.

Reads only a run's own records:
- artifacts/reactive_observations.jsonl: the PCT route (631 poses) and the body poses;
- scan.log: SCAN's lines.
Reports:
- corridor_entry: whether the body passes the corridor entry, i.e. reaches y < -3.9 at x > -4.6 on the upper floor
  (body z > 1.70 m), the corridor beyond the band where v32 and v33 stood (both stood near (-4.9, -3.4)), and the
  first sim time it does; and the longest stay within 0.25 m of any point in the entry box x -5.1...-4.7, y -3.7...-3.2
  (upper floor), with its start time and position;
- first_x_beyond_minus_4: the first sim time the body is east of x = -4.0 on the upper floor;
- farthest_route_pose: the largest route index whose pose lies within 0.5 m (XY) of a recorded body position at a
  similar height (|dz| < 0.4 m), with the sim time; whether route poses 200-207 (the corridor's east-end corner) are
  reached this way;
- final body position and the nearest route pose;
- SCAN counts: evidence_floor_fill lines (each with its counts), "The robot is inside an obstacle", "First three
  control points are in obstacles", final_spline_rejected by status, full_spline_sampled_clear, seed searches failed,
  "0.2 second time limit exceeded" (all variants), REPLAN_TRAJ-to-REPLAN_TRAJ cycles, the replan-limit line.
Usage: python3 nav_progress.py <run dir> <output json>   (writes only the named output)
"""
from pathlib import Path
import collections, json, math, re, sys

run, output = Path(sys.argv[1]), Path(sys.argv[2])
route, bodies = None, []
with (run / "artifacts/reactive_observations.jsonl").open() as f:
    for line in f:
        r = json.loads(line)
        if r["event"] == "pct_route" and route is None:
            route = [(p["pose"]["position"]["x"], p["pose"]["position"]["y"], p["pose"]["position"]["z"])
                     for p in r["data"]["path"]["poses"]]
        elif r["event"] == "body_pose_observer" and r["clock_ns"] is not None:
            p = r["data"]["pose"]["pose"]["position"]
            bodies.append((r["clock_ns"] * 1e-9, p["x"], p["y"], p["z"]))
bodies.sort()
upper = [b for b in bodies if b[3] > 1.70]
entry_pass = next((b for b in upper if b[2] < -3.9 and b[1] > -4.6), None)
beyond = next((b for b in upper if b[1] > -4.0), None)
# Longest stay: consecutive body samples within 0.25 m of the stay's first sample, inside the entry box.
best, start = None, None
for b in upper:
    in_box = -5.1 <= b[1] <= -4.7 and -3.7 <= b[2] <= -3.2
    if start is not None and (not in_box or math.hypot(b[1] - start[1], b[2] - start[2]) > 0.25):
        span = (prev[0] - start[0], start)
        best = max(best, span, key=lambda s: s[0]) if best else span
        start = None
    if in_box and start is None:
        start = b
    prev = b
if start is not None:
    span = (prev[0] - start[0], start)
    best = max(best, span, key=lambda s: s[0]) if best else span
import numpy as np
B = np.array(bodies)
farthest = (-1, None)
for i, (x, y, z) in enumerate(route):
    hit = np.nonzero((np.abs(B[:, 3] - z) < 0.4) & (np.hypot(B[:, 1] - x, B[:, 2] - y) < 0.5))[0]
    if hit.size and i > farthest[0]:
        farthest = (i, float(B[hit[0], 0]))
final = bodies[-1]
nearest_final = min(range(len(route)), key=lambda i: math.hypot(route[i][0] - final[1], route[i][1] - final[2]) + abs(route[i][2] - final[3]))
text = (run / "scan.log").read_text(errors="replace").splitlines()
fills = [list(map(int, m.groups())) for m in (re.search(r"evidence_floor_fill evidence_used=(\d) navigation_layers=(\d+) added=(\d+) drop_rejected=(\d+)", l) for l in text) if m]
rejected = collections.Counter(m.group(1) for m in (re.search(r"final_spline_rejected status=(\d+)", l) for l in text) if m)
record = {
    "run": run.name, "body_samples": len(bodies), "physics_end_s": bodies[-1][0] if bodies else None,
    "corridor_entry": {"passed": entry_pass is not None, "first_time_s": entry_pass[0] if entry_pass else None,
                       "first_xyz": list(entry_pass[1:]) if entry_pass else None,
                       "longest_stay_in_entry_box_s": best[0] if best else 0.0,
                       "longest_stay_start_s": best[1][0] if best else None,
                       "longest_stay_start_xyz": list(best[1][1:]) if best else None},
    "first_x_beyond_minus_4": {"time_s": beyond[0] if beyond else None, "xyz": list(beyond[1:]) if beyond else None},
    "farthest_route_pose": {"index": farthest[0], "time_s": farthest[1], "of": len(route),
                            "east_end_corner_200_207_reached": farthest[0] >= 200},
    "final_body": {"time_s": final[0], "xyz": list(final[1:]), "nearest_route_pose": nearest_final},
    "scan": {"evidence_floor_fill": fills,
             "inside_obstacle": sum("The robot is inside an obstacle" in l for l in text),
             "first_three_control_points": sum("First three control points are in obstacles" in l for l in text),
             "final_spline_rejected_by_status": dict(rejected),
             "full_spline_sampled_clear": sum("full_spline_sampled_clear" in l for l in text),
             "seed_search_failed": sum("reactive_stair_seed_search_failed" in l for l in text),
             "astar_time_limit": sum("0.2 second time limit exceeded" in l for l in text),
             "replan_cycles": sum(l.startswith("[FSM]: from REPLAN_TRAJ to REPLAN_TRAJ") for l in text),
             "replan_limit": sum("Replan failed" in l and "emergency stop" in l for l in text)},
}
output.write_text(json.dumps(record, indent=1) + "\n")
print(json.dumps(record, indent=1))
