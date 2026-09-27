# v5: restore explicitly selected terrain-constrained height optimization

Stage: experiment + analysis. Parent: v4. Dr Sun authorized the targeted height
repair and both flat/Building regression checks after the read-only audit.

One change: expose SCAN's already-computed Z cost/gradient to its existing
optimizer when `optimization.optimize_height=true`. Default false retains the
previous fixed-height behavior and the v3 empty-floor condition. Apply the same
choice to rebound and refinement; otherwise refinement could discard the repair.
Only the optimizer header/source and a Building-specific YAML change. Existing
initialization, objectives, weights, search, control and acceptance gates stay.

This restores the existing three-axis gradient mechanism found in the previous
local stair adaptation and in pinned EGO-Planner; it does not replace the whole
optimizer or copy a new planner. The current native collision decision still
requires positive ground support and body clearance 0.30 +/- 0.12 m. Unknown,
occupied, stale and out-of-map remain blocked. The manager's hard endpoint PVA,
velocity/acceleration and full-curve collision gates remain mandatory. This is
not unconstrained flight or a claim that three-axis optimization alone completes
stair navigation.

## Source and change boundary

Create `runtime/scan44_height_v5` from hash-verified
`runtime/scan43_prefix_diagnostic_v2`, preserve the parent, and patch only
`bspline_optimizer.cpp` and `bspline_optimizer.h`. `materialize_height_candidate.py`
records the exact source identity and diff. Reuse the existing bounded native
builder and cached build products; preserve its full source/install hash checks.
The native manager still rechecks every published curve, including the fixed
ground-height envelope. Existing v4 diagnostic logging is inherited unchanged.

## Prospective gates

1. Freeze the version snapshot before compilation/testing. Native build must
   pass with source bytes unchanged; record source and install identity.
2. Recompile the existing v4 audit API caller against the v5 header/library.
   With the mode omitted/false, the original frozen seed must retain its failure
   and original returned coordinates. With the mode true, the same input must
   produce a successful first optimization and a collision-clear curve, with
   boundary PVA retained. Original map/pose/cloud inputs remain byte-identical.
3. Replay the recorded v4 Building inputs with the complete native planner.
   Require an accepted moving spline, not just optimizer success. Repeat the
   recorded v3 empty-floor condition with the fixed-height mode and check its
   moving curves/acceptance relative to the unchanged v4 native build.
4. Run the existing native sensor cases: empty free space, human/box/thin wall/
   post/low box, occluded space and blocked corridor. Their unknown/occupied and
   stale-input negatives must remain blocked. No geometry rules are changed.
5. Run actual v5 empty 12 m physics using the v3 native CPU, pacing 0.5 condition,
   and Building physics using the original Warp triangle contacts. Preserve the
   original spawn, goal and PD gates. Use the existing reviewers and record
   partial/failure outcomes separately. Produce video from actual recorded states.

Do not extend v5 silently if another cause appears. A separate behavior repair
requires v6. Passing the first frozen seed is a component result, not complete
Building acceptance. Formal training, remote servers and hardware are excluded.
