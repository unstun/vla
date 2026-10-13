# v47 inline implementation review

Scope: Candidate 1 in the 2026-09-30 local 30 Hz audit. This is an inline review;
no independent agent review was performed under the session's inline restriction.

- Native ownership is the FSM header and implementation. The other 96 native
  files retain the v44 SHA-256 values. Planner manager, optimizer, map, terrain
  classifier, trajectory checks and controller implementation are unchanged.
- The accepted window is recorded only after `reboundReplan()` returns success,
  which includes the existing complete trajectory checks. Reuse supplies an
  intermediate target; every new solve still executes those checks.
- Route regeneration, collision/invalid-current-curve handling, emergency stop,
  final planning failure and invalid target selection clear the hint. Identity,
  exact final goal, map instance, finite positive span, clock freshness, measured
  projection, translation, start/target occupancy and current support constrain it.
- The final pre-freeze review found that the first implementation used planned
  start projection for growth. Build attempt 3 adds an independent nearest-route
  projection of measured odometry in the existing selection loop; a regression
  requires that planned progress alone cannot grow the window.
- Growth uses the existing sampling step after half-window measured projection
  progress. Equal-span successes retain the growth anchor. This has no change to
  the final goal or goal orientation. The existing shorter-prefix convention of
  zero intermediate target velocity is retained for a reused shorter window.
- Goal tolerances, controller/planner YAML, navigation contract values, physics,
  policy, real-time pacing and sensor code match v45. Only version identifiers
  and native build paths differ in the launch wiring.
- First build and first test are retained. The first test caught zero-span growth;
  the unfrozen candidate was repaired with explicit finite positive-span guards
  and rebuilt as build attempt 2. Test attempt 2 exposed a fixture assumption:
  these stopped-state cases already succeed at the nominal horizon. Attempt 3
  tested an arbitrarily halved window, which the unchanged full-curve safety
  gate rejected. Attempt 4 searches a bounded set of shorter spans and requires
  complete native acceptance before testing getLocalTarget consumption. The
  v33 stopped state has no safe shorter zero-terminal-velocity window in that
  set. Attempt 5 records this coverage limit and requires the unchanged nominal
  fallback; successful shorter consumption remains a live-trial evidence gate. No frozen parent was overwritten.

The two stopped-state native fixtures establish cold-selection equivalence and
window safety/lifecycle behavior. The log-selected v45 categories are recorded
in `analysis/v45_representative_log_cases.json`, but no exact executable replay
of their complete live map/route/spline state was constructed. Performance claims
must therefore come from the separately bounded v47 physics test, with a clear
separate-run comparison limitation.

Final build 3: attempt 6 passes the 34 native and 48 cache checks, exact cold
geometry and all 24 v33 lifecycle checks; v32 passes actual shorter native
acceptance and getLocalTarget consumption but its growth assertion lands on a
floating-point half-span equality. Attempt 7 changes only that stimulus to
1e-6 route-seconds beyond the threshold, reruns both window fixtures and their
geometry, and explicitly inherits the core checks bound to the identical 98-file
native manifest from attempt 6. No native change follows build 3.
