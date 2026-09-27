# v4: Building startup passes; navigation fails before motion

Stage: experiment + analysis. Date: 2026-09-27. Parent: v3.

The complete original Building was tested at its archived stair start and goal.
Factory startup and a measured PD hold pass. The actual PCT/SCAN trial does not
produce an accepted moving spline and does not move toward the goal. Keep v3 as
the last accepted empty-floor condition; v4 is not a navigation acceptance.

| Evidence | Outcome |
|---|---|
| `test_version_identity.py` | Exact manifest copy, source mutation rejection and invalid version rejection pass |
| `v4_building_pd01` | Seven factory/PD checks pass; 13.2217 s continuous physics, 2.2 s hold observation |
| `v4_building_route01` | 14.5422 s continuous physics; native terminal `failed`, cause `initial_heartbeat_missing` |
| Native PCT | One route, 46 waypoints, 5.0700 m through the original map |
| SCAN | 79 checked short seeds, 79 failed first optimization steps, zero accepted moving splines |
| Applied commands | Zero nonzero steps; 175 acknowledged snapshots, no acknowledgment mismatch |
| Actual navigation movement | 0.00326 m accumulated settling motion; final goal distance 5.1113 m |
| Final control | PD FIXED_STAND; upright, no fall; 3.5014 s final hold interval |
| `v4_building_video01` | 181 original-state frames verified; full MP4 decode passes; 14.48 s encoded duration |

The delivered regular file is
`output/2026-09-27_lite3_versions/v4_building_test.mp4`. The video begins with an
exterior overview, then shows the robot at the stair entrance. Orange is the
native PCT route. Two native spline messages are stationary holds, not walking
curves. The failed terminal remains visible.

## Diagnosis boundary

The initial heartbeat failure is the terminal consequence of no accepted moving
spline. It is not proof of a PD fault or that PCT failed. The native log reports
80 search-pool boundary/endpoint failures on the longer proposals. A shorter
proposal produces a checked seed, but first-stage optimization returns false.
The origin of that optimizer rejection is not established by this live trial.
Current observation, search/optimization geometry and timing require a separate
frozen-input diagnosis before changing a limit or algorithm.

Source references: the existing pinned native `path_searching/dyn_a_star.h`
logs an out-of-range pool index; `dyn_a_star.cpp` rejects unhandled endpoints;
`planner_manager.cpp` records `first_optimize_step_success=0`. The full live
`scan.log` and `diagnosis.json` retain the sequence and counts. A diagnostic line
named `initial_spline_collision` does not alone prove actual collision; its
adjacent footprint verdicts must be read.

## Reproduction and limits

The frozen source/configuration identity and parent diff are `manifest.json`
and `changes.patch`; run08/v3 and its video remain unchanged. Each v4 run stores
the verified manifest. Exact commands and bounds are in its `request.json`.
The full scene uses the original 10,169 vertices and 16,448 triangles, with
the existing Warp CPU triangle-contact solver and automatic contact budget.
Its bounds are approximately 18.43 x 17.94 x 7.16 m. Native flat-plane physics
was not used as a substitute. The added actor is absent in this fixed-building
condition; the old moving-human profile remains available separately.

Simulation body pose supplies localization; LiDAR uses unfiltered geometric
rays. This is not RTX, hardware localization or strict physical factory
calibration. Architectural surface contacts are not scored by the Building
review, so no collision-free claim is made. The factory-to-navigation video
sampling gap differs from the normal frame interval; physical time comes from
the logged solver clock, not the MP4 frame count.

Common review intentionally fails its moving-curve/command/completion checks.
The dedicated Building review also returns `passed=false`. Their records are
under `validation/v4_building_route01_*`. `video_delivery.json` records only
media integrity, not navigation success. The original Isaac A4 stays open.

Any next repair must become v5 with one stated change and a new run ID. First
capture the short seed's optimizer rejection and compare the unchanged pinned
upstream implementation using the recorded current cloud/body/map inputs.
Do not relax unknown-space, collision, freshness or original-goal checks to
convert this failure into apparent success.
