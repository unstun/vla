# Upstream reuse for measured-geometry navigation

Stage: experiment + analysis. This record follows Dr Sun's explicit request to
reuse established GitHub implementations instead of adding local frameworks.

| Source | Pinned revision | License | Actual use |
| --- | --- | --- | --- |
| [SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner) | `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` | Apache-2.0 | Existing native GridMap, AStar, B-spline optimizer/refiner and controller. Restore its arc-length sampling and optimize-before-retime ordering in the local endpoint/collision adapter. |
| [Navigation2 Humble](https://github.com/ros-navigation/navigation2/tree/3c3db59d6969d8ecee8e68468693d006397f4a0c) | `3c3db59d6969d8ecee8e68468693d006397f4a0c` | BSD-3-Clause for costmap sources; Apache-2.0 for Navfn/Smac sources | Surveyed references: class-independent observations, sensor freshness, current footprint, reachable goal-neighborhood proposals. No Nav2 process or library is substituted into SCAN. |
| [Fast-Planner](https://github.com/HKUST-Aerial-Robotics/Fast-Planner/tree/41be219fe4ecc43bf0e0c2b42a523f8755ccc0bd) | `41be219fe4ecc43bf0e0c2b42a523f8755ccc0bd` | GPL-3.0 | Surveyed reference for at most three post-optimization time adjustments. Execution reuses SCAN's existing `refineTrajAlgo`; Fast-Planner itself was not built or reproduced. |
| Newton | `c2ca70bec5998062b0b2d35869865cbe3a49feee` | Apache-2.0 | Existing pinned Newton 1.6.0, SolverMuJoCo, shape BVH, Warp first-hit rays, automatic contact-capacity estimation and native surface-separation calculation. The mesh-contact scenes use MuJoCo-Warp on CPU, while the earlier flat locomotion qualification used native MuJoCo CPU. |
| [Voxblox](https://github.com/ethz-asl/voxblox/blob/c8066b04075d2fee509de295346b1c0b788c4f38/voxblox/include/voxblox/core/common.h) | `c8066b04075d2fee509de295346b1c0b788c4f38` | BSD-3-Clause | Adapt its epsilon-biased point-to-grid floor in SCAN's existing index conversion. `1e-6` voxel units corresponds to 50 nm at the 5 cm map resolution. Both insertion and queries use the same conversion; no Voxblox runtime is installed. |

Exact source bytes, URLs, licenses and SHA-256 manifests are retained under
`references/2026-09-26_trajectory_diagnosis/` and
`references/2026-09-26_generic_occupancy/`. Original build/run instructions stay
in the upstream README snapshots; original SCAN acquisition and local ROS port
are recorded in the experiment's `setup/` manifests. No new dependency was
needed for the geometry repair. The same pinned ROS Humble image and existing
Newton environment execute the bounded tests.

## Local adaptations and their reasons

1. Remove the mandatory person-track batch from the collision owner and driver
   readiness. SCAN already receives all measured points; a semantic detector
   failure must not invalidate unrelated free space.
2. Retain positive terrain classification for the same lifetime as its native
   occupancy cell. Cell reset, support-map replacement and ray clearing
   invalidate it. Current or retained nonterrain occupancy always wins.
3. Initialize Unknown only inside the current, fresh SCAN two-circle footprint
   at the body-height slice. This is narrower than Nav2's unconditional
   footprint clearing: a measured or inflated obstacle is never erased.
4. Replace the local dense quintic seed sampling with SCAN's arc-length sampler.
   Fit the existing hard endpoint PVA constraints, optimize, then adjust time.
   Recheck the native component limits after each adjustment, at most three
   times, then retain endpoint, norm-dynamics and complete collision validation.
5. Use an explicitly recorded vertical envelope for the generic flat cases.
   The `.55 m / .35 m` bounds come from 29 measured robot poses. They cover the
   tested low obstacle, but are not a validated universal stair/foot-contact
   model. The archived `.1 m / .1 m` configuration remains available.
6. Contact capacity is not a collision-clearance threshold. The old explicit
   `nconmax=100` overflowed on the detailed human mesh. Newton's documented
   `None` defaults select 1218 contact slots and 4872 constraint rows for the
   flat scene. One continuous 30.7-second command replay is identical for the
   first seven seconds and remains standing with automatic capacity. The old
   configuration now raises before stepping with more contacts than its buffer.
7. Native contact candidates include a 0.1 m per-shape detection gap. Use
   Newton's own `contact_surface_separation` before labeling them touches.
   Remove the detection gap from AABB-based robot-size estimates. The refined
   flat configuration uses a measured 0.35 m two-circle radius with unchanged
   0.18 m offset. This is a conservative bound on the recorded configurations,
   not every possible joint pose.
8. The SCAN41 empty-neighbor proposal is a failed diagnostic: an empty cell
   need not be reachable. SCAN42 instead adapts Smac's reached-node goal
   tolerance termination in the existing SCAN AStar. The selected v9 flat
   profile uses a 1.0 m temporary neighborhood and 50 approach iterations;
   earlier 0.5 m / one-iteration candidates remain diagnostic evidence. Every search edge, the later
   exact local target, and the complete output curve still need native checks.
   A temporary endpoint cannot complete the original global reference.
9. The captured refined curve is mathematically at `z=0.3`, but double-precision
   arithmetic produces values such as `0.29999999999999993`. Plain floor maps
   these into a different vertical cell. The same native map rejects six raw
   samples but rejects zero when only the diagnostic query height is exactly
   `0.3`. After the Voxblox index convention, all raw refined samples pass;
   two real collisions in the earlier optimized curve remain blocked.

No actor position, class, identity, velocity or bounding box enters navigation.
Simulator body pose is still used as localization, as in the archived bridge.
The synthetic flat control scene supplies a flat support prior; all obstacle
occupancy comes from actual first-hit rays. Frozen-cloud planning evidence does
not establish continuous physical navigation.

## Reproduction entry points

- `materialize.py --variant bounded_retime` creates SCAN40 from hash-verified
  SCAN33. It rejects an existing candidate directory instead of overwriting it.
- `build_candidate.py --source-candidate .../runtime/scan40_geometry_v1
  --cache-from .../runtime/scan39_geometry_v1` runs the original bounded build
  and returns source/install manifests and build logs.
- `scripts/replay_local.py old_positive --native-build .../scan40_geometry_v1
  --run-id <new_id> --inputs .../runs/flat_human_behind_inputs_v1/inputs` reuses
  the unmodified recorded-input replay.
- `scripts/run_bounded.py` requires absolute child-command paths because it
  changes the working directory. Pass `run_local_episode.py` with
  `--geometry-obstacles --static-human --scene flat_static` and the qualified
  native build. Each run must have a new ID.
- Generate the PCT flat pickle with `prepare_flat_scene.py` inside the native
  ROS image, whose NumPy 1.21.5 also reads it. NumPy 2-generated pickle files
  cannot be assumed readable by this pinned NumPy 1 runtime.

Neither the original Isaac stair A4 gate nor real-world generalization has been
validated by these changes. See the repair results for positive and negative
cases instead of promoting source inspection into reproduction claims.

## Controller follow-up

`references/2026-09-26_generic_occupancy/controller_followup_sources.json`
records the pinned SCAN closed-loop controller and Nav2 Humble regulated-pure-
pursuit controller. SCAN's feedforward plus position feedback, endpoint
`finish_dist` test, and yaw-based execution freeze match the local ROS port.
Its configured finish distance is 0.15 m. Source inspection alone does not
prove that changing this tolerance would correct the observed physical drift.
Nav2's approach-speed/collision regulation is surveyed only; no RPP controller,
new local trajectory generator, or changed controller limit ran in v4/v5/box-v1.

Current selected build regeneration:
`materialize.py --variant reachable_goal --revision 9 --native-optimizer
--capture-curves --voxblox-index`, followed by `build_candidate.py` with the
explicit newly created source candidate. Do not overwrite an existing build.
The captured-curve logging belongs to this diagnostic candidate. Its native
optimizer is the hash-verified existing SCAN ROS port from scan04, followed by
the unchanged final PVA, dynamics and complete-curve collision checks.
