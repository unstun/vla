# Native optimization and process-failure boundaries

## 1. Scope and trigger

v232 repairs the failure class observed in v231 near46.686s, on frozen v230
navigation. This is an offline-validated candidate only until separately tested
in physics. Preserve RL, hard collision/support geometry, native heading
freshness and the existing route/retry/terminal acceptance conditions.

## 2. Signatures

- `environmentalCurveCost(q, interval, lookahead, score, heading, gradient,
  measured_yaw=NaN)` evaluates soft geometry with finite fallback headings.
- `GridMap::measuredBodyYaw()` provides finite measured orientation for the
  soft scorer only. `collisionTrajectoryYaw` and `motionHeading` remain hard
  query APIs with the original0.1s body-age rule.
- `scan_runtime::callbackBoundary(logger, site, work, failure) noexcept`
  catches standard/unknown exceptions inside a ROS callback and contains
  exceptions from logging/cleanup too.
- `nativeQueryCallback(logger, reply, work) noexcept` converts exceptions to
  `ready=false`, empty verdicts and `native_query_exception`.
- `runtime_failure.critical_exit_handler(path,run_id,epoch,component)` is
  registered with `OnProcessExit` on actual critical launch children.
- `runtime_failure.finish_failed(root,request,failure,state)` publishes the
  existing FAILED finish schema with matching run/epoch and known request ID.

## 3. Contracts

After distance/rebound evaluation sets STOP_FOR_ERROR or STOP_FOR_REBOUND,
`combineCostRebound` returns finite interim cost/gradient without more objective
work. L-BFGS callbacks latch this stop. The optimization entry must override an
ALREADY_MINIMIZED/convergence return with cancellation whenever the stop flag
is set; zero interim gradient must never turn a failed step into success.
Refinement also has an early-exit callback. Objective exceptions cancel normally
without unwinding through L-BFGS's manual allocations.

For soft scoring, an unavailable native heading falls back to nonzero local
lookahead, velocity, the nearest valid control-point segment, then finite
measured yaw. Position/heading Jacobians follow the chosen geometric source;
measured yaw is constant. Reject nonfinite input/sampled geometry, missing
finite heading, score or gradient before it can grant a successful solve.
Do not substitute fallback yaw into hard admission or remove source-age bounds.

Protect FSM timers and inputs, map callbacks and NativeWorker's query service
at registration/the called callback boundary. An FSM exception releases its
publication lease, invalidates partial/warm state, reports a failed round and
uses the existing emergency-stop/retry path. A map callback exception marks
the writer unhealthy; no partial evidence may be published as ready. The outer
`try { MultiThreadedExecutor::spin(); }` is not a callback exception boundary:
Foxy can terminate an internal joinable thread before that catch is reached.

Failure receipts carry `run_id`, `run_epoch_ns`, `component`, `exit_code`,
`cause` and monotonic time. Causes are `native_process_exit` or
`native_node_unresponsive`. An unexpected exit, including code0, is a fault;
intentional launch shutdown is ignored. The navigation launch registers all
seven critical child handlers before starting nodes. The graph supervisor also
observes its directly owned subprocesses. Keep bridge/driver alive during error
closure; do not raise `native_failure` before the recorder receives FAILED.

MissionBridge checks receipts with a20ms steady-clock timer. During a running
Action, lifecycle responses from controller/planner/recoveries/BT are required
within the configured1s steady timeout. Stop/cancel the active Action, commit
one terminal failure even if session cleanup fails, and reject new goals on
the failed graph. Late acceptance must cancel its handle rather than revive a
terminal job. Old epochs are ignored. The graph supervisor supplies a FAILED
finish even if MissionBridge itself exits; the driver uses first-terminal
atomic publication and checks matching native failure before claiming arrival.

## 4. Validation and error matrix

| Condition | Required result |
|---|---|
| Native rebound error/rebind flag | Skip remaining objective; solver reports cancellation |
| Body age exceeds0.1s at a stationary span | Finite soft fallback; original hard heading still unavailable |
| No finite geometric or measured heading | Ordinary solve failure, not field NaN or process abort |
| Timer/service/cleanup throws standard or unknown exception | Callback contained; failure reported; executor remains alive |
| Query fails after partial response | Unavailable, empty verdicts; subsequent query still works |
| Actual child SIGABRT while launch parent lives | Matching task fails and FAILED finish closes promptly |
| ROS clock pauses during child failure | Steady failure observer still closes the task |
| Session cleanup fails / acceptance arrives late | One terminal result; no job resurrection |
| Foreign epoch / deliberate shutdown | No failure applied to current task / no false fault |

## 5. Good, base and bad cases

Good: two deterministic58.4ms failure-latency injections advance the independent
ROS clock to1.1168s while body stamp remains1s; real zero-tail soft evaluation
stays finite, and native hard heading remains NaN.
Base: moving samples and existing analytic-gradient/corridor tests retain their
ordinary results; all original126324+3 hard verdicts/predicates are compared.
Bad: catch only around spin, skip the soft term globally, relax hard freshness,
or turn a zero interim gradient into successful optimization.

## 6. Required tests and evidence

Use actual BsplineOptimizer/helper/native heading, not a standalone math mock.
Include native STOP_FOR_ERROR, latched ERROR/REBOUND, invalid-input/heading
failure, stationary fallback and finite-difference neighbor-heading Jacobians.
Run the real two-thread Foxy executor with throwing FSM timer, service and
cleanup; check failure notifications, empty error reply, later successful reply
and continuing heartbeat. Use actual launch children with SIGABRT and a live
parent/keeper, a running ROS Action and paused ROS clock; require unique failed
task, matching finish, old-epoch rejection and no late-accept revival. Also test
real intentional launch shutdown and steady missing-node timeout.

Run the affected nine packages, installed Building admission, original replay
and a no-physics actual-graph startup/shutdown. Bind source/install hashes,
CMake package directories and effective header resolution to the result.
Foxy ClockType is imported from `rclpy.clock`. Its old message_filters accepts
the existing member-bind registration, not an arbitrary two-argument lambda.

## 7. Wrong versus correct

Wrong: monitor only `ros2 launch` Popen, terminate the bridge immediately and
let the physical recorder spin to its600s cap with no finish request.
Correct: observe actual child exit, report a run-bound task failure and close
the existing FAILED finish before normal teardown; preserve failure evidence.

## Subsequent physical evidence (v233 execution of frozen v232)

One separately authorized original-route run passes with FINISHED and measured
terminal PD, without SIGABRT or a critical-process fault. This runtime evidence
is separate from the offline real-child SIGABRT injection: the successful route
did not kill the actual controller or demonstrate physical feedback detouring.
Dr Sun adoptedv232/v233 as the latest single-route source/display baseline on
2026-10-17. Preserve the original30Hz/full-qualification failure flags.
