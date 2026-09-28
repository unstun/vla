# v28 start-state thrash: diagnosis from saved inputs

Stage: experiment + analysis, 2026-09-28. This is diagnosis only: no version,
no threshold change and no physics. All replays use the pinned local Humble
image, the v28 native tree (`runtime/scan60_constraint_guard_v28`) and the
v28 regression `gen_probe`, except where the point-semantics counterfactual
below says otherwise.

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

## Not yet explained

With point semantics at 0.3517 m, the continuation still fails in the optimizer.
The rebound A* reports "A-star error" and "A-star failed; aborting
optimization", and one refined curve is "unsafe or dynamically infeasible". At
starts of 0.3549 m and above, production semantics pass every stage. A second
height-dependent effect therefore remains in the optimizer's collision and
rebound path and needs its own trace before any repair.

The separate wall-time freshness chain (clock rejection, reconnect stall,
`odom_stale`) is unaffected by this diagnosis.

## Boundary

Replays use frozen inputs and a fresh clock. The counterfactual build is a
diagnostic prototype only, not reviewed and not a version.
