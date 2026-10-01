# v31: SCAN refreshes pose and scan inputs before each collision-deciding step

Stage: experiment + analysis. Parent: v30. Dr Sun chose option 1 on
2026-09-28, after the v30 stop diagnosis: keep SCAN's pose and scan inputs
fresh while it plans.

## Motivation

`audits/2026-09-28_v30_stop_classes/RESULT.md` traces the v30 stops from saved
inputs:

- SCAN serves its 10 ms planning timer, 50 ms safety timer and the pose and
  scan subscriptions on one `SingleThreadedExecutor`. `/clock` runs on its own
  thread, and ready timers are served before subscriptions.
- Planning callbacks last up to 0.85 s wall (0.21 s sim, a lower bound).
  Pose and scan messages that arrive meanwhile wait, while their age grows.
- Two unchanged input-age gates then fail:
  - a body pose older than 0.1 s leaves a nearly stationary sample without a
    heading, so it is `InvalidCurve`;
  - a processed scan older than 0.25 s turns every query into `StaleInput`.
- In `v30_historical_full01` this most likely produced the 63 conflict stops
  at 0.000 s, the 89 invalidations of the executing curve, the 131 tail
  rejections and 48 of the 53 "inside an obstacle" messages. One planning
  callback's own lines show the processed scan ageing from 0.090 s to
  0.2501 s.

## Design choice

Option 1 as offered named two means: separate callback groups on a
multi-threaded executor, and time-bounded planning. v31 keeps the goal and
uses a narrower means.

- **No multi-threaded executor.** The pose and scan callbacks write the
  GridMap's occupancy buffers, sliding-map origin and reactive state. Every
  planning query reads them without a lock. Running the callbacks
  concurrently would need a lock on every GridMap access that A*, the
  optimizer and the checks use. It would also let the map change in the
  middle of an A* search or a curve check.
- **What v31 does instead.** It keeps the single-threaded executor. At the
  start of each collision-deciding step it takes the pending pose and scan
  messages directly from their subscriptions (`rclcpp::Subscription::take`,
  present in the pinned rclcpp 16.0.12) and applies them through the
  unchanged callbacks, in stamp order. Each step then starts from the newest
  received inputs, and the map never changes inside a step.
- **Bounded planning is left out.** It changes which plans succeed, and the
  project rule is one logical change per version. With refreshed inputs, the
  length of a callback no longer ages the inputs from one step to the next.
  If the trial shows that long callbacks still harm execution, for example
  through safety-check latency, bounding becomes its own version.

## Exact change

`materialize.py` copies `runtime/scan62_support_evidence_v30` to
`runtime/scan63_input_refresh_v31` and changes five files.

1. **`plan_env/include/plan_env/grid_map.h`:** declares
   `refreshSensorInputs(const char *site)`.
2. **`plan_env/src/grid_map.cpp`:** implements it.
   - It takes every pending message from the `sensor_pose`, `cloud` and
     `body_pose` subscriptions.
   - It sorts them by header stamp, with ties in subscription creation order
     as the executor would serve them.
   - It applies them through `sensorPoseCallback`, `cloudCallback` and
     `slidingMapFrameCallback`, all unchanged.
   - It logs `input_refresh` when it applied a scan while the processed scan
     was older than 0.15 s, or a body pose while the pose was older than
     0.05 s. These thresholds only select log lines.
3. **`plan_manage/src/scan_replan_fsm.cpp`:** calls it at the start of the
   planning timer (`exec`) and of the safety timer (`safety`). It also calls it
   in `adjustGlobalTargetIfOccupied` before the route walk (`route_walk`),
   after the goal-neighbourhood A* search.
4. **`plan_manage/src/planner_manager.cpp`:** calls it at the start of each
   replan attempt (`replan_start`), which also covers the fixed-height recovery
   and the prefix proposals, and before the final full-curve check
   (`final_check`).
5. **`bspline_opt/src/bspline_optimizer.cpp`:** calls it at the start of each
   rebound round (`rebound_round`).

Every other v30 byte is unchanged, and the planner YAML files are copied
unchanged.

## Preserved

- **Inputs:** the same three callbacks process the same messages. Queued
  messages are all applied, in order. The `SensorDataQoS` depth of 5 is
  unchanged, so older messages are dropped exactly as in v30.
- **Gates:** 0.1 s pose, 0.25 s scan and 86,400 s terrain. `StaleInput` still
  blocks.
- **Execution:** single-threaded. All map reads and writes stay on the
  executor's thread, and timers, periods and QoS are unchanged.
- **Planner:** the collision model, A* and optimizer limits, all manager
  gates, the controller and the emergency hold.

## Acceptance plan and expected signals

1. **Build** in the pinned image with the scan62 incremental cache. Source
   identity is checked before and after.
2. **Red/green input-refresh contract** (`input_refresh_contract/`). One probe
   source is built against v30 (red) and v31 (green). It replays each of the
   four frozen stop states from the stop diagnosis, then runs one case per
   process. "Pending" means published but not spun, as during a long
   callback; the pending scans and poses are the run's own, from the same
   interval.

   | Case | Setup | Red (v30) | Green (v31) |
   |---|---|---|---|
   | C1 stale scan, nothing pending | clock +0.30 s, body pose re-stamped, safety timer called | conflict stop | the same conflict stop |
   | C2 stale scan, scans pending | as C1 with the run's scans of those 0.30 s pending | conflict stop | clear; the processed scan is the newest pending one |
   | C3 stale pose, poses pending | clock +0.15 s, body pose not re-stamped, the run's body poses pending | holds: `InvalidCurve` at sample 0; moving curve: clear | clear |
   | C4 planning, scans pending | as C2, then one planning-timer call in the state's FSM entry | fails with a stale-scan signature | the result at Δ = 0 |

   C5 checks equivalence: applying the same pending messages through the
   refresh and through the executor must give byte-identical occupancy
   buffers and reactive state.

   **Correction after the first judgement (2026-09-28).** The red C3 cell for
   moving curves ("moving curve: clear") was mis-transcribed from the stop
   diagnosis. Its `RESULT.md` §2, committed in b3a172e5 before this contract
   ran, records that with a stale pose a curve ending at rest fails as
   `InvalidCurve` in its last ~0.1 s. Its `stairs_replan` row at Δ = 0.15 s is
   `InvalidCurve` at 3.9526 s.
   - **First judgement:** failed on exactly this cell. Red stopped on the
     `stairs_replan` curve at that time and sample count
     (`input_refresh_contract/summary_first_judgement.json`).
   - **Corrected criterion:** red's C3 re-check must equal the diagnosis's
     stale-pose row at Δ = 0.15 s (status, time, samples and `raw_t`), and red
     must stop exactly when that row is `InvalidCurve`. That means the holds
     and `stairs_replan` stop, and the corridor entry stays clear.
   - **Also tested now:** red's C4 whole-route block, which the contract
     described but did not test.
   - **Unchanged:** the green criteria and every case output.
3. **The frozen landing and onset states and the seven saved start states**
   (v30's suite) on v31: outputs identical, since replays leave nothing
   pending.
4. **The complete v30 native regression suite** on v31: identical outputs;
   every difference explained before freezing.
5. **Independent review:** a read-only review of the change, the contract
   and the evidence.
6. **Freeze, then one physical trial:** the historical full route with
   `v30_historical_full01`'s profile.
   - **Expected:** far fewer conflict stops at 0.000 s and invalid-curve stops
     on holds, and `input_refresh` lines whose ages fall from above a gate to
     below it.
   - **Not expected to change:** the collision rejections at the wrong-height
     navigation cell (47, 41), which v31 does not touch. The robot may still
     stop in the upper corridor there.

## Claim boundary and residual risk

- **Freshness is per step.** A single step, such as one A* search with its
  0.2 s wall-time limit or one optimizer round, still ages its inputs. At the
  v30 run's ratio of sim to wall time (about 0.4), one such search is about
  0.08 s sim, inside both gates' remaining margins. Other ratios are not
  covered.
- **The map can differ between steps of one attempt.** The route walk, the
  optimizer and the final check can see different scans; the final check
  always sees the newest.
- **Extra time.** Processing a scan inside a timer callback adds its cost to
  that callback. The contract probe measures it.
- **Not refreshed:** the FSM's own odometry subscription (start states).
- **Not addressed:** the wrong-height navigation cell, the 5 unexplained
  "inside an obstacle" messages at the corridor-entry corner, the wall-clock
  `odom_stale` class, the collision model and continuous replanning.

Only a physical run can support a navigation claim. v3 remains the last
accepted condition until one passes.
