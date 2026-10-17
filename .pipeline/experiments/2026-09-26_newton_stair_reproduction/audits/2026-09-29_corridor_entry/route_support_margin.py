"""Static screen of footprint support along the whole PCT route, with the pinned and the counterfactual grounds.

An approximation of the support half of SCAN's footprint query (reactiveFootprintSupportQuery plus decide's height
match), for screening only; the replays are the evidence. It ignores the LiDAR occupancy and the step scores' support
status (every layer counts as selected), so it can only miss blocks, not invent them.
For each route pose (x, y, z = body reference):
- body: the navigation cell under the pose must have a layer within 0.12 m of z - 0.30 (body_height_tolerance);
- heading theta is supported when both circle centres (pose +- 0.18 m along theta) lie over cells with a layer within
  0.26 m (the step) of the body ground and the nearest such layer is within 0.26 m of it.
Reported per ground: poses whose body cell fails; poses where the route's own heading is unsupported; and the free
heading window around the route heading (degrees each way, at 1 degree steps), with the poses where it is below 30.
Grounds: pinned, cells_fixed, entry_filled, both (make_grounds.py), and "surface fallback": the pinned navigation
ground with the pinned surface evidence's layers used wherever the navigation cell has no layer that matches (a rough
model of a code-level fallback).
Usage: python3 route_support_margin.py   (writes route_support_margin.json)
"""
from pathlib import Path
import json, math
import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
RES, OFF, LIM = 0.1, 0.03, 20.0
TOL, STEP, CLEAR, OFFSET = 0.12, 0.26, 0.30, 0.18


def load(path):
    a = np.fromfile(path, dtype="<f4").reshape(-1, 4)
    a = a[np.isfinite(a).all(1) & (a[:, 3] <= LIM)]
    ox, oy = float(a[:, 0].min()) - RES / 2, float(a[:, 1].min()) - RES / 2
    cells = {}
    for x, y, z, _ in a:
        cells.setdefault((math.floor((x - ox) / RES), math.floor((y - oy) / RES)), []).append(float(z) - OFF)
    return cells, ox, oy


def nearest(layers, target, limit):
    best = [z for z in layers if abs(z - target) <= limit]
    return min(best, key=lambda z: abs(z - target)) if best else None


route = json.loads((H / "v33_stand/inputs/route.json").read_text())["data"]["path"]["poses"]
poses = [(p["pose"]["position"]["x"], p["pose"]["position"]["y"], p["pose"]["position"]["z"]) for p in route]
surface, sox, soy = load(E / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
grounds = {"pinned": E / "audits/2026-09-27_pct_precision/ground_precise.f32"}
grounds.update({g: H / f"grounds/{g}.f32" for g in ("cells_fixed", "entry_filled", "both")})
report = {}
for name, path in list(grounds.items()) + [("surface_fallback", grounds["pinned"])]:
    nav, ox, oy = load(path)

    def layers(x, y, target, limit):
        cell = (math.floor((x - ox) / RES), math.floor((y - oy) / RES))
        z = nearest(nav.get(cell, []), target, limit)
        if z is None and name == "surface_fallback":
            z = nearest(surface.get((math.floor((x - sox) / RES), math.floor((y - soy) / RES)), []), target, TOL)
        return z

    body_fail, heading_fail, narrow, rows = [], [], [], []
    for k, (x, y, z) in enumerate(poses):
        if z < 1.3:          # lower floor and lower flight: outside the upper-floor screen
            continue
        nxt = poses[min(k + 1, len(poses) - 1)]
        prv = poses[max(k - 1, 0)]
        route_yaw = math.atan2(nxt[1] - prv[1], nxt[0] - prv[0])
        body = layers(x, y, z - CLEAR, TOL)
        if body is None:
            body_fail.append(k)
            continue
        free = []
        for d in range(360):
            t = math.radians(d)
            ok = True
            for s in (1, -1):
                fz = layers(x + s * OFFSET * math.cos(t), y + s * OFFSET * math.sin(t), body, STEP)
                if fz is None or abs(fz - body) >= STEP:
                    ok = False
                    break
            free.append(ok)
        r0 = round(math.degrees(route_yaw)) % 360
        if not free[r0]:
            heading_fail.append(k)
            continue
        width = 0
        while width < 180 and free[(r0 + width + 1) % 360] and free[(r0 - width - 1) % 360]:
            width += 1
        rows.append({"pose": k, "xy": [round(x, 3), round(y, 3)], "route_yaw_deg": r0, "window_deg": width})
        if width < 30:
            narrow.append({"pose": k, "xy": [round(x, 3), round(y, 3)], "window_deg": width})
    report[name] = {"upper_poses": len(rows) + len(body_fail) + len(heading_fail),
                    "body_cell_fails": [{"pose": k, "xy": [round(poses[k][0], 3), round(poses[k][1], 3)]} for k in body_fail],
                    "route_heading_unsupported": [{"pose": k, "xy": [round(poses[k][0], 3), round(poses[k][1], 3)]} for k in heading_fail],
                    "narrow_window_below_30deg": narrow}
(H / "route_support_margin.json").write_text(json.dumps(report, indent=1) + "\n")
for name, r in report.items():
    print(name, "upper poses", r["upper_poses"], "body fails", len(r["body_cell_fails"]),
          "route heading unsupported", len(r["route_heading_unsupported"]), "narrow(<30)", len(r["narrow_window_below_30deg"]))
    for key in ("body_cell_fails", "route_heading_unsupported", "narrow_window_below_30deg"):
        if r[key]:
            print("  ", key, r[key][:12])
