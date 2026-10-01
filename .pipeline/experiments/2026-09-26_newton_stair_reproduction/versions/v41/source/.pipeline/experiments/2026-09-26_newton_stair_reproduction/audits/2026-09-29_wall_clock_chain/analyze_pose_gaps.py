"""Attribute every backend body-pose gap over 150 ms of an instrumented run (diag_worker records).

Pose stamps are MuJoCo-Warp float32 simulation time, which drifts from physics steps x 1 ms (by +1.78 s
at step 387,640 in diag_v31_clock04). Stamps are therefore mapped to physics steps by interpolating the
run's own (physics_steps, physics_time_s) telemetry pairs; the worker publishes a pose after every fifth
substep, and diagnostics/substeps.npy gives the Mac time each substep finished (= publish time).
For each gap (two consecutive backend callbacks more than 150 ms apart) it reports:
- the two poses' physics steps and whether any published pose in between never reached the backend
  (superseded: the step difference exceeds 5);
- the Mac publish times of every pose from the first to the second, and the longest interval between two
  consecutive Mac publishes: the part of the gap the worker produced. When poses were superseded, the rest
  of the gap arose after publishing;
- the backend receipt delay of the two received poses (container clock mapped to the Mac clock through the
  clock filter's offset);
- the worker's control steps overlapping the interval: the longest one, its main-thread CPU, and, summed
  over those whole steps, the process's runnable-but-waiting time (runnable - CPU, summed over threads, an
  upper bound for any one thread) and E-core share. These are in-step deltas: they do not cover time
  between steps, so when the longest gap between steps covers most of the interval ("mostly_between_steps")
  they describe the neighbouring steps, not the gap;
- the longest gap between steps, the longest logged collection (if logged), the clock client's longest send
  gap, and the external probe's worst lateness.
Label: "no_publish" when no pose was published between the two (the whole gap arose before publishing),
otherwise "superseded_after_publish" (the longest publish interval arose in the worker, the rest after it).
Writes pose_gaps_<run>.json.
"""
import bisect
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]


def main():
    name = sys.argv[1]
    run = E / "runs" / name
    pairs = []
    with open(run / "telemetry.jsonl") as f:
        for line in f:
            row = json.loads(line)
            pairs.append((row["physics_steps"], row["physics_time_s"]))
    pairs = np.asarray(pairs)
    substeps = np.load(run / "diagnostics/substeps.npy")
    steps = np.load(run / "diagnostics/steps.npy")
    gc_path = run / "diagnostics/gc_events.npy"
    gc_events = np.load(gc_path) if gc_path.exists() else None
    probe = np.load(run / "diagnostics/probe_out.npy")
    publish = {int(s): int(t + w) for t, w, _, s in substeps}
    clock = [json.loads(line) for line in open(run / "clock_samples.jsonl") if '"seq"' in line]
    sends = np.array([c["sent"] for c in clock], dtype=np.int64)
    accepted = [c for c in clock if c["accepted"]]
    received = [c["received"] for c in accepted]

    def offset(mac_ns):
        index = min(max(bisect.bisect_right(received, mac_ns) - 1, 0), len(accepted) - 1)
        return accepted[index]["filtered_offset_ns"]

    def to_step(stamp_s):
        k = min(max(np.searchsorted(pairs[:, 1], stamp_s), 1), len(pairs) - 1)
        (s0, t0), (s1, t1) = pairs[k - 1], pairs[k]
        return int(round((s0 + (stamp_s - t0) / (t1 - t0) * (s1 - s0)) / 5) * 5)

    ends = steps[:, 0] + steps[:, 1]
    callbacks = [json.loads(line) for line in open(run / "backend_body_callbacks.jsonl")]
    gaps = []
    for a, b in zip(callbacks, callbacks[1:]):
        gap_ms = (b["entered_ns"] - a["entered_ns"]) / 1e6
        if gap_ms <= 150:
            continue
        step_a, step_b = to_step(a["stamp_ns"] / 1e9), to_step(b["stamp_ns"] / 1e9)
        if step_a not in publish or step_b not in publish:
            continue
        lo, hi = publish[step_a], publish[step_b]
        linux_to_mac = offset(lo)
        inside = (steps[:, 0] < hi) & (ends > lo)
        k = np.flatnonzero(inside)
        longest = k[np.argmax(steps[k, 1])] if len(k) else None
        between = [(steps[i + 1, 0] - ends[i]) / 1e6 for i in range(len(steps) - 1)
                   if ends[i] < hi and steps[i + 1, 0] > lo]
        gc_ms = None
        if gc_events is not None:
            mask = (gc_events[:, 0] < hi) & (gc_events[:, 0] + gc_events[:, 1] > lo)
            gc_ms = round(float(gc_events[mask, 1].max()) / 1e6, 1) if mask.any() else 0.0
        i0, i1 = np.searchsorted(sends, lo), np.searchsorted(sends, hi)
        window = sends[max(i0 - 1, 0):min(i1 + 1, len(sends))]
        probe_mask = (probe[:, 0] < hi) & (probe[:, 0] + 20_000_000 + probe[:, 1] > lo)
        mac_interval = (hi - lo) / 1e6
        published = [publish[s] for s in range(step_a, step_b + 1, 5) if s in publish]
        longest_publish = float(np.diff(published).max()) / 1e6
        longest_between = max(between) if between else 0.0
        record = {
            "backend_gap_ms": round(gap_ms, 1), "physics_steps": [step_a, step_b],
            "superseded_poses": (step_b - step_a) // 5 - 1,
            "mac_publish_interval_ms": round(mac_interval, 1),
            "mac_publish_offsets_ms": [round((t - lo) / 1e6, 1) for t in published],
            "longest_mac_publish_interval_ms": round(longest_publish, 1),
            "backend_receipt_delay_ms": [round((a["entered_ns"] + linux_to_mac - lo) / 1e6, 1),
                                         round((b["entered_ns"] + linux_to_mac - hi) / 1e6, 1)],
            "label": "no_publish" if step_b - step_a == 5 else "superseded_after_publish",
            "longest_step_ms": None if longest is None else round(float(steps[longest, 1]) / 1e6, 1),
            "longest_step_main_cpu_ms": None if longest is None else round(float(steps[longest, 2]) / 1e6, 1),
            "overlapping_steps_runnable_wait_ms": round(float(np.sum(steps[k, 5] - steps[k, 3])) / 1e6, 1) if len(k) else 0.0,
            "overlapping_steps_ecore_share": round(float(1 - steps[k, 4].sum() / max(steps[k, 3].sum(), 1)), 2) if len(k) else None,
            "mostly_between_steps": bool(longest_between > .5 * mac_interval),
            "longest_between_steps_ms": round(longest_between, 1),
            "longest_collection_ms": gc_ms,
            "clock_client_longest_send_gap_ms": round(float(np.diff(window).max()) / 1e6, 1) if len(window) > 1 else None,
            "external_probe_worst_late_ms": round(float(probe[probe_mask, 1].max()) / 1e6, 1) if probe_mask.any() else None,
        }
        gaps.append(record)
    out = {"run": name, "gaps_over_150ms": gaps}
    (H / f"pose_gaps_{name}.json").write_text(json.dumps(out, indent=2) + "\n")
    for g in gaps:
        print(g)


if __name__ == "__main__":
    main()
