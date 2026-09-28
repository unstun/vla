"""Judge versions/v30/PLAN.md steps 3 and 4 from this run; writes review.json.

Every state must continue with the boundary and full-curve gates and all
negatives. The landing and onset frontiers must pass v29's 8.6446 s. Start
states are compared with v29_start_states01 (result, negatives and queries,
byte for byte), and the landing states with the diagnosis audit's unchanged
baseline and probe-only oracle (every result field, negatives and queries).
Every difference from v29 or the oracle, and every log whose normalised text
differs from v29 (log_review.py, rerun here), needs an entry in
difference_explanations.json; an entry without a difference also fails. The
log comparison must be complete: at least one log, every v29 log present,
and only the landing and onset logs (no v29 counterpart here) left out.
"""
from collections import Counter
from pathlib import Path
import csv, json, re, subprocess, sys

P = Path(__file__).resolve().parent
RUNS = P.parent
AUDIT = RUNS.parent / "audits/2026-09-28_v29_landing_stall"
load = lambda path: json.loads(path.read_text())
START = ["stopped", "z_0p35490", "z_0p3600", "z_0p3650", "z_0p3700", "z_0p3800", "control"]
LANDING = ["landing", "onset"]
V29_FRONTIER = 8.6445784420074432
VERDICTS = {"6": "UnknownObstacle", "7": "StaticObstacle", "8": "UnknownSupport"}
review, passed = {"states": {}}, load(P / "execution.json")["exit_code"] == 0
differences = []
same_bytes = lambda a, b: a.read_bytes() == b.read_bytes()
for state in START + LANDING:
    d = P / state
    result, negatives = load(d / "result.json"), load(d / "result_negatives.json")
    full = result["continued"] and result["boundary_pass"] and result["full_clear"] and result["accepted_xy_displacement_m"] > 0
    entry = {"exit_code": (d / "probe_exit_code.txt").read_text().strip(), "full_gates": full, "negatives": negatives,
             "frontier_time_s": result["frontier_time_s"], "accepted_xy_displacement_m": result["accepted_xy_displacement_m"],
             "start_occupied": result["start_occupied"]}
    ok = entry["exit_code"] == "0" and full and all(negatives.values())
    if state in START:
        old = load(RUNS / "v29_start_states01" / state / "result.json")
        entry["v29_accepted_xy_displacement_m"] = old["accepted_xy_displacement_m"]
        entry["identical_to_v29"] = result == old
        entry["files_identical_to_v29"] = {name: same_bytes(d / name, RUNS / "v29_start_states01" / state / name)
                                           for name in ("result.json", "result_negatives.json", "result_queries.csv")}
        differences += [f"{state}/{name}" for name, same in entry["files_identical_to_v29"].items() if not same]
    else:
        baseline, oracle = load(AUDIT / state / "baseline.json"), load(AUDIT / f"{state}_oracle" / "result.json")
        entry["v29_frontier_time_s"], entry["v29_continued"] = baseline["frontier_time_s"], baseline["continued"]
        entry["oracle_frontier_time_s"] = oracle["frontier_time_s"]
        entry["oracle_accepted_xy_displacement_m"] = oracle["accepted_xy_displacement_m"]
        entry["fields_differing_from_oracle"] = sorted(k for k in set(result) | set(oracle) if result.get(k) != oracle.get(k))
        differences += [f"{state}.{k}" for k in entry["fields_differing_from_oracle"]]
        entry["files_identical_to_oracle"] = {name: same_bytes(d / name, AUDIT / f"{state}_oracle" / name)
                                              for name in ("result_negatives.json", "result_queries.csv")}
        differences += [f"{state}/{name}" for name, same in entry["files_identical_to_oracle"].items() if not same]
        entry["frontier_passes_v29"] = result["frontier_time_s"] > V29_FRONTIER + 1e-6
        ok = ok and entry["frontier_passes_v29"] and not baseline["continued"]
        log = (d / "breakdown.log").read_text(errors="replace")
        check = re.search(r"\[LANDING-BREAKDOWN\] frontier=(\S+) .* circle_mismatches=(\d+) sample_mismatches=(\d+) support_mismatches=(\d+)", log)
        breakdown = load(d / "breakdown.json")
        entry["breakdown_result_equals_probe"] = breakdown == result
        entry["breakdown_mismatches"] = [int(check.group(i)) for i in (2, 3, 4)] if check else None
        rows = list(csv.DictReader((d / "breakdown_breakdown.csv").open()))
        samples = {}
        for r in rows:
            samples.setdefault(r["i"], {})[r["circle"]] = r
        reasons = Counter()
        for pair in samples.values():
            front, rear = pair["front"], pair["rear"]
            if float(front["t"]) <= result["frontier_time_s"] + 1e-9:
                continue
            deciding = front if front["native_circle"] == "1" else rear
            stage = deciding["stage"]
            reasons["support" if stage.startswith("support") else VERDICTS.get(stage[8:], stage)] += 1
        entry["reasons_beyond_frontier"] = dict(reasons)
        ok = ok and entry["breakdown_result_equals_probe"] and entry["breakdown_mismatches"] == [0, 0, 0]
    entry["passed"] = ok
    passed = passed and ok
    review["states"][state] = entry
log_path = P / "log_differences_vs_v29.json"
subprocess.run([sys.executable, str(P / "log_review.py"), str(RUNS / "v29_start_states01"), str(P), str(log_path)],
               check=True, capture_output=True)
review["logs_differing_from_v29"] = sorted(load(log_path))
# Guard against an empty or partial comparison: only the landing and onset logs may lack a v29 counterpart.
logs = lambda root: {str(path.relative_to(root)) for path in root.rglob("*.log") if "build" not in path.relative_to(root).parts[0]}
v29_logs = logs(RUNS / "v29_start_states01")
review["logs_compared"] = len(logs(P) & v29_logs)
review["logs_without_v29_counterpart"] = sorted(logs(P) - v29_logs)
review["v29_logs_missing"] = sorted(v29_logs - logs(P))
complete_log_comparison = (review["logs_compared"] > 0 and not review["v29_logs_missing"] and
                           all(name.split("/")[0] in LANDING for name in review["logs_without_v29_counterpart"]))
review["complete_log_comparison"] = complete_log_comparison
differences += review["logs_differing_from_v29"]
explanations = load(P / "difference_explanations.json") if (P / "difference_explanations.json").exists() else {}
review["differences"] = sorted(differences)
review["unexplained_differences"] = sorted(k for k in differences if not explanations.get(k))
review["stale_explanations"] = sorted(set(explanations) - set(differences))
review["logs_not_compared_line_by_line"] = {
    "states": LANDING, "reason": "v29_start_states01 has no landing or onset state; their v29 references are the diagnosis "
    "audit's baseline and oracle, compared above by result files and the breakdown checks."}
passed = passed and not review["unexplained_differences"] and not review["stale_explanations"] and complete_log_comparison
review["passed"] = passed
review["physical_navigation_validated"] = False
(P / "review.json").write_text(json.dumps(review, indent=2) + "\n")
print(json.dumps({"passed": passed, **{s: {k: e[k] for k in ("passed", "frontier_time_s", "accepted_xy_displacement_m")}
                                       for s, e in review["states"].items()},
                  "differences": review["differences"], "unexplained": review["unexplained_differences"],
                  "stale": review["stale_explanations"]}, indent=1))
