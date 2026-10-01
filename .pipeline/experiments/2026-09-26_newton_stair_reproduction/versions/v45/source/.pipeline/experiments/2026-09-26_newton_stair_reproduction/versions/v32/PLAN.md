# v32: collect, then freeze, the Newton worker's heap every simulated second

## Decision and basis

- **Decision (Dr Sun, 2026-09-29):** after the v31 trial, fix the clock fault. That means diagnosing the
  wall-clock freshness chain that ended v28, v30 and v31, then building v32 against it. v31 was committed
  first (`37a55cbc`).
- **The diagnosis** (`audits/2026-09-29_wall_clock_chain/RESULT.md`, revised after review rounds 1 and 2):
  - The backend's `odom_stale` gate measures wall time between body-pose receipts, with a limit of 0.25 s.
  - The two instrumented v31-configuration runs had 20 backend gaps over 150 ms, of two kinds:
    - **A, process-wide freezes, with no pose published (7 of 20).** The gap arose in the Mac-side Newton
      worker, before publishing, and the clock client stopped too (both measured).
      - In `diag_v31_clock04`, a thread held the GIL through a logged full cyclic garbage collection in both
        A gaps, of 143 and 176 ms. The run's five full collections (99–176 ms, rising through the run) each
        coincided with a stall (measured).
      - In `diag_v31_clock03`, the freezes are measured, but that a thread held the GIL, and that the
        holder was a collection, are both inferred.
    - **B, a worker slowdown plus poses superseded after publishing (13 of 20).** The worker still
      published, 39–87 ms apart at worst (measured). The 3–6 poses in between were superseded after
      publishing, at a location that is not measured.
      - Both parts were needed (inferred): had every published pose been delivered with the receipt delays
        observed (3–49 ms), no B gap would have exceeded about 135 ms, far under the 0.25 s gate.
  - The clock-observation rejections and reconnects are a sibling symptom (inferred).
- **How the runs ended:**
  - `diag_v31_clock03` ended on A.
  - `diag_v31_clock04` ended on B. Its superseding, not its slowdown, pushed the gap past the gate.
  - The v31 trial ended on a stall of the physics thread alone, with no pose published for 288 ms while
    the clock client kept running. Its cause is inferred.
- **Scope:** v32 targets A only, without changing any gate, threshold or computation. Whether it removes A
  in a live run is the hypothesis that L1 tests.

## The change

Only `scripts/newton_episode.py` changes, with three insertions and no removal (`materialize.py`,
`changes.patch`, preimage in `parent_source/`):

1. `import gc`.
2. `gc.collect()`, then `gc.freeze()`, immediately before the control loop. By then start-up, the sensors,
   clock sync and the transports all exist.
3. `gc.collect()`, then `gc.freeze()`, after every 50th control step, which is 1 s of simulation.

**What it does (CPython 3.12.13, measured in `audits/2026-09-29_wall_clock_chain` and in review):**
- **The freeze:** `gc.freeze()` moves every tracked object into the permanent generation, which automatic
  collections do not traverse. It also resets the collection counters, so under this schedule automatic
  full collections do not run.
- **The collection first:** the explicit `gc.collect()` before each periodic freeze reclaims the window's
  cyclic garbage, so it is not frozen. That garbage includes roughly 970 objects per LiDAR scan from
  Newton's per-call kernel rebuild in `intersect_ray`. The collection traverses only objects created since
  the previous freeze.
- **The first collection is the exception:** it runs before the loop and covers the whole start-up heap.
  In K3 it took 82 ms in run 01 and 84 ms in run 02. It runs while the clock client and the command receiver are active, but before any
  pose flows. L1 reports its duration.
- **Middle collections:** they are not curtailed under this schedule. K3 logged 95 middle and 1,155 young
  collections in 946 steps, against 16 and 174 without freezing, each well under 1 ms. Only candidate 1's
  freeze-only schedule stopped middle collections, with none in 946 steps.
- **Unchanged:** reference counting frees ordinary garbage at once, as before. Physics, sensing, messages,
  logs, timing gates, the native planner (`scan64`, as v31) and both planner YAMLs (byte-identical copies)
  are all unchanged.

**Candidate 1 (`attempt01/`) is superseded.** It froze without collecting. That freezes pending garbage for
good: 146,504 objects over 946 steps in K3 run 02 (run 01's 154,660 also counted 8,156 objects still
pending).

**The remaining cost:** objects that are alive at a freeze and die later are never reclaimed. An example is
a kernel graph that a scan in progress is still holding. At worst that is about one graph (about 0.14 MB)
per window, which is up to about 80 MB over a 600 s run. K3 measures it, and L1 and L2 report peak RSS.

## Checks before the freeze

| Check | Pass condition |
|---|---|
| K1 byte-exact | `newton_episode.py` = v31 bytes plus exactly the three insertions (removing them restores v31's SHA-256); every other v31 source file unchanged |
| K2 syntax and scope | the file compiles, and its AST differs from v31's only by `import gc`, the collect-and-freeze pair before the loop, and the `if (step + 1) % 50 == 0:` block holding the same pair |
| K3 schedule, offline (`gc_schedule_check/`) | see below |
| K4 independent review | the first round that passes with no blocking finding. Rounds 1–3 failed (`independent_review_round1.json` to `independent_review_round3.json`) |

**K3.** It replays v31_historical_full01's 946 recorded commands through the same physics, LiDAR scan thread
and writer thread. The replay retains data as `newton_episode.py` does: every telemetry row, a video state
every 4 steps, and a cloud record per scan. It runs three schedules: no freezing, candidate 1's freeze-only
schedule, and v32's collect-then-freeze schedule. Every collection is logged. Each run ends with
`gc.collect()`, to reclaim unfrozen pending garbage, and then with `gc.unfreeze(); gc.collect()`, whose
count is exactly the garbage the schedule froze.

v32's schedule passes if all three of these hold:
- **(a)** after the loop starts, no collection lasts longer than 20 ms, whether automatic or explicit. This
  includes the explicit collection at the end of each window, the worst phase.
- **(b)** the frozen garbage is at most 10% of the freeze-only schedule's.
- **(c)** the joint states equal the trial's exactly.

Reported alongside: the start-up collection's duration, the pending garbage at the end, peak RSS in each
mode, and the longest collection without freezing. K3 run 01 (`gc_schedule_check/run01/`) counted pending
and frozen garbage together, an upper bound. Its conditions (a) and (c) passed, and (b) passed on that
upper bound (1,772 against 154,660). Run 02, the one that counts, separates the two counts.

**How the live loop differs:** the replay has no file read between a scan submission and the window's
collection. The live loop reads `backend_latest.json` there, which releases the GIL. So a scan's kernel
construction is more often in progress at a live freeze, and live frozen garbage can exceed K3's 0. The
worst-case bound above (about one kernel graph per window) and the peak-RSS reports cover this.

`probe_gc_freeze.json` measured collections right after a freeze. It stays in the audit as evidence of the
pre-freeze costs only (70 and 160 ms), not as a check of v32.

## Live runs after the freeze

**L1 `diag_v32_clock01`**
- **Setup:** v32 with the instrumented worker (`audits/2026-09-29_wall_clock_chain/diag_worker.py`). It
  records, for observation only:
  - per-step wall time, main-thread CPU and `rusage_info_v6` deltas;
  - the absolute counters at each step's start and end (`steps_abs.npy`), so the time between steps is
    covered too;
  - every collection, with its thread, whether it came from an explicit `gc.collect()` call (the function
    is wrapped to mark the calling thread), and the collecting thread's CPU time during it;
  - every wake-up of the worker's 10 ms watchdog thread (`watchdog_wakeups.npy`), as a continuous liveness
    signal. The watchdog cannot wake while another thread holds the GIL;
  - each telemetry frame's enqueue and send time in the worker's `TelemetryPublisherServer`;
  - the container-side record (`container_site/sitecustomize.py`): each Linux Python process's
    collections, and in the bridge each body state's receive and delivery time and every publish
    callback's duration.

  None of these changes behaviour. L1 is a diagnostic run, not the trial.
- **Exposure rule:** L1 counts only if it covers at least 7,100 control steps. `diag_v31_clock04` had full
  collections at control steps 485, 3,571 and 6,956, and then at 10,671 and 14,745. A shorter run is
  recorded as **inconclusive**, whatever it shows.
- **Stall classes.** Each interval is an in-step stall of more than 150 ms, or a gap of more than 100 ms
  between the end of one step and the start of the next. Over each interval (`l1/evaluate_l1.py`):
  - *m* is the physics thread's CPU time;
  - *w* is the process's runnable wait: runnable time minus CPU time, from the absolute counters, summed
    over threads, so it is an upper bound for any single thread;
  - *g* is the share of the interval covered by logged collections;
  - *W* is the watchdog's longest gap between consecutive wake-ups.

  The watchdog only sleeps 10 ms, so *W* is its sleep plus waiting for the GIL or for a CPU. At most *w* of
  that can be CPU waiting, so *W* − *w* − 10 ms bounds from below how long it was blocked rather than queued
  for a CPU: GIL waiting together with timer lateness and its own work (see the limits below). The
  classes are applied in this order, and the same rule works inside a step and between steps:
  1. **Collection:** *g* ≥ 0.5.
  2. **Process-wide hold:** *W* − *w* > 110 ms. The watchdog was blocked, not queued for a CPU, for more
     than 100 ms. This applies whatever the physics thread's own CPU share, so it is evaluated before class
     4, and a GIL held by the physics thread itself counts too.

     **Limits of this rule** (review round 4):
     - **Subtracting all waiting:** *w* is subtracted in full, including other threads' CPU waiting and
       native work done without the GIL. A hold that overlaps at least *W* − 110 ms of such waiting is
       classed as scheduling.
     - **Short holds:** a hold of up to about 100 ms beyond the watchdog's 10 ms sleep is not class 2.
       Collections of that length are still caught by criterion 1.
     - **What the bound includes:** *W* − *w* − 10 ms bounds GIL waiting together with timer lateness and
       the watchdog's own work (stack sampling and writing). So a false hold would need more than 100 ms of
       such delay.
     - **Missing log:** an interval without a watchdog wake-up on both sides is not classified. It is
       labelled *watchdog log incomplete*, and if the wake-up log does not span the loop, L1's outcome is
       inconclusive.
  3. **Scheduling-type:** *w* ≥ 100 ms.
  4. **Main thread working:** *m* ≥ 50% of the interval.
  5. **Main thread off-CPU while the rest of the process ran:** everything else. It is labelled *blocked*
     when *w* < 20 ms (for example the ZMQ round trip between steps) and *mixed* when 20 ≤ *w* < 100 ms.

  The clock client's send pause, and any clock-client error row (its own network timeout or reconnect), are
  reported for every interval but not used. A timeout of the clock client itself therefore cannot be
  mistaken for a hold.

  The classes are exhaustive, so every interval that the watchdog log covers is reported with a class, and
  none is left unclassified.
  `l1/synthetic_check.py` checked the rules before L1 on fake records covering every case
  (`l1/synthetic_check.json`):
  - holds inside a step at low and high CPU share, a hold between steps, and a hold under load;
  - a clock-client timeout, a ZMQ wait, a scheduling delay, a mixed interval, a watchdog descheduled by the
    OS, and a working main thread;
  - a long automatic collection, a short run, and a watchdog log that stops early. The last is inconclusive,
    and its later interval is labelled incomplete.

  The check records the SHA-256 of the `evaluate_l1.py` it ran.
- **L1 passes if, within the exposure rule, both of these hold:**
  1. **In the Mac worker:** consider the collections that start after the first control step starts and
     end before the last one ends. Among them there is no automatic full (generation 2) collection, and
     none lasts longer than 20 ms of wall time, the explicit window collections included. The start-up
     collection before the loop is reported, not judged, and each collection's CPU time is reported next
     to its wall time.
  2. **No interval is a process-wide hold** (class 2), and no collection interval (class 1) holds a
     collection over 20 ms.
- **What does not fail L1:** scheduling-type, working, blocked and mixed intervals are recorded, and do
  not fail it.
- **Reported:** the maximum duration per generation, in the worker and in each container process, and the
  worker's peak RSS.
- **Delivery-path split, pre-registered for every backend gap over 150 ms.** Each body state is matched by
  its stamp across the worker's frame records, the bridge's records and the backend callbacks. Container
  times are mapped to the Mac clock through the clock filter's offset. Its time is then split into five
  segments:
  - **worker queue:** from enqueue to the start of sending;
  - **worker send:** the send call;
  - **transit and bridge receipt:** from the end of sending to the bridge's receive time. This covers the
    host-to-VM path and the bridge's telemetry thread, and it cannot separate the two, except through the
    bridge's recorded collections and callback activity;
  - **bridge hold:** from receipt to delivery by the 10 ms timer;
  - **ROS delivery:** from delivery to the backend callback.

  A superseded pose p, one that reached the bridge but was never delivered, is blamed by comparison with
  the next pose p′ (`audits/2026-09-29_wall_clock_chain/analyze_pipeline.py`):
  - **bridge timer:** p was received at least 15 ms before p′ (the 10 ms timer period plus a margin for its
    jitter), so the timer did not deliver it in time;
  - **worker sender:** otherwise, if the worker sent p less than 15 ms before p′, the two left the worker
    bunched;
  - **transit or receipt:** otherwise, the two were sent apart but received bunched.

  The receive spacing of every superseded pose is reported alongside, and only offers the bridge accepted
  count as received.

**L2 `v32_historical_full01`**
- **Setup:** v32 alone, with the flags of v31_historical_full01 and the integration version changed.
- **Acceptance:** the unchanged Building review for the historical profile.
- **Recorded separately:**
  - whether `odom_stale` occurs, and the largest body-pose gaps;
  - clock TTL windows and reconnects, against v31;
  - peak RSS;
  - progress past v31's end.
- **Limit:** L2 carries no instrumentation, so any attribution of its gaps to A or B is an inference from
  the saved logs.

## Not addressed by v32

- **B's worker slowdown under host load.** A stall of the physics thread with nothing published, like the
  v31 trial's 288 ms, can still exceed 0.25 s by itself.
- **B's superseding after publishing.** It turned `diag_v31_clock04`'s slowdown into a fatal 297 ms gap.
  L1 locates it. A delivery-side change there would keep B gaps near the worker's publish interval without
  changing any gate.
- **The gate's time base:** for example, the simulation-time age of the newest pose instead of wall time
  between receipts. It is the only option for stalls with nothing published. It changes the navigation
  stack's safety semantics in simulation, and it would have to handle MuJoCo-Warp's float32 time drift (up
  to 1.78 s at 390 s of simulation).
- **Decisions for Dr Sun:** both the delivery-side change and the gate's time base are his.
- **Newton's per-scan kernel rebuild:** it stays, costing about 1 ms of GIL and about 970 garbage objects per
  scan. v32 collects that garbage.
- **Later versions:** the corridor's wrong-height navigation cell, where both diagnostic runs stood on
  collision rejections, and continuous replanning and the collision model.

## Claim boundary

- **Version status:** a version increment is not acceptance, and v3 remains the last accepted condition.
- **What L1 can show:** that, by the watchdog rule, no process-wide hold of more than 100 ms occurred in
  the worker over its exposure, and no collection there lasted more than 20 ms. It cannot show that none can
  occur. A hold that overlaps as much process-wide CPU waiting as its own length, less 110 ms, is counted as
  scheduling rather than as a hold.
- **What L2 can show:** L2 is one run, and host load varies between runs: steps over 250 ms were 0.63% in
  v31 against 0.004% in `diag_v31_clock03`. So a clean L2 does not show that B is harmless, and a
  corridor-entry stop is not evidence for or against v32.
