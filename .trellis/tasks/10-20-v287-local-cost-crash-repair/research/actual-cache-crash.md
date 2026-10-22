# First actual v287 native crash

A04's only physical attempt closes FAILED at60.998104s/61020 steps with controller_server SIGSEGV. The task-owned GDB wrapper preserves exit_code=-11 and a67242-byte all-thread stack, returned in the audit's ultra9/evidence/A04_native_backtraces/. This is an actual fault, separate from five qualification signal injections.

Thread20 faults in std::unordered_map<uint64_t,GridMap::TerrainCellLayers>::find, from terrainCellLayers at scan_reactive_grid_methods.inc:276. Callers are footprintSupportVerdict → reactiveOccupancy → twoCylinderQuery → collisionFreeSegment → AStar::AstarSearch:524 → reboundReplanAttempt → execFSMCallback. The action-control thread is sleeping; the mapping thread is releasing a PointCloud2 message. No stack establishes Eigen alignment or node-pool access as this crash's direct site.

The cache is mutable, stores borrowed layer-vector pointers, and is cleared on snapshot adoption/rescoring and raw-contributor scope transitions. Missing locking alone is not proof of an actual race: snapshotQuery constructs a separate query GridMap and does not mutate the planning object, and native work callbacks have a mutually exclusive group. Rank concurrent invalidation, stale lifetime and earlier heap corruption as hypotheses. A corrupted hash bucket can be a downstream victim. Require a real concurrent/captured-input repro or sanitizer report before claiming the cause.

Actual compile_commands show local plan_env/SCAN/optimizer/controller use C++17, O3, g1 and frame pointers, with no AVX/native-architecture flag. The inherited PCT core remains O2/C++14. Do not describe all14 packages as identically compiled or infer a new alignment fix from macros alone.

Frozen v287 is unchanged. Continue the authorized ten cases once and retain all failed records; no success retries or silently modified physical candidate.
