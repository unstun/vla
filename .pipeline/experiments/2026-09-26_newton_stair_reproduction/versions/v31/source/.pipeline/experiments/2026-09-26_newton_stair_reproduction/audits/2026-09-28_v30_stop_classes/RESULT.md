# v30 stops and invalid curves: diagnosis from saved inputs

Stage: experiment + analysis, 2026-09-28. This is diagnosis only: no version,
no threshold change and no physics. All replays use the pinned local Humble
image, the v30 native sources (`runtime/scan62_support_evidence_v30`) and the
run's planner YAML (`ec120d81…`, identical to `versions/v30/building_planner.yaml`).

Dr Sun's questions after the v30 trial:
1. SCAN seems to replan only when it reaches the end of a path. Why is the
   motion stop-and-go instead of continuous?
2. Is the car-like collision envelope stopping the robot? His rule: the legs
   may touch obstacles; only the main body must not collide.

## Answer in brief

- **Nothing near the robot caused the conflict stops, as far as the evidence
  reaches.**
  - At the four frozen stops, with fresh inputs, three things were clear:
    the curve's current point, the executing curve, and a hold there. Every
    map return inside the footprint circles was terrain, and a replan
    succeeded in three of the four.
  - For all 63 conflict stops the evidence is a different one. The stopping
    callback found no free sample anywhere on the route, including route the
    robot had already walked. An obstacle near the robot does not explain
    that.
- **Two input-age gates most likely produced the stops and holds.** SCAN's
  planning work delays its own pose and scan callbacks while its sim clock
  keeps running.
  - A body pose older than 0.1 s leaves the heading of a nearly stationary
    sample undefined. Holds and the ends of curves that stop then fail as
    `InvalidCurve` (status 2).
  - A processed scan older than 0.25 s turns every query into a silent
    `StaleInput`. The whole route and the robot's own point are then blocked,
    and the safety check stops with the conflict 0.000 s ahead.
  - How this is established:
    - **Elimination:** four conditions in the code block every query. In this
      run the other three are off or unlikely after start-up (§2).
    - **Sufficiency:** pure clock advance in the replay reproduces every stop
      and hold signature.
    - **Live readings:** SCAN's own lines show a pose age of 0.160 s. In one
      planning callback they also show a processed scan exceeding the 0.25 s
      limit:
      0.090 s old at line 274 and 0.2501 s old at line 350, with no scan
      processed in between (§4). No line prints the scan age at a stop, so
      the stops' scan ages are inferred.
- **The reproduced collision rejections come from the static support map,
  not from an obstacle.**
  - 112 of the 137 live collision rejections reproduce.
  - 109 of them fail at one cell of PCT's navigation ground, 0.06 m from the
    route and 2.6 m into the corridor, recorded at the landing height
    (1.419 m) instead of the floor (1.561 m).
  - The other 3 fail where the selected walkway is narrow at the corridor
    corner.
  - None involves a measured return at leg height or body height.
  - 25 do not reproduce; three untested explanations are listed under
    Boundary.
- **Partly open:** 53 "The robot is inside an obstacle" messages during
  planning.
  - In 48 the curve's start and its end were both blocked, as a block of
    every query produces. The most likely cause is the scan exceeding the
    0.25 s limit during the callback; the replays cannot test this.
  - 5, at the corridor-entry corner, are not explained (see Open item).

## 1. What the live log shows

`timeline.py` (→ `timeline.json`) reads `runs/v30_historical_full01` only.
Container log time maps to sim time through the applied-command snapshots,
with an offset fitted on 31 log lines that print both (residual median 0.003 s,
max 0.021 s). Locations come from the recorded body pose at each stop
(torso above 1.80 m means the upper floor; x ≤ −4.5 m there is the corridor
entry).

| Item | Count | Detail |
|---|---|---|
| Emergency-stop transitions by the safety callback | 152 | 63 conflict stops ("Obstacle discovered") and 89 invalid-curve stops (`INVALID_SPLINE_INPUT`: 88 from GEN_NEW_TRAJ, 1 from REPLAN_TRAJ) |
| Conflict stops | 63 | all with the conflict 0.000 s ahead; 52 from GEN_NEW_TRAJ while holding, 11 from REPLAN_TRAJ; 10 on the stairs and landings, 21 at the corridor entry, 32 in the upper corridor |
| …whose replans reported the whole route blocked | 58 (+1 once) | "Target is occupied and no collision-free point was found on the global trajectory", three times each |
| …whose route walk ended silently | 4 | explained in §2 |
| …whose replans found a free route sample | 0 | |
| 3 s holds | 102 published, 100 received | the controller received 89 after invalid-curve stops and 11 after conflict stops from REPLAN_TRAJ; the last two (118, 119) followed the final route cancel (`P2B_CANCEL`, line 11042) and never reached it; the 52 conflict stops while holding published none (`flag_escape_emergency_` was false) |
| Invalidations of the executing curve | 89 | all status 2 before the first sample (`samples=0`); 88 on a 3 s hold, 1 at raw_t 2.456 s, past the end of the 2.296 s first curve |
| New curves rejected with status 2 | 131 | all 0.06–0.15 s before the curve's end, after ≥ 95 clear samples |
| New curves rejected with status 1 (collision) | 137 | median at 86% of the curve's duration |
| "The robot is inside an obstacle" | 53 | in 50 planning callbacks, each of which had found a free route sample earlier; 48 followed by "Trajectory terminal point is in an obstacle; skip this plan"; 25 in the first optimization, 28 in the fixed-height recovery; see Open item |

**Inputs published to SCAN (sim time).**
- Scans arrive every 0.100 s, each published 0.020 s after its stamp
  (`published_at_physics_s`). Body poses arrive every 5 ms (max gap 35 ms).
- Had SCAN processed each scan on arrival, the newest scan at each stop would
  have been 0.059–0.080 s old.

**Ages printed by SCAN itself.**
- **Body pose** (`initial_spline_collision`): two moments, each logged twice,
  at 0.015 s and 0.160 s.
- **Processed scan** (`reactive_collision_blocked`, which prints the stamp of
  the last processed scan): 27 lines, with ages 0.045–0.235 s.
  - At those moments the newest published scan was at most 0.105 s old, or
    0.120 s if line 7756 counts.
  - So, at the moment of printing, SCAN was current in 13 lines, one scan
    behind in 12 and two scans behind in 1. Part of this is the callback's
    own duration, since no scan is processed inside a callback. Line 7756 cannot be decided: its newest scan was published
    within 0.5 ms of the printed `now`.
  - These lines print only for a scan at most 0.25 s old, so they cannot
    show a stale scan.
  - A later line of the same callback can. `scan_age_bounds.py` pairs each
    printed stamp with the later `now=` lines of its callback. There are two
    such moments, each logged twice: 0.090 s at lines 233 and 236, and
    0.2501 s at lines 350 and 351 (§4).

## 2. The two gates in the v30 code

- **Pose gate, 0.1 s.** `motionHeading` (`plan_env/motion_heading.h`) returns
  the measured body yaw only if the body pose is at most 0.1 s old; otherwise
  it returns NaN. It needs the body yaw only for motion that is too small to
  give a heading:
  - For a trajectory sample, that means a 0.8 s look-ahead that moves less
    than 1 cm and a horizontal velocity below 0.01 m/s
    (`collisionTrajectoryYaw`, `scan_reactive_grid_methods.inc:307–313`).
  - For a route segment (`estimateYawFromSegment`), it means a segment
    shorter than 1 cm.

  What a NaN heading does:
  - `checkFullCubicTrajectory` returns `InvalidCurve` at that sample.
    `samples` counts only samples with a finite heading
    (`bspline_opt/full_trajectory_collision.h`).
  - A hold never moves, so it fails at sample 0. A curve that ends at rest
    fails in its last ~0.1 s. A curve that keeps moving never needs the
    fallback.
  - The frontier walk's first route samples then return `false` without a
    log line. These are the 4 "silent" stops.
  - The v29 blind-zone waiver (`knownNavigationFootprintInterior`) uses the
    same 0.1 s test.
- **Scan gate, 0.25 s.**
  - `grid_map.reactive_cloud_max_age` defaults to 0.25 s, and the run's YAML
    does not set it. `CollisionDecision::decide` returns `StaleInput` when
    the last processed scan is older.
  - `reactiveFootprintSupportQuery` calls `decide` first. Every query passes a
    body reference, and `reactiveOccupancy` then returns 1 without logging.
    So a stale scan blocks every query, silently: the robot's own point,
    every route sample and every candidate.
- **Terrain gate: effectively off.** `grid_map.reactive_tomogram_max_age`
  defaults to 86,400 s, and the grounds are published once.
- **Two more blocks of every query, both unlikely after start-up here.**
  - No processed scan. `cloudCallback` clears `reactive_cloud_ready_`
    (`grid_map.cpp:924`) and sets it again at the end of the same callback,
    once the scan is processed (`:1002–1003`, `:808`). An early return, or a
    new ground message, leaves it false, and `decide` returns `MissingInput`
    for every query.
  - No surface ground: `reactiveOccupancy` returns 1 at once.
  - In this run both grounds were published once, the log has no
    "no sensor_pose" warning, and every scan has at least 9,370 points
    (`scan_age_bounds.json`). The stale-scan gate is therefore the only block
    of every query expected to switch on and off during the run.

## 3. Replays at four frozen stops

`prepare_inputs.py` is the landing-stall freezer with the source run and the
stops changed. Each state is frozen at the last recorded body pose at or
before the stop. It replays:
- the original scans and paired poses;
- the executing spline, with its trajectory ID checked against the
  controller's receipts;
- the route and the last committed window.

The navigation and surface grounds match the live publishers (`97d2dfbd…`,
`b68527dd…`).

| State | Stop | Sim time | Scans | Executing | Body (m) |
|---|---|---|---|---|---|
| `stairs_replan` | 1, REPLAN_TRAJ, silent route exit | 17.187 s | 61 | curve 3 | (−5.384, 4.463, 0.649) |
| `stairs_hold` | 2, GEN_NEW_TRAJ, route blocked ×3 | 17.582 s | 65 | hold 4 | (−5.379, 4.349, 0.633) |
| `corridor_entry_replan` | 23, curve flagged after commit | 46.671 s | 356 | curve 63 | (−4.913, −3.479, 1.841) |
| `upper_corridor_hold` | 50, GEN_NEW_TRAJ, route blocked ×3 | 62.557 s | 515 | hold 99 | (−2.022, −4.273, 1.854) |

`stop_probe` (`make_probe.py`, `probe_derivation.json`) is the unchanged v30
regression `gen_probe` input replay (`bac7c07e…`) followed by a read-only
analysis.
- **Sweep.** It advances the node clock by Δ without delivering any new scan
  or pose. At each Δ it runs, with the native functions:
  - the safety check of the executing curve (as `checkCollisionCallback`);
  - the full check from t = 0;
  - a hold at the curve's current point (the `EmergencyStop` shape);
  - that point itself;
  - `adjustGlobalTargetIfOccupied`, and a per-sample route profile.
- **Which point.** "The curve's current point" is the reference the safety
  check tests. The live emergency stop places its hold at the measured body
  position instead, 0.12 m away in `stairs_replan`.
- **Second mode.** A second run re-stamps the recorded body pose at every Δ,
  so only the scan ages.
- **Breakdown.** At Δ = 0 and Δ = 0.4 s both footprint circles are repeated
  step by step. They match the native functions: 0 circle and 0 support
  mismatches in all eight runs.
- **Replans.** Replans are tried at Δ = 0, 0.11 and 0.3 s with the FSM's own
  entry for the state.

### Fresh inputs (Δ = 0: pose age 0, scan age 0.060–0.065 s)

| State | Safety check | Hold | Current point | Frontier (live) | Route samples free | Replan |
|---|---|---|---|---|---|---|
| `stairs_replan` | clear | clear | free | 5.547 s (5.5465 s) | 104 | succeeds |
| `stairs_hold` | clear | clear | free | 5.547 s | 104 | succeeds |
| `corridor_entry_replan` | clear to the end | clear | free | 14.441 s | 177 | fails (status 1, see §5) |
| `upper_corridor_hold` | clear | clear | free | 15.640 s (15.64 s) | 186 | succeeds |

Footprint circles at the current point: every contributor inside the
inflation volume was classified terrain (stairs 89/97 and 63/129,
corridor 39/79 and 40/32 per circle), and 0 contributors were unclassified.

### Where each check flips

| Condition | Pose age | Scan age | Result |
|---|---|---|---|
| Δ ≤ 0.095 s | ≤ 0.095 s | ≤ 0.160 s | as fresh, all four states |
| Δ ≥ 0.105 s, pose ageing | > 0.1 s | < 0.25 s | hold `InvalidCurve` at sample 0 in all four; curves ending at rest `InvalidCurve` in the tail; replan fails in three states. At the corridor entry the Δ = 0.11 s replan succeeds: its curve passed the full check with the stale pose, so none of its samples needed the pose fallback |
| Δ ≥ 0.19–0.20 s, pose re-stamped | 0 | > 0.25 s | safety check `Collision` at 0.000 s; hold `Collision` at 0.000 s; current point occupied; whole route blocked; frontier walk fails; replan at Δ = 0.3 s fails |
| Δ ≥ 0.19–0.20 s, both ageing | > 0.1 s | > 0.25 s | as above on a moving curve; hold `InvalidCurve`; route walk ends silently (`nan_yaw` at the route start) |

With the pose re-stamped, the replan at Δ = 0.11 s succeeds in all four
states. At Δ = 0.4 s the breakdown shows why everything blocks: each circle
fails in the support query's body verdict with `StaleInput` (verdict 4).
Every contributor is still terrain.

Each stop and hold signature has a replay counterpart:
- the 52 conflict stops while holding (0.000 s): pose fresh, scan stale;
- the 11 conflict stops while replanning (0.000 s): scan stale;
- the whole-route messages: scan stale, pose fresh at the walk's end;
- the 4 silent route exits: both stale;
- the 89 invalidations of the executing curve at sample 0: pose stale;
- the 131 tail rejections: pose stale.

## 4. Why SCAN's inputs age

- **One executor for everything.** `scan_planner_node.cpp` runs SCAN in a
  `SingleThreadedExecutor`. It serves the 10 ms planning timer, the 50 ms
  safety timer, the map timers and the pose, sensor-pose and scan
  subscriptions. Timers are wall timers; curves and the gates use sim time.
- **Sim time keeps moving during planning.** In the pinned image, rclcpp
  16.0.12 runs `/clock` on its own thread by default
  (`node_options.hpp:406`, `use_clock_thread_ {true}`). So `now()` advances
  during a planning callback while pose and scan callbacks wait.
- **Timers are served first.** The executor dispatches ready timers before
  subscriptions (`rclcpp/src/rclcpp/executor.cpp` at tag 16.0.12, lines
  846–873). After a long planning callback, the overdue planning and safety
  timers run before the queued pose and scan messages.
- **Planning callbacks are long.** Lengths are lower bounds, measured from
  the first to the last log line of each callback.
  - 201 planning-timer callbacks: median 0.219 s wall (0.085 s sim), p90
    0.409 s (0.174 s sim), max 0.848 s (0.211 s sim).
  - 90 of them exceed 0.1 s sim on their own; none exceeds 0.25 s sim.
  - The 63 safety-timer callbacks that stopped on a conflict took a median
    0.012 s wall. This includes their own replan attempt:
    `checkCollisionCallback` calls `planFromCurrentTraj` before it stops.
    The 89 invalid-curve stops print one line each and cannot be timed.
  - 85 A* searches hit the 0.2 s wall-time limit.
- **One callback can carry the scan past the 0.25 s limit.** A scan is up to about
  0.12 s old when a planning callback starts, even with no lag (the 0.1 s
  period plus the 0.02 s publication delay), and it cannot be replaced until
  the callback ends (`scan_age_bounds.py`).
  - SCAN's own lines show this once. In the REPLAN_TRAJ callback at scan.log
    lines 272–357, the processed scan (stamp 14.5222 s) was 0.090 s old at
    line 274 and 0.2501 s old at line 350 (now = 14.7723 s).
  - After line 350 the forced diagnostic printed no verdict, as expected
    when the support query exits early. After lines 233 and 236 of the first
    callback, with the scan 0.090 s old, the same diagnostic printed its
    verdicts.
  - By the clock mapping, 78 of the same 201 callbacks end with the
    processed scan at least 0.25 s old. This is a lower bound, from the
    newest scan published before the callback's first planning line. None
    exceeds 0.25 s by more than the mapping's maximum residual (0.021 s), so
    the count is indicative only.
- **Queue lag may add to this.** Pose and scan subscriptions use
  `SensorDataQoS` (keep last 5, best effort; `rmw/qos_profiles.h`), with
  Fast DDS. The executor takes one message per subscription per wait cycle.
  - The printed lines (§1) measure lag at the moment of printing, which
    includes the callback's own duration, so they do not separate queue lag
    from it.
  - Poses arrive every 5 ms and stay fresher. This fits the 52 stops with a
    fresh pose and a stale scan.

**What is not measured:** a stale query leaves no log line, because it exits
before the only line that prints the stamp. Apart from the one callback
above, no scan age over 0.25 s can be read, and none at any stop. The scan
age at each stop is therefore inferred. The decisive test is an instrumented
rerun that logs both ages at every check, with no change to decision logic.

## 5. Rejected candidates (Dr Sun's collision-envelope question)

`candidate_probe` (`make_candidate_probe.py`, `candidate_probe_derivation.json`)
keeps `stop_probe`'s input replay and helpers. For each candidate it:
- rebuilds the curve from the logged controls and knots;
- runs the native full check at the fresh inputs (Δ = 0);
- breaks down both footprint circles at the first colliding sample, checked
  against the native functions.

**The replay's own candidates.**
- At Δ = 0 the corridor-entry replan tried two curves, three times each, and
  rejected both as collisions at about 86% of their duration.
- The replay reproduces every value: status, first collision time, duration
  and sample count, to 1e-9 s. The three clear curves of the other states
  reproduce as clear.
- The first colliding sample is 2.61 m ahead at (−2.387, −4.152).
- Both circles fail in the support query at the body cell with `WrongHeight`
  (verdict 10). The inflation volume there holds 2 contributors, both
  terrain.

**All 137 live collision rejections.** `extract_live_candidates.py` takes each
checked curve from its `spline_curve_capture` line and replays it in the
frozen state nearest in sim time: 124 near the corridor entry, 12 near the
upper corridor, 1 on the stairs. A candidate counts as reproduced when the
replay gives the same duration and a first collision within 0.02 s of the
logged one (`analyze_candidates.py`, `candidates_summary.json`).

| Result | Count |
|---|---|
| Reproduced | 112 |
| – `WrongHeight` at the body cell, all in navigation cell (47, 41) | 109 |
| – a footprint circle over a cell with no layer within 0.26 m of the body ground, at the corridor-entry corner (−4.9, −3.4…−3.6) | 3 |
| – a measured non-terrain return, at any height | 0 |
| – a never-observed voxel | 0 |
| Not reproduced | 25 |
| – clear in the frozen map with fresh inputs: all 12 near the upper corridor and 3 near the corridor entry | 15 |
| – collide later along the curve at the same wrong-height cell | 9 |
| – collide at a never-observed voxel in a map 5 s older (stairs) | 1 |

**The wrong-height cell** (`wrong_height_cells.py`, `wrong_height_cells.json`).
- In PCT's navigation ground (`ground_precise.f32`, `97d2dfbd…`), cell
  (47, 41), centred at (−2.345, −4.187), holds layers at 1.4189, 3.083,
  4.533 and 6.090 m. It is 0.062 m from the PCT route polyline.
- The surface evidence (`raw_ground.f32`) has the 1.561 m corridor floor at
  the same place, and so do the neighbouring navigation cells.
- 1.419 m is the upper landing's height.
- The 109 first colliding samples sit 0.120–0.135 m above 1.4189 + 0.30 m,
  just outside the 0.12 m tolerance.
- In the corridor box (x −5.3…0, y −4.7…−3.8), 4 navigation cells carry only
  the landing height where the floor is 1.561 m. They lie 0.06–0.34 m from
  the route polyline. 32 further cells have no layer near the floor (band
  edges).

**Answer to the envelope question for these rejections.**
- No measured return at leg height or body height was involved in any
  reproduced rejection.
- The geometric failures came from the static support map: one mis-mapped
  cell, plus the narrow selected band at the corridor corner.
- The body-versus-legs rule would not change them. Correcting the cell, or
  tolerating an isolated support outlier, would.

**Not the 13 cm question.** Dr Sun's step-over decision concerns the mapped
13 cm box fixture (`audits/2026-09-27_pct_raw_cost`, `mapped_low_box`). The
0.14 m mismatch here is a map error, not an object.

## 6. Corrections to earlier statements

- **A* error "Unable to handle the initial or end point".** I stated this
  wrongly twice: first I tied it to the robot's start point, then I said it
  never decides the outcome. The facts:
  - 276 of the 280 lines come from the goal-neighbourhood search toward the
    distant final goal, as the v29 audit found. They do not decide the
    outcome.
  - The other 4 (scan.log lines 3134, 3150, 3206 and 3222) come from the
    optimizer's rebound A*, right after "The robot is inside an obstacle".
    Each ended that optimization ("rebound_no_valid_new_constraints;
    aborting this optimization").
- **"The conflict was at the robot's own current point."** The safety check
  did report that for all 63 conflict stops. The cause was most likely stale
  inputs, not an obstacle there.
- **Envelope height, confirmed.** The query point sits 0.28–0.32 m above the
  support layer in the four states.
  - The blocking band therefore runs from 0.23–0.27 m below the ground to
    0.63–0.67 m above it (inflation −0.55 / +0.35 m around the query).
  - This matches the earlier "about 0.25 m below to 0.65 m above".

## 7. Implications (candidate scopes, none implemented)

0. **Measure first (optional).** Run an instrumented rerun that logs, at
   every check, the pose and processed-scan ages and the blocking verdict of
   every "robot is inside an obstacle" event. It changes no decision logic,
   though the logging adds a little time inside the callbacks. It would turn
   §4's inference into a measurement and settle the open item.
   A cheaper partial test is a replay that ages the scan between the route
   walk and the optimizer of one planning call.
1. **Keep inputs fresh while planning.**
   - Move pose and scan callbacks into their own callback group on a
     multi-threaded executor, or give planning its own thread.
   - Bound each planning callback; the A* 0.2 s wall limit and repeated
     attempts dominate.
2. **Stop the heading from depending on pose age.** For a nearly stationary
   sample, use the curve's own last finite heading, or the hold's commanded
   yaw, instead of a fresh body pose.
3. **Make stale input explicit.** A stale scan should pause planning with a
   logged reason, not turn into a collision at 0.000 s and an emergency stop.
4. **Repair or tolerate navigation-ground outliers.**
   - Correct the four corridor cells that carry only the landing height.
   - Or let the support query accept a cell whose surface evidence has the
     expected floor when the navigation layer disagrees by more than the
     0.12 m tolerance.
   - Whether the 109 curves then pass has not been tested.
5. **Order relative to continuous replanning.** A fixed-rate replanning loop
   on the same executor would make the starvation worse. It needs item 1
   first.
6. **Collision model (Dr Sun's rule).** Still the right model for a legged
   robot, but it explains none of these stops and none of the reproduced
   rejections. Its evidence will have to come from real leg-height obstacles,
   such as the mapped 13 cm box fixture.

## Open item, partly explained

**53 "The robot is inside an obstacle" messages** (`scan_age_bounds.json`).
- **What the message means.** The rebound optimizer found a colliding
  control point, and every control point from there back to the start
  occupied (`bspline_optimizer.cpp:734–788`).
  - Its check takes each control point's yaw from the neighbouring control
    points and falls back to 0, never to the body pose
    (`bspline_optimizer.cpp:39–55`). So the pose gate's NaN heading cannot
    cause it.
  - The pose age still enters through the v29 blind-zone waiver, which
    switches off for a pose older than 0.1 s. It covers only points inside
    the robot's current footprint. In the four replay states, with the scan
    still fresh, a pose 0.105–0.18 s old left the robot's own point free (at
    the body yaw) and kept every route sample that had been free with fresh
    inputs free. The one sample that lost its heading had already been
    blocked (`<state>/result.json`, sweep).
- **48 were followed at once by "Trajectory terminal point is in an
  obstacle".**
  - The forward search then found no free control point up to the curve's
    end (`bspline_optimizer.cpp:773–789`). So the start and the end were
    both blocked. In 47 of the 48 the goal lay at least 1.05 m from the
    measured body. The waiver reaches a control point only within 0.71 m:
    the footprint reaches 0.53 m, and each query point sits 0.18 m from its
    control point. Line 1660, at 0.36 m, is the exception.
  - A block of every query produces exactly this. The code would print the
    same if a free stretch lay between two blocked ones, so it does not
    prove that every control point was blocked.
  - If it was a block of every query, it began during the callback: the
    route walk earlier in the same callback had found a free sample. The
    stale-scan gate is the only such block expected to switch on and off in
    this run (§2).
  - The timing fits, by the clock mapping (median residual 0.003 s, maximum
    0.021 s).
    - In the 5 callbacks that printed the processed stamp earlier, the scan
      was 0.2515–0.2562 s old at the message.
    - The 48 lower bounds fall in two tight groups: 25 at 0.2503–0.2567 s
      and 23 at 0.1503–0.1615 s. All 23 of the lower group come from
      callbacks whose first line is the A* 0.2 s wall-time timeout, so those
      callbacks began at least 0.2 s wall before the line the bound starts
      from. All 25 of the upper group begin with "Ran out of pool". Both
      groups fit a message printed as the processed scan exceeds 0.25 s.
    - The lower bounds of the 5 unexplained messages spread from 0.137 to
      0.223 s.
  - The replays advance the clock only between calls, so they cannot test a
    scan that ages within one call.
  - Most likely cause: the scan exceeding the 0.25 s limit during the
    callback.
- **5 were not** (lines 3132, 3148, 3168, 3204 and 3220).
  - A later control point was free, so no block of every query was active.
  - They come from two holding callbacks at the corridor-entry corner, near
    (−4.91, −3.40). Four were followed by the rebound A* errors of §6.
  - Cause not established. Candidates include the narrow selected band at
    that corner (§5), the yaw of 0 at coincident control points, and the
    blind-zone waiver.
- **Replay:** none of the replays printed the message, with fresh inputs, a
  stale pose or a stale scan, in the four states.

## Review

- **Round 1: FAIL.** An independent read-only review recomputed the counts,
  code claims, replay numbers and local-only totals. It found:
  - four wrong facts: the processed-scan stamp is logged, the corridor
    Δ = 0.11 s replan succeeds, the stop locations, and the height range;
  - two overclaims: the headline was stated as measured, and one cause was
    given for the 25 unreproduced candidates;
  - wording points: the 152 stop transitions, the scope of the A* error, the
    heading condition, the reading count, the callback mix, and route
    distances to vertices instead of the polyline.
- **Revision 1** addressed each finding. `timeline.py`,
  `wrong_height_cells.py` and the added counts reproduce the corrected
  numbers.
- **Round 2: FAIL.** A second independent review confirmed the round-1 fixes
  and found:
  - one wrong fact: the unreproduced candidates were replayed up to 6.4 s
    from their own time, not 10.4 s;
  - one wrong inference: a single planning callback can carry the scan past
    the 0.25 s limit, and SCAN's own lines show it once (§4);
  - one unsupported exclusion: a free route sample does not rule out the
    stale scan for the "inside an obstacle" messages, because the scan can
    exceed the limit later in the same callback;
  - overclaims and wording: "the only global block", "every live
    signature", the rejection headline, the hold count (102 published), the
    lag wording, the safety-callback count, the line-9434 example, and a
    reviewer check cited in §7 but not recorded.
- **Revision 2** addressed each finding. `scan_age_bounds.py` reproduces the
  exact and mapped scan ages, the preconditions of the other global blocks
  and the hold counts. It also adds one check the review did not make: the
  pose gate's NaN heading cannot cause the "inside an obstacle" message,
  because the optimizer's check never takes its yaw from the body pose. The
  pose age still reaches that check through the blind-zone waiver.
- **Round 3: FAIL.** A third independent review confirmed the round-2 fixes,
  re-ran `scan_age_bounds.py` to identical output, and found:
  - one wrong fact: the scan-lag counts ignored the 0.020 s publication
    delay (now 13 current, 12 one behind, 1 two behind, 1 undecidable);
  - one unsupported exclusion: a stale pose can still block line 9434's
    colliding sample through the blind-zone waiver;
  - one overclaim: "inside" followed by "terminal point" shows the start
    and end blocked, not every control point;
  - wording: the route samples left free, "passed the gate" used in both
    senses, the callback's first line (272), the two callback counts,
    "changes no behaviour", and three propagated records.
- **Revision 3** addressed each finding. `timeline.py` now uses the
  publication time; `scan_age_bounds.py` adds the missing planning line,
  which reconciles both counts at the same 201 callbacks, the lower-bound
  groups, the goal distances and the line-9434 geometry.
- **Round 4: PASS.** A fourth independent review re-ran both scripts to
  byte-identical output and found no wrong fact and no overclaim. Its
  wording points are applied: the waiver's 0.71 m reach, the A* timeout
  behind the lower group of bounds, the 0.12 s scan age at a callback's
  start, "no change to decision logic", and lag measured at the moment
  of printing.

## Attempts

- **Attempt 1** (`attempt01/`): used `ROS_DOMAIN_ID=233`, which Fast DDS
  rejects ("Calculated port number is too high"). All four probes exited 1
  before any analysis. The inputs were frozen and the probe built.
- **Attempt 2:** domain 232, plus the pose re-stamping mode. Exit 0 in 352 s;
  all eight probe runs exited 0.
- **Candidate pass** (`execute_candidates.py`): the replan candidates of all
  four states. Exit 0 in 221 s.
- **Live candidate pass** (`execute_live_candidates.py`): the 137 live
  collision rejections, with the same binary. Exit 0 in 158 s.

## Boundary

- This is diagnosis and probe-only counterfactuals. It is not a fix, a version
  or a relaxed threshold.
- The replay advances the clock without compute. It shows what each input age
  does, not the live ages themselves.
- Three explanations fit the 25 unreproduced live candidates, and none was
  tested:
  - the live map differed, for example through scans skipped when the queue
    was full;
  - the candidates were replayed in states up to 6.4 s from their own time;
  - the live check itself met stale inputs.
  - Two examples. scan.log line 9065 collided at the first sample, which
    fits a stale scan. Line 9434 collided at 0.369 s (sample 38), in a state
    7 ms away, so the time gap does not explain it; nor does a stale scan,
    which would block the first sample. Its look-ahead moves 0.116–0.293 m
    at every sample up to the collision, so a stale pose cannot give status
    2 there. The colliding sample lies 0.012 m from the curve's start,
    inside the current footprint, so a stale pose could still block it
    through the blind-zone waiver. A map difference also remains possible
    (`scan_age_bounds.json`, `live_candidate_line_9434`).
- The explanation of the 48 "inside an obstacle" messages rests on the code
  and on mapped timing. No replay ages the scan within one planning call.
- `timeline.py` reads local-only files of the run (`applied_sent.jsonl`,
  `artifacts/reactive_observations.jsonl`), listed with their SHA-256 in
  `versions/v30/LOCAL_ONLY_BYTES.json`.
- The frozen inputs (3,047 files, 152.6 MB) and the two probe builds (166
  files, 23.6 MB) stay local-only. They are listed with SHA-256 and
  regeneration steps in `LOCAL_ONLY_BYTES.json`, and ignored path by path.
- v30 stays frozen and unvalidated, and v3 remains the only accepted condition.
