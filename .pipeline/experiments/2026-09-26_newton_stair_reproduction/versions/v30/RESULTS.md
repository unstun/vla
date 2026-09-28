# v30 physical trial: the landing stall is gone; the run ends on `odom_stale` in the upper corridor

Component results in `COMPONENT_RESULTS.md` remain valid. The trial followed
`PHYSICAL_RUN_PLAN.md`, with exactly `v29_historical_full01`'s profile. Only
the native build, the planner YAML path (a byte-identical copy) and the
integration version differed.

## Outcome of `v30_historical_full01`

- **Gates and route:** the version, native-identity and reviewed-candidate
  gates passed before physics. In the Building review, the automatic native
  layers, historical route length and correct goal level all pass.
- **v30's target, the landing stall, is gone:**
  - The reference frontier reached 15.64 s of the 73.60 s global path. v29
    never passed 8.6446 s.
  - The robot passed v29's stop on the upper landing, (−5.00, −2.45), at
    34.97 s. That segment took 4 replans; v29 spent 5,515 replans beyond
    y = −0.4 m and never got past it.
- **Timeline:** the RL policy took over at 12.62 s, and the body was more than
  0.10 m from the start by 13.12 s. It climbed faster than v29 and had no
  first-landing pause (v29 paused there from 30 to 42 s).

  | Body z | v30 | v29 |
  |---|---|---|
  | 0.90 m (first landing) | 22.10 s | 26.6 s |
  | 1.40 m | 30.16 s | 46.8 s |
  | 1.65 m (upper landing) | 34.19 s | 60.7 s |

  - **Corridor entry:** the robot then paused about 15 s at the corridor
    entry, (−4.92, −3.46, body z 1.85), from 35.9 to 51.0 s.
  - **Upper corridor:** it walked along the corridor towards +x, and has
    stayed within 0.05 m of its final position,
    (−1.99, −4.25, body z 1.85), since 57.5 s.
- **Totals:** the actual XY path is 13.44 m (v29: 9.77 m), and the net
  displacement is (3.57, −10.36, +1.45) m.
  - There are 17 moving curves (v29: 13).
  - The controller received 117 trajectories, 100 of them fixed 3.000 s
    holds.
- **Navigation still failed.** The first failing gate is an `odom_stale` fault
  at 69.35 s sim (stop flow started at wall 171.05 s).
  - **What tripped it:** the body-pose callbacks paused for 0.264 s of wall
    time (170.747 → 171.011 s), while simulation time moved only 15 ms
    (69.314 → 69.329 s). The gate's limit is 0.25 s.
  - **Finish:** the driver finished `case_failed`.
  - **Goal and body:** goal XY error is 4.15 m (v29: 6.97 m). There is no
    arrival and no final PD hold (0 s). There is no fall (minimum base-up z
    0.946), and physics is continuous.
  - **Building review:** `passed=false`, with the same failing checks as v29;
    no check changed.
  - **Local review:** it fails process and driver completion, as v29 did. It
    also fails `no_applied_read_errors_after_first_ack`: 10
    `applied_snapshot_stale` reads from wall 185.66 s. They come after physics
    had ended (last body callback 183.77 s), during the stop flow.
- **Freshness chain, unchanged by v30:**
  - The clock sync rejected 143 of 7,656 samples (v29: 24 of 7,281). 49 of
    those fall in the last 20 s of host time, when the simulation ran at
    about 0.21× real time (about 0.4× earlier in the run).
  - The command transport had one reconnect and one protocol error
    (`clock_observation_stale`).
  - The wall-clock gate is the class that ended v28 (a 0.344 s stall), and
    `PLAN.md` lists it as not addressed by v30.
- **No crash:** `scan.log`, `native_graph.log` and `run.log` contain no crash.

## Why the robot stopped before the fault

The robot was already stationary for 12 s when the fault fired. Between the
moving curve received at 54.0 s and the next one at 68.6 s, the planner sent
34 fixed 3.000 s hold trajectories.

- **What the planner logged in that window:**
  - 83 `final_spline_rejected status=2` and 12 `status=1` (Collision);
  - 33 `remaining_spline_invalid status=2`, alongside 32 "Obstacle
    discovered" replans;
  - 13 `reactive_collision_blocked` with verdict 6 (UnknownObstacle).
- **What status 2 means:** it is `TrajectoryCheckStatus::InvalidCurve`, not a
  collision. `checkFullCubicTrajectory` returns it when:
  - the spline layout, duration, knots or derivative is invalid; or
  - a sample, its look-ahead point, its velocity or the heading computed from
    them is non-finite.
- **Emergency stops:** in the upper corridor segment (155 replans, 3
  committed), the FSM went to `EMERGENCY_STOP` 33 times on
  `INVALID_SPLINE_INPUT` and 31 times on `SAFETY`.
- **The same pattern earlier:** it produced the pause at the corridor entry
  (227 replans, 5 committed, 50 `INVALID_SPLINE_INPUT` and 16 `SAFETY`
  emergency stops).
- **Stance mode:** from 56.4 s it flipped between RL and the stand modes about
  50 times, until the hold at 69.35 s. The commands were small, with
  |vx| + |vy| + |wz| at most 0.32.

Which condition makes these curves invalid is not yet diagnosed, and this
record claims no cause. It is a different class from the v29 landing stall,
and v30 did not change it.

Update, 2026-09-28: diagnosed afterwards from saved inputs in
[`audits/2026-09-28_v30_stop_classes`](../../audits/2026-09-28_v30_stop_classes/RESULT.md).
Status 2 is a heading left undefined when the body pose is older than 0.1 s
on a nearly stationary sample. The emergency stops at 0.000 s most likely
follow a processed scan older than 0.25 s (inferred: no line logs the scan
age at a stop, though one planning callback's own lines show the processed
scan pass 0.25 s). Both ages grow while planning blocks SCAN's
single-threaded executor.

## Planner statistics

- **Replans:** 508 in total (v29: 6,002), with 17 committed.
- **Emergency stops:** 153 (v29: 552).
- **Seed searches with status 2:** 98 (v29: 4,374).
- **A* pool errors:** 280 (v29: 5,503).
- **Rebound-guard aborts:** 11 (v29: 65).
- **Full-curve rejections:** 137 with status 1 (Collision) and 131 with
  status 2 (InvalidCurve).
- **Remaining-curve invalidations:** 89, all with status 2.

Grouped by the planner's start position (`start:` lines):

| Segment | Replans | Committed | `INVALID_SPLINE_INPUT` stops | `SAFETY` stops |
|---|---|---|---|---|
| Start area | 10 | 2 | 0 | 0 |
| First flight and landing | 52 | 2 | 2 | 4 |
| Second flight | 60 | 4 | 3 | 1 |
| Upper landing (v29's stop) | 4 | 1 | 0 | 0 |
| Corridor entry (−4.92, −3.46) | 227 | 5 | 50 | 16 |
| Upper corridor (x > −4.5) | 155 | 3 | 33 | 31 |

## Evidence

- **Raw run:** `runs/v30_historical_full01/`. The reviews are in
  `validation/v30_historical_full01_review.json` and `_building.json`.
- **Video:** `output/2026-09-27_lite3_versions/v30_historical_full_odom_stale.mp4`
  (71.4 s, 892 frames, SHA256 `6a98b17e…`), with the renderer unchanged from
  v29.
  - **Checks:** it is fully decoded, and six frames were visually checked
    (`video_receipt.json`).
  - **What it shows:** the climb, the upper landing past v29's stop and the
    corridor entry.
  - **Limitation:** from about 53.6 s the unchanged follow camera sits behind
    the corridor wall. The last 18 s show only the wall, with the overlay
    still reporting the state, ending in "Navigation: failed (odom_stale)".

## Status

v30 is frozen and unvalidated, and its component scope passed. In its one
physical trial it removed the landing stall: the robot crossed the upper
landing and walked about 3.7 m further than v29. It did not arrive. v3 remains
the last accepted navigation condition.

Still open:
- the invalid-curve holds at the corridor entry and in the upper corridor
  (diagnosed afterwards: input-age gates; see the update above);
- the wall-clock freshness class (`odom_stale`, which ended v28 and v30);
- the emergency-hold feedback;
- the 13 cm protrusion choice;
- drop handling, which this map can no longer exercise under v30;
- full-floor navigation, the final PD handoff and Isaac A4.
