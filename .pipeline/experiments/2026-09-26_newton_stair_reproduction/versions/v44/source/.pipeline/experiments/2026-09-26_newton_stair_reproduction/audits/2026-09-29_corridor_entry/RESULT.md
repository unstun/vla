# Corridor entry: why v32's and v33's trials stood there, from replays of both stands

Stage: experiment + analysis, 2026-09-29. This is diagnosis only: no version, no threshold or map change and no
physics. Revised after independent review rounds 1 and 2 (see Review).

- **The trials:** v32's ran on this MacBook and v33's on gpu5070ti.
- **The replays:** all ran in this Mac's Docker VM, with:
  - the pinned local Humble image (`sha256:f7363cc3…`);
  - the scan64 native sources that both trials ran (`runtime/scan64_input_refresh_v31`, v33's `native_build`);
  - each run's planner YAML (the two are identical).

Dr Sun asked to diagnose the corridor-entry failure, then build v34. The planned v34 scope was the wrong-height
navigation cell (47, 41); v33's trial added "The robot is inside an obstacle" failures and SCAN's replan limit to
the diagnosis.

## Answer in brief

- **Two separate properties of PCT's pinned navigation ground (`ground_precise.f32`) stop the robot at the
  corridor entry.** SCAN's footprint support query turns each into a planning failure.
  1. **Wrong-height cells: v32's failure.**
     - Four corridor cells carry only the upper landing's height (1.419 m) where the floor is 1.561 m (v30 stop
       audit, §5).
     - A curve sample whose body reference lies over cell (47, 41) above z 1.839 m fails the body-cell height match
       (`WrongHeight`): the cell's 1.419 m layer matches only up to 1.419 + 0.30 + 0.12 m. v32's rejected curves,
       and v33's first attempts once its start is freed (§5), cross it at z 1.845–1.847 m, about 1 cm too high.
  2. **A narrow entry band with PCT's route along its edge: v33's failure.**
     - **The band:** at the entry, the navigation ground keeps the floor only in a band 0.8–1.0 m wide. In rows
       47–53 its east edge is 0.60–0.70 m from the wall face that LiDAR measures at body height (x −4.198). The
       pinned surface evidence has the same floor up to 0.2 m from that face. Further south, rows 45–46 open onto the
       corridor, whose northern strip the navigation ground also lacks.
     - **The route:** PCT's route runs 0.04–0.17 m inside the band's east edge.
     - **The rule:** SCAN needs the centres of both footprint circles, 0.18 m ahead of and behind the reference
       point along the heading, over navigation cells with a floor layer near the body level.
     - **At both stands:** headings within 44° (v33) or 49° (v32) of east–west are therefore unsupported. v33's
       start also has two 10° blocked windows, caused by one missing corner cell.
- **v33, measured in the replay:**
  - The rebound optimizer's first three control points all lie exactly at the start.
  - **The first two:** SCAN estimates a control point's heading from its two neighbours, and falls back to 0°
    when they coincide. So these two are checked at 0°, and their front circles fall in the missing column.
  - **The third:** it is checked at −98.96°, inside a blocked window. Its rear circle centre lies 0.66 mm inside
    the missing corner cell (22, 51).
  - **The result:** no control point back to the start is free, so SCAN prints "The robot is inside an obstacle".
  - **The repair fails too:** its A* then moves the blocked start away from control point 3 in 0.05 m steps and
    leaves the search pool at index 58 100 49, as live.
  - **The per-step causes (a Python replica, not measured natively; §3):** first the rear circle over the corner
    cell (22, 51), then (22, 52), then mostly the reference point's own cell, which has no navigation floor there.
- **v32:** its start, 7 cm further south, has no corner window. After its two rebound rounds, the optimized curve had
  index 2 at −118.08°, which is free. No rebound check found index 2 as its first new collision, since "inside an
  obstacle" never occurs in its 355 stand cycles. Curves are built, and the final check rejects them at cell
  (47, 41), as v32's own analysis found.
- **Reproduction:**
  - Each replay prints the same 9-attempt event sequence as its trial's first stand cycle.
  - The printed details compared are the start and target lines, iteration counts, rejection times and durations,
    time adjustments, A* pool indices and every printed frontier time. All 9 of v32's attempts are identical in
    them. For v33, 6 of 9 are identical; the 5th, 7th and 9th differ only in the printed frontier time (live
    14.5409 s, replay 14.4909 s). That is most likely because the live map took new scans during the cycle (4) and
    the replay delivers none.
  - The step-by-step footprint breakdown matched the native functions, with 0 mismatches in all runs.
- **Counterfactual grounds (probe inputs only):**

  | Change | v32's frozen first cycle | v33's frozen first cycle |
  |---|---|---|
  | Fix the four wrong-height cells | plans on the first attempt | still fails, identically |
  | Fill the entry band | plans only a 1.84 s hop to (−4.73, −3.88); both full-length attempts are still rejected at (47, 41) | plans |
  | Both | plans on the first attempt | plans on the first attempt |

- **So:**
  - Fixing the four wrong-height cells, (47, 41) among them, let v32's frozen first cycle plan but not v33's.
  - The planned v34 scope alone would therefore not have unblocked v33's stand.
- **Along the rest of the route (a static screen, approximate, with blind spots; §7):**
  - With the pinned ground, 97 route poses above z 1.3 m leave less than ±30° of supported heading around the
    route direction. They form seven groups over three floors. The entry and the turn into the corridor are one
    group, and the corridor's east-end corner another, both on the corridor floor; the rest lie on the two floors
    above, which the route reaches later.
  - Correcting the two spots leaves 88 such poses.
  - A modelled fallback to the surface evidence leaves 6.
  - diag_v32_clock01 stopped at (7.42, −4.29), about 0.25 m before the first narrow pose at the corridor's east-end
    corner. Its cause was not examined.
- **The replan limit** only ended v33's stand, and v32's run ended on `odom_stale` first. With the same start, every
  cycle printed the same event sequence: all 1,000 of v33's stand cycles and all 355 of v32's.

## 1. What the live logs show

`runs/<run>/scan.log`; counts over the whole run, unless the table says otherwise.

| | v32 (MacBook) | v33 (gpu5070ti) |
|---|---|---|
| Last moving curve (traj 12) | 38.091–39.920 s, ends at (−4.9122, −3.4793) | 30.885–33.151 s, ends at (−4.9227, −3.4078) |
| First stand replan began | 39.9197 s, 0.27 ms before the curve's end | 33.153 s, after the curve's end |
| Replan start (the curve at that moment; `planFromCurrentTraj`) | (−4.9122, −3.4793), velocity about 1e-7 m/s (9.0e-8) | the curve's end, velocity 0 |
| Measured body at the stand | (−4.915, −3.486), yaw −81.2° | (−4.863, −3.422), yaw −83.6° |
| Failed replan cycles (`REPLAN_TRAJ` to `REPLAN_TRAJ`) | 360 in the run, 355 at the stand | 1,000 (the limit), all at the stand |
| "The robot is inside an obstacle" | 10, all before the stand (lines 1474–2073) | 6,000 |
| "First three control points are in obstacles" | 710 | 0 |
| Final-check collision rejections | 2,138 (2,130 at the stand) | 7 (all before the stand) |
| Seed searches failed | 366 | 1,006 |

- **One cycle is one `planFromCurrentTraj` call: 9 rebound attempts.**
  - It makes three calls to `callReboundReplan`, which share a budget of three prefix proposals.
  - **Three attempted targets:**
    - the local target (−1.66, −4.14), at route time 13.3 s, six times (each first attempt plus its fixed-height
      recovery);
    - the prefix (−3.49, −4.21) twice;
    - the prefix (−4.73, −3.88) once.
  - **One more candidate,** (−4.39, −4.15), is rejected as occupied without an attempt.
  - **The reference frontier:** printed at route time 14.49 s at (−0.47, −4.25) in v33, and 14.44 s at
    (−0.52, −4.25) in v32.
  - Both runs cycle through the same targets. Only the outcomes differ.
- **v33's cycle:**
  - The six local-target attempts end "inside an obstacle".
  - The (−3.49) attempts end with the optimizer failing after its restarts.
  - The (−4.73) seed search hits A*'s 0.2 s limit (status 2).
- **v32's cycle:**
  - The local-target attempts produce curves that the final check rejects at (47, 41).
  - The (−3.49) attempts end "First three control points are in obstacles".
  - The (−4.73) seed search fails as in v33.

## 2. The replays

`prepare_inputs.py` is the v30 stop audit's freezer, with the source runs and the moment changed. Each state is
frozen at the recorded body pose at which the live `REPLAN_TRAJ` call of the first stand cycle began. The FSM leaves
`EXEC_TRAJ` once t_cur > duration − 0.01 on its 10 ms timer, so that moment can fall on either side of the curve's
end. It is identified from logged values:
- **v33: 33.1534 s**, the first pose after the curve's end.
  - The cycle's first line printing the sim time shows `now=33.153` (scan.log line 1084).
  - The printed start velocity is 0.
- **v32: 39.9197 s**, the last pose before the curve's end.
  - The printed start velocity (scan.log line 2128) is the curve's velocity 0.27 ms before its end. The freezer
    checks this.
  - The cycle's cloud age (0.1099 s) gives the same time.
  - The first version froze v32 5 ms later, at the first pose after the end. Independent review round 1 found this
    (B2); that state is kept in `attempt03_v32_freeze_late/`.

**What each state holds:**
- the original published scans up to that clock with their paired sensor and body states (v33: 221 scans; v32: 288);
- the executing curve;
- the route;
- the last committed window (v33: 9.566948 s; v32: 9.639669 s).

**The probe.** `corridor_probe` (`make_probe.py`, `probe_derivation.json`) keeps the v31 regression `gen_probe`
input replay (`bac7c07e…`, the same file as the v30 audit's base) byte for byte, with two additions: five read-only
includes, and the line that lets `$VLA_NAV_GROUND` replace the navigation ground. It then runs, read-only:
- **Yaw sweep:** a heading sweep at the replan start and at the measured body, every whole degree. Each heading gets
  the native `getInflateOccupancy`, and both circles are broken down step by step with the v30 audit's circle
  breakdown, cross-checked against the native functions.
- **Live entry:** `planFromCurrentTraj()` once, the live `REPLAN_TRAJ` entry, from the restored executing curve.
- **First attempt:** `getLocalTarget()`, then one `reboundReplanAttempt` with the live first attempt's start,
  target and derivatives. Afterwards the probe repeats, read-only on the optimizer's control points:
  - the scan of `check_collision_and_rebound()`: each control point's native heading and occupancy, the
    new-collision test against its stored constraints, the first new collision, and the backward search for a
    free control point;
  - the trajectory check behind "First three control points are in obstacles".
- **Which control points it reads:**
  - **For an attempt that aborts in the optimizer (v33),** these are the points the aborting rebound check saw.
    The abort follows the failed check, and the message printed once.
  - **For an attempt whose optimization succeeds (v32),** refinement has since overwritten them. The rebound-stage
    values for v32 therefore come from the log's own curve captures (§4).

**Reproduction.**
- Each replay's live-entry section prints the same 9-attempt event sequence as the trial's first stand cycle
  (scan.log lines 1080–1258 for v33 and 2120–2345 for v32). That covers the targets, "inside an obstacle", the A*
  pool indices (58 100 49 / 50 and −19 46 20 in v33; −19 45 20 in v32), "First three control points", the seed
  failures, and the cell of every final-check rejection. That cell is found by evaluating the logged checked curve at
  its logged first-collision time, as `versions/v32/corridor_entry_curves.py` does.
- **Printed details** (`analyze.py`):
  - **What is compared, per attempt, as text:** start and target lines, iteration counts, rejection status, time and
    duration, post-optimization durations, pool indices, and every frontier time printed before the next attempt
    (`reference_frontier` lines and the `frontier=` field of the `[DEBUG-prefix-01]` lines). Attempts are numbered
    from 1.
  - **v32:** all 9 attempts are identical.
  - **v33:** 6 are identical. In the 5th, 7th and 9th attempts the printed frontier time differs (live
    14.540880500718, replay 14.490911839203).
    - **Most likely cause:** the live map processed new scans during the cycle (4, scan.log lines 1136, 1174, 1196
      and 1247), and the replay delivers no input during it.
    - **Not proven:** v32's first cycle also processed 7 scans, with no printed difference.
  - **An independent full-text check** (review round 2) masked timings, `input_refresh` lines and the
    `near_sensor_verdict` diagnostics, and found no other difference in either cycle.
- **Native cross-check:** circle, support and whole-query mismatches against the native functions are 0 in all
  runs (`summary.json`).

## 3. v33's start

**Supported headings (yaw sweep, replay):**

| Point | Free headings (degrees) |
|---|---|
| Replan start (−4.9227, −3.4078) | −135…−109, −98…−45, 45…71, 82…135 |
| Measured body (−4.863, −3.422) | −112…−68, 68…112 |

Every blocked heading fails in one circle with `support_footprint_layer_4`: no navigation layer within the step
(0.26 m) of the body ground (1.558 m) at that circle's centre. Where the centres fall:
- **Column 23** (x −4.795 to −4.695), rows 48–50: headings within 44° of east–west.
- **Corner cell (22, 51)** (x −4.895 to −4.795, y −3.237 to −3.137): the windows −108…−99 and 72…81. Rows 51–53 of the
  band are one cell narrower than rows 48–50.

**The first attempt's control points at the abort** (local target (−1.6575, −4.1444), 22 control points; the scan
covers 2–14):

| Index | Position | Heading | Occupied | Failing circle |
|---|---|---|---|---|
| 0 | the start | 0.0° (coincident neighbours) | yes | front, centre (−4.7427, −3.4078): column 23, 0.053 m past the band edge |
| 1 | the start | 0.0° (coincident neighbours) | yes | as index 0 |
| 2 | the start | −98.96° (toward index 3) | yes | rear, centre (−4.89465, −3.22998): corner cell (22, 51), 0.66 mm past its edge |
| 3–16 | south along the band, then east into the corridor | −87.5° … 18.9° | no | — |
| 17 | (−2.3575, −4.2024) | 15.8° | yes | body cell (47, 41): `WrongHeight` (`support_body_verdict_10`) |
| 18–21 | on to the target | | no | — |

- **The rebound check:** index 2 is the first new collision, and indices 1 and 0 are also blocked. That is "The
  robot is inside an obstacle", reproduced read-only (`inside_replicated`).
- **The repair.**
  - **What it does:** its A* starts at index 0 and must move the blocked start away from its end point (index 3),
    in 0.05 m steps along the reversed path heading. Measured: it leaves the pool at index 58 100 49, as live.
  - **Per-step causes:** `astar_start_walk.py` repeats that loop in Python, with the pool, the start-aligned
    centre, grid-snapped points and the support half of the query. It ignores LiDAR occupancy, so it can miss a block
    but not invent one. It reproduces the exit index after 50 positions, all unsupported, from x −4.92 to −4.52 and
    y −3.41 to −1.01:
    - positions 0–3: the rear circle over the corner cell (22, 51), then (22, 52);
    - from position 4: mostly the reference point's own cell, which has no navigation floor near the body level
      east of the landing band (one position fails at the front circle).

    These per-step causes are the replica's, not a native measurement.
- **The trajectory check:** its first occupied sample is t = 0 at −98.96°. It would also have failed as "First three
  control points".
- **Index 17 shows the second blocker on the same curve.** With the start freed (the `entry_filled` ground), the
  first attempt is rejected at (47, 41), and the fixed-height recovery passes (§5).

## 4. v32's start

- **Supported headings at the replan start (−4.9122, −3.4793):** −130…−50 and 50…130. Every blocked heading puts a
  circle centre in column 23, rows 47–49. No corner cell is within reach.
- **At the measured body:** −131…−49 and 49…131.
- **The first attempt** (from the curve captures, identical in the live log and the replay):
  - **The rebound phase:** the optimizer ran two rebound rounds (11 and 25 iterations). Its optimized curve has
    index 2 at −118.08°, inside the free window. Control points 0 and 1 are again at the start with heading 0°.
  - **The rebound checks:** they found their new collisions at later indices, and their backward searches found a
    free control point. "Inside an obstacle" occurs in none of v32's 355 stand cycles.
  - **The final check:** it rejects the refined curve at (47, 41).
  - **What the probe read:** the control points left after refinement, those of the curve the final check tested
    (index 2 at −102.2°), not the rebound phase's.
- **So (most likely):** the 7 cm between the two starts decided which blocker each stand met.
  - **What supports it:** the yaw sweeps explain the corner window by position.
  - **Not tested:** the two states also differ in start velocity and map, and swapping the starts was not run.
- **Why the starts differ (inferred):** the approach curves ended where SCAN's last committed windows put them,
  9.567 s against 9.640 s on the route. The logs show how each window was chosen:
  - **v33 (lines 1042–1071):** replan start (−4.99, −2.86), projection 8.925 s, local target 11.49 s. The halved
    prefix at 10.21 s was occupied, and 9.567 s was committed.
  - **v32 (lines 2016–2112):** replan start (−4.97, −3.12), projection 9.275 s, local target 12.19 s, after earlier
    failed cycles. The prefixes at 10.73 s and 10.00 s were occupied, and 9.640 s was committed.

  Whether planning timing decided this was not examined.

## 5. Counterfactual grounds

`make_grounds.py` (`grounds/grounds.json`) writes three navigation grounds. They are probe inputs, not pinned-map
versions.
- **`cells_fixed`:** moves the 1.4189 m layer of the four landing-only corridor cells, (37, 43), (47, 41), (63, 44)
  and (70, 41), to the surface evidence's floor in the same cell (1.5609 m). Only z changes.
- **`entry_filled`:** adds the surface evidence's floor layer to the 51 corridor-entry cells that lack a navigation
  layer within 0.12 m of their row's band height.
  - **The box:** x −5.8 to −4.3, y −3.9 to −2.9. In rows 47–53 it stops about 0.1 m short of the wall face (x
    −4.198); the surface evidence's floor ends at −4.395 there.
  - **The match:** the surface evidence must have a layer within 0.03 m of the row's band height.
  - **Cost:** each record gets 16.671875, the highest cost PCT kept.
- **`both`:** both changes.

The decode origin does not move; the script checks this.

| State | Ground | Live entry | Committed curve (native full check) | Start headings free |
|---|---|---|---|---|
| v33 | pinned | fails (as live) | — | 4 windows (§3) |
| v33 | `cells_fixed` | fails, identically | — | as pinned |
| v33 | `entry_filled` | plans: the first attempt is rejected at (47, 41), its fixed-height recovery is clear | clear, 6.21 s, to (−1.658, −4.144) | all |
| v33 | `both` | plans on the first attempt | clear, 6.43 s, same target | all |
| v32 | pinned | fails (as live) | — | −130…−50, 50…130 |
| v32 | `cells_fixed` | plans on the first attempt | clear, 5.51 s, to (−1.658, −4.144) | as pinned |
| v32 | `entry_filled` | plans only the third prefix: both local-target attempts are still rejected at (47, 41) | clear, 1.84 s, to (−4.730, −3.879) | all |
| v32 | `both` | plans on the first attempt | clear, 6.04 s, to (−1.658, −4.144) | all |

- **Inferred, not tested:** whether v32 under `entry_filled` would meet (47, 41) again from the hop's end. The
  replay did not plan from there.
- **The `entry_filled` recovery for v33:** the rejected first attempt and the clear recovery ran on the same frozen
  state and clock, and they differ in height mode.
  - **Where they cross (47, 41):** the recovery's curve crosses the cell at z 1.835–1.836 m, inside the 0.12 m
    tolerance of the cell's 1.419 m layer (up to 1.839 m). The first attempt crosses it at 1.845–1.846 m.
  - **So:** the recovery passes because it runs about 1 cm lower, not because it misses the cell. That is the
    centimetre sensitivity the v30 audit described.

## 6. The navigation band and PCT's route at the entry

- **Band width** (navigation cells with a layer at 1.50–1.62 m, per 0.1 m row):
  - rows 51–53 (y −3.24 to −2.94): 0.8 m, east edge x −4.895;
  - rows 48–50 (y −3.54 to −3.24): 0.9 m, east edge −4.795;
  - rows 45–47: 1.0 m;
  - then it widens into the corridor (row 43: 1.2 m).
- **The wall** (`entry_geometry.py`, `entry_geometry.json`: LiDAR world points from every 50th scan of both trials
  after their first stand replan, 136 scans):
  - at body height (z 1.85–2.55) the face is at x −4.198, in rows 47–58 (y −3.64 and north);
  - returns at x −4.26 occur only from z 2.55 up;
  - in rows 47–53 the band therefore ends 0.60 m (rows 47–50) to 0.70 m (rows 51–53) short of the face;
  - rows 40–46 have no body-height return near the entry. The corridor opens east there, and its north wall face
    runs east from (−4.198, −3.60).
- **The surface evidence** (`raw_ground.f32`) continues the band's floor eastward:
  - up to x −4.395 in rows 47–53, 0.2 m before the face;
  - up to −4.295 in row 46;
  - on into the corridor in rows 40–45.
- **The corridor's northern strip:** the navigation ground also lacks it east of the band, up to column 40. Row 42
  misses columns 26–32, row 43 25–33 and 37, row 44 24–34, row 45 23–35 and row 46 23–40
  (`entry_geometry.json`, `missing_columns_east_to_40`).
- **PCT's costs** (measured): the band's edge cells have 13.5–16.7, and 16.671875 is the file's maximum. The
  interior is not monotone: rows 45–47 have a central ridge of 14.5, and rows 51–53 fall from 12.1 in the west to
  7.6–8.1 just before the east edge cell.
  - **A hypothesis, not examined in PCT's code:** that PCT's wall cost trimmed the cells beyond.
- **PCT's route** runs inside the band's east edge by, at its route poses:
  - 0.09 and 0.08 m (rows 53, 52);
  - 0.17, 0.15 and 0.13 m (rows 50–48);
  - 0.10, 0.07 and 0.04 m (rows 47–45);
  - 0.10–0.05 m (row 44).

  That is the inside of the coming left turn.
- **Why a stop there matters:**
  - Moving along the route, a curve keeps headings close to the route's, and those are supported.
  - A stop is different. At a stop, the rebound optimizer checks the coincident start control points at 0°, which
    is east-facing and unsupported there. Headings within 44° (v33) and 49° (v32) of east–west are unsupported at
    the starts, and within 67° and 48° at the measured bodies.

## 7. Along the rest of the route (static screen)

`route_support_margin.py` (`route_support_margin.json`) is a Python approximation of the support half of the query.
- **What it checks, for every route pose above z 1.3 m (578 poses, on three floors at body height about 1.9, 3.4
  and 4.8 m, and on the flights between):**
  - the body-cell height match, a layer within 0.12 m of the body level z − 0.30;
  - both circle centres, for each whole-degree heading.
- **Grounds:** the pinned ground and the three counterfactuals, plus a rough model of a code-level fallback. The
  fallback uses the surface evidence's layer within 0.12 m wherever the navigation cell has no matching layer: for
  the body cell, of the body level; for a circle, of the body ground.
- **Direction of error:** it ignores LiDAR occupancy and the step scores' support status, so at a given pose it can
  miss blocks but not invent them.
- **Blind spots:**
  - it evaluates route poses only, and those never lie over a wrong-height cell, so it cannot see v32's failure (an
    off-route curve sample over (47, 41));
  - its footprint check accepts the 1.419 m layer (0.142 m below, inside the 0.26 m step);
  - its metric (±30° around the route heading) is not the stand mechanism (the 0° heading of coincident start
    control points).

| Ground | Body-cell fails at route poses | Route heading unsupported | Poses with less than ±30° free around the route heading |
|---|---|---|---|
| pinned | 0 | 0 | 97 |
| `cells_fixed` | 0 | 0 | 97 |
| `entry_filled`, `both` | 0 | 0 | 88 |
| surface fallback | 0 | 0 | 6 |

**Where the 97 narrow poses are (pinned), in seven groups:**

| Poses | Count | Where | Route z (m) |
|---|---|---|---|
| 79–96 | 15 | the entry and the turn into the corridor | 1.78–1.88 |
| 200–207 | 6 | the corridor's east-end corner (x 7.67–8.21, y −4.24 to −3.71) | 1.85–1.89 |
| 290–312 | 18 | x 6.5–8.2, y 5.80–6.55 | 3.36–3.38 |
| 413–437 | 17 | x 6.5–8.2, y −6.74 to −5.95 | 3.34–3.36 |
| 454–461 | 8 | x 8.27–8.28, y −3.97 to −3.13 | 3.35–3.45 |
| 510–521 | 12 | x 8.2, y 2.27–3.54 | 4.30–4.51 |
| 535–556 | 21 | x 6.8–8.4, y 5.42–6.06 | 4.78–4.84 |

- **What changes:**
  - Filling the entry clears 9 of them. The other 88, including 6 at the entry turn (poses 89–96), remain.
  - The modelled fallback leaves 6: poses 457 and 458 at (8.27, −3.61 to −3.49), and 512, 513, 514 and 519 at
    (8.18–8.19, 2.49–3.29).
- **diag_v32_clock01** stopped at (7.42, −4.29) by about 60 s (versions/v32/RESULTS.md). The nearest route pose, 198
  at (7.47, −4.33), is not narrow. The first narrow corner pose, 200, is about 0.25 m further on. The stop's cause
  was not examined.

## 8. Implications for v34 (candidate scopes, none implemented)

1. **Only the wrong-height cells (the planned scope).**
   - Correct the four landing-only cells in the pinned navigation ground.
   - The replay shows this lets v32's frozen first cycle plan, but not v33's.
   - A trial that stops where v33 stopped would stand again.
2. **Correct the pinned navigation ground at both spots.**
   - Fix the four cells and fill the entry band, as the `both` counterfactual does. That would make it a new
     pinned-map version.
   - Both frozen stands then plan on the first attempt.
   - It is data only. The edit is specific to this building, and the fill box was chosen by hand.
   - The static screen still shows 88 narrow poses.
3. **A support fallback in SCAN (code).**
   - Where the navigation ground has no layer that the support query can associate, SCAN would accept the pinned
     surface evidence's layer at that cell if it lies within the 0.12 m body tolerance of the body ground.
   - The body check runs `CollisionDecision::decide` before association. The fallback must therefore reach the
     decision too, not only the height association.
   - It is expected to remove both blockers by one rule. The only basis is the model; in the static screen it leaves
     6 narrow poses.
   - Its effect at the two stands is untested. It needs a red/green contract on both frozen states, drop and
     wrong-level negatives, and the full native regression.
   - It changes what support means: PCT's wall margin no longer limits SCAN's footprint, and walls are left to SCAN's
     own LiDAR check.
4. **Not sufficient alone: the heading of coincident start control points.**
   - The fallback to 0° blocked indices 0 and 1 at v33's start. Checking them at the start heading instead would
     not free index 2 at −98.96°.
   - It is a separate weakness, for a separate version.

Dr Sun chose option 3 on 2026-09-29. `versions/v34/PLAN.md` records how v34 implements it, including a drop guard
added while building v34 (PLAN.md, "Decision and basis"). This audit only required drop negatives in the contract.

## Attempts

- **Attempt 1 (`attempt01/`):** `prepare_inputs.py` asserted before any input was written. The pose sample chosen
  for the planned clock (33.1484 s) fell 2.6 ms before traj 12's end. The freezer then took the first pose at or after
  the curve's end.
- **Attempt 2 (`attempt02/`):** the inputs were frozen (kept), and the probe failed to compile. A stream named
  `points` clashed with the replay prefix's `points` matrix; it was renamed.
- **Attempt 3:** exit 0 in 344 s, with all 8 probe runs at exit 0. Operator note, with no artifact: the app was quit
  during this attempt's first launch, which left no container, and the run recorded here was started afterwards.
- **v32 re-frozen after review round 1 (B2):**
  - **The late state:** attempt 3's v32 state (5 ms late) and its four results are kept in
    `attempt03_v32_freeze_late/`. v33's state and results are attempt 3's, unchanged.
  - **`attempt04_docker_quit/`:** Docker Desktop quit as the re-freeze started ("error waiting for container:
    unexpected EOF"), after the container had written part of the new v32 inputs.
  - **`attempt05_partial_inputs/`:** the retry found the partial inputs folder, skipped the freeze, and every probe
    aborted on the missing planner YAML.
  - **The final re-freeze** (`execute_v32.py`, `request_v32.json`): exit 0 in 223 s, with all 4 probe runs at
    exit 0.

## Review

- **Round 1: FAIL.** An independent read-only review re-derived the reproduction, the freeze moments, the
  control-point tables, the wall position, the static screen and the counts. It found seven blocking points:
  - **B1:** the replays were claimed to reproduce the live cycles exactly, but only their event signature was
    compared.
  - **B2:** v32 was frozen 5 ms after its live replan began.
  - **B3:** v32's index-2 heading came from the post-refine control points.
  - **B4:** the wall face at body height is x −4.198.
  - **B5:** only two of the seven groups of narrow route poses were listed.
  - **B6:** diag_v32_clock01's stop was placed at the narrow corner.
  - **B7:** the A* walk's per-step causes were stated as measured.

  It also found 19 non-blocking points: target naming, the probe's includes, flag wording, the attempt 1 wording,
  inferences stated as facts (planning timing, the hop, the wall-cost cause, the fallback's effect), the screen's
  blind spots, the machines behind each run, the missing ignore entries, and wording.
- **Revision 1:**
  - v32 is re-frozen at its live replan moment and replayed again.
  - `analyze.py` compares the printed details.
  - `astar_start_walk.py` makes the start-adjustment replica reproducible.
  - The wall position is re-measured.
  - The text is corrected point by point.
- **Round 2: FAIL.** A second independent review confirmed B2, B5, B6 and B7 as fixed and B1, B3 and B4 as partly
  fixed. It found five blocking points:
  - **R2-B1:** the `entry_filled` recovery crosses (47, 41) about 1 cm lower; it does not miss the cell.
  - **R2-B2:** the body-height wall face exists only from row 47 north, and rows 45–46 open onto the corridor.
  - **R2-B3:** the −118.08° heading is the optimized curve's, after the rebound rounds.
  - **R2-B4:** v33's frontier differs in three attempts, not two, and the attempt numbers were 0-based.
  - **R2-B5:** the drop guard came from building v34, not from this audit.

  It also found 14 non-blocking points: the start velocity's magnitude, v32's frontier, the static screen's floors
  and ranges, the A* replica's second cell, cost rows, the scan count behind the frontier difference, the angle
  convention, the missing geometry script, the grounds docstring, the fallback's poses, which run the replan limit
  ended, the 7 cm inference, and the regeneration of the frozen inputs.
- **Revision 2:**
  - `entry_geometry.py` records the entry geometry.
  - `analyze.py` compares every printed frontier value and numbers attempts from 1.
  - The text is corrected point by point.

## Boundary

- This is diagnosis and probe-only counterfactuals, not a fix, a version or a relaxed threshold.
- **Frozen inputs:** the replays freeze inputs at one moment per stand. The live stands lasted 245 s (v32) and
  427 s (v33), and every live cycle printed the same event sequence, but later map states were not replayed.
- **Optimizer state:** for the aborting v33 attempt, the probe reads the control points of the failed check, as
  §2 explains; for v32's successful attempt, the rebound-stage values come from the log's curve captures.
- **The per-step A* causes** come from a support-only Python replica.
- **The (−3.49, −4.21) attempts** were not broken down.
- **The static screen** is an approximation with the blind spots in §7.
- **Local-only bytes:** all frozen inputs, including the superseded v32 states, the probe build and the
  counterfactual grounds are local-only. They are listed with SHA-256 and regeneration steps in
  `LOCAL_ONLY_BYTES.json`, and need path-specific ignore entries before any commit.
- **Regeneration is not byte-identical:**
  - v33's inputs came from the freezer's first version, which used the same moment rule (first pose after the
    curve's end).
  - Serialized CDR messages carry padding bytes that differ between freezes. v32's `route.cdr` and `spline.cdr` differ
    between attempt 3 and the re-freeze, although their JSON is identical.
- **Labels:** v33 stays frozen and unvalidated, and v3 remains the only accepted condition.
