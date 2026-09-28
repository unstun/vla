"""Compare the near_sensor_verdict diagnostic lines of v29 and v30.

python3 near_sensor_sets.py  ->  near_sensor_sets.json

GridMap::reactiveOccupancy prints near_sensor_verdict for the first 120
distinct voxels queried within 0.8 m of the sensor (a process-wide set, in
query order). A different planner path therefore prints a different set of
voxels. This script checks, for every log pair, whether any query point
printed by both runs changed verdict or voxel class. It also lists the points
that only one run printed with a non-Free verdict.
"""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parents[2] / "runs"
PATTERN = re.compile(r"near_sensor_verdict verdict=(\d+) voxel=(\d+) q=\(([^)]*)\)")
PAIRS = {f"saved_states/{s}/probe.log": (f"v29_start_states01/{s}/probe.log", f"v30_saved_states01/{s}/probe.log")
         for s in ["control", "stopped", "z_0p35490", "z_0p3600", "z_0p3650", "z_0p3700", "z_0p3800"]}
PAIRS.update({f"regression/{n}.log": (f"v29_native_regression01/{n}.log", f"v30_native_regression01/{n}.log")
              for n in ["expired", "original", "v26", "v26_repeat"]})


def read(path):
    lines, points = 0, {}
    for match in PATTERN.finditer((RUNS / path).read_text(errors="replace")):
        lines += 1
        points.setdefault(match.group(3), set()).add((int(match.group(1)), int(match.group(2))))
    return lines, points


report = {}
for name, (old, new) in PAIRS.items():
    (old_lines, a), (new_lines, b) = read(old), read(new)
    common = set(a) & set(b)
    non_free = lambda points, keys: sorted([q, sorted(points[q])] for q in keys if any(v != 0 for v, _ in points[q]))
    report[name] = {"lines": {"v29": old_lines, "v30": new_lines}, "points": {"v29": len(a), "v30": len(b)},
                    "printed_by_both": len(common), "changed_verdict_or_voxel": sorted(q for q in common if a[q] != b[q]),
                    "only_v29_non_free": non_free(a, set(a) - set(b)), "only_v30_non_free": non_free(b, set(b) - set(a))}
summary = {"no_shared_point_changed": all(not r["changed_verdict_or_voxel"] for r in report.values()),
           "only_v29_non_free": {n: len(r["only_v29_non_free"]) for n, r in report.items() if r["only_v29_non_free"]},
           "only_v30_non_free": {n: len(r["only_v30_non_free"]) for n, r in report.items() if r["only_v30_non_free"]}}
(HERE / "near_sensor_sets.json").write_text(json.dumps({"summary": summary, "logs": report}, indent=1) + "\n")
print(json.dumps(summary, indent=1))
