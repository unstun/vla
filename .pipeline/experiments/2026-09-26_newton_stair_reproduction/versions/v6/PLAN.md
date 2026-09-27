# v6: resolution-aware local progress

Stage: experiment + analysis. Parent: frozen v5. Dr Sun approved diagnosing and
repairing the short frontier handoff, then testing the original full Building.

## Confirmed gap and seam

Native replay of the original 54 published scans, original body pose at
16.532543182 s, original PCT route and accepted spline 3 exactly reproduces
0.1739528469 m separation to the next frontier. Two repeated FSM/manager calls
reject it. Existing native queries report a free start, target and entire
straight connecting segment. The two-layer 0.2 m rejection is therefore a real
barrier before cubic optimization, not a hypothetical obstacle relaxation.

One change: an explicit Building-only `manager.resolution_aware_progress` mode
uses the existing map's resolution and XY cell coordinates for local progress.
Require at least one resolution of horizontal translation and different XY
cells. Same position, sub-resolution displacement, non-finite/out-of-map inputs
are rejected. A shared manager predicate serves its own short-distance guard
and the FSM's neighbor, prefix and final target guards. False/default preserves
the prior finite-input 0.2 m behavior, including the empty-floor configuration.

## Planned source boundary

- `planner_manager.h`: declare the shared local-progress predicate and mode.
- `planner_manager.cpp`: load the mode, implement the resolution/cell predicate
  and use it at the existing close-target rejection seam.
- `scan_replan_fsm.cpp`: replace its three duplicated distance predicates with
  the same manager predicate. Preserve all progress-time and target checks.
- Building YAML: enable the explicit mode while retaining v5 height optimization.

Do not replace search, spline fitting, costs or constraints. Keep original
unknown/stale/collision rejection, complete trajectory check, hard endpoint PVA,
dynamics, route goal, PD/RL control and temporal watchdogs. No new short-path
fallback and no manufactured free-space observations. No live-clock or flat
startup repair is included. A separate logical repair requires v7.

## Prospective validation

1. Freeze source, parent diff and exact config before native build/run. Native
   source/install hashes and previous frozen versions remain unchanged.
2. Recompile the original-input FSM probe against the candidate. Default mode
   must retain old rejection. Enabled mode must select the original short
   target and pass native continued planning, boundary PVA and full-curve gates.
   The probe must observe continued planning before any separate direct-manager
   call can replace the captured local trajectory.
3. Same-position, below-map-resolution, vertical-only and invalid target
   negatives must fail before optimization; advancing the clock beyond the
   existing freshness limits must block continued planning. Original measured
   inputs are not restamped.
4. Replay the recorded successful v3 flat inputs with the default mode. Require
   accepted moving curves; preserve all outcomes and do not infer live stability.
5. Run one bounded physical Building trial with the exact original scene,
   spawn, goal and original Warp triangle contacts. Use existing common and
   Building reviewers. Preserve failure if another independent barrier appears.
   Render original saved states only and deliver a regular, verified MP4.

Native FSM code is compiled unchanged for diagnosis; compiler access-check
suppression allows the probe to call private methods but does not alter data,
returns or planning branches. Its two automatic FSM timers are canceled only
while restoring/calling the captured state; normal map subscriptions remain.
The actual physical run uses the normal production executable and timers.
