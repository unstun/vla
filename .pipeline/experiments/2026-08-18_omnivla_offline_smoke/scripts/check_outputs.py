#!/usr/bin/env python
"""Validate one edge run directory against the acceptance criteria (AC5).

Checks only what the upstream code itself defines; it invents no threshold.
    shape (8, 4)                          - len_traj_pred=8, [x, y, hx, hy]
    all values finite
    0 <= v <= 0.5, -1 <= w <= 1           - the PD clip in run_omnivla_edge.py
    |v| <= 0.3, |w| <= 0.3                - the velocity limiter (maxv, maxw)
    heading unit norm hx^2 + hy^2 ~ 1     - F.normalize in model_omnivla_edge.py
    output figure exists and is > 10 KB
Usage: check_outputs.py <run_dir> [<run_dir> ...]
"""
import json, math, os, sys

def check(run):
    fails, notes = [], []
    op = os.path.join(run, "outputs.json")
    if not os.path.isfile(op):
        return ["outputs.json missing"], []
    d = json.load(open(op))

    wp = d["waypoints_raw"]
    if [len(wp), len(wp[0])] != [8, 4]:
        fails.append(f"shape {[len(wp), len(wp[0])]} != [8, 4]")
    flat = [v for row in wp for v in row]
    if not all(math.isfinite(v) for v in flat):
        fails.append("non-finite value in waypoints_raw")
    if not d.get("all_finite"):
        fails.append("all_finite flag is False")

    v, w = d["linear_vel_pd_clipped"], d["angular_vel_pd_clipped"]
    if not (math.isfinite(v) and math.isfinite(w)):
        fails.append("non-finite (v, w) after PD clip")
    if not (0.0 <= v <= 0.5):
        fails.append(f"v={v} outside the script's clip [0, 0.5]")
    if not (-1.0 <= w <= 1.0):
        fails.append(f"w={w} outside the script's clip [-1, 1]")

    vl, wl = d["linear_vel_limited"], d["angular_vel_limited"]
    if abs(vl) > 0.3 + 1e-9:
        fails.append(f"limited v={vl} exceeds maxv=0.3")
    if abs(wl) > 0.3 + 1e-9:
        fails.append(f"limited w={wl} exceeds maxw=0.3")

    for i, row in enumerate(wp):
        n = math.hypot(row[2], row[3])
        if abs(n - 1.0) > 1e-3:
            fails.append(f"waypoint {i} heading norm {n:.6f} != 1")

    imgs = [f for f in os.listdir(run) if f.endswith(".jpg")]
    if not imgs:
        fails.append("no output figure")
    else:
        for f in imgs:
            sz = os.path.getsize(os.path.join(run, f))
            if sz <= 10240:
                fails.append(f"{f} is only {sz} B (<= 10 KB)")
            else:
                notes.append(f"figure {f}: {sz} B")

    meta = os.path.join(run, "meta.json")
    if os.path.isfile(meta):
        m = json.load(open(meta))
        if m.get("exit_code") != 0:
            fails.append(f"exit_code {m.get('exit_code')} != 0")
        notes.append(f"exit={m.get('exit_code')} wall={m.get('wall_seconds')}s "
                     f"peak_rss={m.get('peak_rss_mib')} MiB")
    else:
        fails.append("meta.json missing")

    notes.append(f"modality={d['modality_id']} ({d['modality_name']}) "
                 f"prompt={d['language_instruction']!r} "
                 f"v={vl:.6f} w={wl:.6f} forward={d['forward_seconds']:.3f}s")
    return fails, notes

rc = 0
for run in sys.argv[1:]:
    fails, notes = check(run)
    print(f"\n=== {os.path.basename(run)} ===")
    for n in notes:
        print("  .", n)
    if fails:
        rc = 1
        for f in fails:
            print("  FAIL:", f)
    else:
        print("  ALL CHECKS PASSED")
sys.exit(rc)
