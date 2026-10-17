# v4 cause audit: spline height leaves known free space; optimizer freezes Z

Stage: experiment + analysis. Date: 2026-09-27. Audit only: v4 working sources,
frozen version manifest, native source/install and planner configuration are
unchanged. No v5, new physics run, training or hardware actuation was performed.
New files in this directory are diagnostic inputs, an observational API caller,
its outputs and this report, not an integration change.

## Finding

The first recorded short seed is feasible to native AStar, but the local
hard-boundary cubic fit moves intermediate heights out of the known-free slice.
The unchanged original SCAN optimizer zeroes every Z gradient. It adjusts XY
while retaining the failed height profile, then exhausts its three collision
restarts. The absent initial trajectory heartbeat is the later terminal effect.

This is an integration mismatch between the local spline initializer and the
upstream optimizer's fixed-height assumption. It is not evidence that the
physical stair corridor is impossible or that unknown cells should be cleared.

## Evidence chain

1. Live v4: native PCT publishes 46 waypoints over 5.0700 m. There are 79 checked
   short seeds, zero moving splines and zero walking commands. Each failed
   optimization has one rebound plus exactly three `keep optimizing` messages.
   The unchanged code emits that message only after its collision recheck fails.
2. The existing complete native replay consumes 630 recorded body observations,
   35 original unfiltered clouds, the original route and the original ground
   projection (87,775 points, generated with the same NumPy 1.21.5). Slower
   scheduling still produces 886 checked seeds and zero moving curves. More
   processing time alone does not remove the captured geometry failure.
3. An audit-only executable reuses the existing measured-cloud probe, links the
   unchanged installed `plan_env`, `path_searching` and `bspline_opt` libraries,
   and calls their public APIs. It loads the first 11 actual cloud/pose pairs,
   the original static support map and the body pose that exactly matches the
   first captured seed. Native AStar succeeds with 15 nodes. The native cubic
   fitter and native optimizer reproduce the same failure/retry pattern.
4. In the original seed, the intermediate plateau is z=0.4486473083 m. The
   fitted curve reaches z=0.4598216965 m at t=0.336481 s: 11.17 mm above that
   plateau. Another blocked sample is z=0.4545359670 m. Both cross the 0.45 m
   boundary between 5 cm occupancy layers in this local map.
5. The diagnostic verdict at the rejected rear-circle points is 6
   (`UnknownObstacle`), with occupancy Unknown and inflation=0. A measured solid
   obstacle is not the rejection cause at these two sampled positions.
6. All eight native collision-check sample heights remain numerically identical
   after optimization; only XY changes. This matches `grad_3D.row(2).setZero()`
   in both rebound and refinement costs. Upstream contains the same behavior.
7. A second identical native evaluation returns exactly the same result.
   At both blocked samples, before and after optimization, changing only the
   queried height to the original seed plateau changes blocked to free. The
   0.449 m control is free; 0.451 m is blocked. These are scoring-only queries,
   not an alternative trajectory, parameter relaxation or navigation success.

| Same XY/yaw/map query | Native result |
|---|---|
| Captured curve height 0.45982 or 0.45454 m | Blocked |
| Original seed plateau 0.448647 m | Free |
| 0.449 m, below the local voxel boundary | Free |
| 0.451 m, above the local voxel boundary | Blocked |

## Hypotheses and secondary issues

- **Fitting leaves the valid height corridor:** supported by the native fit,
  native collision queries and height-only controls.
- **Optimizer cannot repair the changed height:** directly confirmed by source
  and identical pre/post Z samples. The problem is adapting this fixed-height
  optimizer to the locally fitted three-dimensional stair seed.
- **Heading discrepancy:** real code inconsistency. GridMap/search uses measured
  body heading for sub-centimetre segments; the optimizer retains the upstream
  0.1 mm / zero-heading fallback. However, querying the captured failed curve
  with measured body yaw does not clear these blocked samples. It is not the
  demonstrated primary cause here.
- **Terrain misclassification or a physical obstacle:** not the verdict at the
  decisive sampled failures. Other neighboring queries do return UnknownSupport;
  broader terrain qualification remains separate.
- **Search pool too small:** the live log has 80 endpoint/pool failures on longer
  proposals, but the 15-node short search succeeds. Enlarging the pool alone
  would not resolve the demonstrated post-fit collision rejection.
- **CPU or transport timing alone:** insufficient explanation because the
  slower full replay and frozen-map optimizer reproduce the failure.

## Source references

All local paths below are relative to the experiment root:

- `runtime/scan43_prefix_diagnostic_v2/src/bspline_opt/include/bspline_opt/timed_cubic_initialization.h:38`:
  local hard-PVA fit fixes three controls at each end and least-squares fits
  the remaining position samples without an occupancy constraint.
- `runtime/scan43_prefix_diagnostic_v2/src/bspline_opt/src/bspline_optimizer.cpp:1014`:
  native collision recheck; lines 1049-1070 restart and eventually return false.
- Same file, line 1169 and line 1197: Z gradients are explicitly zero.
- `runtime/scan43_prefix_diagnostic_v2/src/plan_env/include/plan_env/scan_reactive_grid_methods.inc:108`:
  occupancy below the observed threshold is Unknown; the current footprint can
  resolve it only in the existing measured interior and height band.
- `runtime/scan43_prefix_diagnostic_v2/src/plan_env/include/plan_env/known_lite3_trunk.h:30`:
  the existing footprint allowance is bounded in height and never erases an
  inflated hit. Crossing a layer can leave this allowance.
- [Pinned SCAN optimizer, upstream](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/bspline_opt/src/bspline_optimizer.cpp#L1043):
  original fixed-Z cost and collision restart implementation, verified online.

## Artifacts and limits

`SUMMARY.json` contains machine-readable conclusions and immutable-source checks.
`native_map.json` contains native pre/post samples; `native_map.log` contains the
matched classification trace. `height_query_control.json` and its log retain the
16 isolated queries and the identical optimizer repeat. `frozen_map/` preserves
the exact first seed and selected input pairs. The observational caller lives
under `probe_source/`; compiled output remains under `probe_build/`.
`FILES_SHA256.json` records the non-build audit files. The full replay is under
`replays/v4_cause_replay01/`, with its exact command and build/input hashes.

The native API probe freezes the map and pose; it does not claim wall-time
scheduling parity with the live episode. It establishes this first seed's
geometric failure mechanism. It does not prove that every later proposal has
the same cause or that a single repair will complete the whole Building route.

## Recommended v5 boundary

First repair only the height contract between the validated AStar seed and
the spline initializer/optimizer. Reuse the existing native search and spline
interfaces, preserve the fixed endpoint PVA and ground-clearance requirements,
and verify the generated curve against the same known-space collision rule
before treating it as a feasible optimizer input. Do not blindly unlock Z,
which could permit physically unsupported vertical motion.

The fixed captured input is the first regression gate. Preserve the current
unknown/occupied rules and original goal. Only after that gate passes should
a separately versioned v5 Building trial test actual motion and final PD hold.
This audit does not implement or claim that repair.
