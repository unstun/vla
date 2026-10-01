"""Counterfactual navigation grounds for the corridor-entry probe. Probe inputs only: no version or run uses them.

Both pinned grounds are float32 (x, y, z, cost) records on the same 0.1 m grid (their decode origins differ by whole
cells); SCAN decodes z - 0.03 m and skips cost > 20 (GridMap::decodeReactiveGround). Written to grounds/:
- cells_fixed.f32: ground_precise.f32 with the landing-height layer (decoded 1.4189 m) of the four corridor cells
  that carry only that layer (audits/2026-09-28_v30_stop_classes/wrong_height_cells.json, cell (47, 41) among them)
  moved to the surface evidence's corridor floor in the same cell. Only z changes; the record count, x, y and cost
  stay.
- entry_filled.f32: ground_precise.f32 plus one record per corridor-entry cell (x -5.8...-4.3, y -3.9...-2.9) that the
  navigation ground lacks near the floor (in rows 47-53 the box stops 0.1 m short of the east wall's face at body
  height, x -4.198; rows 45-46 open onto the corridor, entry_geometry.json): where the navigation cell has no layer within 0.12 m of the floor band's
  height in that row (the nearest kept floor cell of the row, decoded 1.50-1.62 m) and the surface evidence has a
  layer within 0.03 m of it. The record is the cell centre, the surface evidence's encoded z and cost 16.671875
  (the highest cost PCT kept, so the cost filter passes it as it passes the kept edge cells).
- both.f32: both changes.
The decode origin (minimum x and y of kept records) must not move; the script checks this.
Usage: python3 make_grounds.py   (writes grounds/*.f32 and grounds/grounds.json)
"""
from pathlib import Path
import hashlib, json, math
import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
NAV = E / "audits/2026-09-27_pct_precision/ground_precise.f32"
SUR = E / "audits/2026-09-27_dense_static_sampling/raw_ground.f32"
WRONG = json.loads((E / "audits/2026-09-28_v30_stop_classes/wrong_height_cells.json").read_text())
RES, OFF, LIM = 0.1, 0.03, 20.0
BOX = (-5.8, -4.3, -3.9, -2.9)
EDGE_COST = 16.671875
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

nav = np.fromfile(NAV, dtype="<f4").reshape(-1, 4)
sur = np.fromfile(SUR, dtype="<f4").reshape(-1, 4)
assert np.isfinite(nav).all() and (nav[:, 3] <= LIM).all() and np.isfinite(sur).all() and (sur[:, 3] <= LIM).all()


def origin(a):
    return float(a[:, 0].min()) - RES / 2, float(a[:, 1].min()) - RES / 2


nox, noy = origin(nav)
sox, soy = origin(sur)
shift = ((nox - sox) / RES, (noy - soy) / RES)
assert all(abs(s - round(s)) < 1e-3 for s in shift), shift        # same grid, whole-cell offset
cell_of = lambda x, y, ox, oy: (math.floor((x - ox) / RES), math.floor((y - oy) / RES))
nav_cells, sur_cells = {}, {}
for k, (x, y, z, c) in enumerate(nav):
    nav_cells.setdefault(cell_of(x, y, nox, noy), []).append(k)
for k, (x, y, z, c) in enumerate(sur):
    sur_cells.setdefault(cell_of(x, y, sox, soy), []).append(k)
to_sur = lambda i, j: (i + round(shift[0]), j + round(shift[1]))
decoded = lambda a, k: float(a[k, 2]) - OFF

# cells_fixed: move each landing-only cell's 1.4189 m layer to the surface floor of the same cell.
fixed = nav.copy()
fixes = []
for row in WRONG["landing_height_only_cells"]:
    i, j = row["cell"]
    landing = [k for k in nav_cells[(i, j)] if abs(decoded(nav, k) - 1.4189) < 0.005]
    floor = [k for k in sur_cells.get(to_sur(i, j), []) if abs(decoded(sur, k) - 1.561) < 0.02]
    assert len(landing) == 1 and len(floor) == 1, (row, landing, floor)
    fixed[landing[0], 2] = sur[floor[0], 2]
    fixes.append({"cell": [i, j], "record": landing[0], "from_m": round(decoded(nav, landing[0]), 6),
                  "to_m": round(decoded(sur, floor[0]), 6)})

# entry_filled: add the surface floor where the navigation ground lacks it in the corridor-entry box.
added = []
rows = {}
for (i, j), ks in nav_cells.items():
    x, y = nox + (i + 0.5) * RES, noy + (j + 0.5) * RES
    if not (BOX[0] <= x <= BOX[1] and BOX[2] <= y <= BOX[3]):
        continue
    for k in ks:
        if 1.50 <= decoded(nav, k) <= 1.62:
            rows.setdefault(j, []).append((i, decoded(nav, k)))
for j in sorted(rows):
    for i in range(math.floor((BOX[0] - nox) / RES), math.floor((BOX[1] - nox) / RES) + 1):
        x, y = nox + (i + 0.5) * RES, noy + (j + 0.5) * RES
        if not (BOX[0] <= x <= BOX[1]):
            continue
        reference = min(rows[j], key=lambda r: abs(r[0] - i))[1]
        if any(abs(decoded(nav, k) - reference) < 0.12 for k in nav_cells.get((i, j), [])):
            continue
        candidates = [k for k in sur_cells.get(to_sur(i, j), []) if abs(decoded(sur, k) - reference) < 0.03]
        if not candidates:
            continue
        k = min(candidates, key=lambda k: abs(decoded(sur, k) - reference))
        added.append({"cell": [i, j], "centre": [round(x, 4), round(y, 4)], "z_m": round(decoded(sur, k), 6),
                      "row_reference_m": round(reference, 6), "record": [x, y, float(sur[k, 2]), EDGE_COST]})
extra = np.array([a["record"] for a in added], dtype="<f4").reshape(-1, 4)
filled = np.concatenate([nav, extra])
both = np.concatenate([fixed, extra])

out = H / "grounds"
out.mkdir(exist_ok=True)
record = {"source": {"navigation": str(NAV.relative_to(E)), "navigation_sha256": sha(NAV),
                     "surface": str(SUR.relative_to(E)), "surface_sha256": sha(SUR)},
          "cell_fixes": fixes, "entry_added": [{k: v for k, v in a.items() if k != "record"} for a in added],
          "files": {}}
for name, array in (("cells_fixed", fixed), ("entry_filled", filled), ("both", both)):
    assert origin(array) == (nox, noy), name                     # the decode origin does not move
    path = out / f"{name}.f32"
    array.astype("<f4").tofile(path)
    record["files"][name] = {"records": int(len(array)), "sha256": sha(path)}
(out / "grounds.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"fixes": fixes, "added": len(added), "files": record["files"]}, indent=1))
