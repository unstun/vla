"""Clock-client pauses as a stand-in for process-wide freezes in runs without the diagnostic worker.

Post-trial analysis for v32's RESULTS.md (not part of v32's change or its pre-registered judge). The clock-sync
client thread sends a sample every 20 ms and does nothing else, so a long pause between its sends means it did not
run: either another thread held the GIL (mechanism A) or the process waited for a CPU (mechanism B). The pause alone
cannot tell the two apart; in the instrumented runs the watchdog and rusage records do (l1/evaluate_l1.py).
For each run:
- every pause between consecutive sends longer than 150 ms;
- every control step over 150 ms (telemetry control_wall_s, aligned to the host clock as in
  audits/2026-09-29_wall_clock_chain/ttl_windows.py), and the share of it covered by the longest overlapping pause.
  A step whose pause covers at least 80% of it is counted as "clock stopped for the step".
Usage: python3 clock_pause_signature.py [<run> ...]; writes clock_pause_signature.json next to this script.
"""
import json
from pathlib import Path
import statistics
import sys

H = Path(__file__).resolve().parent
E = H.parents[1]
RUNS = sys.argv[1:] or ["v31_historical_full01", "diag_v31_clock03", "diag_v31_clock04", "diag_v32_clock01",
                        "v32_historical_full01"]


def lines(path):
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def summarize(name):
    run = E / "runs" / name
    telemetry = [(r["state_sequence"], r["control_wall_s"], r["wall_s"]) for r in lines(run / "telemetry.jsonl")]
    sent = {s["snapshot"]["state_epoch"]["state_sequence"]: s["snapshot"]["host_step_started_monotonic_ns"]
            for s in lines(run / "applied_sent.jsonl")}
    started = statistics.median(sent[q] / 1e9 + c - w for q, c, w in telemetry if q in sent)
    sends = sorted(c["sent"] / 1e9 for c in lines(run / "clock_samples.jsonl") if "seq" in c)
    pauses = [(a, b) for a, b in zip(sends, sends[1:]) if b - a > .15]
    long_steps = []
    for q, c, w in telemetry:
        if c <= .15:
            continue
        lo, hi = started + w - c, started + w
        covered = max((min(b, hi) - max(a, lo) for a, b in zip(sends, sends[1:]) if a < hi and b > lo), default=0.)
        long_steps.append({"state_sequence": q, "step_ms": round(c * 1e3, 1), "longest_pause_cover": round(covered / c, 2)})
    return {"run": name, "control_steps": len(telemetry),
            "clock_pauses_over_150ms": len(pauses),
            "clock_pause_ms": sorted((round((b - a) * 1e3) for a, b in pauses), reverse=True),
            "steps_over_150ms": len(long_steps),
            "steps_with_clock_stopped_80pct": sum(s["longest_pause_cover"] >= .8 for s in long_steps),
            "long_steps": long_steps}


def main():
    report = [summarize(name) for name in RUNS]
    (H / "clock_pause_signature.json").write_text(json.dumps(report, indent=2) + "\n")
    for r in report:
        print(r["run"], "steps", r["control_steps"], "pauses>150", r["clock_pauses_over_150ms"], r["clock_pause_ms"][:8],
              "steps>150", r["steps_over_150ms"], "clock stopped >=80%", r["steps_with_clock_stopped_80pct"])


if __name__ == "__main__":
    main()
