# Response to independent review round 3 (`independent_review_round3.json`, failed)

v32's code (`scripts/newton_episode.py`, candidate 2, sha256 840e8e5f…) is unchanged in this round. What changed
are the L1 judge, one instrumentation addition and some wording.

## Blocking

**B1: the process-wide-hold class could not detect holds inside a step. Verified and fixed.**
- **The old rule:** it required main-thread CPU under 20 ms. Every step over 150 ms carries about 39 ms or
  more of physics CPU, so the rule could not fire inside a step.
- **New signal:** the instrumented worker logs every wake-up of its 10 ms watchdog thread
  (`diag_worker.py` → `diagnostics/watchdog_wakeups.npy`). The watchdog cannot wake while another thread holds
  the GIL, and it does no network I/O.
- **New rule:** class 2 (process-wide hold) is *W* − *w* > 110 ms. *W* is the watchdog's longest gap
  between wake-ups in the interval, and *w* is the process's runnable wait, an upper bound on the watchdog's
  own CPU waiting. At least 100 ms of the watchdog's gap was then spent blocked, not queued for a CPU. The
  rule is identical inside and between steps, needs no main-thread CPU threshold, and covers a GIL held by
  the physics thread itself.
- **Your required fixes:**
  - **Order:** class 2 is evaluated before class 4 ("main thread working").
  - **Clock client:** its pauses and error rows are reported but not used, so its own network timeout
    cannot pass for a hold.
  - **Mixed intervals:** they are defined. Class 5, "off-CPU while the rest of the process ran", is labelled
    *blocked* for *w* < 20 ms and *mixed* for 20 ≤ *w* < 100 ms.
  - **Criterion 3:** the classes are exhaustive, so it is dropped. L1 now passes or fails on criterion 1
    (collections) and criterion 2 (holds), after the exposure rule.
- **Synthetic check** (`l1/synthetic_check.py` → `l1/synthetic_check.json`), run before L1 on the revised
  `evaluate_l1.py`:
  - **Run "cases":**

    | Case | Class |
    |---|---|
    | in-step hold, low CPU share (40 of 200 ms) | hold |
    | in-step hold, high CPU share (160 of 300 ms) | hold |
    | between-step hold | hold |
    | hold under load (w 60 ms) | hold |
    | clock-client timeout with its error row | blocked |
    | ZMQ wait | blocked |
    | scheduling delay | scheduling |
    | watchdog descheduled by the OS | scheduling |
    | mixed | mixed |
    | working main thread | main working |

    The run's outcome is failed, as expected.
  - **Run "benign":** passed.
  - **Run "collection":** a 120 ms automatic collection is classed as a collection, fails criterion 1, and
    the run fails.
  - **Run "short":** inconclusive.
  - **Summary:** every class and outcome matches, with no unexpected intervals.
- **Plans aligned:** PLAN.md (stall classes, criteria, claim boundary) and PHYSICAL_RUN_PLAN.md now use the
  new rule.

## Non-blocking

- **N1:** labelled as inferences, with the bound: at most about 135 ms for the B gaps, and about 84–105 ms
  for `diag_v31_clock04`'s fatal gap (RESULT.md, PLAN.md).
- **N2:** criterion 1 now covers only collections that start after the first step starts and end before
  the last one ends. `diag_worker.py` also records the collecting thread's CPU time per collection, which is
  reported next to the wall time.
- **N3:** `analyze_pipeline.py` counts only accepted offers.
- **N4:** the blame threshold is 15 ms, the timer period plus a margin, and the receive spacing of every
  superseded pose is reported (PLAN.md and the script).
- **N5:** the numbers are updated in PLAN.md:
  - full collections at control steps 485, 3,571, 6,956, 10,671 and 14,745;
  - candidate 1's leak as 146,504 frozen objects (run 02);
  - the start-up collection at 82 and 84 ms.
- **N6:** in PLAN.md's A bullet, the GIL hold is measured for `diag_v31_clock04` and inferred for
  `diag_v31_clock03`.
- **N7:** `freeze.py` names K4 as the first passing round, after rounds 1–3 failed.
- **N8:** PLAN.md explains how the live loop differs from the replay, and why live frozen garbage can exceed
  0.
- **N9:** the backend is matched as `native_backend_entry.py` and the bridge as `foxy_bridge_node`.
