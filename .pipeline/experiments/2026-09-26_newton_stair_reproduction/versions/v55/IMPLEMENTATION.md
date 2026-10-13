# v55 component result

Parent: qualified frozen v54. Recovery prefix endpoint admission now drains existing queued FSM body odometry and map inputs in the original callback/stamp order, before querying occupancy. The spline-derived start PVA stays fixed. The diagnostic line reuses this same boundary query; no verdict crosses a drain or later planner admission. Full manager/connector/optimization/final-curve gates remain unchanged.

The actual DDS test publishes recorded geometry with controlled fixture timestamps. Frozen v54 leaves fresh queued input unread and rejects the stale endpoint. v55 consumes queued current input and admits it, preserves exact start PVA, rejects absent/stale/future input and recovers with a new current sample. The cloud limit is still 0.25 s. This tests the real admission boundary and existing callbacks; it is not a live mid-solve observer reconstruction.

Build and contract attempt01 passed: 9 DDS freshness checks; pre-trajectory/clock/callback guards; 35 native and 64 cache checks; both byte-exact inactive-feature cold fixtures; 47 warm PVA/dynamics/final-curve checks per fixture; goal-region and backend contracts. Both complete native post-refresh corner rounds still succeed. Exact source materialization passes 100 hashes. Full corner reserve extension/physics/30 Hz await v56 integration. Bulk data stays on gpu5070ti.
