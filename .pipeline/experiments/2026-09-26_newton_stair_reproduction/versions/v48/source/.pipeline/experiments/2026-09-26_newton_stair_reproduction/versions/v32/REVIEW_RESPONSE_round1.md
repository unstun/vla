# Response to independent review round 1 (`independent_review_round1.json`, failed)

**Superseded in part.** Round 2 (`independent_review_round2.json`) found the statement "All 20 arose before
publishing" under B2 below to be wrong for the 13 gaps with superseded poses. Those gaps combine a worker
slowdown with superseding after publishing. The correction is in `REVIEW_RESPONSE_round2.md`, and this file
is kept as it was answered.

Each finding was verified against the raw data before it was acted on. The v32 candidate was rebuilt, so
`scripts/newton_episode.py` changed. The first candidate's records are in `attempt01/`.

## Blocking

- **B1, the stamp-to-step unit error. Verified and fixed.**
  - **Verified:** MuJoCo-Warp's float32 time drifts from `steps × 1 ms` by −43.3 ms at step 100,000,
    +450.6 ms at 200,000, +1,158.6 ms at 300,000 and +1,779.1 ms at 387,640.
  - **Recomputed from `diag_v31_clock04`'s telemetry pairs:** its fatal stamps map to physics steps
    387,640 and 387,675, published 278.6 ms apart. In that window a 176.8 ms step had 58.3 ms of CPU and
    465.5 ms of runnable wait.
  - **Script fix:** `analyze_gc.py` no longer attributes pose gaps. Its wrong round-1 output is kept as
    `gc_attribution_diag_v31_clock04_round1.json`. The new `analyze_pose_gaps.py` maps stamps through the
    run's own (physics_steps, physics_time_s) pairs.
  - **Record fix:** `RESULT.md` sections 4–5, the source table and `PLAN.md` now read: `diag_v31_clock04`
    ended on B, with six poses superseded.
- **B2, mechanism C was not supported. Verified and fixed.**
  - **Verified:** `analyze_pose_gaps.py` covers all 20 backend gaps over 150 ms in `diag_v31_clock03` and
    `diag_v31_clock04`.
    - All 20 arose before publishing: the Mac publish interval is at least half the backend gap, and
      receipt took 2–49 ms.
    - The 13 gaps with superseded poses all show B signatures.
    - The 7 gaps with consecutive poses all show process-wide freezes.
  - **Record fix:** C is removed as a mechanism. The superseding is recorded as co-occurring with B,
    with its location not measured.
  - **L1 addition:** the instrumented worker now records each telemetry frame's enqueue and send time
    (`diag_worker.py`). Together with the container's bridge receive and delivery records, this splits a
    delay into worker sender, network and bridge.
- **B3, inferences stated as measurements. Fixed.**
  - **RESULT.md:** it defines measured and inferred, and the source table has a status column:
    - v31: B inferred, with a possible A part of up to about 78 ms;
    - `diag_v31_clock03`: the freeze measured, its collection cause inferred;
    - `diag_v31_clock04`: B measured.
  - **"Since resolved":** removed.
  - **Durations:** logged collection durations (99–176 ms) are kept separate from `diag_v31_clock03`'s
    inferred freezes.
  - **Code comment:** it now reads "Logged full collections in this worker took 99-176 ms, holding the
    GIL throughout".
- **B4, the freeze-only schedule leaks. Verified and fixed.**
  - **Verified:** `gc.freeze()` resets `gc.get_count()` from (206, 10, 0) to (0, 0, 0). Freezing without
    collecting froze 6,000 of 6,000 cyclic test objects, and collecting first froze none.
  - **Candidate 2:** it calls `gc.collect()` immediately before each `gc.freeze()`, both before the loop and
    every 50 steps.
  - **K3 (`gc_schedule_check/result.json`), on v31's 946 commands:**

    | Schedule | Garbage frozen for good | Middle collections |
    |---|---|---|
    | freeze only | 154,660 objects | 0 |
    | collect, then freeze | 1,772 objects | 95 |

    The explicit collections took at most 1.34 ms (median 1.15 ms), and the joint states were identical.
  - **Records:** `PLAN.md` and `RESULT.md` describe the counter reset, the curtailed middle collections,
    the kernel garbage and the remaining bounded cost (objects alive at a freeze).
- **B5, gates that could not fail. Fixed.**
  - **K3 redefined:** it is a worker-sized replay with the episode's retention. The window's explicit
    collection is measured at the worst phase, 49 steps after a freeze. It has three conditions (≤ 20 ms,
    ≤ 10% frozen garbage, identical states), and they were pre-registered in `PLAN.md` before it ran.
  - **`probe_gc_freeze.json`:** relabelled as evidence of pre-freeze costs only.
  - **L1 exposure rule:** at least 7,100 control steps or 300 s of loop wall time, otherwise the run is
    inconclusive.

## Non-blocking

- **N1:** `freeze.py` pins `bench/*/summary.json`, and excludes K3's bulky per-mode outputs except each
  `summary.json` and `gc_events.npy`.
- **N2:** L1's criteria are restated:
  - criterion 1 is limited to the Mac worker;
  - a process-wide hold is defined numerically;
  - gaps between steps are classified, and scheduling-type stalls do not fail L1.
- **N3:** `sitecustomize.py` flushes every 0.5 s and at interpreter exit. It installs no signal handler, so
  the observed processes' shutdown stays unchanged; the shadowing of Ubuntu's sitecustomize is stated. A
  smoke check in the pinned image (Python 3.10.12) loaded all three bridge patches and wrote the records at
  exit.
- **N4:** the scheduling attribution is labelled an upper bound and an inference, and the external probe
  results are reported:
  - at most 10 ms late during the freezes;
  - 7–44 ms late during B steps.
- **N5:** each point was verified against the raw data, and all are corrected:
  - the step after the 159 ms freeze read `active`;
  - six poses, not seven;
  - the efficiency-core share reached 0.89;
  - v28 had a 200 ms gap between steps before step 228, and v30 a 125 ms gap before step 2917;
  - the replay claim is limited to v31;
  - the claim that the callbacks resumed at a normal pace is removed.
- **N6:** labelled as inferred.
- **N7:** host memory pressure is recorded as a residual factor (free memory 7.4 → 2.5 GB, 1,112
  swap-ins; the worker had 26 page-ins).
- **N8:** the float32 drift is stated in `RESULT.md` and `PLAN.md`.
- **N9:** v32's effect is phrased as the hypothesis L1 tests, and the manifest's "decisions" field lists
  the superseding as not addressed.
- **N10:** `PHYSICAL_RUN_PLAN.md` labels L2's attributions as inferences, and says the corridor stop is
  not evidence for or against v32.
- **N11:** both statements are labelled as inferences.
- **N12:** round 2 reviews the current files, and `independent_review.json` records their hashes.
