# v31 physical trial: no stale-input stops in its 29.9 s; the run ends on `odom_stale` on the upper stair flight

Component results in `COMPONENT_RESULTS.md` remain valid. The trial followed
`PHYSICAL_RUN_PLAN.md`, with exactly `v30_historical_full01`'s profile. Only
the native build (`scan64_input_refresh_v31`), the planner YAML path (a
byte-identical copy) and the integration version differed.

## Outcome of `v31_historical_full01`

- **Gates:** the integration-version, native-identity and reviewed-candidate
  gates passed before physics. In the Building review, the automatic native
  layers, historical route length and correct goal level all pass.
- **Navigation failed.** The first failing gate is an `odom_stale` fault at
  about 27.7 s sim.
  - **What tripped it:** the backend's body-pose callbacks paused for 0.288 s
    of wall time (84.543 → 84.831 s on the callback clock), while simulation
    time moved only 5 ms (27.726 → 27.731 s). The gate's limit is 0.25 s.
  - **Finish:** the owner's hold was confirmed at 27.82 s, the failure was
    published at 29.02 s, and physics ended at 29.94 s. The driver finished
    `case_failed`.
  - **Goal and body:** goal XY error is 7.12 m. There is no arrival and no
    final PD hold (0 s). There is no fall, and physics is continuous.
  - **Building review:** `passed=false`, with exactly v30's failing checks.
  - **Local review:** it fails process and driver completion, as v30 did.
    Unlike v30, it passes `no_applied_read_errors_after_first_ack`.
  - **Stop rule:** the diagnostic stop rule was not needed; the run ended by
    itself.
- **Motion** (from `video_states.json` at 12.5 Hz; the Building review's
  numbers are separate):
  - **Start:** the RL policy took over at 12.62 s, and the body was more than
    0.10 m from its takeover position by 13.18 s.
  - **Climb:** it climbed faster than v30.

    | Body z | v31 | v30 |
    |---|---|---|
    | 0.90 m (first landing) | 19.34 s | 22.14 s |
    | 1.40 m | 25.82 s | 30.22 s |
    | 1.65 m (upper landing) | not reached | 34.21 s |

  - **End:** it had no pause after the start. It was still walking, slowing
    from 0.53 to 0.17 m/s between 27.0 and 27.74 s as its local curve neared
    its end. The command dropped to zero with the fault's hold at 27.82 s
    (`STAND_SETTLING`). It then stood on the upper stair flight, finishing at
    (−4.99, −1.40, body z 1.53).
- **Totals:** the actual XY path is 7.78 m and the navigation path 8.33 m
  (Building review). All 9 moving curves passed their final check. The net
  displacement from the takeover is (0.58, −7.49, +1.16) m.

## v31's target: the stale-input signatures

`trial_signatures.py` counts SCAN's own log lines. For v30, the stop
diagnosis's timeline (`audits/2026-09-28_v30_stop_classes/timeline.json`)
gives the sim time of each event, so v30 is counted over the same first
29.94 s:

| First 29.94 s sim | v30 | v31 |
|---|---|---|
| Conflict stops at 0.000 s | 8 (17.19–26.99 s) | 0 |
| Invalidations of the executing curve (`remaining_spline_invalid`) | 5 | 0 |
| Final-curve rejections: `InvalidCurve` / `Collision` | 41 / 1 | 0 / 0 |
| Final checks clear | 7 | 9 |
| "Target is occupied and no collision-free point" (whole route blocked) | 26 lines | 0 |
| "The robot is inside an obstacle" | 1 | 0 |

- **Emergency stops:** v31's only emergency-stop transition is the cancel
  after the fault (`P2B_CANCEL:EXEC_TRAJ`).
- **Where v30 stopped:** v31 passed without stopping at v30's first two
  conflict stops, 17.19 and 17.58 s on the stairs. They are the frozen
  `stairs_replan` and `stairs_hold` states of the contract. The video shows
  the robot climbing there at +0.82 m/s.
- **Input refresh** (`runs/v31_historical_full01/trial_signatures.json`):
  - The four inner sites logged 73 calls, and 40 of them applied messages.
  - The largest ages before a refresh were 0.08 s for the body pose (the
    gate is 0.1 s) and 0.17 s for the processed scan (the gate is 0.25 s).
  - After every inner-site refresh, both ages were under their gates.
  - The timers logged 5 lines, all applying a stale input or carrying a
    negative age. Three of them applied a body pose stamped 5 ms (one
    physics step) ahead of the node's clock. No invalid curve followed any of
    them. No scan was stamped ahead of the clock, and no take failed.

**What this shows and what it does not**
- **Shown:** in the stretch it covered, the start and both stair flights,
  v31 had none of the stale-input signatures that stopped v30 there eight
  times.
- **Not shown:** the run ended before the upper landing. The corridor entry
  and the upper corridor held most of v30's stops (51 of 63 conflict stops)
  and the wrong-height navigation cell, and none of them was reached.
- **One run:** a single run cannot separate v31's effect from run-to-run
  timing variation, which the A* wall-time budget makes large.

## Why the run ended: the wall-clock freshness chain

This is the class that ended v28 (15.56 s) and v30 (69.35 s). `PLAN.md` lists
it as not addressed by v31.

- **Command transport:** 3 reconnects with 3 protocol errors, the last
  `clock_observation_stale` (v30: 1 of each over its whole run). The applied
  command was marked stale at 15.66 s and from 28.94 s. The 11.04–11.08 s
  marks are start-up, as in v30.
- **Clock sync:** it rejected 95 of 3,697 samples (2.6%), a faster rate than
  v30's 143 of 7,656 (1.9%), 43 of them in v30's first 90 s of host time.
  v31's run lasted about 90 s of host time. The p99 round trip was 24.6 ms (v30: 16.9 ms).
- **Body-pose callback gaps:** three exceeded 0.2 s wall (0.204, 0.201 and
  0.288 s), each while simulation time barely moved. v30's largest before
  150 s of wall time was 0.175 s.
- **Bridge:** it recorded one `simulation_clock_stall_events` (v30: 0).
- **Speed:** the simulation ran at about 0.35× real time over the callback
  span (v30: about 0.39×).
- **Cause, not determined:** these numbers are consistent with the known
  chain: rejected clock observations, then command reconnects, then a blocked
  control step, then a physics stall, then the 0.25 s gate. They do not show
  whether v31 contributed.
  - **Possible v31 contribution:** extra load in the planner container, for
    example scans processed inside timer callbacks. It is not measured.
  - **Against it:** v28 failed the same way at 15.56 s, before v31's code
    existed.

## Videos

- **Standard view:**
  `output/2026-09-27_lite3_versions/v31_historical_full_odom_stale.mp4`. This
  is the unchanged renderer; receipt in `video_receipt.json`. The robot is
  visible throughout.
- **Heading-follow view:**
  `output/2026-09-27_lite3_versions/v31_historical_full_odom_stale_heading_view.mp4`.
  `scripts/render_heading_view.py` changes only the display camera, and the
  run is `runs/v31_historical_full01_video02` with its own receipt.
- **Comparison:**
  `output/2026-09-27_lite3_versions/v30_historical_full_odom_stale_heading_view.mp4`.
  It shows v30's last 18 s, which its standard video lost behind the
  upper-corridor wall. The robot stands still in an open corridor on its
  route until `odom_stale`.

## Status

The trial failed: its first failing gate is `odom_stale`. v31 is frozen and
unvalidated, and v3 remains the last accepted navigation condition. Local-only
bytes are inventoried in `LOCAL_ONLY_BYTES.json`; the heading-view renders
have their own inventories.
