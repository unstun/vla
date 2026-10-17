# v201 — step 2 completed at component scope

`PCTPlanner` now calls `OfflineElePlanner` directly in C++. It loads a pre-exported
map bundle and publishes the resulting path. There is no planning client,
PlanRoute service round trip, Python planner process or embedded interpreter in
this runtime path.

MissionBridge is reduced from 451 to 276 lines. Its planner, planning lock,
planning service, route publication, canonical planned endpoint and cached-route
fallback have been removed. It retains HTTP goal submission/cancellation/status
and Nav2 action handling.

## Verification

- Six related ROS packages built successfully in the existing ARM64 Foxy image.
- **11 fixed-input comparisons passed**: eight successful paths and three
  matching rejection cases. All **2,033 compared XYZ points had zero difference**
  against the old Python wrapper plus MissionBridge height semantics.
- The six native input matrices, metadata and original ground-validity mask
  matched the legacy map preprocessing exactly for both fixture maps.
- **21 component cases passed** (24 colcon report entries including wrappers):
  real plugin loading/planning without a mission service, fixed goal pose/yaw,
  failure after a previous success, malformed input, HTTP/action lifecycle,
  cancellation, default/explicit yaw and launch parameters.
- Dynamic linkage resolves to the rebuilt C++ PCT libraries, with no missing
  library or Python interpreter dependency. The reference comparison separately
  loaded the original v174 native libraries; their paths are recorded.
- All 116 original PCT source entries were verified before copying. Only its
  package/build metadata changed; native algorithm sources remain unchanged.
- **756 protected files** across v196–v200 remain unchanged.

The first build attempt lacked the OSQP CMake search prefix. The existing v174
build script supplied the archived v167 dependency path; no package was downloaded
and no algorithm repair was needed. The initial failure log is retained.

## Deliberate interface difference

The final goal pose now comes from the Nav2 request. HTTP input still supplies
ground XYZ, with body reference height added once; omitted `target_yaw_rad`
defaults to zero. PCT no longer rewrites that task pose or returns a previous
route when a fresh solve fails. The native optimized points themselves retain
the checked legacy coordinate and height semantics. A final connector over 2 m
is rejected, preserving the prior connector limit.

The launch argument is now `pct_map_bundle`, and HTTP status no longer exposes
the removed cached-path/canonical-planned-goal fields. See BUILD.md.

## Scope

No physics steps, full-route experiments or real-robot actions were executed.
The action tests used loopback fixtures, not the physical navigation graph.
The prior v196 physical route evidence and all frozen versions are retained.
The v200 single velocity publisher and physical terminal completion are inherited;
its controller sources were rebuilt unchanged. Their existing regression record
remains in v200 rather than being counted again here.

Steps 3–5 remain: LocalMotion consolidation, terrain/startup simplification and
event-driven global planning. The existing 1 Hz planning child is unchanged;
no dynamic blockage mask was added to PCT.
