# v48 inline review

The single behavior change is manager initialization from its own accepted
remaining curve, with explicit P2B identity/goal/time supplied by the FSM. Only
manager/FSM source/header pairs change; 94 native files match v47. Candidate 1's
window selection policy is unchanged. No independent subagent review occurred.

The candidate refreshes sensor inputs, validates the entire remaining cubic via
the unchanged native heading/occupancy/support predicate, checks any connector
via collisionFreeSegment, and fits fresh samples to original input start/end
PVA. It retains source timing in the guess. The original optimizer, time
adjustment, minimum cruise, upper dynamics, hard final boundary PVA and newest
full-curve checks still run. An accepted result receives a new native trajectory
identity. A rejected guess clears warm ownership and runs the original graph
and fixed-height chain; it does not count an extra warm failure as a parent graph
failure or publish the old curve.

Invalid identity, goal, map instance, trajectory ownership, malformed/expired
curve, regressed clock, input PVA mismatch, stale/missing support, blocked
remaining geometry, unsafe connector, route regeneration and emergency stop
reject/invalidate reuse. There is no cached safety verdict. Collision and terrain
implementations, controller, final yaw logic and physics/sensing are unchanged.

Unfrozen candidate build01 used upstream arc-length resampling with a nominal
interval; all six paired warm optimizations rejected and fell back, with a slow
55-57 ms v33 tail. Build02 retains accepted timing in the initial guess and all
six warm solves pass without graph fallback, at roughly 3 ms versus 10.6-11.7 ms
cold. Both candidates, build/test logs and hashes are retained. These stopped
states are paired component evidence, not a claim about live 30 Hz.

The backend package is materialized as actual v48 files before freeze and its
ten files match the parent bytes. Verify live navigation_contract/global_refresh
in the physical run. This prevents the missing-dependency fallback observed in
v47's excluded first trial.
