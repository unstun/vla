# v35: nominal local replanning at a configured frequency

Stage: experiment + analysis. Parent: frozen v34; native parent:
`runtime/scan65_evidence_floor_v34`. Dr Sun's instruction, 2026-09-30:
"按一定频率触发" (trigger at a configured frequency).

## Behavior and boundary

The existing 1 m displacement trigger can defer replenishment until a short
stopping trajectory expires. v35 adds `fsm.replan_frequency`, enabled at 2 Hz
in the version's Building and flat configurations. This is a provisional
default: v34's 26 logged successful optimizer durations have median 0.02415 s
and maximum 0.121 s, but do not measure complete planning/transport latency.

The change belongs in the native FSM, not in the bridge or locomotion loop.
Nominal initial planning and retry attempts are rate-limited by their start
times. During `EXEC_TRAJ`, periodic scheduling replaces the distance trigger;
the global-goal proximity and completion checks remain. Paused ROS time does
not create requests. Missed periods coalesce into one attempt instead of a
catch-up queue. A timestamp below the last nominal attempt re-anchors the interval;
smaller backward steps that remain after that attempt are not separately detected. The existing
single-threaded executor prevents overlapping solves. Execution-frozen status
suppresses the periodic transition from `EXEC_TRAJ`; a replan already queued
before the freeze signal is not cancelled by this change.

The parameter defaults to zero when omitted, preserving legacy scheduling.
Invalid, non-finite, negative, above-100-Hz, or non-representable periods are
rejected at initialization. The existing 10 ms FSM polling timer remains;
the configured frequency is a nominal maximum, not a hard real-time guarantee.

Collision-triggered replanning, explicit route/goal state transitions, emergency stops,
the admitted global route, PVA start state, complete-curve checks, braking
tails, controller, and locomotion remain unchanged. Safety-triggered solves
may occur between nominal attempts. The controller keeps its current valid
trajectory while a successor is being computed. The existing exhausted-retry
limit remains 1,000 attempts; at 2 Hz its elapsed duration will change.
Nominal solves following route/goal transitions share the same rate limit.

## Files

New native candidate: `runtime/scan66_periodic_replan_v35`, copied from v34.
Only its FSM header and implementation change. Version-owned files contain
the materializer, exact parent preimages/diff, two YAML configurations, source
identity, and targeted native tests. No change to frozen v34, scene geometry,
floor evidence, planner objective, deployment interface, or upstream repository.

## Checks and claim boundary

1. Verify the frozen parent and every copied native source hash; applying the
   recorded patch to saved parent bytes must reproduce the candidate exactly.
2. Build the native candidate in the existing pinned ROS image.
3. Exercise the actual compiled FSM: short trajectories replan on elapsed
   time before expiration; displacement does not trigger early; failure
   retries are limited; paused/rewound clocks do not burst; frozen execution
   suppresses periodic updates; final-goal/completion and legacy mode remain.
4. Check invalid frequency rejection and configurable periods.
5. Check that failed/throttled replans do not publish a replacement spline;
   preserve existing safety code byte for byte.

This task implements and checks scheduling. It does not authorize a new long
physics run, prove seamless PVA switching under compute latency, fix the
east-end corner's search failures, or validate dynamic-obstacle behavior.
Runtime/navigation acceptance and video remain separate evidence gates.
