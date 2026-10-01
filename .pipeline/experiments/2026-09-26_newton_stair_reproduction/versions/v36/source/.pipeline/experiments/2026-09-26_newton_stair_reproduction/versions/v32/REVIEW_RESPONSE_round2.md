# Response to independent review round 2 (`independent_review_round2.json`, failed)

Both blocking findings were verified against the raw data before they were acted on. v32's code
(`scripts/newton_episode.py`, candidate 2, sha256 840e8e5f…) is unchanged in this round. What changed are the
diagnosis record, the plans, the L1 instrumentation and evaluation, and K3's leak measure.

## Blocking

- **B1, where B gaps arise. Verified and fixed.**
  - **Verified:** in all 13 B gaps the worker kept publishing. The longest intervals between consecutive
    Mac publishes were 69.7, 38.9, 79.8, 83.5, 67.8, 82.2 and 69.4 ms in `diag_v31_clock03`, and 87.1,
    62.8, 60.8, 73.8, 83.9 and 83.5 ms in `diag_v31_clock04`.
    - In `diag_v31_clock04`'s fatal gap, poses were published at 0, 83.5, 121.6, 146.9, 179.7, 216.6,
      244.5 and 278.6 ms.
    - In the 7 A gaps the longest interval is the whole gap.
  - **`analyze_pose_gaps.py` now reports** every publish offset, the longest publish interval, and a
    no_publish or superseded_after_publish label.
  - **RESULT.md now states:**
    - A gaps arose before publishing.
    - B gaps combine a worker slowdown (39–87 ms between publishes) with 3–6 poses superseded after
      publishing, at an unmeasured location, and both parts were needed.
    - Section 5's non-discriminating row is replaced by the longest publish interval.
    - `diag_v31_clock04`'s fatal gap would have been about 84 ms without the superseding.
    - Its source row says the superseding, not the slowdown, tripped the gate.
    - The v31 trial's row describes a stall of the physics thread alone, with nothing published.
    - "What v32 can and cannot change" and PLAN.md's basis and "Not addressed" section list two separate
      options for Dr Sun: a delivery-side change once L1 has located the superseding, and the gate's time
      base, which is the only option for stalls with nothing published.
- **B2, the stall classes could not be evaluated between steps. Fixed.**
  - **Counters:** `diag_worker.py` records the absolute counters (main-thread CPU, process CPU, P-core
    CPU, runnable time, page-ins) at each step's start and end in `steps_abs.npy`, so the time between
    steps has deltas.
  - **Rules:** `PLAN.md` defines six classes that are computed the same way inside and between steps.
    A process-wide hold between steps is main CPU and runnable wait both under 20 ms plus a clock-client
    pause over 100 ms.
  - **Evaluator:** `l1/evaluate_l1.py` implements the rules as written. It was checked on synthetic records
    before L1: a scheduling-type step, a between-step hold, and a blocked gap were classed 3, 2 and 5.
    - That check led to one rule change before L1: class 5 ("blocked") is now main CPU under 50%,
      runnable wait under 20 ms and no clock-client pause. Under the first wording, a gap with 30 ms of
      main-thread CPU and a blocking wait would have been left unclassified.
  - **RESULT.md:** for the 5 A gaps that fell between steps, the runnable-wait and efficiency-core signs are
    now marked "not measured". The measured signs, a clock-client pause and an on-time probe, cover all 7.
    The section 5 rows are labelled as in-step counters.

## Non-blocking

- **N1:** the start-up collection before the loop took 84 ms in K3 run 02. It is stated in PLAN.md,
  reported by K3, and reported (not judged) by L1.
- **N2:** corrected. Under v32 middle collections are not curtailed: 95 middle and 1,155 young in K3, each
  well under 1 ms. Only candidate 1's freeze-only schedule stopped them.
- **N3:** `bench_gc.py` now runs `gc.collect()` before `gc.unfreeze()`. K3 run 02 (`gc_schedule_check/`,
  run 01 kept in `run01/`) passes:

  | Schedule | Frozen garbage | Pending at the end |
  |---|---|---|
  | collect, then freeze (v32) | **0** | 1,772 |
  | freeze only | 146,504 | 8,156 |

  Its longest in-loop collection was 3.84 ms, and the joint states were identical. The criterion
  sharpening was written into PLAN.md before run 02. L1 and L2 report peak RSS, and PLAN.md states the
  worst-case bound for graphs alive at a freeze.
- **N4:** `diag_worker.py` wraps `gc.collect` to mark explicit collections by thread, in a seventh
  gc_events column.
- **N5:** the exposure rule is now by step count only: at least 7,100 control steps.
- **N6:** `sitecustomize.py` keeps append-only buffers flushed by index under a lock shared only by the
  two flush paths, so writers take no lock. `analyze_linux.py` and `analyze_pipeline.py` sort by time.
- **N7:** PLAN.md pre-registers the five-segment split and a fixed rule for blaming each superseded pose
  (bridge timer, worker sender, or transit and receipt). `analyze_pipeline.py` implements it and reads the
  worker's frame records.
- **N8:** `container_site/smoke_check.sh` and `smoke_check_output.txt` are stored. The docstring now
  names `telemetry_frames_enqueued.npy` and `telemetry_frames_sent.npy`.
- **N9:** "coincides with" replaces "matches exactly".
