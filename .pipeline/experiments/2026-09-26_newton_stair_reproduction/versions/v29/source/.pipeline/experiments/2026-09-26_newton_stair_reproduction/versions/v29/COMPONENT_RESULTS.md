# v29 component results

All runs used the local pinned image `sha256:f7363cc3…` (ROS 2 Humble,
amd64 emulation) on 2026-09-28. This record contains no physical episode.

## Build

`runtime/scan61_sensor_column_v29` built in 37.1 s with the scan60 incremental
cache (`build_result.json`: passed, source unchanged). Only
`scan_reactive_grid_methods.inc` and `known_lite3_trunk.h` differ from v28;
`grid_map.cpp` was the one recompiled unit. The installed tree differs from v28
in exactly five entries:

- the two changed headers;
- `libplan_env.a`;
- the relinked `scan_planner_node`;
- `measured_cloud_probe`.

The only compiler warning is the pre-existing unused `all_info` parameter.

## Red/green waiver contract

`waiver_contract/` compiles one contract source against v28 (`red_v28/`) and
v29 (`green_v29/`) and replays three frozen states: stopped at 0.3517 m, the
0.365 m variant, and the standing control. For each state it checks about
160,000 points: 27 per voxel, over every voxel within the body-frame box
|x| <= 0.75, |y| <= 0.55, z -0.20..0.25 m. Each point is compared with two
independent oracles, one for each specification (`check.py`,
`contract_results.json`: passed).

| State | v28 vs v29 oracle | v29 vs v28 oracle | Waived only by v29 | Waived only by v28 |
|---|---|---|---|---|
| stopped | 3,733 mismatches | 3,733 mismatches | 3,282 | 451 |
| 0.365 m | 2,422 | 2,422 | 1,041 | 1,381 |
| control | 1,949 | 1,949 | 1,822 | 127 |

The last two columns count points where the two specifications disagree and a
free voxel would pass the tree's verdict.

- **Oracles:** each tree matches its own oracle with zero mismatches.
- **Stale pose:** 0.15 s later, none of the 18,153-19,250 previously waived
  Unknown points is free in either tree. The cloud is still within its 0.25 s
  obstacle age at that time, so the check is not vacuous.
- **Identical results:** results at non-Unknown voxels are identical between
  the trees, as are the Unknown points where both specifications agree
  (digests match).

`discriminating_breakdown.json` classifies the points where the two
specifications disagree:

- **Waived only by v29:**
  - above the trunk band up to the LiDAR origin: 3,134 / 912 / 1,642;
  - the footprint edge where the point is inside and the centre outside:
    134 / 129 / 180;
  - 14 bottom-edge points at 0.3517 m.
- **Waived only by v28:**
  - below the trunk bottom where the centre is in the band: 277 / 1,163 / 0;
  - the footprint edge where the centre is inside and the point outside:
    174 / 218 / 127.

Most of v29's extra waiving is in the slice between the trunk band and the
LiDAR origin. It also waives footprint-edge points whose voxel centre lies
outside the circles, and 14 bottom-edge points. It waives less than v28 below
the trunk bottom and at the other footprint edge.

`fov_check.py` compares the v29-only points against the URDF mount (15 degrees
nose-down) and the pattern's -7 to +52 degree elevation and 0.1 m minimum
range, ignoring self-occlusion. Among the informative ones, 51 of 3,282,
16 of 1,041 and 24 of 1,822 lie inside the sensor's field beyond its minimum
range. These are unobserved rather than structurally unobservable. v29
therefore waives some never-observed cells that the sensor could see, not only
the blind slice. The field is taken from the simulator pattern, not from a
hardware datasheet.

## Saved start states

`runs/v29_start_states01` recompiled the unchanged regression `gen_probe`
against v29 and replayed the seven frozen states. All seven continue, with
boundary PVA, the full-curve gate and all three negatives:

| State | Accepted XY | v28 |
|---|---|---|
| stopped, 0.3517 m | 1.016 m | fails |
| 0.3549 m | 1.016 m | 1.016 m |
| 0.360 m | 1.016 m | 1.968 m |
| 0.365 m | 1.968 m | 1.968 m |
| 0.370 m | 1.016 m | 1.968 m |
| 0.380 m | 1.016 m | 1.968 m |
| control, 0.3987 m | 0.564 m | 0.564 m |

`result.json` and `result_queries.csv` are byte-identical to the diagnostic
counterfactual's (`column_waiver_probe`, top 0.1085 m, traced build) for all
seven states. At 0.360, 0.370 and 0.380 m, v29 accepts the 1 m prefix where
v28 accepted the 2 m one. v29 is also stricter than v28 at some points, so this
may be an effect of v29 rather than search order. It was not traced, and routes
that v28 handled could progress less under v29.

## Native regression

`runs/v29_native_regression01` reran v28's unchanged suite (476 s). `review.py`
compares the 24 fixture and continuation JSON outputs and the 11 continuation
query CSVs with `runs/v28_native_regression01`. It checks the negatives files
and the ground contract only for their pass flags. The independent review
separately confirmed that all 36 JSON outputs are identical to v28's.

- **Continuations:** all 11 manager continuation replays are accepted, with
  boundary PVA, the full-curve gate and negatives. Their complete JSON outputs
  are identical to v28's, and repeats are identical.
- **Fixtures and contracts:** all 8 unmapped and 5 mapped fixture outputs are
  identical to v28's. The ground and body-support contracts pass.
- **Query CSVs:** two differ from v28's in three rows; every other column is
  equal. The explanations are in `difference_explanations.json`, recomputed
  from the saved body poses:
  - `original_queries.csv`, rows 3 and 7: `active_occupied` goes from 1 to 0.
    The rear circle centres lie at body-frame z +0.0604 and +0.0573, but their
    voxel centres lie at +0.0726 and +0.0754, above v28's band. v29 now waives
    them.
  - `expired_queries.csv`, row 4: `active_occupied` goes from 0 to 1. The rear
    circle centre is 0.368 m from the nearest circle centre, outside the 0.35 m
    radius, but its voxel centre is inside at 0.348 m. v29 now blocks it, a
    stricter verdict.

  Neither changes a continuation outcome. Before the independent review found
  these, `review.py` compared JSON only.

After normalizing timestamps and timings, 18 files still differ from v28:
17 probe logs and `execution.log` (`log_differences_vs_v28.json`):

- **Near-sensor diagnostics** (all 13 fixtures, v26, v26_repeat): these are
  the first 120 near-sensor query diagnostics. Queries at 0.35 m that v28
  reported as UnknownObstacle, such as a fixture body at 0.30 m queried at
  body-frame +0.05 m inside a voxel whose centre is at +0.075 m, are now
  waived. Because the dedup set fills differently, later diagnostic lines
  shift.
- **Throttled `reactive_collision_blocked` lines:**
  - In `mapped_low_box` and `unmapped_empty`, the first blocked query changes
    from the now-waived (-0.177, -0.177, 0.350) to (-0.002, 0.302, 0.275).
    Both the point and its voxel centre are outside the footprint circles, so
    both versions block it.
  - In `mapped_low_box_near_wall` the new first blocked query is
    (0.540, -0.040, 0.287). The point is outside the circles (0.362 m), but its
    voxel centre is inside (0.346 m) and not inflated. v28 would have waived
    it, so this is another stricter verdict, like `expired` row 4. The fixture
    output is identical.
  - In v26 and v26_repeat, v28's only such line (UnknownObstacle at z 0.409,
    body-frame +0.067 with its voxel centre above the band) disappears without
    replacement.
- **v26 and v26_repeat, first three-axis solve:** in both versions, "The robot
  is inside an obstacle" is followed by `first_optimize_step_success=0`. v28
  ended that solve through "A-star error" and
  `rebound_no_valid_new_constraints`. v29 instead ends it with "First three
  control points are in obstacles; t=0". The fixed-height recovery that
  follows is identical, and so is the accepted curve.
- **v23 and v23_repeat:** in both v29 repeats, the first goal-neighbour A*
  exceeds its 0.2 s wall-clock budget. v28 found the 0.728 m neighbour there.
  The next candidate (0.710 m) is then found as in v28, and the output is
  identical. The same timeout, frontier and 0.710 m sequence appears in 1 of
  2 v27 runs, 0 of 2 v28 runs and 2 of 2 v29 runs, at the same line. This is
  consistent with emulation wall-clock variance, but v29 also changes
  near-start verdicts that this A* queries, and no node counts were recorded.
  A v29 contribution is not excluded.
- **execution.log:** build progress lines only.

## Independent review

The first read-only review (2026-09-28) failed two of eight checks. Both were
gaps in this record, not in the code:

- the two query-CSV differences were unrecorded;
- the conclusion about where v29 is more permissive was too strong.

The corrections above address both. The re-review then passed all eight
checks and replaced the first verdict in place
(`runs/v29_native_regression01/independent_review.json`). Its first concern
summarizes the first outcome. The review's non-blocking concerns are kept as
limits:

- **Wider risk example:** an unobserved lateral railing or shelf edge beside
  the trunk, inside the 0.35 m circles, is also waived (see PLAN.md).
- **Per-point verdicts:** the verdict is now point-dependent within one voxel
  at the circle edge and at the -0.05/+0.10854 m limits. A* nodes, optimizer
  samples and the safety check can therefore see different verdicts inside the
  same voxel. The function itself is deterministic and shared by all of them.
- **Sensor height while walking:** in the stopped state the measured sensor
  sits about 1.1 cm above the URDF origin, probably from pose-stamp skew. The
  URDF limit is the more conservative of the two.
- **Contract scope:** the contract covers one recorded state family and only
  the path without a body reference.
- **Carried-over mount:** the regression request still mounts an unused v17
  `/probe` directory, as v28's did.

## Not repeated

The v28 UBSAN saved-seed replay targeted an optimizer crash in code that v29
does not touch (PLAN.md).
