"""Classify each clock-sync TTL window (no accepted sample for over 200 ms after convergence).

For each window, from the run's own records:
- longest gap between the client's sends inside it: the client thread did not run (starved);
- rejected samples inside it and their round trips: the client ran but its samples were rejected;
- overlapping control steps over 150 ms (telemetry `control_wall_s`), and for runs with diag_worker
  records, overlapping gaps over 100 ms between the end of one step and the start of the next.
Writes ttl_windows.json.
"""
import json
from pathlib import Path
import statistics
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
RUNS = sys.argv[1:] or ["v28_historical_full01", "v30_historical_full01", "v31_historical_full01", "diag_v31_clock03"]


def lines(path):
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    out = {}
    for name in RUNS:
        run = E / "runs" / name
        telemetry = [(r["state_sequence"], r["control_wall_s"], r["wall_s"]) for r in
                     ({k: row[k] for k in ("state_sequence", "control_wall_s", "wall_s")} for row in lines(run / "telemetry.jsonl"))]
        sent = {s["snapshot"]["state_epoch"]["state_sequence"]: s["snapshot"]["host_step_started_monotonic_ns"]
                for s in lines(run / "applied_sent.jsonl")}
        started = statistics.median(sent[q] / 1e9 + c - w for q, c, w in telemetry if q in sent)
        steps = [(started + w - c, started + w, q, c) for q, c, w in telemetry]
        freezes = []
        if (run / "diagnostics/steps.npy").exists():
            s = np.load(run / "diagnostics/steps.npy")
            ends, starts = (s[:-1, 0] + s[:-1, 1]) / 1e9, s[1:, 0] / 1e9
            freezes = [(a, b) for a, b in zip(ends, starts) if b - a > .1]
        clock = [c for c in lines(run / "clock_samples.jsonl") if "seq" in c]
        accepted = [c for c in clock if c["accepted"] and c["samples"] >= 500]
        windows = []
        for a, b in zip(accepted, accepted[1:]):
            if b["received"] - a["received"] <= 200_000_000:
                continue
            lo, hi = a["received"] / 1e9, b["received"] / 1e9
            inside = [c for c in clock if lo < c["sent"] / 1e9 < hi]
            sends = [a["sent"] / 1e9] + [c["sent"] / 1e9 for c in inside] + [b["sent"] / 1e9]
            windows.append({
                "mac_s": [lo, hi], "without_accepted_ms": round((hi - lo) * 1e3),
                "longest_send_gap_ms": round(max(np.diff(sends)) * 1e3),
                "rejected_inside": len(inside), "rejected_rtt_ms": [round(c["rtt_ns"] / 1e6, 1) for c in inside],
                "overlapping_steps_over_150ms": [[q, round(c, 3)] for x, y, q, c in steps if x < hi and y > lo and c > .15],
                "overlapping_between_step_freezes_ms": [round((y - x) * 1e3) for x, y in freezes if x < hi and y > lo],
            })
        out[name] = windows
        print(name)
        for w in windows:
            print(f"  {w['without_accepted_ms']} ms: longest send gap {w['longest_send_gap_ms']} ms, "
                  f"{w['rejected_inside']} rejected {w['rejected_rtt_ms']}, long steps {w['overlapping_steps_over_150ms']}, "
                  f"freezes {w['overlapping_between_step_freezes_ms']}")
    (H / "ttl_windows.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
