# v50: conservative rejection of impossible goal-neighborhood searches

Direct parent: frozen v48. v49 is not an ancestor. Dr Sun authorized executing
the plan on 2026-10-01, including profiling, optimization, builds, safety tests
and performance comparison. No hard solve deadline or new stop protocol is used.

## One optimization and its proof boundary

The expensive upfront path is `getLocalTarget -> adjustGlobalTargetIfOccupied ->
findGoalNeighborhoodPath -> AstarSearch`. Before warm initialization, it searches
for the final goal or a tolerance endpoint even when no such endpoint can fit
within the current rolling map's collision bounds.

`getInflateOccupancy` requires both symmetric cylinder footprints to be inside
the map. Consequently their body center must be inside the map AABB reduced by
the cylinder radius in XY and by the unchanged vertical inflation in Z. Averaging
the two centers proves this necessary condition for every yaw; it is deliberately
looser than the true heading-dependent condition and does not assert clearance.

The precheck runs only for exact-endpoint searches with positive goal tolerance.
If the exact goal is in the necessary box, retain the original search, including
all exact terminal recovery. Otherwise inspect the goal ball against the box.
If they are disjoint, no successful endpoint exists. In the configured upstream
search-plane mode, enumerate a superset of its possible endpoint lattice positions
using the original plane formula and test box/ball intersection. Include the
initial node conservatively. If none can fit, return the original SEARCH_ERR with
an empty path. The FSM then uses its unchanged frontier/shorter-window handling.

Full 3D search, uncertain/invalid inputs, extreme coordinate scales and any
possibly eligible endpoint retain the complete native search. Numeric bounds
are expanded outward by 1e-6 m; invalid proof inputs cannot reject a search.
No result or occupancy verdict is cached, so each query uses current bounds.
The precheck never touches the executing trajectory, final goal, admission,
controller or stop state. Ordinary exact seed searches (zero tolerance) are
unchanged. The inherited A* 200 ms limit is unchanged; there is no new timeout.

## Passive profiling

`planning_profile.h` aggregates inclusive wall and thread-CPU durations for
local target selection, goal search/proof, input refresh, cloud/sliding-map
updates, seed/warm initialization, optimizer/refinement and final checks. Nested
categories must not be summed as disjoint costs. Existing loop timing now also
records the initial nominal round, avoiding the parent's missing initial result.
Timers never affect eligibility or dispatch cancellation. Instrumentation may
have small measurement overhead, shared by paired baseline/candidate replays.

## Paired replay and safety gates

The profiling harness uses original v48 observer messages, original point arrays,
archived PCT/support geometry and fixed clocks at three original round starts:
fast warm, slow warm and the 1.09 s live extreme. Both paths use the same compiled
native algorithm; the comparison switch only disables the new necessary-condition
precheck. It is not exposed as a runtime parameter. All accepted control points
and knots must match exactly. Observer receive order is deterministic, but original
DDS drain batching and feasible-window hints are not reconstructed; this is a
controlled paired replay, not an exact recreation of the original live latencies.

The three repeats of each case all succeed and retain exact geometry. In the
initial paired evidence the slow-warm median decreases from 106.004 to 3.128 ms;
the extreme-round input decreases from 33.403 to 4.805 ms. This latter replay
does not reproduce the original 1,090 ms dynamic retry sequence. Full-stack
trials remain the required measurement of live maximum latency and continuity.

Native goal/yaw/controller/cache/warm tests, independent exhaustive endpoint
checks, reachable-goal parity and newly expanded map bounds cover the precheck.
The actual native exhaustion notice must retain `native_replan_exhausted` and its
owner. Tests invoke the unchanged real backend handler, command gate and adapter:
the notice closes commands; stillness without hold cannot complete stop; motion
resets dwell; only hold plus measured stillness releases ownership. Wrong-owner
notices cannot close a new owner's gate. No backend/controller source changes.

`continuity_contract_identity.json` binds unchanged stop, collision, replanning,
admission, dynamics and cruise function bodies, backend files and configurations.
Builds and tests execute on gpu5070ti with exact sync and artifact-return hashes.
