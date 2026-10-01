"""Judge versions/v34/PLAN.md K4 (saved states) from this run; writes review.json.

Adapted from runs/v31_saved_states02/review.py. v34 adds guarded evidence floor to SCAN's copy of the navigation
ground, so outputs may differ from v31_saved_states02 (scan64) wherever the added floor changes support. Every output
that differs, and every log whose normalised text differs (log_review.py: v31's normalisation, plus dropping v34's
evidence_floor_fill lines), needs an entry in difference_explanations.json or log_difference_explanations.json, with
no stale entry. The log comparison must be complete: at least one log, and every log present in both runs.
"""
from pathlib import Path
import json, subprocess, sys

P = Path(__file__).resolve().parent
RUNS = P.parent
previous = RUNS / "v31_saved_states02"
load = lambda path: json.loads(path.read_text())
STATES = ["stopped", "z_0p35490", "z_0p3600", "z_0p3650", "z_0p3700", "z_0p3800", "control", "landing", "onset"]
review, differences = {"states": {}}, []
for state in STATES:
    old_files = sorted(x.name for x in (previous / state).iterdir() if x.is_file() and x.suffix != ".log")
    new_files = sorted(x.name for x in (P / state).iterdir() if x.is_file() and x.suffix != ".log")
    same = {name: (P / state / name).exists() and (P / state / name).read_bytes() == (previous / state / name).read_bytes()
            for name in old_files}
    differences += [f"{state}/{name}" for name, ok in same.items() if not ok]
    differences += [f"{state}/{name}" for name in new_files if name not in same]
    result = load(P / state / "result.json")
    review["states"][state] = {"files_identical_to_v31": same, "exit_code": (P / state / "probe_exit_code.txt").read_text().strip(),
                               "continued": result.get("continued"), "frontier_time_s": result.get("frontier_time_s"),
                               "accepted_xy_displacement_m": result.get("accepted_xy_displacement_m")}
explanations_path = P / "difference_explanations.json"
explanations = load(explanations_path) if explanations_path.exists() else {}
log_path = P / "log_differences_vs_v31.json"
subprocess.run([sys.executable, str(P / "log_review.py"), str(previous), str(P), str(log_path)], check=True,
               capture_output=True)
log_differences = sorted(load(log_path))
log_explanations_path = P / "log_difference_explanations.json"
log_explanations = load(log_explanations_path) if log_explanations_path.exists() else {}
logs = lambda root: {str(path.relative_to(root)) for path in root.rglob("*.log") if "build" not in path.relative_to(root).parts[0]}
compared = logs(P) & logs(previous)
review.update(outputs_differing_from_v31=differences,
              unexplained_differences=[x for x in differences if not explanations.get(x)],
              stale_difference_explanations=sorted(set(explanations) - set(differences)),
              logs_differing_from_v31=log_differences,
              unexplained_log_differences=[x for x in log_differences if not log_explanations.get(x)],
              stale_log_explanations=sorted(set(log_explanations) - set(log_differences)),
              logs_compared=len(compared), logs_without_v31_counterpart=sorted(logs(P) - logs(previous)),
              v31_logs_missing=sorted(logs(previous) - logs(P)))
review["component_scope_passed"] = bool(
    all(entry["exit_code"] == "0" for entry in review["states"].values()) and compared and
    not review["logs_without_v31_counterpart"] and not review["v31_logs_missing"] and
    not review["unexplained_differences"] and not review["stale_difference_explanations"] and
    not review["unexplained_log_differences"] and not review["stale_log_explanations"])
(P / "review.json").write_text(json.dumps(review, indent=2) + "\n")
print(json.dumps({k: v for k, v in review.items() if k != "states"}, indent=2))
