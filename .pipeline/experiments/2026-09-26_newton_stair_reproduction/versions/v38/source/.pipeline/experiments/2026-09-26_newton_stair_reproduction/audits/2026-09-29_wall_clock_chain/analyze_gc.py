"""Match logged garbage collections (diag_worker gc_events.npy) against the stalls of a diagnostic run.

- Collections: count, duration by generation, the longest ones and which thread ran them.
- In-step stalls over 150 ms and between-step gaps over 100 ms (steps.npy): the longest overlapping collection.
- Clock TTL windows (no accepted sample for over 200 ms): the longest overlapping collection.
Collections that started before the first control step (start-up) are reported separately.
Writes gc_attribution_<run>.json. Body-pose gaps are attributed by analyze_pose_gaps.py: this script's
round-1 pose-gap section mapped stamps as stamp x 1000, which MuJoCo-Warp's float32 time makes wrong by up
to 1.78 s (gc_attribution_diag_v31_clock04_round1.json keeps that output).
"""
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]


def overlapping(events, lo, hi):
    """Longest collection overlapping [lo, hi] (ns), as (duration_ms, generation, main_thread)."""
    starts, ends = events[:, 0], events[:, 0] + events[:, 1]
    mask = (starts < hi) & (ends > lo)
    if not mask.any():
        return None
    k = np.flatnonzero(mask)[np.argmax(events[mask, 1])]
    return [round(events[k, 1] / 1e6, 1), int(events[k, 2]), bool(events[k, 5])]


def main():
    name = sys.argv[1]
    run = E / "runs" / name
    gc_events = np.load(run / "diagnostics/gc_events.npy")
    steps = np.load(run / "diagnostics/steps.npy")
    substeps = np.load(run / "diagnostics/substeps.npy")
    first = steps[0, 0]
    loop = gc_events[gc_events[:, 0] >= first]
    startup = gc_events[gc_events[:, 0] < first]
    summary = {"run": name, "collections": int(len(gc_events)), "startup_collections": int(len(startup))}
    by_generation = {}
    for generation in (0, 1, 2):
        d = loop[loop[:, 2] == generation, 1] / 1e6
        by_generation[str(generation)] = None if not len(d) else {
            "count": int(len(d)), "median_ms": float(np.median(d)), "max_ms": float(d.max()),
            "over_20ms": int((d > 20).sum()), "over_50ms": int((d > 50).sum())}
    summary["loop_collections_by_generation"] = by_generation
    order = np.argsort(loop[:, 1])[::-1][:12]
    summary["longest_loop_collections"] = [
        {"started_s": round(loop[k, 0] / 1e9, 3), "duration_ms": round(loop[k, 1] / 1e6, 1),
         "generation": int(loop[k, 2]), "main_thread": bool(loop[k, 5])} for k in order]
    ends = steps[:, 0] + steps[:, 1]
    stalls = [{"kind": "in_step", "started_s": round(steps[i, 0] / 1e9, 3), "ms": round(steps[i, 1] / 1e6, 1),
               "collection": overlapping(gc_events, steps[i, 0], ends[i])}
              for i in np.flatnonzero(steps[:, 1] > 150e6)]
    gaps = steps[1:, 0] - ends[:-1]
    stalls += [{"kind": "between_steps", "started_s": round(ends[i] / 1e9, 3), "ms": round(gaps[i] / 1e6, 1),
                "collection": overlapping(gc_events, ends[i], steps[i + 1, 0])}
               for i in np.flatnonzero(gaps > 100e6)]
    summary["stalls"] = sorted(stalls, key=lambda s: s["started_s"])
    clock = [json.loads(line) for line in open(run / "clock_samples.jsonl") if '"seq"' in line]
    accepted = [c for c in clock if c["accepted"] and c["samples"] >= 500]
    windows = []
    for a, b in zip(accepted, accepted[1:]):
        if b["received"] - a["received"] > 200_000_000:
            windows.append({"started_s": round(a["received"] / 1e9, 3), "ms": round((b["received"] - a["received"]) / 1e6),
                            "collection": overlapping(gc_events, a["received"], b["received"])})
    summary["clock_ttl_windows"] = windows
    (H / f"gc_attribution_{name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "stalls"}, indent=1)[:5000])
    for s in summary["stalls"]:
        print(s)


if __name__ == "__main__":
    main()
