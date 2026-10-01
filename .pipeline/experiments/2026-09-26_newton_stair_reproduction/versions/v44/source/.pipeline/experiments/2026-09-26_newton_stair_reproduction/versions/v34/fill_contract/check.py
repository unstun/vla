"""Judge the red/green fill contract (versions/v34/PLAN.md, K2); writes contract_results.json.

- Cases: every output layer of both builds is compared with its expectation, layer by layer in order: red must return
  the navigation input unchanged; green must equal oracle.py. Each case's designed outcome (make_cases.EXPECTATION)
  is asserted on the oracle's output as well, so a wrong oracle cannot pass a wrong native result.
- Real map: green's added layers on the pinned grounds must equal the oracle's exactly (cell and float64 height),
  with every navigation layer kept; red must add nothing.
- Node: every checkpoint of both orders must show the node's raw ground, scored terrain and decision terrain equal
  to the tree's own headers on the node's decoded inputs, and green's kept navigation ground equal to the decoded
  navigation ground. Green must have added layers after valid evidence and fewer with the entry hole; red none.
"""
from pathlib import Path
import csv, json, math, sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
sys.path.insert(0, str(HERE))
import oracle  # noqa: E402
import make_cases  # noqa: E402

LABELS = {"red_v33": False, "green_v34": True}
FLOOR, HOLE = make_cases.FLOOR, (15, 6)


def snapshot(cells_list, origin=(0.0, 0.0), resolution=0.1, frame="world"):
    cells = {}
    for x, y, z in cells_list:
        cells.setdefault((x, y), []).append(z)
    return oracle.Snapshot(cells, origin, resolution, frame)


def case_inputs(mode, origin, nav, evidence):
    navigation = snapshot(nav)
    if mode == "none":
        return navigation, None
    e = snapshot(evidence, origin, 0.2 if mode == "resolution_0.2" else 0.1, "map" if mode == "frame_map" else "world")
    if mode == "empty":
        e.cells = {}
    if mode == "nan":
        e.cells.setdefault((0, 0), []).append(math.nan)
    return navigation, e


def near_hole(x, y):
    gx, gy = max(0, abs(x - HOLE[0]) - 1) * 0.1, max(0, abs(y - HOLE[1]) - 1) * 0.1
    return gx * gx + gy * gy <= 0.35 * 0.35 + 1e-12


def designed(name, navigation, out, added):
    """The case's designed outcome, judged on an output (the oracle's or the native one)."""
    trimmed = {(x, y) for x in range(6, 21) for y in range(13)}
    at_floor = {c for c, z in added if abs(z - FLOOR) < 1e-9}
    kind = make_cases.EXPECTATION[name]
    if kind == "adds":
        return at_floor == trimmed and len(added) == len(trimmed)
    if kind == "adds_at_6_6_keeps_wrong":
        return added == [((6, 6), FLOOR)] and out[(6, 6)][0] == 1.42
    if kind == "rejects_near_hole":
        return at_floor == {c for c in trimmed if not near_hole(*c)} - {HOLE}
    if kind == "adds_all_trimmed":
        return at_floor == trimmed - {HOLE}
    if kind == "adds_none_at_floor":
        return not at_floor
    if kind == "adds_beside":
        return at_floor == trimmed and all(abs(out[c][0] - (FLOOR - 0.13)) < 1e-9 for c in trimmed)
    if kind == "adds_once":
        return at_floor == trimmed and len(added) == len(trimmed)
    if kind == "adds_shifted":
        return bool(added) and all(c[0] <= 19 and c[1] <= 11 for c, _ in added) and any(c[0] == -1 for c, _ in added)
    if kind == "unchanged":
        return not added and out == navigation.cells
    raise KeyError(kind)


def read_case_layers(path):
    layers = {}
    for r in csv.DictReader(path.open()):
        layers.setdefault(r["case"], {}).setdefault((int(r["ix"]), int(r["iy"])), []).append(float(r["elevation"]))
    return layers


results = {"cases": {}, "map": {}, "node": {}}
oracle_cases = {}
for name, spec in make_cases.CASES.items():
    navigation, evidence = case_inputs(*spec)
    out, added, rejected, used = oracle.fill(navigation, evidence)
    oracle_cases[name] = {"navigation": navigation, "out": out, "added": added, "used": used,
                          "designed": designed(name, navigation, out, added)}
nav = oracle.decode_f32(BASE / "audits/2026-09-27_pct_precision/ground_precise.f32")
evidence = oracle.decode_f32(BASE / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
map_out, map_added, map_rejected, _ = oracle.fill(nav, evidence)
results["oracle"] = {"cases_designed": {n: c["designed"] for n, c in oracle_cases.items()},
                     "map_added": len(map_added), "map_rejected": map_rejected,
                     "map_added_by_level_m": {}}
for _, z in map_added:
    key = f"{round(z, 1):.1f}"
    results["oracle"]["map_added_by_level_m"][key] = results["oracle"]["map_added_by_level_m"].get(key, 0) + 1

for label, green in LABELS.items():
    out_dir = HERE / label
    exit_codes = {p.name: p.read_text().strip() for p in out_dir.glob("*_exit_code.txt")}
    native = read_case_layers(out_dir / "cases_layers.csv")
    summaries = {r["case"]: r for r in csv.DictReader((out_dir / "cases_summary.csv").open())}
    case_results = {}
    for name, o in oracle_cases.items():
        expected = o["out"] if green else o["navigation"].cells
        got = native.get(name, {})
        equal = got.keys() == expected.keys() and all(got[c] == expected[c] for c in expected)
        added = [(c, z) for c in got for z in got[c][len(o["navigation"].cells.get(c, [])):]]
        entry = {"equals_expected": equal, "native_added": int(summaries[name]["added"]),
                 "native_evidence_used": summaries[name]["evidence_used"] == "1"}
        if green:
            entry["designed"] = designed(name, o["navigation"], got, added)
            entry["passed"] = equal and entry["designed"] and o["designed"] and entry["native_added"] == len(o["added"])
        else:
            entry["passed"] = equal and entry["native_added"] == 0 and not entry["native_evidence_used"]
        case_results[name] = entry
    fill = json.loads((out_dir / "fill.json").read_text())
    added_rows = [((int(r["ix"]), int(r["iy"])), float(r["elevation"])) for r in csv.DictReader((out_dir / "map_added.csv").open())]
    if green:
        map_passed = (fill["fill_available"] and fill["navigation_layers_changed"] == 0 and
                      sorted(added_rows) == sorted(map_added) and fill["map_added"] == len(map_added) and
                      fill["map_rejected"] == map_rejected)
    else:
        map_passed = not fill["fill_available"] and not added_rows and fill["map_added"] == 0
    node = {}
    for order in ("nav_first", "evidence_first"):
        record = json.loads((out_dir / f"order_{order}.json").read_text())
        checks = []
        for name, cp in record["checkpoints"].items():
            if "raw_differs" not in cp:
                checks.append(cp["node_raw_layers"] == 0)
                continue
            ok = cp["raw_differs"] == 0 and cp["terrain_differs"] == 0 and cp["decision_differs_from_node"] == 0
            if green:
                ok = ok and cp.get("kept_navigation_differs") == 0
            checks.append(ok)
        expected_added = record["expected_added"]
        if green:
            adds = (expected_added["none"] == 0 and expected_added["surface"] == len(map_added) and
                    0 < expected_added["holed"] < expected_added["surface"])
        else:
            adds = expected_added == {"none": 0, "surface": 0, "holed": 0}
        node[order] = {"checkpoints": len(checks), "all_equal": all(checks), "added_as_expected": adds,
                       "expected_added": expected_added, "removed_evidence_points": record["removed_evidence_points"]}
    results["cases"][label] = case_results
    results["map"][label] = {"passed": map_passed, "native": {k: fill[k] for k in (
        "fill_available", "map_added", "map_rejected", "navigation_layers_changed", "fill_ms_best_of_3", "added_step_labels")}}
    results["node"][label] = node
    results[label + "_exit_codes"] = exit_codes

results["passed"] = (all(c["passed"] for label in LABELS for c in results["cases"][label].values()) and
                     all(results["map"][label]["passed"] for label in LABELS) and
                     all(n["all_equal"] and n["added_as_expected"] for label in LABELS for n in results["node"][label].values()) and
                     all(v == "0" for label in LABELS for v in results[label + "_exit_codes"].values()) and
                     all(results["oracle"]["cases_designed"].values()))
(HERE / "contract_results.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps({"passed": results["passed"],
                  "cases_failed": {l: [n for n, c in results["cases"][l].items() if not c["passed"]] for l in LABELS},
                  "map": {l: results["map"][l]["passed"] for l in LABELS},
                  "node": {l: {o: (n["all_equal"], n["added_as_expected"]) for o, n in results["node"][l].items()} for l in LABELS},
                  "oracle_map_added": len(map_added), "oracle_map_rejected": map_rejected}, indent=1))
