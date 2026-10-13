# v58 live endpoint-evidence certificate

Stage: experiment + analysis. Authorized by Dr Sun: "fix the prblem" following the post-70-second audit. Parent v57 (native v56); v49 excluded.

## Smallest change

Repeated final-goal A* expansion returns no path before warm initialization. Extend the existing necessary endpoint-region certificate with live, optimistic occupancy evidence. No admissible endpoint implies no successful search. Any possibly eligible endpoint retains native A*, all support/occupancy/PVA/dynamic/final-goal/yaw checks and recovery. No cached rejection, deadline, cancellation or stop change.

Native ownership: `plan_env/goal_region_bounds.h` (shared lattice enumeration), `grid_map.h` and `scan_reactive_grid_methods.inc` (necessary observed-footprint evidence), `path_searching/dyn_a_star.{h,cpp}` (certificate integration). Preserve v57 and its snapshots. Packaging changes only bind the new build/version.

The evidence is conservative: any known voxel in the square containing all possible cylinder centers retains a possible endpoint, regardless of its occupancy verdict. Unknown cells cannot admit a remote endpoint at any yaw. Near-body masking conservatively disables the evidence rejection. A positive result never grants free space or stair support. No callbacks execute concurrently in the qualified single-thread planner. Evidence is recomputed on each call.

## Validation

1. Preserve the original audit as the failing performance reproduction.
2. Property/native tests: no false negatives versus actual occupancy at multiple yaws; known/unknown/changed input, near-body waiver, shifted map, endpoint connectors, unchanged zero-tolerance and 3D paths. Keep all inherited native/cache/warm/freshness/physical-floor/backend contracts.
3. Build on idle gpu5070ti, bounded external build supervisor 1200 s and native tests 600 s (not planner timeouts).
4. Pair all 20 captured late states with certificate enabled/disabled, alternate order, require identical return/path, record max/P95. Freeze only after qualification.
5. One bounded 90 s simulation after qualification, external supervisor 360 s, original configuration. Preserve full-round tails, 70–90 s stage costs, complete-window successful Hz, travel/pauses and tracking.
6. Keep heavy data/builds on gpu5070ti; return compact reports, hashes, plots and a review video only.

## Following separate repair

The inherited sample/publication/receipt clock mismatch is a separate logical change, planned as v59 after v58 is measured. It must use an explicit shared trajectory time origin and preserve freeze, yaw, stop and all dynamics/safety contracts. Verify actual handover PVA/phase and closed-loop tracking; do not infer timing correctness from fixed-input PVA alone.
