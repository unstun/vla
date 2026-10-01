"""Judge the red/green support contract (versions/v30/PLAN.md step 2); writes contract_results.json."""
from collections import Counter
from pathlib import Path
import csv, json, math, sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
sys.path.insert(0, str(HERE))
import oracle  # noqa: E402

LABELS = ("red_v29", "green_v30")
TARGET = (6, 1)
# The PLAN.md step-2 table: expected label of the edge cell (6, 1) for (v29, v30).
EXPECTED = {"artifact_edge": (0, 1), "evidence_step_up": (0, 2), "evidence_step_mixed": (0, 3), "sub_cell_origin_offset": (0, 1),
            "real_drop": (0, 0), "evidence_absent_there": (0, 0), "ambiguous_evidence": (0, 0), "evidence_beyond_capability": (0, 0),
            "absent_neighbours": (1, 1), "navigation_has_level": (1, 1), "no_evidence": (0, 0), "evidence_other_frame": (0, 0),
            "evidence_other_resolution": (0, 0), "evidence_empty": (0, 0), "evidence_non_finite": (0, 0)}


def parse_cases():
    cases, name = {}, None
    for line in (HERE / "cases.txt").read_text().splitlines():
        tag, *rest = line.split()
        if tag == "case":
            name = rest[0]
            cases[name] = {"mode": None, "origin": None, "nav": {}, "evidence": {}}
        elif tag == "evidence_mode":
            cases[name]["mode"] = rest[0]
        elif tag == "evidence_origin":
            cases[name]["origin"] = (float(rest[0]), float(rest[1]))
        elif tag in ("N", "E"):
            cases[name]["nav" if tag == "N" else "evidence"].setdefault((int(rest[0]), int(rest[1])), []).append(float(rest[2]))
    return cases


def evidence_for(case):
    mode = case["mode"]
    if mode == "none":
        return None
    cells = {k: list(v) for k, v in case["evidence"].items()}
    if mode == "empty":
        cells = {}
    if mode == "nan":
        cells.setdefault((0, 0), []).append(math.nan)
    return oracle.Snapshot(cells, case["origin"], 0.2 if mode == "resolution_0.2" else 0.1, "map" if mode == "frame_map" else "world")


def read_labels(path):
    labels = {}
    for r in csv.DictReader(path.open()):
        labels.setdefault(r["case"], {}).setdefault((int(r["ix"]), int(r["iy"])), []).append(
            (int(r["support"]), float(r["first_pass"]), float(r["elevation"])))
    return labels


def compare(native, expected):
    differ = 0
    for cell, layers in expected.items():
        got = native.get(cell, [])
        if len(got) != len(layers):
            differ += len(layers)
            continue
        for (label, first), (native_label, native_first, _) in zip(layers, got):
            same_first = (math.isnan(first) and math.isnan(native_first)) or abs(first - native_first) <= 1e-12
            differ += label != native_label or not same_first
    return differ + sum(len(v) for c, v in native.items() if c not in expected)


cases = parse_cases()
v29_case = {n: oracle.score(oracle.Snapshot(c["nav"]), None) for n, c in cases.items()}
v30_case = {n: oracle.score(oracle.Snapshot(c["nav"]), evidence_for(c)) for n, c in cases.items()}
nav = oracle.decode_f32(BASE / "audits/2026-09-27_pct_precision/ground_precise.f32")
evidence = oracle.decode_f32(BASE / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
v29_map, v30_map = oracle.score(nav), oracle.score(nav, evidence)
change = Counter((v29_map[c][i][0], v30_map[c][i][0]) for c in nav.cells for i in range(len(nav.cells[c])) if v29_map[c][i][0] != v30_map[c][i][0])
box = [(c, i) for c in nav.cells for i, e in enumerate(nav.cells[c])
       if -5.3 <= nav.origin[0] + c[0] * 0.1 <= -3.5 and -4.5 <= nav.origin[1] + c[1] * 0.1 <= -2.3 and 1.35 <= e <= 1.65]
results = {"oracle_map_change": {f"{a}->{b}": n for (a, b), n in sorted(change.items())},
           "oracle_landing_box": {"layers": len(box), "v29_unknown": sum(v29_map[c][i][0] == 0 for c, i in box),
                                  "v30_unknown": sum(v30_map[c][i][0] == 0 for c, i in box)}}
checks = {}
for label in LABELS:
    out = HERE / label
    step = json.loads((out / "step.json").read_text())
    native_cases = read_labels(out / "cases_labels.csv")
    native_map = read_labels(out / "map_labels.csv")["map"]
    spec, other = (v29_case, v30_case) if label == "red_v29" else (v30_case, v29_case)
    map_spec, map_other = (v29_map, v30_map) if label == "red_v29" else (v30_map, v29_map)
    per_case = {}
    for name in cases:
        index = [i for i, e in enumerate(cases[name]["nav"][TARGET])][0]
        target = native_cases[name][TARGET][index][0]
        want = EXPECTED[name][0 if label == "red_v29" else 1]
        per_case[name] = {"target_label": target, "expected": want,
                          "differ_from_own_spec": compare(native_cases[name], spec[name]),
                          "differ_from_other_spec": compare(native_cases[name], other[name])}
    orders = {o: json.loads((out / f"order_{o}.json").read_text()) for o in ("nav_first", "evidence_first")}
    exits = {p.name: p.read_text().strip() for p in out.glob("*_exit_code.txt")}
    checks[label] = {
        "exit_codes_zero": all(v == "0" for v in exits.values()) and len(exits) == 3,
        "evidence_overload_as_expected": step["evidence_overload"] == (label == "green_v30"),
        "cell_set_unchanged": step["cell_set_violations"] == 0,
        "cases_match_own_spec": all(c["differ_from_own_spec"] == 0 for c in per_case.values()),
        "case_targets_match_plan_table": all(c["target_label"] == c["expected"] for c in per_case.values()),
        "map_matches_own_spec": compare(native_map, map_spec) == 0,
        "map_differs_from_other_spec": compare(native_map, map_other) > 0,
        "map_layers": sum(len(v) for v in native_map.values()),
        "cases": per_case, "orders": orders,
    }
green, red = checks["green_v30"], checks["red_v29"]
discriminating = ["artifact_edge", "evidence_step_up", "evidence_step_mixed", "sub_cell_origin_offset"]
green["discriminating_cases_differ_from_v29"] = all(green["cases"][n]["differ_from_other_spec"] > 0 for n in discriminating)
red["discriminating_cases_differ_from_v30"] = all(red["cases"][n]["differ_from_other_spec"] > 0 for n in discriminating)
same = [n for n in cases if n not in discriminating]
green["other_cases_identical_to_v29"] = all(green["cases"][n]["differ_from_other_spec"] == 0 for n in same)
nf, ef = green["orders"]["nav_first"]["checkpoints"], green["orders"]["evidence_first"]["checkpoints"]
green["order_navigation_only_is_v29"] = nf["navigation_only"]["differ_without_evidence"] == 0
green["order_uses_evidence_after_arrival"] = all(nf[k]["differ_with_evidence"] == 0 and nf[k]["differ_without_evidence"] > 0
                                                 for k in ("navigation_then_evidence", "evidence_restored", "navigation_again"))
green["order_malformed_evidence_falls_back"] = nf["malformed_evidence"]["differ_without_evidence"] == 0
green["order_evidence_first_same_result"] = (ef["evidence_only"]["node_cells"] == 0 and ef["evidence_then_navigation"]["differ_with_evidence"] == 0
                                             and ef["evidence_then_navigation"]["digest"] == nf["navigation_then_evidence"]["digest"])
green["order_decision_copy_consistent"] = all(c["decision_differs_from_node"] == 0 and c["decision_ready"]
                                              for c in list(nf.values()) + [ef["evidence_then_navigation"]])
rnf, ref = red["orders"]["nav_first"]["checkpoints"], red["orders"]["evidence_first"]["checkpoints"]
red["order_never_uses_evidence"] = all(c["differ_without_evidence"] == 0 for c in list(rnf.values()) + [ref["evidence_then_navigation"]])
passed = all(v for item in checks.values() for k, v in item.items() if isinstance(v, bool)) and \
    results["oracle_landing_box"]["v30_unknown"] == 0 and results["oracle_landing_box"]["v29_unknown"] > 0
results.update(passed=passed, checks=checks)
(HERE / "contract_results.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps({"passed": passed, "oracle_map_change": results["oracle_map_change"], "landing_box": results["oracle_landing_box"],
                  **{label: {k: v for k, v in item.items() if isinstance(v, bool) or k == "map_layers"} for label, item in checks.items()}}, indent=1))
