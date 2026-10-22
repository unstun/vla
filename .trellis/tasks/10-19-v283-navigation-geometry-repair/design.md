# v283 design

## Source and change boundary

The local VLA repository is authoritative. Own new files under experiment
`versions/v283/`, using frozen native v280 and benchmark/execution v281/v282 as
parents. Resolve inherited bytes through manifests and snapshot locations.
The integrated change is consistent endpoint, local-trajectory, and spawn
admission under existing physical geometry. Preserve all parent snapshots.

## Replanning

Separate physical geometry validity from route-selection hints in
`pct_route_planner.cpp`. Use request-local endpoint context so live-feedback hint
disks cannot blacklist endpoints or connecting transitions. Real support/solid
and current live-obstacle admission remain binding. Apply the scope consistently
before and after solving: ignored live hints must not re-enter as hard repair
constraints in `pct_planner.cpp`.

Record endpoint role, request XYZ/yaw, geometry verdict, feedback/repair match,
mission identity, and map revision at rejection. Do not infer support validity
from a generic exception string. Existing neighboring-cell/16-heading start
expansion stays unless a failing regression proves a change necessary.

Reuse `route_policy.hpp` and `PlanOnGoalChange` ownership rather than adding a
second retry loop. Distinguish initial evidence-not-ready, temporary solve
failure, hint-only exclusion, and actual invalidity. Retained routes require
the same mission/destination, a valid current-to-remaining-route connection,
and fresh checks of the remaining geometry. Discarded path behind the robot
must not decide current route viability. Renewing a timestamp is not a fresh
safety proof. If no route exists yet, readiness waiting remains subject to
existing startup/mission deadlines and command ownership. Cancellation and
actual invalidity keep their original terminal behavior.

## Shared local geometry

Use the StaticSolidField already bound to PCT's descriptor/hash in SCAN. Connect
it to the common local collision query used by search, B-spline rebound,
post-refinement checking, and active-curve checking. Ensure controller snapshot
views retain the same immutable field. Keep existing support, live observation,
freshness and map-health checks.

The source field is a radial clearance at actual height/yaw, not a 3-D ESDF.
Reuse its exact assess/gradient in local repair where needed. Do not introduce
a second coarse map or a height-independent distance approximation. Keep the
two-cylinder profile unchanged; soft penalties never replace the hard final
curve check.

For CD12, inspect the four support refusals beginning at 37.511013 s against
the published spline, controller-lookahead yaw, measured pose, source epoch,
and support layer. Local support checks already exist. Correct the demonstrated
mismatch at the query, trajectory-admission, or tracking owner; a new wall check
alone is not a SupportGap repair. Retain distinction between an unsafe planned
curve and safe geometry followed incorrectly. Do not adopt the rejected
historical all-heading inflation or waive a true gap.

Expected copied source seams, only as needed:

- `lite3_nav2_plugins`: PCT route planner, plugin, route policy, and existing BT
  plan decorator; their targeted tests.
- `plan_env`: GridMap query, reactive methods, immutable query-view ownership.
- `bspline_opt`: exact geometry repair cost and existing sampled-curve helpers.
- `plan_manage` / `scan_nav2_controller`: only the owner identified by the CD12
  discrepancy, preserving PVA, dynamics, epoch and publication checks.

## Start construction

Extend the existing mesh-certified generator. Assess every old legal start,
including inherited historical requests, with authoritative geometry. Retain
qualifying starts. For each failure, enumerate connected candidates at the same
support level and requested heading; choose the nearest qualifying unused
start by deterministic distance/key order, then certify its attachment and path
to the unchanged goal. Require both extra margins >=0.10 m. Do not consult
native planner scores during selection.

Freeze a separate cohort and endpoint-difference table. Check distinct spatial
pairs as well as pose tuples. Keep low-margin goals as boundary tests; the new
0.10 m rule applies to starts. Freeze the original ten physical case identities
independently of the inherited score-based representative selector. Apply the
same replacement rule to G05 and every other failing start.

## Execution and sync gate

Execute on gpu5070ti with the inherited pinned container/policy and resource
admission rules. Do not alter unrelated jobs. Use an isolated v283 native copy.
Run all 53 CPU2 native timing calls before independent audit workers. Bind actual
installed binaries, fixtures, evaluators and generated configs to the freeze.
Begin physics only after the offline gate and all ten fixed cases pass.

Proposed remote roots:

- `/data/sun/vla_mppi_20261009/navigation_geometry_v283/`: native/build/evaluation.
- `/home/sun/vla_exec/physical_runs_v283/`: raw physical captures.

Local evidence root under the experiment:
`audits/2026-10-19_v283_navigation_geometry/`.

Sync sequence: local source -> owned-path transfer -> remote SHA equality ->
native tests and locally returned receipts -> freeze -> 53 cases and locally
returned gate -> ten attempts -> compact artifacts and video hash equality.
Remote-only results cannot satisfy acceptance. Adapt the existing once-only
physical ledger and immutable-state rendering; never rerun physics for a video.

## Risks, failure handling and rollback

The added static gate can expose unsafe seeds; fix optimization/repair instead
of bypassing the gate. Exact queries may cost time; use proven immutable caches
and measure the full cohort. A 0.10 m spawn margin only narrowly exceeds the
observed 0.0968 m drift. Offline success cannot establish physical tracking.

Keep formal failures and all ten route denominators. Once v283 is frozen, do
not rewrite it or silently rescore the same version after a code change. A new
logical repair needs the next integer version. Rollback means leaving existing
parents and the selected baseline untouched. No baseline promotion is implied.
