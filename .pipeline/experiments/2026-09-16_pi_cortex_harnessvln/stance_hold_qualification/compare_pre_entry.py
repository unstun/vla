#!/usr/bin/env python3
"""Pre-entry determinism check for reused hold-off baselines (task 09-17-isaac-runner-stance-hold, PRD D6).

A hold-on run and the hold-off baseline use the same seed, scene and command script, so until the hold first takes
the joints (the first STAND_TRANSITION row) both should record the same rows. This compares every row before that
point, matched by `step`, and reports the largest absolute differences. It is a reported item without a threshold.

    compare_pre_entry.py --baseline RUN_DIR --run RUN_DIR [--run ...] --output OUT.json
"""
import argparse
import json
from pathlib import Path

FIELDS = ("base_xyz", "base_quat_wxyz", "yaw_rate_radps", "joint_pos", "joint_vel", "admitted_command")


def load_rows(run_dir):
    path = Path(run_dir) / "returned_artifacts/runner_output/metrics.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def as_list(value):
    return value if isinstance(value, list) else [value]


def compare(baseline_rows, rows):
    first_entry = next((r for r in rows if r.get("stance_mode") == "STAND_TRANSITION"), None)
    limit_step = first_entry["step"] if first_entry is not None else None
    base_by_step = {r["step"]: r for r in baseline_rows}
    diffs = {name: 0.0 for name in FIELDS}
    compared = 0
    missing = 0
    time_diff = 0.0
    for row in rows:
        if limit_step is not None and row["step"] >= limit_step:
            break
        base = base_by_step.get(row["step"])
        if base is None:
            missing += 1
            continue
        compared += 1
        time_diff = max(time_diff, abs(row["sim_time_s"] - base["sim_time_s"]))
        for name in FIELDS:
            a, b = as_list(row[name]), as_list(base[name])
            if len(a) != len(b):
                raise ValueError("field %s has different lengths at step %s" % (name, row["step"]))
            diffs[name] = max([diffs[name]] + [abs(float(x) - float(y)) for x, y in zip(a, b)])
    return {
        "first_entry_step": limit_step,
        "first_entry_sim_time_s": None if first_entry is None else first_entry["sim_time_s"],
        "rows_compared": compared,
        "rows_missing_in_baseline": missing,
        "max_abs_sim_time_difference_s": time_diff,
        "max_abs_difference": diffs,
        "identical": missing == 0 and time_diff == 0.0 and all(v == 0.0 for v in diffs.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline_rows = load_rows(args.baseline)
    report = {
        "purpose": __doc__.strip().splitlines()[0],
        "baseline": str(args.baseline),
        "fields": list(FIELDS),
        "threshold": None,
        "runs": {str(run): compare(baseline_rows, load_rows(run)) for run in args.run},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for run, item in report["runs"].items():
        print(Path(run).name, "identical" if item["identical"] else "DIFFERENT", item["rows_compared"], "rows",
              json.dumps(item["max_abs_difference"]))


if __name__ == "__main__":
    main()
