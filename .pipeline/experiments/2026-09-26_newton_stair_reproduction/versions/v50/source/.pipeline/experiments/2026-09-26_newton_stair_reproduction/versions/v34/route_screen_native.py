"""The corridor-entry audit's static route screen (audits/2026-09-29_corridor_entry/route_support_margin.py's method),
recomputed with the pinned navigation ground plus the layers scan65's fill actually adds (fill_contract/green_v34/
map_added.csv), for PLAN.md's offline-effect statements. Same approximation and blind spots as the audit's screen.
Writes route_screen_native.json. Usage: python3 route_screen_native.py
"""
from pathlib import Path
import csv, json, math
import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
RES, TOL, STEP, OFFSET = 0.1, 0.12, 0.26, 0.18
a = np.fromfile(E / "audits/2026-09-27_pct_precision/ground_precise.f32", dtype="<f4").reshape(-1, 4)
a = a[np.isfinite(a).all(1) & (a[:, 3] <= 20.0)]
ox, oy = float(a[:, 0].min()) - RES / 2, float(a[:, 1].min()) - RES / 2
cells = {}
for x, y, z, _ in a:
    cells.setdefault((math.floor((float(x) - ox) / RES), math.floor((float(y) - oy) / RES)), []).append(float(z) - 0.03)
added = 0
for r in csv.DictReader((H / "fill_contract/green_v34/map_added.csv").open()):
    cells.setdefault((int(r["ix"]), int(r["iy"])), []).append(float(r["elevation"]))
    added += 1
route = json.loads((E / "audits/2026-09-29_corridor_entry/v33_stand/inputs/route.json").read_text())["data"]["path"]["poses"]
poses = [(p["pose"]["position"]["x"], p["pose"]["position"]["y"], p["pose"]["position"]["z"]) for p in route]
cell = lambda x, y: (math.floor((x - ox) / RES), math.floor((y - oy) / RES))


def near(c, target, limit):
    layers = [z for z in cells.get(c, []) if abs(z - target) <= limit]
    return min(layers, key=lambda z: abs(z - target)) if layers else None


narrow, upper = [], 0
for k, (x, y, z) in enumerate(poses):
    if z < 1.3:
        continue
    upper += 1
    nxt, prv = poses[min(k + 1, len(poses) - 1)], poses[max(k - 1, 0)]
    r0 = round(math.degrees(math.atan2(nxt[1] - prv[1], nxt[0] - prv[0]))) % 360
    body = near(cell(x, y), z - 0.30, TOL)
    if body is None:
        narrow.append({"pose": k, "fails": "body"})
        continue
    free = []
    for d in range(360):
        t = math.radians(d)
        ok = True
        for s in (1, -1):
            fz = near(cell(x + s * OFFSET * math.cos(t), y + s * OFFSET * math.sin(t)), body, STEP)
            if fz is None or abs(fz - body) >= STEP:
                ok = False
                break
        free.append(ok)
    if not free[r0]:
        narrow.append({"pose": k, "fails": "route_heading"})
        continue
    w = 0
    while w < 180 and free[(r0 + w + 1) % 360] and free[(r0 - w - 1) % 360]:
        w += 1
    if w < 30:
        narrow.append({"pose": k, "window_deg": w, "xy": [round(x, 3), round(y, 3)]})
entry_rows = {}
for j in range(43, 54):
    cols = sorted(i for i in range(10, 40) if any(1.50 <= zz <= 1.62 for zz in cells.get((i, j), [])))
    entry_rows[j] = [round(ox + cols[0] * RES, 4), round(ox + (cols[-1] + 1) * RES, 4)]
record = {"added_layers": added, "upper_poses": upper, "narrow_below_30deg": len(narrow),
          "narrow_in_entry_group_79_96": [n for n in narrow if 79 <= n["pose"] <= 96],
          "entry_band_rows_43_53_x": entry_rows, "narrow": narrow}
(H / "route_screen_native.json").write_text(json.dumps(record, indent=1) + "\n")
print({k: v for k, v in record.items() if k != "narrow"})
