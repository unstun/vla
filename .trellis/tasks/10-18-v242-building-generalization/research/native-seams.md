# Installed native evaluation seams

Read-only source inspection, 2026-10-18. No new batch/build/physics was run.
Paths below are repository-relative and were inspected in the local source.

## Reuse and interpretation

- versions/v232/tools/admission_probe.cpp: actual pluginlib PCTPlanner
  configure/activate/createPlan and original STATIC_ONLY support service.
  ROUTE_ENDPOINTS already accepts XYZ pairs; current probe forces yaw=0.
  A case adapter must preserve actual start yaw and native goal-heading policy.
- versions/v232/tools/field_probe.cpp: actual PCTRoutePlanner::plan,
  ENV225, 0.025 m samples and staticTraversability. FIELD_SCAN is only a
  soft-cost evaluation, not a completed SCAN plan/publication.
- versions/v230/src/lite3_nav2_plugins/src/pct_planner.cpp:128:
  first two attempts use GPMP, final attempt can use graph fallback. Separate
  first-GPMP admission from eventual admission and preserve repair reasons.
- versions/v232/tools/raw_route_probe.cpp and v224 PointCloudReference:
  evaluate original Building static raw-cloud oracle. This is not a new-pose
  LiDAR observation. Raw probe also forces start yaw=0 and needs adapter input.
- audits/2026-10-17_v237_terminal_approach/replay_probe.cpp: actual FSM,
  map, A*, optimizer and full-curve/publication observation. Historical curves,
  warm flags and prefix must not be inherited by a cold new-start case.
  Prefer public FSM init/DirectIO/nav2Map/setReferencePath/execution feedback.

## Critical boundaries

GridMap::staticTraversability in the v230 reactive-grid implementation tests
support/floor/height/edge/gap, not live LiDAR occupancy. STATIC_ONLY admission
therefore cannot grant live body clearance. initialize_map's three terrain
clouds do not constitute LiDAR coverage. Feed fresh paired body/sensor/cloud
through original callbacks and retain unknown-space and 0.35 s/0.1 s ages.

EnvironmentalField::assess().edge_margin and pointAssessment()[1] provide
body edge/raw-cloud margins. Positive values cap at target 0.15 m. Record
saturation as >=0.15 m and floor-known flags. Dynamic local margin needs its
own source/coverage label. Cold target selection alone is not a valid first
plan; require full dynamic/collision/epoch checks and normal spline publication.

## Identity and timing

Frozen v240 is the full 317-file v232 composition plus the five cumulative
FSM/GridMap/A* changes, not just the three files stored in v240/src.
Check actual PCT plugin/route library/core and inherited package prefixes.
Frozen core SHA-256:
80c020d7e652bebb59eab9c9418ce3f32c92c76b96241af5a4398ab5c0a89a68.
plan_env/path_searching/bspline_opt are static archives; a probe must not embed
old code that overrides the installed implementation.

Use steady_clock around createPlan, plus existing planning_profile phase
wall/cpu/calls for target, goal search, seed, optimizer, refinement, final check,
inputs and cloud. Record static service requests/rejected samples/reasons and
all retries. Fresh processes avoid cross-case warm/feedback/repair leakage.
