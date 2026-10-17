# Reactive stair collision contract (local candidate)

Status: **inactive source candidate**. The ROS-free `reactive_collision.h` is
locally compiled and exercised by focused tests. It is not connected to
`GridMap::getInflateOccupancy`, ROS topics, SCAN search, spline optimization,
or the live trajectory safety callback. No Foxy or Isaac result follows from
these tests.

## Required input boundary

The shared `CollisionDecision::decide` function takes these separate inputs:

1. `TerrainSnapshot`: source ID, frame, observation timestamp, XY resolution,
   XY grid origin,
   and a complete set of ground surfaces for the queried region. Each XY cell
   can have multiple elevations and each surface carries `Flat`, `Stair`,
   `Unsupported`, or `Unknown` support. A wide tread needs supported cells
   throughout its interior, not just near its nosing. Missing cells are
   unknown. The snapshot needs a declared valid age and body-height alignment.
2. `NonTerrainVoxel`: source ID, frame, timestamp, and `Free`, `Occupied`, or
   `Unknown` at the current 3D collision query. It must retain every
   unclassified raw obstacle as occupied. `Free` must mean that a separate
   producer has positively separated terrain returns from nonterrain returns;
   the existing inflated SCAN buffer alone cannot make that distinction.
3. `TrackSnapshot`: source ID, frame, timestamp, `complete=true`, and the
   **entire currently observed** person set. Each track has identity, its own
   observation timestamp, current XY center, and physical footprint radius.
   The decision adds robot radius to each footprint. An accepted fresh empty
   snapshot is the explicit clearing observation. Missing, incomplete,
   duplicate-ID, future, or stale tracks block planning. No velocity field or
   trajectory prediction exists in this contract.

All lengths are metres and times are seconds on one monotonic clock domain.
The adapter must verify frame transforms before accepting a snapshot. The
planner's query must be in map bounds; unknown and out-of-map queries block.
The default age limits in the pure contract are illustrative local-test values,
not an approved runtime timing budget. A production adapter must pin them to
measured update rates and fail closed on missed updates. A stale track snapshot
blocks all queries until a fresh complete observation arrives.

The PCT source already has a possible **terrain input lead**:
`p2b_execution/pct_runtime/python/pct_planner/planner_node.py` publishes
`/pct_tomogram` as a `PointCloud2` with world `x/y/z` and `intensity` cost
fields. Its ground elevation comes from `planner_wrapper.py`'s `elev_g` array.
An adapter would have to preserve the originating tomogram hash, resolution,
layered elevations, frame, freshness, cost threshold, and publisher's
`tomogram_visual_z_offset` (default 0.03 m). The published cells are selected
for endpoint visibility and the publication is not a live obstacle classifier.
This source has not been accepted as a complete terrain-support producer for
SCAN. It must not be inferred from the raw occupied voxel columns.

No corresponding current-person track publisher or source identity was found
for this slice. A simulator-oracle track, if used later, must be labelled as
such, never reported as sensor-derived. The existing SCAN `cloud` input fuses
terrain and arbitrary obstacle returns, so a verified nonterrain occupancy
producer is also missing. These two missing inputs prevent a safe live hook.

## Source gate

`materialize_scan_05.py` verifies the entire accepted `scan_04` built source
tree against `source_sha256.json`, verifies its `overlay_manifest.json` plus
`terminal_accel_fix_manifest.json` provenance chain, and verifies the pinned
`baseline_config/planner.yaml` SHA-256. It copies only the source tree into a
new `builds/scan_05/src`, adds the ROS-free header, and writes a manifest that
says `inactive_no_live_adapter`. It refuses an existing output. No accepted
source or frozen occupancy parameter is edited. The added header is unused by
the copied planner, so this candidate retains scan_04 runtime behavior until
a separate, reviewed adapter and common collision hook are implemented.

Local checks:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic reactive_stair/test_reactive_collision.cpp -o /private/tmp/test_reactive_collision
/private/tmp/test_reactive_collision
python3 reactive_stair/test_materialize_scan_05.py -v
python3 reactive_stair/materialize_scan_05.py
```

Run these commands from `p2b_execution`. The C++ test covers full tread
interiors, layered elevation, flat terrain, nonterrain box/wall precedence,
person precedence, multiple tracks, freshness, explicit clearing, unknown,
out-of-map, wrong height, and the absence of any predicted person path. The
Python test checks the hash gate, a tampered baseline refusal, an immutable
source fixture, and duplicate-materialization refusal.
