# v49: bounded local solve and recovery

Stage: experiment + analysis. Authorized by Dr Sun on 2026-10-01, including
gpu5070ti testing and updated time-series plots. Inline implementation/checking;
no Trellis task. Parent v48 and all original evidence remain immutable.

One behavior change: a shared monotonic deadline across local target selection,
warm initialization, native graph search, optimization, retiming, native recovery
and outer retries. Search/optimization receive 20 ms; full final safety checks,
publication preparation and timeout continuation validation share a 25 ms total
deadline. No retry resets it. Reject a candidate if any required check cannot
finish within the deadline. Native goal, yaw, PVA, dynamics, minimum cruise,
occupancy, support, freshness, controller and stop contracts remain unchanged.

Cancellation unwinds without publishing partial candidates. Preserve the prior
accepted trajectory transactionally. On timeout, continue it without restamping
only after exact current owner/route/goal/map/trajectory identity, nonexpired
time and a fresh complete remaining-curve check pass. If validation fails or
its reserved budget expires, close the same command gate and immediately invoke
the original emergency-stop publication. This is not a controller hold or
measured-stillness acknowledgment. Existing backend stop completion remains
mandatory. Independent safety callbacks retain their complete curve checks;
their recovery solve receives the same bounded chain.

Checkpoint cancellation does not preempt operating-system scheduling, allocations,
ROS publications or atomic input-update callbacks. Measure actual elapsed times
including recovery and report any deadline overshoot; do not claim a hard
real-time guarantee or eliminated tails from source inspection alone.

Native fork: `runtime/scan72_solve_budget_v49`, parent
`runtime/scan71_remaining_curve_v48`. Own deadline, planner, FSM, graph and
optimizer cancellation hooks plus exception-safe L-BFGS workspace cleanup.
No Candidate 4 cache/diagnostic changes, policy training or hardware actuation.

Before freezing: build on gpu5070ti; run inherited native/cache/cold-geometry/warm
tests and explicit timeout cases (search, objective/line search, retries, final
checking, old-curve preservation, fresh continuation, invalid/stale/expired/wrong
owner curve, exhausted validation reserve, stop admission). Preserve failed
candidate evidence. Compare recorded inputs against v48 with the budget inactive.

Then freeze exact source/configuration/install hashes and run the same complete
Building, historical-full route, geometry-only LiDAR, factory PD/RL startup,
RTF=1 and 6-CPU profile for up to 90 native seconds, bounded by 360 wall seconds.
Report attempt, successful new-trajectory, safe-continuation and controller rates
separately; a 30 Hz timer alone does not satisfy planning acceptance. Return raw
logs, state, configuration, source/install hashes and all original run files,
verify them locally, and render v48/v49 time-series comparisons. Full route
completion and final hold remain independent acceptance gates.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Execution copy: `/home/sun/vla_exec/vla` on gpu5070ti. Exact frozen dependencies
and native installation must match before launch. Evidence under `versions/v49`
and `runs/v49_realtime_trial01`; incomplete execution is not validation.
