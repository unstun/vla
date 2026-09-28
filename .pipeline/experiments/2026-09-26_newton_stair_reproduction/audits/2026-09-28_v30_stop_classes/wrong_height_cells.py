"""Find upper-corridor navigation-ground cells without the corridor floor layer.

Decodes both pinned grounds as GridMap::decodeReactiveGround does (0.1 m cells,
origin = min kept point - res/2, z - 0.03 m, points with cost > 20 skipped).
In the box x -5.3..0, y -4.7..-3.8, a cell counts when the surface evidence has
the 1.561 m floor there. It reports navigation cells that carry only the
1.419 m landing height and cells with no layer within 0.12 m of the floor,
with the distance of each cell centre to the PCT route polyline (segments
between consecutive route poses) and to the nearest route vertex. Also reports
how far the reproduced live rejections' first colliding samples sit above
that cell's exact landing-height layer + 0.30 m (tolerance 0.12 m). Writes wrong_height_cells.json.

Usage: python3 wrong_height_cells.py <experiment root> <audit dir>
"""
import json, math, sys
from pathlib import Path
import numpy as np

base, audit = Path(sys.argv[1]), Path(sys.argv[2])


def load(path, res=0.1, off=0.03, lim=20.0):
    a = np.fromfile(path, dtype="<f4").reshape(-1, 4)
    a = a[np.isfinite(a).all(1) & (a[:, 3] <= lim)]
    ox, oy = float(a[:, 0].min()) - res / 2, float(a[:, 1].min()) - res / 2
    cells = {}
    for x, y, z, _ in a:
        cells.setdefault((math.floor((x - ox) / res), math.floor((y - oy) / res)), []).append(float(z) - off)
    return cells, ox, oy


nav, nox, noy = load(base / "audits/2026-09-27_pct_precision/ground_precise.f32")
sur, sox, soy = load(base / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
route = None
with (base / "runs/v30_historical_full01/artifacts/reactive_observations.jsonl").open() as f:
    for line in f:
        record = json.loads(line)
        if record["event"] == "pct_route":
            route = [(p["pose"]["position"]["x"], p["pose"]["position"]["y"]) for p in record["data"]["path"]["poses"]]
            break


def polyline_distance(x, y):
    best = float("inf")
    for (ax, ay), (bx, by) in zip(route, route[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


landing_only, no_floor, total = [], [], 0
for (i, j), zs in sorted(nav.items()):
    x, y = nox + (i + 0.5) * 0.1, noy + (j + 0.5) * 0.1
    if not (-5.3 <= x <= 0.0 and -4.7 <= y <= -3.8):
        continue
    surface = sur.get((math.floor((x - sox) / 0.1), math.floor((y - soy) / 0.1)), [])
    if not any(abs(z - 1.561) < 0.03 for z in surface):
        continue
    total += 1
    if any(abs(z - 1.561) < 0.12 for z in zs):
        continue
    row = {"cell": [i, j], "centre": [round(x, 3), round(y, 3)], "layers": sorted(round(z, 3) for z in zs),
           "route_polyline_m": round(polyline_distance(x, y), 3),
           "route_vertex_m": round(min(math.hypot(x - a, y - b) for a, b in route), 3)}
    (landing_only if any(abs(z - 1.419) < 0.01 for z in zs) else no_floor).append(row)

offsets = []
summary = json.loads((audit / "candidates_summary.json").read_text())
for rows in summary["live_status1"]["per_state"].values():
    for r in rows:
        if r.get("reproduced") and r.get("cause") == "support_body_verdict_10":
            x, y, z = r["sample"]
            cell = (math.floor((x - nox) / 0.1), math.floor((y - noy) / 0.1))
            layer = min(nav[cell], key=lambda v: abs(v - 1.419))  # exact landing-height layer of this cell
            offsets.append({"cell": list(cell), "layer_m": round(layer, 6), "above_layer_plus_0p30_m": round(z - 0.30 - layer, 6)})
cells_hit = sorted({tuple(o["cell"]) for o in offsets})
record = {
    "corridor_cells_with_surface_floor": total,
    "landing_height_only_cells": landing_only,
    "cells_without_floor_layer": len(no_floor),
    "cells_without_floor_layer_rows": no_floor,
    "reproduced_wrongheight_rejections": len(offsets),
    "their_cells": [list(c) for c in cells_hit],
    "their_layer_m": sorted({o["layer_m"] for o in offsets}),
    "their_offset_above_layer_plus_0p30_m": {"min": min(o["above_layer_plus_0p30_m"] for o in offsets),
                                             "max": max(o["above_layer_plus_0p30_m"] for o in offsets)} if offsets else None,
}
(audit / "wrong_height_cells.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: v for k, v in record.items() if k != "cells_without_floor_layer_rows"}, indent=2))
