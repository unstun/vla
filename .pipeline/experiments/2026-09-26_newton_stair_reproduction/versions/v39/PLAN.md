# v39 scoped raw-contributor classification cache

Stage: experiment + analysis. Evidence parent: frozen v38; native source parent:
frozen v36 `scan67_nav2_contract_v36`. One change: reuse an identical raw voxel
contributor classification during a single planner-manager replan call.

Dr Sun approved the CPU/GPU comparison and native local hotspot optimization
on 2026-09-30. The diagnostic native replay preserves the v36 geometry result:
122.220 ms total, 114.896 ms inclusive raw contributor classification, 10,274
classification calls inside 12,082 reactive queries. Timing scopes include
overhead; final performance must be measured with uninstrumented source.

Owned native changes are grid_map.h, grid_map.cpp,
scan_reactive_grid_methods.inc and planner_manager.cpp in a new scan68 tree.
The cache stores only the Occupancy derived from contributing raw log-odds and
retained terrain/nonterrain hit labels at one ring-buffer address. Freshness,
support/height/layer association, original physical XYZ, map bounds, current
trunk mask and final collision decisions are never cached.

An RAII scope enables/clears reuse for one replan call, including its original
fallback. All actual input/map mutations invalidate before modifying buffers,
hit labels, inflation offsets or sliding origin. Queued input refresh invalidates
even if no message is taken. The scope restores its previous state and clears
on exit, including exceptions; ordinary safety queries remain uncached.
The single-executor map ownership remains the preceding SCAN contract.

Before execution, preserve v38 and v36 bytes, old native preimages and an exact
source snapshot. Test real cache hits, mixed unclassified obstacles, unknown
contributors and mutation invalidation. Replay both v32/v33 recorded states;
require the full geometry JSON to match v36 exactly and record actual wall
durations vs 33.333 ms. Re-run native timing/goal/emergency/cancel checks.
Any speed gain without matching geometric safety/outputs is rejected.

No optimizer iterations, objective, search budgets, voxel size, collision sample
spacing, feasibility checks, native goal/control contract or physics changes.
GPU graph remains a separate physics component; it is not silently adopted by
this native optimization. Full episode launch remains v36 until separately
integrated, reviewed and authorized. No full navigation/RTF acceptance is implied.
