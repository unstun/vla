# Local reference-window progress

## 1. Scope

Scoped to the versioned local Newton/SCAN Building integration. v6 addresses
the frozen v5 continuation whose selected target is 0.173953 m from the previous
accepted curve endpoint. Native queries classify its start, target and straight
connection as free, but the former FSM/manager guards require 0.2 m.

This contract covers local translation admission. It does not establish full
Building arrival, arbitrary obstacle handling or real-robot capability.

## 2. Signatures

- `SCANPlannerManager::hasLocalTranslation(const Eigen::Vector3d &start,
  const Eigen::Vector3d &target) const -> bool`.
- ROS boolean `manager.resolution_aware_progress`, default `false`.
- `versions/v6/building_planner.yaml` enables the mode alongside the v5 height
  optimization mode. The original empty-floor configuration omits it.

## 3. Contracts

The manager owns one predicate shared by its close-target guard and the FSM's
goal-neighbor, shorter-prefix and final local-target guards. Do not restore a
separate hard-coded distance at one of those callers.

Both modes reject non-finite endpoints. The default retains the finite-input
0.2 m norm threshold. The explicit resolution-aware mode also requires:

1. Both endpoints lie inside the existing native map.
2. Map resolution is finite and positive.
3. Horizontal translation spans at least one map resolution, allowing only
   `1e-9` cells of numerical roundoff.
4. Endpoints occupy different XY cells using `GridMap::posToIndex`.

Use actual configured resolution; never substitute a new fixed centimeter
threshold. XY translation prevents vertical-only motion from counting as
forward progress. The full-resolution requirement rejects tiny movements that
happen to cross a cell boundary.

A true result is not a collision verdict. Existing search, supported terrain,
unknown/stale rejection, boundary PVA, dynamic feasibility and complete-curve
checks still determine whether a trajectory can be published. Original route
goal and progress-time ordering remain mandatory. Do not use this predicate
to bypass a failed planner or to synthesize a short connector.

## 4. Validation and errors

| Condition | Required result |
|---|---|
| Legacy mode, captured 0.173953 m target | Reject as before |
| Explicit mode, same captured target and native-free map | Select target; native continuation must independently pass |
| Same position or less than one resolution of translation | Reject |
| Vertical-only displacement | Reject in explicit mode |
| Non-finite endpoint | Reject |
| Out-of-map endpoint | Reject in explicit mode |
| Stale sensor/body after clock advances without new inputs | Full native planning rejects, regardless of translation predicate |
| Valid translation with a colliding or unsupported curve | Original trajectory gates reject |

## 5. Cases

Good: the original 54 scans, PCT route and accepted spline 3 reproduce the v5
failure twice; v6 accepts the same target through actual FSM/manager calls and
retains full-curve/PVA checks. Base: the default mode continues to reject that
short proposal and preserves the empty-floor condition. Bad: change only the
FSM's literal, leave the manager rejecting the same proposal, and call it fixed.

The Nav2 Smac reference at commit
`3c3db59d6969d8ecee8e68468693d006397f4a0c` separates same-cell goals from translated
goals. This local predicate additionally requires one full cell resolution;
it is an adaptation, not a reproduction/import of the full Nav2 planner.

## 6. Required tests

- Call actual native FSM and manager on the original captured continuation,
  not a copied expression or fabricated unobstructed path.
- Verify old rejection, same target selection, native continuation success,
  original goal, hard boundary PVA and complete collision coverage.
- Retain no-progress, sub-resolution, vertical-only, invalid-coordinate and
  stale-input negatives. The out-of-map negative applies to the explicit mode.
- Call continued planning before a separate direct-manager check can replace
  the captured local trajectory. Evaluate the returned spline with a mutable
  value copy because native inspection APIs take non-const references.
- Repeated frozen runs compare actual native control points as well as booleans.
- Full physical acceptance and video remain separate; a passing frozen fixture
  or recorded-input flat replay cannot establish live navigation stability.

## 7. Wrong versus correct

Wrong: lower 0.2 m in one layer, relax unknown-space or freshness checks, or
rename a failed whole-route trial after one short curve succeeds.

Correct: share the scale-aware translation rule across all relevant callers,
retain the native trajectory gates, freeze a new version before running it,
and report the precise component and physical outcomes separately.
