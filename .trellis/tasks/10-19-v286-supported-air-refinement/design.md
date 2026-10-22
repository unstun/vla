# Design and change boundary

## Verified parent and behavior gaps
Parent native manifest b7e3ac56673c125540c17676723f4b2c9e479406ead783b1cc0a6f9ef23388d8; execution d1ec17d503abaf2f77f8e9e67ccee39fbec762083f7602f44e0fb828025643dc. Its 329 composed native source files are SHA-pinned. Scope is the local map decision, local A-star/target wrapper, two optimizer stages and tracker. No global planning, sensor, policy, timeout or hard-profile change.

## Contracts
1. Preserve occupancy provenance. An unknown-air candidate is admissible only inside the map, without an inflated obstacle, after the existing complete support decision passes and known source solids are clear. Keep real obstacle and evidence/freshness decisions. Do not enlarge the measured-trunk waiver or relabel unsupported terrain.
2. Endpoint XY proposals stay finite and on the nearest legal support layer. Evaluate projected candidates with feasible local headings; every expanded edge keeps full collision checks. Goal-neighborhood searches use the same terrain mode and original 3D tolerance; invalid far/out-of-map local requests fall back to the existing retained-reference frontier. Strict exact-endpoint behavior stays available.
3. Refinement scores smoothness, fitness and feasibility only. Environmental and new source-distance costs remain in rebound, followed by unchanged final checks. The shared ENV225 field stays unchanged. The requested 0.02 m source-cost knob does not exist in v285: add a local-only, smooth 0.055 m exact-source buffer, without global GPMP calls or publication vetoes.
4. Raise the large-heading travel scale floor from0.2 to0.5 while retaining the existing full-speed region and smooth transition. Apply one scale to both translation and phase. Existing final yaw, slew, emergency/cancel and measured-seed fallback remain.

## Owned paths
New v286 snapshot/wrappers and focused probes; production overrides in grid_map.h, scan_reactive_grid_methods.inc, dyn_a_star.cpp/.h as needed, inherited planner_manager.cpp, bspline_optimizer.cpp and tracking_node.hpp. Native tests/probes exercise real classes. Reporting/dispatch wrappers reuse verified v285 mechanisms with new output roots and manifests. Frozen v285 is read-only.

## Execution and rollback
Compose a private native tree from the verified v285 inventory; build with pinned ROS container, two CPUs and6GiB. Qualify parent/candidate fixtures, inherited tests, and unscored captured cases. Freeze source/installed/evaluator/cohort identity before all53 scored calls. CPU physics/policy and available-capacity GPU rendering use the already approved resource policy. Execute ten routes once after strict offline acceptance. Record/render original states without physics retries. Return compact proof and ten regular MP4s; retain raw data on gpu5070ti. On failure retain evidence and report unmet criteria; do not edit a frozen candidate.


## Authorized host recovery on2026-10-20
The original9700x is powered off pending a water-cooled RTX4090 fan cable. Dr Sun requested progress without that host. Reuse the existingv234 prefix onultra9 as a read-only dependency/input reference; create a separatev286 prefix. Recover all329 native files from local SHA-pinned snapshots, preserving the frozenv286 source and manifest. New host/build/installed/input identities belong in a migration receipt, never in the old native manifest. Reconstruct source geometry with pinned producers and compare original hashes. Preserve all53 endpoint/scenario identities and start certificates; if old captured scans cannot be recovered, regenerate zero-step captures and bind a clearly separate new-host input manifest. Re-run complete new-host validation under unchanged thresholds; preserve the old inaccessible53-call batch as separate evidence. Ten physical routes are unstarted and remain once-only across hosts.

Storage work is limited initially to inventory and concrete cleanup candidates onultra9. Preserve trained models, teacher banks, raw evidence, review videos, shared environments andljh data. Any deletion must identify exact paths and byte counts under the user's authorization; no broad prune or unique-data deletion. Keep full inventories and source identities local.
