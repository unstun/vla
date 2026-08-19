#!/usr/bin/env python
"""Compare edge runs against the upstream-default run and emit a markdown table.

Reports observations only. It applies no pass/fail threshold: whether a
trajectory difference is "large enough" is a research question, not something
this script decides. Usage: compare_runs.py <baseline_run> <run> [<run> ...]
"""
import json, os, sys
import numpy as np

def load(run):
    d = json.load(open(os.path.join(run, "outputs.json")))
    m = json.load(open(os.path.join(run, "meta.json")))
    return d, m, np.array(d["waypoints_raw"], dtype=np.float64)

base_run = sys.argv[1]
bd, bm, bw = load(base_run)

rows = []
for run in sys.argv[1:]:
    d, m, w = load(run)
    dif = np.abs(w - bw)
    end = w[-1, :2] - bw[-1, :2]
    rows.append({
        "run": os.path.basename(run),
        "modality": f"{d['modality_id']} ({d['modality_name']})",
        "prompt": d["language_instruction"],
        "exit": m["exit_code"],
        "wall": m["wall_seconds"],
        "rss": m["peak_rss_mib"],
        "finite": d["all_finite"],
        "shape": tuple(d["waypoints_raw_shape"]),
        "maxabs_all": dif.max(),
        "maxabs_xy": dif[:, :2].max(),
        "maxabs_head": dif[:, 2:].max(),
        "endpoint_shift_m": float(np.hypot(*end) * d["metric_waypoint_spacing"]),
        "v": d["linear_vel_limited"],
        "w": d["angular_vel_limited"],
        "fwd": d["forward_seconds"],
    })

print("| run | modality | prompt | exit | wall s | peak RSS MiB | finite | shape | max abs Δ (all) | max abs Δ (x,y) | max abs Δ (heading) | endpoint shift m | v | ω | forward s |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    tail = "baseline" if r["run"] == os.path.basename(base_run) else ""
    print(f"| `{r['run'].split('_edge_')[1]}` | {r['modality']} | `{r['prompt']}` | {r['exit']} | "
          f"{r['wall']} | {r['rss']} | {r['finite']} | {r['shape']} | "
          f"{r['maxabs_all']:.4f}{' (' + tail + ')' if tail else ''} | {r['maxabs_xy']:.4f} | "
          f"{r['maxabs_head']:.4f} | {r['endpoint_shift_m']:.4f} | "
          f"{r['v']:.6f} | {r['w']:.6f} | {r['fwd']:.3f} |")
