"""Measure the corridor-entry geometry that RESULT.md §6 cites (review round 2, R2-N8); writes entry_geometry.json.

Per 0.1 m row of the navigation grid (rows 40-58, y -4.34...-2.44), for columns 10-40 (x -6.09...-3.00):
- band: the navigation cells with a layer at 1.50-1.62 m, their east edge x, and the columns missing east of it;
- costs: PCT's cost of those navigation layers, west to east;
- surface: the surface-evidence cells (same grid, whole-cell offset) with a layer at 1.50-1.62 m, and the east edge x
  of the run that continues the band eastward;
- wall: LiDAR world points at body height (z 1.85-2.55 m) with x in -4.60...-3.90, from every 50th published scan of
  both trials after their first stand replan (v33 scans 222-4480, v32 scans 290-2740): the smallest x per row (the
  face nearest the band), with the number of scans that saw one;
- route: the PCT route poses in the row, and how far each lies inside the band's east edge.
Usage: python3 entry_geometry.py
"""
from pathlib import Path
import json, math
import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
RES = 0.1


def load(path):
    a = np.fromfile(path, dtype="<f4").reshape(-1, 4)
    a = a[np.isfinite(a).all(1) & (a[:, 3] <= 20.0)]
    ox, oy = float(a[:, 0].min()) - RES / 2, float(a[:, 1].min()) - RES / 2
    cells = {}
    for x, y, z, c in a:
        cells.setdefault((math.floor((float(x) - ox) / RES), math.floor((float(y) - oy) / RES)), []).append((float(z) - 0.03, float(c)))
    return cells, ox, oy


nav, nox, noy = load(E / "audits/2026-09-27_pct_precision/ground_precise.f32")
sur, sox, soy = load(E / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
di, dj = round((nox - sox) / RES), round((noy - soy) / RES)
floor_at = lambda layers: [c for z, c in layers if 1.50 <= z <= 1.62]
route = json.loads((H / "v33_stand/inputs/route.json").read_text())["data"]["path"]["poses"]
route = [(p["pose"]["position"]["x"], p["pose"]["position"]["y"], p["pose"]["position"]["z"]) for p in route]
walls = {}
scans = {"v33_historical_full01": range(222, 4481, 50), "v32_historical_full01": range(290, 2741, 50)}
for run, indices in scans.items():
    manifest = json.loads((E / "runs" / run / "sensor_manifest.json").read_text())
    for i in indices:
        with np.load(E / "runs" / run / manifest[i]["file"]) as d:
            w = d["world_points"]
        sel = w[(w[:, 2] >= 1.85) & (w[:, 2] < 2.55) & (w[:, 0] >= -4.60) & (w[:, 0] <= -3.90)]
        for x, y, _ in sel:
            j = math.floor((float(y) - noy) / RES)
            entry = walls.setdefault(j, {"min_x": math.inf, "scans": set()})
            entry["min_x"] = min(entry["min_x"], float(x))
            entry["scans"].add((run, i))
rows = {}
for j in range(40, 59):
    band = [i for i in range(10, 41) if floor_at(nav.get((i, j), []))]
    surf = [i for i in range(10, 41) if any(1.50 <= z <= 1.62 for z, _ in sur.get((i + di, j + dj), []))]
    row = {"y_range": [round(noy + j * RES, 4), round(noy + (j + 1) * RES, 4)]}
    if band:
        east = max(i for i in band if all(k in band for k in range(min(band), i + 1)))
        row["band"] = {"columns": [min(band), east], "east_edge_x": round(nox + (east + 1) * RES, 4),
                       "missing_columns_east_to_40": [i for i in range(east + 1, 41) if i not in band],
                       "costs_west_to_east": [round(floor_at(nav[(i, j)])[0], 2) for i in range(min(band), east + 1)]}
        run_end = east
        while run_end + 1 in surf:
            run_end += 1
        row["surface_run_east_edge_x"] = round(nox + (run_end + 1) * RES, 4)
    w = walls.get(j)
    row["wall_face_min_x_body_height"] = round(w["min_x"], 4) if w else None
    row["wall_scans"] = len(w["scans"]) if w else 0
    if band and w:
        row["band_east_edge_to_face_m"] = round(w["min_x"] - row["band"]["east_edge_x"], 3)
    row["route"] = [{"pose": k, "x": round(x, 4), "y": round(y, 4),
                     "inside_east_edge_m": round(row["band"]["east_edge_x"] - x, 3) if band else None}
                    for k, (x, y, z) in enumerate(route) if 1.5 < z < 2.3 and math.floor((y - noy) / RES) == j and -6.0 < x < -4.0]
    rows[j] = row
record = {"navigation_origin": [nox, noy], "surface_origin": [sox, soy], "scans_used": {r: len(s) for r, s in scans.items()},
          "rows": rows}
(H / "entry_geometry.json").write_text(json.dumps(record, indent=1) + "\n")
for j, r in rows.items():
    b = r.get("band")
    print(j, r["y_range"], "band", b["columns"] if b else None, "east", b["east_edge_x"] if b else None,
          "surface_east", r.get("surface_run_east_edge_x"), "wall", r["wall_face_min_x_body_height"], r["wall_scans"],
          "gap", r.get("band_east_edge_to_face_m"), "route", [(p["pose"], p["inside_east_edge_m"]) for p in r["route"]])
