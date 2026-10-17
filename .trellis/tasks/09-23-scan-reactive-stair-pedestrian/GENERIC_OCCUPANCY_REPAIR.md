# Class-independent measured-geometry repair

Stage: experiment + analysis. Authorized by Dr Sun on 2026-09-26: repair
navigation for arbitrary nontraversable geometry, including an initially
stationary person, without simulator object coordinates or semantic labels.
This supersedes the person-tracker prerequisite in the original task design.

## Behavior and source boundary

SCAN already inserts all unfiltered LiDAR endpoints into its native occupancy
map and preserves unclassified nonterrain hits. The local common collision
decision additionally requires a complete current person-track batch, making
semantic detection failure invalidate unrelated free space. Remove this
dependency at the collision owner and at the experiment driver's readiness
check. Geometry-only episodes do not launch a tracker; old tracker replays
remain diagnostic evidence for the former failure.

The required navigation inputs remain measured clouds, synchronized sensor/body
poses, terrain support and the requested route. Unknown/out-of-map space,
unclassified occupied voxels, stale clouds and invalid support remain blocked.
Positive terrain-return classification must never clear a nonterrain hit.
No object identities, semantic classes, animation roots, bounding boxes or
simulator hit labels may enter navigation. The same native decision remains
used by search, optimization and full-trajectory execution checks.

Use Nav2's Humble obstacle/voxel layers at
`3c3db59d6969d8ecee8e68468693d006397f4a0c` as a surveyed design reference:
measured points mark occupancy regardless of category or motion, clearing is
based on rays, and freshness belongs to sensor observations. Do not import a
new planner or describe this adaptation as a Nav2 reproduction.

Dr Sun reiterated the upstream-first requirement on 2026-09-26. Native SCAN
continues to own AStar, occupancy, B-spline optimization, refinement and final
validation. Restore SCAN's original control-point arc-length sampling and
optimize-before-retime ordering. Use Fast-Planner's bounded post-optimization
adjustment pattern with SCAN's existing refinement function; do not introduce
another trajectory generator. Preserve every failed candidate and label
search paths, accepted curves, physical execution and goal arrival separately.

## Owned changes

- New repair sources, materializer and tests under the Newton experiment's
  `repairs/2026-09-26_generic_occupancy/`; materialize from hash-verified SCAN33
  into a new local runtime build. Preserve old builds, thresholds and runs.
- Native collision header, GridMap subscription/callback seam and a bounded
  native cloud-query probe. Capture exact spline initialization inputs to
  diagnose and repair the timing defect separately.
- A separately materialized episode driver with geometry-based readiness;
  explicit candidate selection in `run_local_episode.py` / `native_graph.py`.
- Static actor controls and generic geometric sensor fixtures used only to
  construct actual ray measurements and score outcomes, never planner inputs.

Do not modify sibling repositories, restart the remote server, train policies
or actuate a physical robot. Do not refactor unrelated Isaac work.

## Ordered acceptance

1. Native contract tests fail on the old mandatory-track dependency and pass
   on the candidate. Fresh geometry works without a tracker; stale/missing
   geometry, unknown space and nonterrain occupancy still reject queries.
2. Actual first-hit rays of an initially stationary official human, box,
   thin wall, post and low obstacle enter the native GridMap without classes
   or object coordinates. Check occupied geometry, available detours and a
   blocked corridor. Check partial visibility and explicit ray clearing.
   Any robot-volume blind spot found by these cases must be resolved before
   claiming class-independent collision coverage.
3. Replay the captured failure clouds and a complete native planning attempt.
   The original two shape-gate rejections may remain in diagnostic tracking;
   they must not be the cause of an unrelated navigation stop.
4. Capture exact seed arrays / endpoint PVA / limits, reproduce the excessive
   timing and repair it against the upstream ordering without bypassing native
   dynamics, endpoint or complete collision checks.
5. Run a bounded continuous local loop and deliver actual trajectory/video
   evidence. State separately planning success, physical execution and route
   completion. Original Isaac A4 stays open.
