"""Judge L1 exactly as versions/v32/PLAN.md pre-registers it (written before L1 ran; revised after review round 3).

Input: runs/<run>/ recorded by audits/2026-09-29_wall_clock_chain/diag_worker.py: diagnostics/steps_abs.npy
(absolute counters at each step's start and end), gc_events.npy (8 columns: start, wall duration, generation,
collected, thread, main thread, explicit, collecting thread's CPU), watchdog_wakeups.npy (every wake-up of the
10 ms watchdog thread), clock_samples.jsonl, process.json, and diagnostics/linux/ for the container record.

- Exposure: at least 7,100 control steps, otherwise "inconclusive".
- Criterion 1 (Mac worker): for collections that start after the first control step starts and end before the
  last one ends, no automatic generation-2 collection and none longer than 20 ms of wall time (explicit window
  collections included). The start-up collection before the loop is reported only.
- Intervals: in-step stalls over 150 ms and gaps over 100 ms between steps. Over each interval, from the
  absolute counters: main CPU m (physics thread), runnable wait w = process runnable time - process CPU time
  (summed over threads, so an upper bound for any one thread), collection overlap g (share of the interval
  covered by logged collections), and W, the watchdog's longest gap between consecutive wake-ups overlapping it.
  The watchdog does nothing but sleep 10 ms, so a gap is its sleep plus waiting for the GIL or for a CPU, and
  at most w of it can be CPU waiting: W - w - 10 ms is a lower bound on how long it could not get the GIL.
  Classes, in order:
    1 collection: g >= 0.5;
    2 process-wide hold: W - w > 110 ms (the watchdog was blocked, not queued for a CPU, for over 100 ms);
    3 scheduling-type: w >= 100 ms;
    4 main thread working: m >= 50% of the interval;
    5 main thread off-CPU while the rest of the process ran: everything else, labelled "blocked" (w < 20 ms,
      for example the ZMQ round trip between steps) or "mixed" (20 <= w < 100 ms).
  The classes are exhaustive, so no interval is left unclassified.
- Criterion 2: no class-2 interval and no class-1 interval whose collection exceeds 20 ms.
Also reported per interval: the clock client's longest send pause and whether a clock-client error row (its own
network timeout or reconnect) falls in it; these are not used for judging.
Watchdog coverage (added after review round 4): an interval without a watchdog wake-up on both sides cannot be
judged for holds. It gets the label "watchdog_log_incomplete" (class 0) instead of a class, and if the wake-up log
does not span the loop (first wake-up at or before the first step's start, last at or after the last step's end)
the outcome is "inconclusive" whatever else holds.
Writes l1_evaluation_<run>.json next to this script.
"""
import array
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[2]


def longest_gap(times, lo, hi):
    """Longest gap between consecutive times, over the times inside [lo, hi] plus one on each side."""
    i0, i1 = np.searchsorted(times, lo), np.searchsorted(times, hi)
    window = times[max(i0 - 1, 0):min(i1 + 1, len(times))]
    return float(np.diff(window).max()) / 1e6 if len(window) > 1 else float("inf")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "diag_v32_clock01"
    run = E / "runs" / name
    s = np.load(run / "diagnostics/steps_abs.npy")
    g = np.load(run / "diagnostics/gc_events.npy")
    wakeups = np.sort(np.load(run / "diagnostics/watchdog_wakeups.npy"))
    sends, errors = [], []
    for line in open(run / "clock_samples.jsonl"):
        row = json.loads(line)
        if "seq" in row:
            sends.append(row["sent"])
        elif "error" in row:
            errors.append(row["local_ns"])
    sends, errors = np.array(sorted(sends), dtype=np.int64), np.array(sorted(errors), dtype=np.int64)
    first, last = s[0, 0], s[-1, 1]
    loop_gc = g[(g[:, 0] >= first) & (g[:, 0] + g[:, 1] <= last)]
    startup_gc = g[g[:, 0] < first]

    def by_generation(events):
        return {str(k): {"count": int((events[:, 2] == k).sum()),
                         "max_ms": round(float(events[events[:, 2] == k, 1].max()) / 1e6, 2) if (events[:, 2] == k).any() else 0.0}
                for k in (0, 1, 2)}

    automatic_full = loop_gc[(loop_gc[:, 2] == 2) & (loop_gc[:, 6] == 0)]
    longest = int(np.argmax(loop_gc[:, 1])) if len(loop_gc) else None
    criterion1 = {"automatic_generation2_in_loop": int(len(automatic_full)),
                  "longest_collection_in_loop_ms": round(float(loop_gc[longest, 1]) / 1e6, 2) if longest is not None else 0.0,
                  "its_cpu_ms": round(float(loop_gc[longest, 7]) / 1e6, 2) if longest is not None else 0.0,
                  "explicit_in_loop": int((loop_gc[:, 6] == 1).sum())}
    criterion1["passed"] = criterion1["automatic_generation2_in_loop"] == 0 and criterion1["longest_collection_in_loop_ms"] <= 20.0

    def gc_cover(lo, hi):
        mask = (g[:, 0] < hi) & (g[:, 0] + g[:, 1] > lo)
        if not mask.any():
            return 0.0, 0.0
        overlap = np.minimum(g[mask, 0] + g[mask, 1], hi) - np.maximum(g[mask, 0], lo)
        return float(overlap.sum()) / (hi - lo), float(g[mask, 1].max()) / 1e6

    intervals = []

    def classify(kind, lo, hi, main_cpu, proc_cpu, runnable, physics_steps):
        length = (hi - lo) / 1e6
        wait = (runnable - proc_cpu) / 1e6
        main = main_cpu / 1e6
        cover, longest_gc = gc_cover(lo, hi)
        watchdog = longest_gap(wakeups, lo, hi)
        covered = len(wakeups) > 0 and wakeups[0] <= lo and wakeups[-1] >= hi
        if not covered:
            cls, label = 0, "watchdog_log_incomplete"
        elif cover >= .5:
            cls, label = 1, "collection"
        elif watchdog - wait > 110:
            cls, label = 2, "process_wide_hold"
        elif wait >= 100:
            cls, label = 3, "scheduling"
        elif main >= .5 * length:
            cls, label = 4, "main_working"
        else:
            cls, label = 5, "blocked" if wait < 20 else "mixed"
        intervals.append({"kind": kind, "physics_steps": int(physics_steps), "ms": round(length, 1),
                          "main_cpu_ms": round(main, 1), "runnable_wait_ms": round(wait, 1),
                          "collection_cover": round(cover, 2), "longest_collection_ms": round(longest_gc, 1),
                          "watchdog_longest_gap_ms": round(watchdog, 1),
                          "clock_client_longest_pause_ms": round(longest_gap(sends, lo, hi), 1),
                          "clock_client_error_in_interval": bool(((errors >= lo) & (errors <= hi)).any()),
                          "class": cls, "label": label})

    for i in range(len(s)):
        start, end, t0, t1, p0, p1, _, _, r0, r1, _, _, steps = s[i]
        if end - start > 150_000_000:
            classify("in_step", start, end, t1 - t0, p1 - p0, r1 - r0, steps)
        if i + 1 < len(s) and s[i + 1, 0] - end > 100_000_000:
            n = s[i + 1]
            classify("between_steps", end, n[0], n[2] - t1, n[4] - p1, n[8] - r1, steps)
    classes = [x["class"] for x in intervals]
    criterion2 = {"process_wide_holds": classes.count(2),
                  "collection_intervals_over_20ms": sum(1 for x in intervals if x["class"] == 1 and x["longest_collection_ms"] > 20)}
    criterion2["passed"] = criterion2["process_wide_holds"] == 0 and criterion2["collection_intervals_over_20ms"] == 0
    exposure = {"control_steps": int(len(s)), "required": 7100}
    exposure["met"] = exposure["control_steps"] >= exposure["required"]
    watchdog_coverage = {"wakeups": int(len(wakeups)),
                         "spans_loop": bool(len(wakeups) > 0 and wakeups[0] <= first and wakeups[-1] >= last),
                         "incomplete_intervals": classes.count(0)}
    passed = criterion1["passed"] and criterion2["passed"]
    judgeable = exposure["met"] and watchdog_coverage["spans_loop"] and watchdog_coverage["incomplete_intervals"] == 0
    outcome = "inconclusive" if not judgeable else ("passed" if passed else "failed")
    containers = {}
    linux = run / "diagnostics/linux"
    if linux.exists():
        for path in linux.glob("*_gc.i64"):
            pid = path.name.split("_")[0]
            data = array.array("q")
            data.frombytes(path.read_bytes())
            events = np.asarray(data, dtype=np.int64).reshape(-1, 5)
            command = (linux / f"{pid}_cmdline.txt").read_text().strip() if (linux / f"{pid}_cmdline.txt").exists() else "?"
            containers[pid] = {"command": command[:140], "by_generation": by_generation(events)}
    process = json.loads((run / "process.json").read_text()) if (run / "process.json").exists() else {}
    result = {"run": name, "outcome": outcome, "exposure": exposure, "watchdog_coverage": watchdog_coverage,
              "criterion1": criterion1, "criterion2": criterion2,
              "classes": {label: sum(1 for x in intervals if x["label"] == label)
                          for label in ("watchdog_log_incomplete", "collection", "process_wide_hold", "scheduling",
                                        "main_working", "blocked", "mixed")},
              "startup_collections_ms": [round(float(d) / 1e6, 1) for d in startup_gc[startup_gc[:, 6] == 1, 1]],
              "worker_loop_collections": by_generation(loop_gc), "container_collections": containers,
              "peak_child_rss_bytes": process.get("child_peak_rss_bytes"),
              "intervals": intervals}
    (H / f"l1_evaluation_{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("intervals", "container_collections")}, indent=1))


if __name__ == "__main__":
    main()
