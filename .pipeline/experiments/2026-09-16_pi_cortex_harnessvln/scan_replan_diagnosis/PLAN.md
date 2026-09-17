# SCAN Cancel/Resubmit Diagnosis

Date: 2026-09-16. Stage: experiment + analysis.

Dr Sun requested diagnosis after three display-probe conditions failed at
goal-A resubmission. The earlier actual4 pilot succeeded. Existing raw logs
reproduce the observed chain: first route executes, explicit cancellation
reaches WAIT_TARGET, the second route enters GEN_NEW_TRAJ, refined candidates
fail the acceleration hard gate, no second spline reaches the controller,
and the backend completes a fault stop after its initial heartbeat deadline.

## Change boundary

Keep frozen scan_03, the accepted run packages, sibling repositories, controller
limits and heartbeat deadlines unchanged. Build a small executable that calls
the real C++ SCAN planner manager in isolation. An empty map is a declared
minimization, not simulator or collision validation. Fixtures derived from PCT
requests approximate the native start pose; native console output only retained
three significant digits. Do not label those fixtures as exact argument capture.

All new source, diagnostic instrumentation, candidate experiments and results
live here. The root agent owns this plan, fixture extraction, execution and
analysis; the runner subagent owns native_repro/. Other subagents perform
read-only optimizer and cancellation investigations. No automatic commits,
long experiments, model calls or physical actuation are included.

## Ranked predictions before intervention

1. Endpoint derivative construction: the polynomial sampling loop omits its
   true final time and records acceleration at the last sampled time as the
   endpoint constraint. If this constraint exceeds the final hard gate, a
   fresh manager should also fail at the captured stop pose; fixing only the
   terminal derivative in a diagnostic copy should remove that failure.
2. Time allocation/refinement: if the input derivatives are legal but the
   refinement reintroduces a violation, stage-level trajectory diagnostics
   should show it first after reparameterization or optimization. Inspect
   both control-point checks and sampled vector-norm checks.
3. Cancellation state: if residual previous-trajectory state is necessary,
   the same pose/goal must pass in a fresh manager and fail after the stop
   sequence. If fresh planning fails, cancellation is not necessary to
   trigger this dynamic-feasibility failure.

## Feedback loop and evidence

- Build against the existing pinned Foxy image and scan_03 libraries, with no
  controller, sensor publisher, Isaac process or GPU workload.
- Start from recorded actual4 and failed-run start/goal pairs. Freeze seed and
  flags; repeat identical inputs to measure deterministic reproducibility.
- Report success, duration, acceleration/velocity norms, polynomial sampling
  time, terminal derivatives and stage identity. Preserve every raw log.
- Change one aspect per diagnostic condition. Do not loosen thresholds or
  reinterpret timeout as a successful plan.
- Each case is bounded to 20 wall seconds; the native build to 180 seconds.
- Verify source hashes before execution and returned artifact hashes locally.
- A planner-only candidate pass establishes the mechanism at that boundary;
  continuous cancellation/navigation still requires a separate Isaac test.

No production fix or complete-navigation claim follows from source inspection
alone. End with a source-backed diagnosis and the observed scope of any
candidate repair.
