"""Characterize every difference between this run (scan65) and runs/v31_native_regression03 (scan64); writes
difference_analysis.json. The explanations files cite it. Adapted from runs/v34_saved_states01/difference_analysis.py:
the eleven continuation replays use the pinned grounds (navigation ground 97d2dfbd..., surface evidence raw_ground.f32),
so the same fill applies; outputs sit at the run's top level instead of per-state directories.

- Query CSVs (gen_probe's `_queries.csv`): row by row. The columns front_support_count and rear_support_count are the
  number of layers of SCAN's scored terrain in the cell under each footprint circle's centre (0.18 m ahead of and
  behind the query point along its heading). Under v34 that terrain is the navigation ground plus the guarded
  evidence floor, so each count must grow by exactly the number of layers the fill added in that cell
  (versions/v34/fill_contract/green_v34/map_added.csv, the pinned grounds, which every saved state uses). Rows whose
  other columns change are listed with their circle cells and the layers added there.
- JSON outputs: the differing fields.
- Logs, normalised as log_review.py does: the diff lines grouped by kind, with these checks:
  - reactive_collision_blocked: the same line except terrain_cells (27,278 -> 28,378, the fill's new cells);
  - near_sensor_verdict: the verdicts printed (a diagnostic that prints the first 120 voxels queried near the sensor,
    so the printed set follows the query order);
  - "A-star exact endpoint recovered": the same connector, cost and tries, with a different candidate count.
"""
from pathlib import Path
import collections, csv, difflib, importlib.util, json, math, re

P = Path(__file__).resolve().parent
OLD = P.parent / "v31_native_regression03"
E = P.parents[1]
spec = importlib.util.spec_from_file_location("log_review_norm", P / "log_review.py")
source = (P / "log_review.py").read_text().split("old_dir, new_dir, output")[0]
norm_ns = {}
exec(compile(source, str(P / "log_review.py"), "exec"), norm_ns)
norm = norm_ns["norm"]
X0, Y0, RES, OFFSET = -7.0953147888183592, -8.3368108749389656, 0.1, 0.18
added = collections.Counter()
for r in csv.DictReader((E / "versions/v34/fill_contract/green_v34/map_added.csv").open()):
    added[(int(r["ix"]), int(r["iy"]))] += 1
cell = lambda x, y: (math.floor((x - X0) / RES), math.floor((y - Y0) / RES))
COUNTS = ("front_support_count", "rear_support_count")


def circle_cells(row):
    x, y, yaw = float(row["x"]), float(row["y"]), float(row["yaw"])
    return (cell(x + OFFSET * math.cos(yaw), y + OFFSET * math.sin(yaw)),
            cell(x - OFFSET * math.cos(yaw), y - OFFSET * math.sin(yaw)))


def queries(old_path, new_path):
    a, b = list(csv.DictReader(old_path.open())), list(csv.DictReader(new_path.open()))
    out = {"rows": [len(a), len(b)], "count_only_rows": 0, "count_deltas_match_fill": 0, "count_delta_mismatches": [],
           "unchanged_rows_with_added_layers": 0, "other_changes": []}
    for i, (x, y) in enumerate(zip(a, b)):
        changed = [k for k in x if x[k] != y[k]]
        front, rear = circle_cells(y)
        expected = {"front_support_count": added[front], "rear_support_count": added[rear]}
        same_pose = all(x[k] == y[k] for k in ("kind", "t", "x", "y", "z", "yaw"))
        if same_pose:
            deltas = {k: int(y[k]) - int(x[k]) for k in COUNTS}
            if deltas == expected:
                out["count_deltas_match_fill"] += 1
            else:
                out["count_delta_mismatches"].append({"row": i, "deltas": deltas, "added": expected})
        if not changed:
            if any(expected.values()):
                out["unchanged_rows_with_added_layers"] += 1
            continue
        if set(changed) <= set(COUNTS):
            out["count_only_rows"] += 1
            continue
        out["other_changes"].append({"row": i, "kind": y["kind"], "changed": {k: [x[k], y[k]] for k in changed},
                                     "circle_cells": [list(front), list(rear)],
                                     "added_layers": [added[front], added[rear]],
                                     "body_cell": list(cell(float(y["x"]), float(y["y"]))),
                                     "added_body": added[cell(float(y["x"]), float(y["y"]))]})
    return out


def json_diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = {}
        for k in sorted(set(a) | set(b)):
            out.update(json_diff(a.get(k), b.get(k), f"{path}.{k}" if path else k))
        return out
    return {} if a == b else {path: [a, b]}


def logs(old_path, new_path):
    dropped, fills = collections.Counter(), []
    x, y = norm(old_path, collections.Counter(), []), norm(new_path, dropped, fills)
    minus = [l[1:] for l in difflib.unified_diff(x, y, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
    plus = [l[1:] for l in difflib.unified_diff(x, y, lineterm="", n=0) if l.startswith("+") and not l.startswith("+++")]
    kinds = collections.Counter()
    for side, lines in (("-", minus), ("+", plus)):
        for line in lines:
            m = re.search(r"\]: (\w+)", line) or re.search(r"^(\S+)", line)
            kinds[side + (m.group(1) if m else line[:30])] += 1
    blocked_old = [re.sub(r"terrain_cells=\d+", "terrain_cells=N", l) for l in minus if "reactive_collision_blocked" in l]
    blocked_new = [re.sub(r"terrain_cells=\d+", "terrain_cells=N", l) for l in plus if "reactive_collision_blocked" in l]
    cells_counts = sorted({re.search(r"terrain_cells=(\d+)", l).group(1) for l in minus + plus if "terrain_cells=" in l})
    recovered = lambda lines: [re.sub(r"candidates=\d+", "candidates=N", l) for l in lines if "A-star exact endpoint recovered" in l]
    verdicts = lambda lines: collections.Counter(re.search(r"verdict=(\d+)", l).group(1) for l in lines if "near_sensor_verdict" in l)
    return {"kinds": dict(kinds),
            "reactive_collision_blocked_equal_except_terrain_cells": blocked_old == blocked_new,
            "terrain_cells_values": cells_counts,
            "astar_recovered_equal_except_candidates": recovered(minus) == recovered(plus),
            "near_sensor_verdicts": {"v31": dict(verdicts(minus)), "v34": dict(verdicts(plus))},
            "evidence_floor_fill_lines": fills}


names = ["original", "expired", "v18", "v19", "v19_repeat", "v21", "v21_repeat", "v23", "v23_repeat", "v26", "v26_repeat"]
record = {"fill_added_layers": sum(added.values()), "fill_cells_with_added_layers": len(added), "states": {}}
for name in names:
    entry = {}
    for suffix in (".json", "_negatives.json", "_queries.csv"):
        f, old = P / (name + suffix), OLD / (name + suffix)
        if old.read_bytes() == f.read_bytes():
            continue
        if suffix == "_queries.csv":
            entry[f.name] = queries(old, f)
        else:
            entry[f.name] = {"differing_fields": json_diff(json.loads(old.read_text()), json.loads(f.read_text()))}
    entry[name + ".log"] = logs(OLD / (name + ".log"), P / (name + ".log"))
    record["states"][name] = entry
(P / "difference_analysis.json").write_text(json.dumps(record, indent=1) + "\n")
for state, entry in record["states"].items():
    for name, v in entry.items():
        if name.endswith("_queries.csv"):
            print(state, name, "rows", v["rows"], "count-only", v["count_only_rows"], "deltas match", v["count_deltas_match_fill"],
                  "mismatches", len(v["count_delta_mismatches"]), "other", len(v["other_changes"]))
        elif name.endswith(".log"):
            print(state, name, "blocked==", v["reactive_collision_blocked_equal_except_terrain_cells"], v["terrain_cells_values"],
                  "astar==", v["astar_recovered_equal_except_candidates"], "verdicts", v["near_sensor_verdicts"])
        elif "differing_fields" in v:
            print(state, name, list(v["differing_fields"])[:12])
