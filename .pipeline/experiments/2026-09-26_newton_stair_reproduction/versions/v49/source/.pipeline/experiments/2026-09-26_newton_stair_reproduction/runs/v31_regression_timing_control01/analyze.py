"""Summarise the paired A* wall-time control (execute.py); writes summary.json.

For every repetition, build and fixture it records the exit code, whether the
JSON output equals runs/v30_native_regression01's output for that fixture, the
elapsed times of failed A* searches that dyn_a_star.cpp prints (only above
0.1 s), and the 0.2 s wall-budget failures by kind. dyn_a_star.cpp is
byte-identical in v30 and v31, and its elapsed time covers the whole
AstarSearch call on steady_clock.
"""
from pathlib import Path
import json, re, statistics

P = Path(__file__).resolve().parent
REFERENCE = P.parent / "v30_native_regression01"
FIXTURES = ["v18", "v23", "v23_repeat", "mapped_low_box", "unmapped_low_box"]
TOOK = re.compile(r"A-star path search took ([0-9.]+)s, iter=(\d+)")
BUDGET = re.compile(r"0\.2 second time limit exceeded( during [a-z ]+)?")
records = json.loads((P / "execution.json").read_text())
runs, per_build = [], {}
for record in records:
    rep = P / record["name"]
    row = {"name": record["name"], "build": record["build"], "repetition": record["repetition"],
           "container_exit_code": record["exit_code"], "fixtures": {}}
    for fixture in FIXTURES:
        log = (rep / f"{fixture}.log").read_text(errors="replace")
        output = json.loads((rep / f"{fixture}.json").read_text())
        took = [(float(t), int(i)) for t, i in TOOK.findall(log)]
        budget = {}
        for match in BUDGET.finditer(log):
            kind = (match.group(1) or " during search").strip()
            budget[kind] = budget.get(kind, 0) + 1
        row["fixtures"][fixture] = {
            "exit_code": int((rep / f"{fixture}_exit_code.txt").read_text()),
            "output_equals_v30_regression": output == json.loads((REFERENCE / f"{fixture}.json").read_text()),
            "failed_search_elapsed_s": [t for t, _ in took], "failed_search_iterations": sorted({i for _, i in took}),
            "budget_failures": budget}
        entry = per_build.setdefault(record["build"], {}).setdefault(fixture, {"equal": 0, "runs": 0, "elapsed": [],
                                                                               "budget_failures": 0})
        entry["runs"] += 1
        entry["equal"] += row["fixtures"][fixture]["output_equals_v30_regression"]
        entry["elapsed"] += [t for t, _ in took]
        entry["budget_failures"] += sum(budget.values())
    runs.append(row)
summary = {}
for build, fixtures in per_build.items():
    summary[build] = {}
    for fixture, entry in fixtures.items():
        elapsed = entry.pop("elapsed")
        summary[build][fixture] = dict(entry, printed_failed_searches=len(elapsed),
                                       elapsed_s=None if not elapsed else {
                                           "min": min(elapsed), "median": statistics.median(elapsed), "max": max(elapsed)})
out = {"all_exit_zero": all(r["container_exit_code"] == 0 and all(f["exit_code"] == 0 for f in r["fixtures"].values())
                            for r in runs),
       "by_build": summary, "runs": runs}
(P / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"all_exit_zero": out["all_exit_zero"], "by_build": summary}, indent=1))
