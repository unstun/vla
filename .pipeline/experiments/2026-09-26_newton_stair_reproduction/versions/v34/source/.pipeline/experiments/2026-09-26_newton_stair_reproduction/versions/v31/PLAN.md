# v31: SCAN refreshes pose and scan inputs before each collision-deciding step

Stage: experiment + analysis. Parent: v30.

**Decisions.**
- **Option 1 (2026-09-28).** After the v30 stop diagnosis, Dr Sun chose to
  keep SCAN's pose and scan inputs fresh while it plans.
- **Narrower means (2026-09-28).** The first candidate kept the
  single-threaded executor and left bounded planning out, although option 1
  had been offered with two means: separate callback groups on a
  multi-threaded executor, and time-bounded planning. The first independent
  review flagged this as blocking (B4), because no record showed Dr Sun
  accepting it. He then decided in chat: "keep the narrower design, fix all
  findings, and continue, give me videos". So v31 keeps take-and-apply on the
  single-threaded executor, and bounded planning is a later version.

The first candidate, `runtime/scan63_input_refresh_v31`, is superseded by
`runtime/scan64_input_refresh_v31`. Its records are kept in `attempt01/`
(README there).

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

## Design

- **No multi-threaded executor.** The pose and scan callbacks write the
  GridMap's occupancy buffers, sliding-map origin and reactive state. Every
  planning query reads them without a lock. Running the callbacks
  concurrently would need a lock on every GridMap access that A*, the
  optimizer and the checks use, and it would let the map change in the middle
  of an A* search or a curve check.
- **Take and apply at safe points.** At the start of each collision-deciding
  step, v31 takes the pending pose and scan messages directly from their
  subscriptions (`rclcpp::Subscription::take`, in the pinned rclcpp 16.0.12).
  It applies them through the unchanged callbacks, in stamp order, on the
  executor's thread. Each step then starts from the newest received inputs,
  and the map never changes inside a step.
- **Bounded planning is a later version.** It changes which plans succeed,
  and the project rule is one logical change per version.

## Exact change

`materialize.py` copies `runtime/scan62_support_evidence_v30` to
`runtime/scan64_input_refresh_v31` and inserts lines into five files. It
removes nothing.

1. **`plan_env/include/plan_env/grid_map.h`:** declares
   `refreshSensorInputs(const char *site, int fsm_odometry = -1)`.
2. **`plan_env/src/grid_map.cpp`:** implements it.
   - **Drain order.** It takes every pending message from the `cloud`,
     `sensor_pose` and `body_pose` subscriptions, in that order. This is the
     reverse of the bridge's publication order (pose, then cloud, with one
     stamp), so a scan pair that arrives during the drain cannot leave its
     cloud taken without its pose.
   - **Order of application.** It sorts the messages by header stamp, read as
     plain numbers. Ties keep subscription creation order (sensor pose, cloud,
     body pose), as the executor would serve them.
   - **Callbacks.** It applies them through `sensorPoseCallback`,
     `cloudCallback` and `slidingMapFrameCallback`, all unchanged.
   - **Take errors.** A failed `take` (`rclcpp::exceptions::RCLError`) is
     logged and ends that subscription's drain, as the executor's
     `take_and_do_error_handling` logs and skips it.
   - **Logging.** It logs `input_refresh` with the counts applied and the
     processed-scan and body-pose ages before and after. At the four sites
     inside a callback it logs every call. At the two timers it logs only a
     scan applied while the processed scan was older than 0.15 s, a body pose
     applied while the pose was older than 0.05 s, or any input stamped ahead
     of the clock. These thresholds only select log lines.
3. **`plan_manage/src/scan_replan_fsm.cpp`:**
   - **Timers.** It calls the refresh at the start of the planning timer
     (`exec`) and of the safety timer (`safety`). Just before, a file-local
     helper takes the FSM's own pending `body_pose` messages and applies them
     through the unchanged `odometryCallback`, so `odom_pos_` and `odom_vel_`
     are as fresh as the map's body pose. The count is logged as `fsm_odom`.
   - **Target check.** It calls the refresh at the start of
     `adjustGlobalTargetIfOccupied` (`target_check`), before the final-point
     check, the goal-neighbourhood A* search and the route walk. A route
     message (`p2bRouteCallback`) reaches this function without a timer.
4. **`plan_manage/src/planner_manager.cpp`:** calls the refresh at the start of
   each replan attempt (`replan_start`), which also covers the fixed-height
   recovery and the prefix proposals. It calls it again before the final
   full-curve check (`final_check`).
5. **`bspline_opt/src/bspline_optimizer.cpp`:** calls the refresh at the
   start of each rebound round (`rebound_round`).

**Byte identity.** Every other v30 byte is unchanged, and the planner YAML
files are byte-identical copies.
- **Materialization.** `materialize.py` edits raw bytes. Inserted lines take
  the line ending of the anchor line they follow. The `grid_map.cpp`
  insertion has no anchor before it, so it takes the ending of the line after
  it. `grid_map.h`, `grid_map.cpp` and `bspline_optimizer.cpp` mix CRLF and
  LF lines. It asserts two things:
  removing the inserted lines gives back v30's bytes, and the CR count grows
  only by the inserted CRs.
- **Patch.** `changes.patch` applies to v30's five files and reproduces
  v31's bytes exactly. `parent_source/` holds v30's bytes.

## Preserved

- **Inputs:** the same callbacks process the same messages, in stamp order.
  The `SensorDataQoS` depth of 5 is unchanged. Because the refresh drains the
  queues more often than the executor does during a long callback, fewer
  messages are dropped than in v30.
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
   interval. Only refresh lines between the call's begin and end markers
   count.

   | Case | Setup | Red (v30) | Green (v31) |
   |---|---|---|---|
   | C1 stale scan, nothing pending | clock +0.30 s, body pose re-stamped, safety timer called | conflict stop | the same conflict stop; nothing applied |
   | C2 stale scan, scans pending | as C1 with the run's scans and poses of those 0.30 s pending | conflict stop | clear; the processed scan is the newest pending one; `odom_pos_` and the map's body pose are the newest pending pose |
   | C3 stale pose, poses pending | clock +0.15 s, body pose not re-stamped, the run's body poses pending | re-check equals the diagnosis's stale-pose row at Δ = 0.15 s; stops exactly when that row is `InvalidCurve` | clear, body age under 0.1 s; `odom_pos_` is the newest pending pose |
   | C4 planning, scans pending | as C2, then one planning-timer call in the state's FSM entry | fails in its entry state with the whole route blocked | applies the inputs at `exec`; no stale signature; `odom_pos_` is the newest pending pose |
   | C5spin | as C2, but the executor processes the pending inputs | map digest equals green's | map digest equals green's C2 |
   | C6 inputs arrive during a planning call | as C4, but only the second scan and what precedes it are pending; a helper thread publishes the rest during the call, the last scan's pose and cloud in adjacent batches | no refresh; final map digest equals red C5spin | refresh lines at `target_check`, `replan_start`, `rebound_round` and `final_check`; at least one message applied there; final map digest equals green C5spin |
   | C7 split batches | five batches {p1, c1, bodies}, {p2}, {c2, bodies}, {c3}, {p3, bodies}, each followed by an executor spin (C7spin) or one direct refresh (C7refresh, green only) | C7spin | C7refresh and C7spin: per-batch records and final digest equal red C7spin |

   - **C4 green and the diagnosis.** Green's C4 plan result is recorded beside
     the diagnosis's replan at Δ = 0, not compared with it. Green plans 0.30 s
     later, from newer inputs and a later start point. The first plan's green
     cell ("the result at Δ = 0") was never tested and does not hold at the
     corridor entry (review finding B2).
   - **C7 batch 4.** Its cloud has its pose only in batch 5. Both paths apply
     it with the previous pose, as v30's executor would. v31 does not repair
     a cloud delivered before its own pose.
   - **Where the criteria come from.** C1–C5 keep the criteria corrected
     after the first contract's first judgement (`attempt01/`: the red C3
     cell had been mis-transcribed from the diagnosis, and the red C4 test
     was added). C6, C7 and the odometry checks answer review findings N4 and
     N6.
     - **Fixed before the run:** the cases and this table.
     - **Written during the run:** the analyzer, before any output was
       inspected. Its first version's file time is 7 s after the first two
       outputs (both C1) and before every C2–C7 output. The v31 directory is
       untracked, so git cannot date either file (round-2 review NB2).

   **Correction after this contract's first judgement (2026-09-28).**
   - **What failed:** the first judgement
     (`input_refresh_contract/summary_first_judgement.json`, from
     `analyze_first_judgement.py`) failed one check in all four states,
     "C1 green applies nothing". It had implemented this cell's "nothing
     applied" as "no refresh line in the call".
   - **Why that was the wrong test:** v31 now logs every call at the inner
     sites. Green's safety callback replans after its conflict, as red's
     does, and each replan attempt passes `target_check`. So green C1 logs
     three `target_check` lines per state, all applying nothing.
   - **Corrected test:** every refresh line in the call applied no message.
     C5's "applies nothing" uses the same test; it passed under both.
   - **Unchanged:** every other criterion and every case output. Green C1's
     stop and map digest equal red's in all four states.
3. **Saved states** (`runs/v31_saved_states02`): the seven saved start states
   and the frozen landing and onset states, with v30's suite. Expected:
   - outputs identical to v30's;
   - logs identical once `input_refresh` lines that applied nothing are
     removed. Any line that applied something is a difference to explain.
     Since the round-2 review (NB4), a line with a negative age is also kept
     as a difference; the rerun reviews are unchanged, since no line had one.
4. **Native regression** (`runs/v31_native_regression03`): the complete v30
   suite, run with no other container on the Docker VM. The same expectation
   as step 3. Every difference is explained before freezing; A* wall-budget
   flips are judged against the paired timing control
   (`runs/v31_regression_timing_control01`, run on the first candidate with
   byte-identical A* code).
5. **Independent review:** a read-only re-review of the change, the contract
   and the evidence, including every first-round finding.
6. **Freeze, then one physical trial:** the historical full route with
   `v30_historical_full01`'s profile.
   - **Expected:** far fewer conflict stops at 0.000 s and invalid-curve stops
     on holds. `input_refresh` lines should show ages falling from above a
     gate to below it.
   - **Not expected to change:** the collision rejections at the wrong-height
     navigation cell (47, 41), which v31 does not touch. The robot may still
     stop in the upper corridor there.

## Claim boundary and residual risk

- **Freshness is per site, not per query.** Between two sites, a step can
  contain several A* searches, each with a 0.2 s wall-time budget:
  - the seed search, and one per collision segment in `initControlPoints`,
    all before the first `rebound_round`;
  - one per segment inside each round's collision check.

  At v30's sim-to-wall ratios (0.39–0.43), a search that uses its whole
  budget takes about 0.08 s sim. So two such searches in one step can pass
  the 0.1 s pose gate before the next site; several can pass the 0.25 s scan
  gate. Only `final_check` is certain to
  judge the final curve on the newest received inputs. The inner-site
  `input_refresh` lines (the age before each refresh) measure this in the
  trial.
- **Inputs stamped ahead of the clock.** Every freshness test treats a stamp
  ahead of `now()` as stale, and `now()` comes from the `/clock` thread.
  - **Body poses:** the bridge publishes `/clock` and then the body pose
    with the same stamp. So a body pose applied just before a decision,
    before the clock thread has processed that `/clock`, reads as stale.
  - **Scans:** a scan stamped ahead of `now()` would turn every query into
    `StaleInput`. That is the conflict-stop and whole-route signature v31
    targets. The bridge publishes each scan about 0.020 s after its stamp, so
    this needs the clock thread to lag by more than that.

  v31 applies the newest inputs immediately before decisions, which may make
  either case more frequent than in v30. A negative age is logged at every
  site, and `trial_signatures.py` reports the minimum after-age and the
  number of negative ones for both inputs.
- **The map can differ between steps of one attempt.** The target check, the
  optimizer and the final check can see different scans; the final check
  always sees the newest.
- **FSM odometry.** It is refreshed at the two timers only.
  - **Within a callback:** the map's body pose can become newer than
    `odom_pos_`. In the reference-path mode used here (`fsm.navi_mode: 3`),
    the FSM reads `odom_pos_` for decisions at the start of a callback (start
    states, emergency-stop placement, the stillness test). During planning it
    only checks it for finiteness.
  - **Latent, other mode only:** in preset-waypoint mode (`navi_mode` 2), the
    first odometry message starts the preset plan inside
    `odometryCallback`. With v31 that can happen inside the refresh at the
    start of the planning timer, so the preset plan and a `GEN_NEW_TRAJ`
    step can fall in one callback. This trial does not use that mode.
- **Extra time.** Processing a scan inside a timer callback adds its cost to
  that callback. The contract measures it.
- **Pairing.** A cloud delivered before its own sensor pose is applied with
  the previous pose, as on v30's executor path (C7 batch 4).
- **Not addressed:**
  - the wrong-height navigation cell;
  - the 5 unexplained "inside an obstacle" messages at the corridor-entry
    corner;
  - the wall-clock `odom_stale` class;
  - the collision model and continuous replanning;
  - bounded planning.

Only a physical run can support a navigation claim. v3 remains the last
accepted condition until one passes.
