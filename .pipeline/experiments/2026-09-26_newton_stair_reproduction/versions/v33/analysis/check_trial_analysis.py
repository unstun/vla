"""Synthetic check of trial_analysis.py's gap paths, written before v33's trial.

No recorded run has a flagged or terminal pose gap, so two synthetic copies of v32_historical_full01 (the Mac
trial, which ended on odom_stale at 1151.70 s of the backend's clock) remove body-pose callbacks and nothing else:
  A. every callback in the 1.0 s after 1100.0 s: expected one gap of about 1 s, flagged by both measures, exposed,
     with the commands physics received reported;
  B. every callback from 3.0 s before the stop flow's start: expected a terminal gap, flagged by measure 2, and an
     odom_stale cause classified as the backstop (trip lag about 3 s).
The other records are linked unchanged. Scratch copies go to the directory given as argument 1; the result goes to
check_trial_analysis.json beside this script.
"""
import json
from pathlib import Path
import subprocess
import sys

H = Path(__file__).resolve().parent
E = H.parents[2]
SOURCE = E / "runs/v32_historical_full01"
LINKED = ["applied_sent.jsonl", "telemetry.jsonl", "backend_states.jsonl", "artifacts/reactive_observations.jsonl"]


def make(scratch, name, keep):
    run = scratch / name
    (run / "artifacts").mkdir(parents=True, exist_ok=False)
    for rel in LINKED:
        (run / rel).symlink_to(SOURCE / rel)
    kept = removed = 0
    with open(SOURCE / "backend_body_callbacks.jsonl") as src, open(run / "backend_body_callbacks.jsonl", "w") as dst:
        for line in src:
            if not line.strip():
                continue
            if keep(json.loads(line)["entered_ns"] / 1e9):
                dst.write(line)
                kept += 1
            else:
                removed += 1
    return run, kept, removed


def analyse(run):
    out = run.parent / (run.name + "_analysis.json")
    subprocess.run([sys.executable, str(H / "trial_analysis.py"), str(run), str(out)], check=True,
                   stdout=subprocess.DEVNULL, env={"PYTHONDONTWRITEBYTECODE": "1"})
    return json.loads(out.read_text())


def main():
    scratch = Path(sys.argv[1])
    stop = 1151.702668355
    result = {}
    run, kept, removed = make(scratch, "case_a", lambda t: not 1100.0 < t < 1101.0)
    a = analyse(run)
    gap = max(a["pose_gaps"]["gaps"], key=lambda g: g["wall_s"])
    result["A"] = {"removed_callbacks": removed, "gap_wall_s": gap["wall_s"], "terminal": gap["terminal"],
                   "measure1_s": gap["measure1_sim_advance_s"], "measure2_s": gap["measure2_physics_advance_s"],
                   "flagged": gap["flagged"], "exposure": gap["exposure"]["verdict"],
                   "steps_started_inside": gap["received"]["steps_started_inside"],
                   "applied_command_kinds": len(gap["received"]["applied"]),
                   "observer_gated_command_kinds": len(gap["received"]["observer_gated_commands"]),
                   "odom_stale_classification": (a["odom_stale_cause"] or {}).get("classification")}
    run, kept, removed = make(scratch, "case_b", lambda t: t < stop - 3.0)
    b = analyse(run)
    gap = next(g for g in b["pose_gaps"]["gaps"] if g["terminal"])
    result["B"] = {"removed_callbacks": removed, "gap_wall_s": gap["wall_s"], "measure1_s": gap["measure1_sim_advance_s"],
                   "measure2_s": gap["measure2_physics_advance_s"], "flagged": gap["flagged"],
                   "exposure": gap["exposure"]["verdict"], "odom_stale_cause": b["odom_stale_cause"]}
    result["passed"] = (result["A"]["flagged"] and not result["A"]["terminal"] and 0.95 < result["A"]["gap_wall_s"] < 1.1
                        and result["A"]["measure1_s"] > 0.25 and result["A"]["measure2_s"] > 0.25
                        and result["A"]["steps_started_inside"] > 0 and result["B"]["flagged"]
                        and result["B"]["measure1_s"] is None and b["odom_stale_cause"]["classification"] == "backstop"
                        and 2.9 < b["odom_stale_cause"]["trip_lag_s"] < 3.1)
    (H / "check_trial_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
