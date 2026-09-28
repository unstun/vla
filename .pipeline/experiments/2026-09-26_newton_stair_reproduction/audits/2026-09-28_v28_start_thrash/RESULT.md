# v28 start-state thrash: diagnosis from saved inputs

Stage: experiment + analysis, 2026-09-28. This is diagnosis only: no version,
no threshold change and no physics. All replays use the pinned local Humble
image, the v28 native tree (`runtime/scan60_constraint_guard_v28`) and the
v28 regression `gen_probe`, except where the point-semantics, traced or
sensor-column counterfactuals below say otherwise. Those builds change
production thresholds only inside diagnostic copies.

## Frozen states from `v28_historical_full01`

`prepare_inputs.py` was adapted from `2026-09-27_v26_frontier` and uses the
original scans, paired poses, route and traj 1.

| State | Clock | Scans | Body z | Continuation |
|---|---|---|---|---|
| control | 12.296 s, when traj 1 was published | 12 | 0.3987 m | accepted 0.5641 m, matching the live traj 1 |
| stopped | 12.686 s, the last pose before the emergency hold | 16 | 0.3517 m | fails; every seed search returns status 2 |

The stopped replay reproduces the live thrash. `attempt01_domain_id` failed
before any replay because ROS domain 233 exceeds the DDS limit. Its inputs were
reused unchanged.

## Mechanism

1. Under the RL gait, walking lowers the measured body by about 4.7 cm relative
   to the factory-PD stand (0.399 m to 0.352 m). The first plan started from the
   standing height.
2. SCAN's footprint query samples up to about 5 cm above the body reference.
   At a 0.352 m body it reaches the voxel layer spanning 0.40–0.45 m (centre
   0.425 m) beside the trunk. The LiDAR (at 0.473 m, shallow downward field of
   view) never crosses those cells, so their log-odds stays unknown (−2.00243).
3. The Nav2-derived known-footprint waiver (`known_lite3_trunk.h`) frees an
   Unknown cell only if the cell centre lies within `|local z − 0.01| ≤ 0.06`.
   Hand computation for the seven blocking cells gives:
   - voxel-centre local z of +0.0707 to +0.0753, which fails the band, although
     every cell is inside the footprint circles;
   - queried-point local z of +0.048 to +0.066, which passes.
4. The queries therefore return UnknownObstacle (verdict 6). The live safety
   check at 12.691 s hit these same cells (q z 0.40095) and stopped "in
   0.000s". Every later GEN replan from the lowered pose then failed its seed
   search.

## Evidence

- **Height sweep** (`height_sweep/`, `fine_sweep/`): with every other input byte
  unchanged, only the final body z varies. The continuation flips between
  0.3545 m (fails) and 0.3549 m (passes, 1.016 m accepted). The band predicts
  0.425 − 0.07 = 0.355 m. The 0.4 mm offset matches the body's roughly 1°
  pitch in the local-frame rotation. Starts at 0.360–0.380 m accept 1.968 m,
  and every passing start clears the boundary and full-curve gates.
- **Point-semantics counterfactual** (`point_waiver_probe/`): a diagnostic copy
  of the v28 tree evaluates the waiver at the queried point instead of the
  voxel centre (one expression; see `diagnostic_change.json`).
  - `attempt01_static_link` is invalid: `plan_env` installs only
    `libplan_env.a`, so the prebuilt probe still contained v28's code.
  - With `gen_probe` rebuilt from the same regression probe source, near-sensor
    Unknown hits fall from 7 to 1. The seed searches that failed now succeed:
    46 nodes to the 2 m prefix, and an exact endpoint recovered for the 1 m
    prefix.

## Optimizer trace with point semantics (2026-09-28, after Dr Sun chose it)

`optimizer_trace/` copies the point-semantics tree and adds stderr tracing
gated by `VLA_TRACE` (`make_trace_source.py`, `diagnostic_source.json`). The
tracing covers blocked queries with their reason, the optimizer's segment and
rebound checks, its A* endpoint checks and the refine checks. The traced
stopped and control replays match the untraced counterfactual byte for byte
(`result.json`, `result_queries.csv`), so tracing did not change decisions.
The same frozen stopped state, with only the final body z changed, was
replayed at six heights:

| Body z | v28 (voxel centre) | Point semantics | Point + sensor column |
|---|---|---|---|
| 0.3517 (stopped) | fails | fails | 1.016 m |
| 0.3549 | 1.016 m | fails | 1.016 m |
| 0.3600 | 1.968 m | fails | 1.016 m |
| 0.3650 | 1.968 m | 0.541 m | 1.968 m |
| 0.3700 | 1.968 m | fails | 1.016 m |
| 0.3800 | 1.968 m | 1.968 m | 1.016 m |
| 0.3987 (control) | 0.564 m | 0.564 m | 0.564 m |

Accepted values are the continuation's XY displacement. Every accepted curve
passes boundary PVA and the full-curve gate.

**Point semantics alone is a regression on this state family.** It fixes the
seed search at 0.3517 m but still fails there. It also fails at 0.3549, 0.360
and 0.370 m, where v28 plans. The reason is that the voxel-centre test waived
a whole voxel whenever its centre was in the band. For bodies between about
0.355 and 0.38 m, that included the upper part of the 0.40-0.45 m layer, up to
2.5 cm above the band. The point test removes that accidental margin.

The trace (`optimizer_trace/trace_summary.json`) shows two blocking classes:

- **Never-observed cells above the band inside the footprint.** These are
  UnknownObstacle queries above the band. At 0.3517 m there are 97, of which
  60 lie inside the footprint circles at body-frame z 0.07-0.1085. At 0.360 m
  there are 222, of which 115 lie there. The rest are outside the footprint,
  and almost all of those are above 0.1085. They end the refine checks and
  the A* end checks. For example, the refined curve at 0.3517 m is rejected at
  body-frame (0.41, -0.02, 0.088). The seed search is not traced. Still, with
  point semantics the seed first backs up about 0.15 m and climbs 5 cm. With
  the sensor column added (below), it leaves straight ahead, so these cells
  also cause the detour.
- **Footprint support at rotated headings.** After that detour, the early
  control points turn up to about 40 degrees away from the body yaw (-1.385
  rad). The footprint circle centres then fall on cells to the robot's west
  that have no selected ground within the step limit (`foot_height`). The
  optimizer's A* endpoint walk then moves backward and downhill through the
  floor until it leaves its pool ("Ran out of pool"). The walk is upstream
  EGO-Planner behavior. The support check is unchanged from v28. Both also
  occur at 0.380 m, where planning succeeds.

## Why these cells are never observed

`optimizer_trace/voxel_dump/blind_zone.json` dumps the voxels around the start
(from a fresh probe build, see Attempts). The pinned Isaac URDF (`803d5527...`)
places the Mid-360 scan frame at (0.1824, 0, 0.10854) m in `TORSO`. It is
pitched 15 degrees nose-down. The simulated Mid-360 uses the official Livox
scan pattern with elevations of -7 to +52 degrees
(`runtime_sources/bridge/lite3_sim_bridge/mid360_pattern.py`, pattern SHA-256
`aa1fc08b...`). After the mount pitch, the lowest rearward ray is 8 degrees
above horizontal. Unknown voxels have log-odds below
clamp_min_log - 1e-3, as in `reactiveOccupancy`. In the stopped state, within
|body y| <= 0.35 m:

- Every voxel behind the body centre, from 0.20 to 0.60 m, is Unknown.
- Ahead, the 0.35-0.40 m layer is Unknown to about 0.4 m. The 0.40-0.45 m
  layer is 67% Unknown in the first 0.2 m and 9% at 0.2-0.4 m.

This region is structurally unobservable from the robot's own sensor. The
trunk band (|z - 0.01| <= 0.06) covers only part of it.

## Causal test: point semantics plus the sensor column

`column_waiver_probe/` changes one more expression in the traced
point-semantics tree (`diagnostic_change.json`). The footprint waiver's
vertical test becomes -0.05 <= body-frame z <= 0.1085. The upper limit is the
URDF LiDAR origin height above `TORSO`; the same value was measured in the
control replay. The footprint circles, the Unknown/inflation tests, the torso
function and every other byte are unchanged.

All seven states now plan and pass boundary PVA and the full-curve gate, as the
table above shows. The no-progress, out-of-map and stale negatives still
reject. The seed now leaves the stopped start straight ahead with no detour.
Every UnknownObstacle block that remains has body-frame z above 0.1085 (70
queries; 29 inside the footprint XY, 41 outside it). None lies inside the
column.

Two differences from v28 are unexplained. At 0.360, 0.370 and 0.380 m the
column variant accepts the 1 m prefix where v28 accepts the 2 m one. These
accepted curves were not traced further.

## Implication

The remaining optimizer failure is caused by never-observed cells between the
trunk band and the sensor. These cells are inside the robot's own footprint,
where the tilted LiDAR cannot see. Point semantics alone makes this worse. The
causal counterfactual changes the waiver's vertical threshold. That is a
safety-semantics decision for Dr Sun, so no v29 was built from this audit.

Decision (2026-09-28): Dr Sun chose "Point + LiDAR column" after seeing this
trace. It became v29 (`versions/v29/`), with the URDF value 0.10854 m.

## Attempts

- `optimizer_trace/` reused a copy of the counterfactual `probe_build` made
  with `cp -R`. The copy gave its objects new timestamps, so the edited
  `gen_probe.cpp` was not recompiled, and the first voxel dump was absent. The
  traced libraries and `planner_manager.cpp` were rebuilt (their trace lines
  appear), and decisions match the untraced run.
  `optimizer_trace/voxel_dump/` reran stopped, 0.360 and control with a fresh
  probe build. Its results equal the first trace run's and include the dump.

## Boundary

Replays use frozen inputs and a fresh clock. Across the sweep only the final
body z changes. The recorded sensor pose, scans and map stay the same, so every
stopped-family voxel dump is byte-identical. The point-semantics, traced and
sensor-column builds are diagnostic prototypes only, not reviewed and not
versions. The replays show planning outcomes for one recorded state family, not
live behavior. The wall-time freshness chain is untouched.
