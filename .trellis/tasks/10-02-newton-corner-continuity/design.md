# Corner repair design

E2 denotes .pipeline/experiments/2026-09-26_newton_stair_reproduction.
Base: frozen runtime/scan74_terrain_lookup_v52. Stage: planning.

## D1: Compatible reference refresh — planned v53

P2BRoute already separates requested goal_pose from the grid-snapped path endpoint.
The backend caches requested XYZ/yaw per full owner identity (v52/backend_ros/
p2b_backend_ros/node.py:145–170); the controller retains its initial requested
pose/latch. FSM end_pt_ follows the path endpoint.

Bind reuse to exact qualified requested XYZ/orientation and every current owner/
map field. Use existing finite/unit-quaternion validation; add no goal tolerance.
Real requested-goal/yaw changes invalidate reuse. Keep FSM target/reference
endpoint and controller goal/yaw semantics unchanged. Unqualified/legacy goal
input retains exact-endpoint context and the original unconditional invalidation
on reference regeneration; compatible-refresh reuse requires a qualified pose.

Make reference regeneration transactional: save previous reference/window/binding
and flags, restore them on failed refresh without publishing/restamping the old
curve. On successful compatible refresh retain the accepted local curve and create
a newly projected window candidate. Never copy old reference times into new times.

Remember accepted window endpoint and measured/growth anchor in world geometry;
reproject with existing sampling/resolution/progress contracts. Preserve original
TTL and growth rule in corresponding geometry. Nonfinite, unmappable or blocked
mapping disables the hint. Measured progress/expiry reserve are separate from new
accepted IDs: repeated trimming of one endpoint is not extension.

All reuse runs newest-input full remaining-cubic and native connector checks,
then original fit, optimization, retiming, minimum cruise, PVA/dynamics and final
whole-curve gates. target_connector remains a rejection; select an admissible
shorter window instead of forcing the long connection. No old curve restamping.

Native ownership: plan_manage/include/plan_manage/scan_replan_fsm.h and src/
scan_replan_fsm.cpp; minimal planner_manager.h/cpp context/helper changes only.
Controller and message schema are read-only. Tests/replay are version-owned.

## D2: Recovery freshness — planned v54

Keep the original spline-derived start PVA fixed within a recovery chain. Before
considered prefix endpoint/support admission, drain queued sensor/body messages
through existing refreshSensorInputs with original stamp order/callback ownership.
Target projection/yaw, fresh-body fallback and occupancy queries remain unchanged.
No Free verdict survives a drain. No new executor or parallel solve.

Cloud limit stays 0.25 s; all other freshness/bounds/support rules remain. No valid
queued input means rejection. Use original map/cache invalidations. Drain at
recovery decision boundaries, not each A* node/sample; profile full rounds to detect
redundant processing. Expected ownership: FSM cpp, minimal GridMap interface only
if the existing drain needs it. Controller, clocks, stop and deadlines unchanged.

## D3: Physical floor presence — planned v55

Saved dense products show cells (154,59)/(155,59) have floor 1.583031 m but raw
traversal cost 50, removed by existing <=20 publication. Front cell (156,55) has
floor 1.558031 m and cost 3.642. The guarded fill mistakes the omitted neighboring
floor for a drop. Physical floor existence is not central traversal or clearance.

Keep selected navigation and current <=20 surface evidence unchanged for central
admission and measured terrain-return classification. Derive a separate qualified
physical-floor snapshot from the same pinned dense PCT ground before traversal
cost filtering, following existing selected_ground_points(cost_limit=None) with
exact world frame, resolution and layer precision. Use a distinct physical-floor
input role/type, retaining elevation and cost without a traversable Support label; cost-50
cells remain ineligible for central traversal. No mesh/manual-fill runtime authority.

Use the new snapshot only where guarded fill/ETH neighbor evidence asks whether
missing selected support is an absent floor/drop. Keep unambiguous nearest height,
true-drop and step tests unchanged. Central positive support candidates originate
only from original selected evidence. Thresholds, guard/footprint radii and layer
rules do not change. New geometry never feeds LiDAR terrain-return classification,
waives an occupied contributor, or grants central traversal in a rejected cell.

Bind producer bytes/source provenance to the new version. Native input validation
covers original layout plus source/frame/clock, resolution/origin and layer
association. Missing/stale/mismatched physical input grants no new support;
absent optional input preserves original behavior. Configured readiness prevents
old-publisher fallback. Clear borrowed caches before snapshot/scored-ground
replacement; retain all nonterrain history.

Ownership: plan_env grid_map.h/cpp, scan_reactive_grid_methods.inc,
evidence_floor_fill.h and minimal ETH neighbor-evidence plumbing. Version-owned
producer/asset generator, bridge publication entry and Building config are needed.
Original navigation tensor, cost threshold and selected surface bytes stay fixed.

## Upstream distinction

Pin 348e8a590a50a5a6bbab8d8c6dcfd171f009be26 uses have_new_target_ for fresh
polynomial init after refresh. It has no local v47 feasible-window cache or v48
accepted-owner cache/target_connector rejection. Remaining-trajectory initialization
appends an unchecked polynomial extension and rewrites Z; those remain excluded.
The compatible-refresh reuse is a deliberate local improvement, not a claim to
restore the upstream callback verbatim. See research/upstream_comparison.md.

## Rollout, rollback and risks

Planned chain: v52 -> v53 -> v54 -> v55; v49 excluded. Freeze each qualified
component delta before the next logical change. A frozen failed version stays
immutable; repair uses next integer with recorded parent. Reuse exact parent
snapshots; no copied builds/runtime assets. Navigation reference remains v48
until reviewed physical evidence supports changing it.

Rollback selects a frozen predecessor. Keep existing single-thread behavior,
failure counters and backend admission/stop reasons. No hard solve deadline,
new stop reason or old-curve restamping.

Tests exercise route callback -> selection -> real manager and queued input ->
actual drain -> predicate, with sequential clock/input progression. Seed-only or
point-intersection passes are insufficient. All identity/new-obstacle/true-drop/
multilevel/stale/history/final-check negatives remain. Physical-floor role tests
must prove no obstacle waiver or rejected-central-cell grant. If listed safety
cannot be preserved, retain the failed fixture and present the conflict for review.
Shared-host load can block physical performance evidence; never stop another job.
Corner passage, strict 30 Hz and complete-route arrival are separate measured gates.


## Version allocation update 2026-10-02

Frozen v53 passes its declared component suite but actual DDS pre-trajectory replay exposes a mixed-clock exception. Preserve that failure. Chain is v52 -> v53 -> v54 (clock guard) -> v55 (D2 freshness) -> v56 (D3 physical floor). Original behavior scope and final physics gates are unchanged.
