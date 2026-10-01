"""Replica of the rebound A*'s start adjustment in v33's first attempt, with the support half of the footprint query.

Independent review round 1, B7: only the A* exit index (58 100 49) is measured. This replica repeats, in Python,
AStar::ConvertToIndexAndAdjustStartEndPoints (path_searching/src/dyn_a_star.cpp:94-122) for the rebound segment of
v33_stand's first attempt, from control point 0 (the start) to control point 3 (the first free one after the new
collision at index 2), with the planner's pool (100 x 100 x 100, planner_manager.cpp:62), the 0.05 m map resolution
as step, the start-aligned search centre (plan_env/astar_grid_coordinates.h) and grid-snapped query points
(Index2Coord). It walks the start away from the end point in 0.05 m steps while the snapped point is occupied, until
the index leaves the pool, and reports the exit index.

"Occupied" here is only the support half of getInflateOccupancy at the path heading: the body cell of the snapped
point needs a navigation layer within 0.12 m of z - 0.30, and each footprint circle's centre (0.18 m ahead and behind
along the heading) needs a navigation layer within 0.26 m of that body ground (nearest layer; every layer counts as
selected, as the step score labels them all Flat or Stair on this map since v30). LiDAR occupancy is ignored, so the
replica can miss a block but not invent one. Natively the body verdict is part of each circle's query, so a failing
body cell fails in the front circle's query first. Writes astar_start_walk.json.
Usage: python3 astar_start_walk.py
"""
from pathlib import Path
import json, math

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
RES, STEP_SIZE, POOL, CENTRE_INDEX = 0.1, 0.05, 100, 50
TOLERANCE, STEP, CLEARANCE, OFFSET = 0.12, 0.26, 0.30, 0.18

a = np.fromfile(E / "audits/2026-09-27_pct_precision/ground_precise.f32", dtype="<f4").reshape(-1, 4)
a = a[np.isfinite(a).all(1) & (a[:, 3] <= 20.0)]
ox, oy = float(a[:, 0].min()) - RES / 2, float(a[:, 1].min()) - RES / 2
cells = {}
for x, y, z, _ in a:
    cells.setdefault((math.floor((float(x) - ox) / RES), math.floor((float(y) - oy) / RES)), []).append(float(z) - 0.03)
cell_of = lambda x, y: (math.floor((x - ox) / RES), math.floor((y - oy) / RES))


def nearest(cell, target, limit):
    layers = [z for z in cells.get(cell, []) if abs(z - target) <= limit]
    return min(layers, key=lambda z: abs(z - target)) if layers else None


def support(point, yaw):
    """The first failing element of the support half, or None."""
    body = nearest(cell_of(point[0], point[1]), point[2] - CLEARANCE, TOLERANCE)
    if body is None:
        return {"fails": "body_cell", "cell": list(cell_of(point[0], point[1]))}
    for side, sign in (("front", 1), ("rear", -1)):
        c = (point[0] + sign * OFFSET * math.cos(yaw), point[1] + sign * OFFSET * math.sin(yaw))
        layer = nearest(cell_of(*c), body, STEP)
        if layer is None or abs(layer - body) >= STEP:
            return {"fails": side + "_circle", "cell": list(cell_of(*c))}
    return None


result = json.loads((H / "v33_stand/result_state.json").read_text())
controls = [cp["xyz"] for cp in result["attempt"]["control_points"]]
start, end = np.array(controls[0]), np.array(controls[3])
centre = np.array([s + STEP_SIZE * math.floor((e - s) / (2 * STEP_SIZE) + 0.5) for s, e in zip(start, end)])


def to_index(point):
    return [int(math.floor((p - c) / STEP_SIZE + 0.5)) + CENTRE_INDEX for p, c in zip(point, centre)]


to_coord = lambda index: (np.array(index) - CENTRE_INDEX) * STEP_SIZE + centre
direction = (end - start) / np.linalg.norm(end - start)
path_yaw = math.atan2(end[1] - start[1], end[0] - start[0])
steps, point, index = [], start.copy(), to_index(start)
first = support(to_coord(index), path_yaw)
steps.append({"step": 0, "index": index, "snapped": [round(v, 4) for v in to_coord(index)], "blocked": first})
exit_index = None
if first is not None:
    while True:
        point = point - direction * STEP_SIZE
        index = to_index(point)
        if any(i < 0 or i >= POOL for i in index):
            exit_index = index
            break
        blocked = support(to_coord(index), path_yaw)
        steps.append({"step": len(steps), "index": index, "snapped": [round(v, 4) for v in to_coord(index)], "blocked": blocked})
        if blocked is None:
            break
record = {"start": controls[0], "end": controls[3], "path_yaw_deg": math.degrees(path_yaw), "centre": centre.tolist(),
          "exit_index": exit_index, "live_exit_index": [58, 100, 49], "positions_checked": len(steps),
          "all_blocked": all(s["blocked"] for s in steps),
          "first_failures": [{"from_step": s["step"], **s["blocked"]} for k, s in enumerate(steps)
                             if s["blocked"] and (k == 0 or steps[k - 1]["blocked"] is None or
                                                  steps[k - 1]["blocked"]["fails"] != s["blocked"]["fails"])],
          "x_range_m": [min(s["snapped"][0] for s in steps), max(s["snapped"][0] for s in steps)],
          "y_range_m": [min(s["snapped"][1] for s in steps), max(s["snapped"][1] for s in steps)],
          "steps": steps}
(H / "astar_start_walk.json").write_text(json.dumps(record, indent=1) + "\n")
print(json.dumps({k: v for k, v in record.items() if k != "steps"}, indent=1))
