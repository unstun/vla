# v52: bounded terrain-cell lookup reuse

Stage: experiment + analysis. Continue the authorized local-planner tail task.
Parent: v50 (itself directly from v48); v49 is not an ancestor. v51 is storage-only.

The 2026-10-02 unchanged-native replay reproduces the cold corner failure at
476-482 ms. Sampled CPU profiling places terrain-tree lookups first (24.28%).
Change only the raw/scored cell lookup inside reactiveFootprintSupportQuery.
Within the existing single-threaded raw-contributor cache scope, reuse pointers
to the two immutable layer vectors for an exact integer XY cell; bound the table
to 4096 cells and clear it at the existing scope and input-mutation boundaries.
Missing cells may be memoized, but no selected layer or safety verdict is cached.

Owned runtime files: grid_map.h and scan_reactive_grid_methods.inc in the new
scan74_terrain_lookup_v52 source tree. Preserve all parent source bytes.
Source identities, frames, exact positions, layer association, step threshold,
clock/freshness, map boundaries, occupancy, final goal/yaw, PVA, controller,
trajectory ownership and stop flow retain their original checks and order.
No deadline, retry removal, cross-callback cache or physics change.

Before a physical trial: test real cache hit/miss/capacity, nested scopes,
mutation invalidation and uncached parity; run inherited native/cache/warm/
goal-region/backend contracts; compare repeated cold replay outputs bit exactly.
Build and run on gpu5070ti, retaining bulk inputs/builds/logs there. Return only
compact checks, original-input hashes, performance results and review videos.
A component speedup alone cannot establish 30 Hz or physical continuity.
