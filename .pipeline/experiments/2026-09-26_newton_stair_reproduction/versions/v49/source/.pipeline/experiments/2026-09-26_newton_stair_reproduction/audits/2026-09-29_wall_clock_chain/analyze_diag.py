"""Attribute slow control steps of a diagnostic run (diag_worker.py records) to their causes.

Per control step (diagnostics/steps.npy): wall time, main-thread CPU, process CPU, the part of it on
performance cores, runnable time (includes running) and page-ins. Derived:
- main_offcpu = wall - main-thread CPU: time the physics thread did not run;
- os_wait = runnable - process CPU: summed over all threads, time runnable but not given a CPU;
- other_cpu = process CPU - main-thread CPU: CPU used by the other threads during the step.
A slow step's main_offcpu is split into an OS part, min(os_wait, main_offcpu), and the rest, which is
time the main thread was blocked inside the process (GIL, lock or I/O) while not runnable to the OS.
Also reports the E-core share of process CPU, the scan-cycle position of slow steps, the longest
substeps, and the run's clock-sync rejections and TTL windows.
"""
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]


def main():
    name = sys.argv[1]
    run = E / "runs" / name
    steps = np.load(run / "diagnostics/steps.npy")
    started, wall, main_cpu, proc_cpu, pcore, runnable, pageins, physics = steps.T
    control = physics >= 0
    wall_ms, main_ms = wall / 1e6, main_cpu / 1e6
    other_ms, wait_ms, pcore_ms, proc_ms = (proc_cpu - main_cpu) / 1e6, (runnable - proc_cpu) / 1e6, pcore / 1e6, proc_cpu / 1e6
    offcpu = wall_ms - main_ms
    os_part = np.minimum(np.maximum(wait_ms, 0), offcpu)
    inner_part = offcpu - os_part
    index = np.round(physics / 20).astype(int)

    def stats(values):
        return {"median": float(np.median(values)), "p90": float(np.quantile(values, .9)),
                "p99": float(np.quantile(values, .99)), "max": float(values.max())}

    slow = wall_ms > 100
    rows = []
    for i in np.flatnonzero(slow):
        rows.append({"physics_steps": int(physics[i]), "control_index": int(index[i]), "scan_phase": int(index[i] % 5),
                     "wall_ms": round(float(wall_ms[i]), 1), "main_cpu_ms": round(float(main_ms[i]), 1),
                     "other_cpu_ms": round(float(other_ms[i]), 1), "os_wait_ms": round(float(wait_ms[i]), 1),
                     "ecore_share": round(float(1 - pcore_ms[i] / proc_ms[i]), 2) if proc_ms[i] > 0 else None,
                     "main_offcpu_ms": round(float(offcpu[i]), 1), "os_part_ms": round(float(os_part[i]), 1),
                     "in_process_part_ms": round(float(inner_part[i]), 1), "pageins": int(pageins[i])})
    fast = wall_ms <= 60
    summary = {
        "run": name, "control_steps": int(len(wall)),
        "wall_ms": stats(wall_ms), "main_cpu_ms": stats(main_ms),
        "over_100ms": int(slow.sum()), "over_150ms": int((wall_ms > 150).sum()), "over_250ms": int((wall_ms > 250).sum()),
        "fast_steps_median": {"wall_ms": float(np.median(wall_ms[fast])), "main_cpu_ms": float(np.median(main_ms[fast])),
                              "ecore_share": float(np.median(1 - pcore_ms[fast] / np.maximum(proc_ms[fast], 1e-9)))},
        "slow_steps_totals": {"main_offcpu_ms": float(offcpu[slow].sum()), "os_part_ms": float(os_part[slow].sum()),
                              "in_process_part_ms": float(inner_part[slow].sum())},
        "slow_steps_by_scan_phase": {str(k): int(sum(1 for r in rows if r["scan_phase"] == k)) for k in range(5)},
        "pageins_total": int(pageins.sum()),
        "slow_steps": rows,
    }
    substeps = np.load(run / "diagnostics/substeps.npy")
    if len(substeps):
        sub_wall, sub_cpu = substeps[:, 1] / 1e6, substeps[:, 2] / 1e6
        order = np.argsort(sub_wall)[::-1][:10]
        summary["substeps"] = {"count": int(len(substeps)), "wall_ms": stats(sub_wall),
                               "longest": [{"physics_steps": int(substeps[i, 3]), "wall_ms": round(float(sub_wall[i]), 1),
                                            "main_cpu_ms": round(float(sub_cpu[i]), 1)} for i in order]}
    clock = [json.loads(line) for line in open(run / "clock_samples.jsonl") if '"seq"' in line]
    accepted = [c for c in clock if c["accepted"]]
    gaps = [(b["received"] - a["received"]) / 1e6 for a, b in zip(accepted, accepted[1:]) if a["samples"] >= 500]
    summary["clock"] = {"samples": len(clock),
                        "rejected_after_convergence": sum(1 for c in clock if not c["accepted"] and c["samples"] >= 500),
                        "longest_gaps_between_accepted_ms": sorted(round(g) for g in gaps)[-5:],
                        "windows_over_200ms": sum(g > 200 for g in gaps)}
    result = json.loads((run / "result.json").read_text()) if (run / "result.json").exists() else {}
    summary["command_transport"] = result.get("command_transport")
    out = H / f"diag_attribution_{name}.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("slow_steps",)}, indent=1)[:4000])
    for r in rows[:40]:
        print(r)


if __name__ == "__main__":
    main()
