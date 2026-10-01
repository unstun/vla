"""Check l1/evaluate_l1.py on synthetic records before L1 (review round 3 asked for this).

Builds fake runs in a temporary experiment root (argument 1), runs the unchanged evaluate_l1.py with its E and H
pointed there, and compares each interval's class and each run's outcome with the expected ones.
Run "cases" (7,200 steps) holds one of each:
  a in-step hold, low CPU share      (200 ms step, main 40, wait 2, watchdog gap 190)   -> process_wide_hold
  b in-step hold, high CPU share     (300 ms step, main 160, wait 3, watchdog gap 281)  -> process_wide_hold
  c between-step hold                (150 ms gap, main 1, wait 1, watchdog gap 140)     -> process_wide_hold
  d clock-client network timeout     (105 ms gap, main 3, wait 2, watchdog running, 211 ms clock pause with an
                                      error row)                                         -> blocked
  e ZMQ-type wait                    (120 ms gap, main 10, wait 5, watchdog running)    -> blocked
  f scheduling delay                 (200 ms step, main 60, wait 230, watchdog gap 40)  -> scheduling
  h mixed                            (180 ms step, main 60, wait 50, watchdog running)  -> mixed
  i GIL hold under load              (220 ms step, main 40, wait 60, watchdog gap 210)  -> process_wide_hold
  j watchdog descheduled by the OS   (200 ms step, main 50, wait 250, watchdog gap 180) -> scheduling
  k main thread working              (250 ms step, main 200, wait 5, watchdog running)  -> main_working
  expected outcome: failed (holds a, b, c, i).
Run "benign" (7,200 steps): d, e, f, h, j, k and 2 ms explicit collections every 50 steps -> passed.
Run "collection" (7,200 steps): a 120 ms automatic generation-2 collection inside a 160 ms step -> collection,
  and criterion 1 fails -> failed.
Run "short" (5,000 steps, otherwise benign) -> inconclusive.
Run "watchdog_cut" (added after review round 4): the benign run plus a scheduling-type step at step 5,000, with the
  watchdog log ending at step 3,000; the step after the cut is labelled watchdog_log_incomplete and the outcome is
  inconclusive.
Writes synthetic_check.json next to this script, with the SHA-256 of the evaluate_l1.py it ran, and exits
non-zero on any mismatch.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
MS = 1_000_000


def build(root, name, steps_total, specials, gaps, collections, watchdog_until_step=None):
    """specials: {step index: (duration, main, proc, runnable, watchdog gap or 0, label)} for in-step intervals;
    gaps: {step index: (gap, main, proc, runnable, watchdog gap or 0, clock pause or 0, error, label)} after it."""
    run = root / "runs" / name
    (run / "diagnostics").mkdir(parents=True)
    rows, t, cpu, proc, runnable = [], 1_000 * MS, 0, 0, 0
    watchdog_holes, clock_holes, errors, expected = [], [], [], []
    for i in range(steps_total):
        duration, main, pcpu, run_t, wgap, label = specials.get(i, (40 * MS, 38 * MS, 40 * MS, 40 * MS, 0, None))
        rows.append((t, t + duration, cpu, cpu + main, proc, proc + pcpu, 0, 0, runnable, runnable + run_t, 0, 0, (i + 1) * 20))
        if wgap:
            watchdog_holes.append((t + 5 * MS, t + 5 * MS + wgap))
        if label:
            expected.append(("in_step", (i + 1) * 20, label))
        t, cpu, proc, runnable = t + duration, cpu + main, proc + pcpu, runnable + run_t
        gap, gmain, gproc, grun, gw, gclock, gerror, glabel = gaps.get(i, (2 * MS, MS, MS, MS, 0, 0, False, None))
        if gw:
            watchdog_holes.append((t + 5 * MS, t + 5 * MS + gw))
        if gclock:
            clock_holes.append((t - 50 * MS, t - 50 * MS + gclock))
        if gerror:
            errors.append(t + 20 * MS)
        if glabel:
            expected.append(("between_steps", (i + 1) * 20, glabel))
        t, cpu, proc, runnable = t + gap, cpu + gmain, proc + gproc, runnable + grun
    s = np.array(rows, dtype=np.int64)
    np.save(run / "diagnostics/steps_abs.npy", s)
    wake = np.arange(s[0, 0] - 20 * MS, s[-1, 1] + 20 * MS, 10 * MS, dtype=np.int64)
    for lo, hi in watchdog_holes:
        wake = wake[(wake < lo) | (wake > hi)]
    if watchdog_until_step is not None:
        wake = wake[wake <= s[watchdog_until_step, 0]]
    np.save(run / "diagnostics/watchdog_wakeups.npy", wake)
    sends = np.arange(s[0, 0] - 40 * MS, s[-1, 1] + 40 * MS, 20 * MS, dtype=np.int64)
    for lo, hi in clock_holes:
        sends = sends[(sends < lo) | (sends > hi)]
    with open(run / "clock_samples.jsonl", "w") as f:
        for k, v in enumerate(sends):
            f.write(json.dumps({"seq": k, "sent": int(v)}) + "\n")
        for e in errors:
            f.write(json.dumps({"error": "timed out", "local_ns": int(e)}) + "\n")
    gc_rows = [(s[0, 0] - 200 * MS, 84 * MS, 2, 0, 1, 1, 1, 84 * MS)]   # start-up collection, reported only
    for when, duration, generation, explicit in collections(s):
        gc_rows.append((when, duration, generation, 0, 1, 1, explicit, duration))
    np.save(run / "diagnostics/gc_events.npy", np.array(gc_rows, dtype=np.int64))
    (run / "process.json").write_text(json.dumps({"child_peak_rss_bytes": 1}) + "\n")
    return expected


def main():
    root = Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location("evaluate_l1", H / "evaluate_l1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.E, module.H = root, root
    cases_special = {
        100: (200 * MS, 40 * MS, 45 * MS, 47 * MS, 190 * MS, "process_wide_hold"),        # a
        300: (300 * MS, 160 * MS, 165 * MS, 168 * MS, 281 * MS, "process_wide_hold"),     # b
        700: (200 * MS, 60 * MS, 70 * MS, 300 * MS, 40 * MS, "scheduling"),               # f
        900: (180 * MS, 60 * MS, 70 * MS, 120 * MS, 0, "mixed"),                          # h
        1100: (220 * MS, 40 * MS, 50 * MS, 110 * MS, 210 * MS, "process_wide_hold"),      # i
        1300: (200 * MS, 50 * MS, 60 * MS, 310 * MS, 180 * MS, "scheduling"),             # j
        1500: (250 * MS, 200 * MS, 205 * MS, 210 * MS, 0, "main_working"),                # k
    }
    cases_gaps = {
        200: (150 * MS, 1 * MS, 2 * MS, 3 * MS, 140 * MS, 0, False, "process_wide_hold"),  # c
        400: (105 * MS, 3 * MS, 5 * MS, 7 * MS, 0, 211 * MS, True, "blocked"),            # d
        500: (120 * MS, 10 * MS, 12 * MS, 17 * MS, 0, 0, False, "blocked"),                # e
    }
    benign_special = {k: v for k, v in cases_special.items() if v[5] != "process_wide_hold"}
    benign_gaps = {k: v for k, v in cases_gaps.items() if v[7] != "process_wide_hold"}
    explicit = lambda s: [(s[i, 1] + MS // 2, 2 * MS, 2, 1) for i in range(49, len(s), 50)]
    runs = {
        "cases": (7200, cases_special, cases_gaps, explicit, "failed"),
        "benign": (7200, benign_special, benign_gaps, explicit, "passed"),
        "collection": (7200, {600: (160 * MS, 38 * MS, 160 * MS, 160 * MS, 130 * MS, "collection")}, {},
                       lambda s: explicit(s) + [(s[600, 0] + 20 * MS, 120 * MS, 2, 0)], "failed"),
        "short": (5000, benign_special, benign_gaps, explicit, "inconclusive"),
        "watchdog_cut": (7200, {**benign_special, 5000: (200 * MS, 60 * MS, 70 * MS, 300 * MS, 0, "scheduling")},
                         benign_gaps, explicit, "inconclusive"),
    }
    report, ok = {}, True
    for name, (total, special, gap, collections, outcome) in runs.items():
        expected = build(root, name, total, special, gap, collections,
                         watchdog_until_step=3000 if name == "watchdog_cut" else None)
        if name == "watchdog_cut":
            # Intervals after the cut cannot be judged for holds.
            expected = [(k, p, "watchdog_log_incomplete" if p > 3000 * 20 else e) for k, p, e in expected]
        sys.argv = ["evaluate_l1.py", name]
        module.main()
        result = json.loads((root / f"l1_evaluation_{name}.json").read_text())
        got = {(x["kind"], x["physics_steps"]): x["label"] for x in result["intervals"]}
        cases = [{"kind": k, "physics_steps": p, "expected": e, "got": got.get((k, p))} for k, p, e in expected]
        extra = [x for x in result["intervals"] if (x["kind"], x["physics_steps"]) not in {(k, p) for k, p, _ in expected}]
        run_ok = result["outcome"] == outcome and all(c["expected"] == c["got"] for c in cases) and not extra
        ok = ok and run_ok
        report[name] = {"expected_outcome": outcome, "outcome": result["outcome"], "cases": cases,
                        "unexpected_intervals": extra, "criterion1": result["criterion1"],
                        "criterion2": result["criterion2"], "passed": run_ok}
    report["all_passed"] = ok
    report["evaluate_l1_sha256"] = hashlib.sha256((H / "evaluate_l1.py").read_bytes()).hexdigest()
    (H / "synthetic_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: (v["outcome"], v["passed"]) if isinstance(v, dict) else v for k, v in report.items()}))
    for name in runs:
        for c in report[name]["cases"]:
            if c["expected"] != c["got"]:
                print("MISMATCH", name, c)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
