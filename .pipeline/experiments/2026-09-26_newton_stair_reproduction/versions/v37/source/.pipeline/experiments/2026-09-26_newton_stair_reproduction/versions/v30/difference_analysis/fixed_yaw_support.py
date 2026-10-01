"""Explain the [FIXED_START_YAW] log differences between v29 and v30.

python3 fixed_yaw_support.py  ->  fixed_yaw_support.json

The probes print GridMap::getInflateOccupancy(start, yaw) for four fixed yaws.
That call checks circles at start +/- double_cylinder_offset (0.18 m) along
the heading. reactiveFootprintSupportQuery returns 1 unless the body cell's
nearest layer to z - body_clearance (0.3 m, within 0.12 m) and each circle
centre's nearest layer to that body ground (within 0.26 m) are unambiguous
Flat or Stair layers. This script applies that necessary condition to the
oracle labels (versions/v30/support_contract/oracle.py, which the contract
matched to the native v29 and v30 labels on all 86,775 layers). It checks
the prediction against every printed value. A passing support check does
not by itself make the occupancy 0: the obstacle decision follows it.
"""
import json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "support_contract"))
import oracle  # noqa: E402

OFFSET, BODY_CLEARANCE, BODY_TOLERANCE = 0.18, 0.3, 0.12
YAWS = (-1.994691, -1.5707963267948966, 2.54264767, -1.57547993)
NAMES = {0: "Unknown", 1: "Flat", 2: "Stair", 3: "Unsupported"}
nav = oracle.decode_f32(E / "audits/2026-09-27_pct_precision/ground_precise.f32")
evidence = oracle.decode_f32(E / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
labels = {"v29": oracle.score(nav), "v30": oracle.score(nav, evidence)}
STATES = ["control", "stopped", "z_0p35490", "z_0p3600", "z_0p3650", "z_0p3700", "z_0p3800"]
CASES = {s: (E / f"runs/v29_start_states01/{s}/probe.log", E / f"runs/v30_saved_states01/{s}/probe.log",
             E / f"runs/v30_saved_states01/{s}/result.json") for s in STATES}
for name in ("v26", "v26_repeat"):
    CASES[f"regression_{name}"] = (E / f"runs/v29_native_regression01/{name}.log", E / f"runs/v30_native_regression01/{name}.log",
                                   E / f"runs/v30_native_regression01/{name}.json")


def cell_of(x, y):
    return math.floor((x - nav.origin[0]) / nav.resolution), math.floor((y - nav.origin[1]) / nav.resolution)


def support(version, cell, target, limit):
    layers = nav.cells.get(cell)
    if layers is None:
        return {"cell": list(cell), "state": "no navigation ground"}
    best = sorted(range(len(layers)), key=lambda i: abs(layers[i] - target))
    k = best[0]
    ambiguous = len(best) > 1 and abs(abs(layers[best[1]] - target) - abs(layers[k] - target)) <= 1e-9
    if ambiguous or abs(layers[k] - target) > limit:
        return {"cell": list(cell), "state": "no unambiguous layer in reach"}
    label = labels[version][cell][k][0]
    return {"cell": list(cell), "elevation_m": round(layers[k], 4), "label": NAMES[label], "selected": label in (1, 2)}


def observed(path):
    return {float(m.group(1)): int(m.group(2))
            for m in re.finditer(r"\[FIXED_START_YAW\] yaw=(\S+) occupancy=(\d+)", path.read_text(errors="replace"))}


report, matches, total = {}, 0, 0
for case, (old_log, new_log, result) in CASES.items():
    x, y, z = json.loads(result.read_text())["start"]
    seen = {"v29": observed(old_log), "v30": observed(new_log)}
    entry = {"start": [x, y, z], "yaws": {}}
    for yaw in YAWS:
        row = {}
        for version in ("v29", "v30"):
            body = support(version, cell_of(x, y), z - BODY_CLEARANCE, BODY_TOLERANCE)
            circles = {}
            for tag, sign in (("front", 1), ("rear", -1)):
                px, py = x + sign * OFFSET * math.cos(yaw), y + sign * OFFSET * math.sin(yaw)
                circles[tag] = (support(version, cell_of(px, py), body["elevation_m"], oracle.CRIT)
                                if body.get("selected") else {"state": "body support failed"})
            passes = bool(body.get("selected")) and all(c.get("selected") for c in circles.values())
            printed = next(v for k, v in seen[version].items() if abs(k - yaw) < 1e-6)
            # A failed support check forces 1; a passed one leaves the obstacle decision.
            consistent = printed == 1 if not passes else printed in (0, 1)
            matches += consistent
            total += 1
            row[version] = {"body": body, "circles": circles, "support_check_passes": passes,
                            "printed_occupancy": printed, "consistent": consistent}
        entry["yaws"][str(yaw)] = row
    report[case] = entry
exact = sum(row[v]["printed_occupancy"] == (0 if row[v]["support_check_passes"] else 1)
            for e in report.values() for row in e["yaws"].values() for v in ("v29", "v30"))
summary = {"consistent": f"{matches}/{total}", "all_consistent": matches == total,
           "support_check_alone_predicts_printed_value": f"{exact}/{total}",
           "changed_yaws": {case: [yaw for yaw, row in e["yaws"].items()
                                   if row["v29"]["printed_occupancy"] != row["v30"]["printed_occupancy"]]
                            for case, e in report.items()},
           "support_decides_every_change": all(
               not row["v29"]["support_check_passes"] and row["v30"]["support_check_passes"]
               for e in report.values() for row in e["yaws"].values()
               if row["v29"]["printed_occupancy"] == 1 and row["v30"]["printed_occupancy"] == 0)}
(HERE / "fixed_yaw_support.json").write_text(json.dumps({"summary": summary, "cases": report}, indent=1) + "\n")
print(json.dumps(summary, indent=1))
