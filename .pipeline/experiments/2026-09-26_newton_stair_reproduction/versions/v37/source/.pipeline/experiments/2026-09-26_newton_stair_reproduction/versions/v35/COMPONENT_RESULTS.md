# v35 scheduling component results

Status: implemented and component-tested; **unfrozen, navigation unvalidated**.
Parent: v34. Native candidate: `runtime/scan66_periodic_replan_v35`.

Dr Sun requested frequency-triggered replanning and then directed compilation
to gpu5070ti. `fsm.replan_frequency: 2.0` is enabled in this version's Building
and flat configurations. It replaces the nominal displacement trigger and
limits nominal initial/retry attempts to one per 0.5 s of ROS time. Safety
replanning remains immediate. Overruns coalesce; this is a nominal rate, not a
hard real-time guarantee or a demonstrated cure for every pause.

## Direct evidence

- **Source delta:** two FSM files change; the other 96 native source files are
  byte-identical to v34. The saved parent bytes plus `changes.patch` reproduce
  both native files and both configuration files exactly. PVA start-state
  handling, complete planner/publication, collision safety, emergency stop and
  exhausted-retry stop functions remain byte-identical. `source_checks.json`.
- **Build on gpu5070ti:** the existing pinned image, native amd64 execution
  through the reviewed docker/podman shim, network disabled. Eight packages
  build; exit 0, 18.76 s wall time. `remote5070ti/build_result.json` and
  `remote5070ti/build.log`. There are no compiler warning/error lines in this
  incremental build log.
- **Actual compiled FSM, attempt 04:** no simulated physics or robot control.
  The short synthetic spline has a zero-velocity tail and lasts longer than
  the trigger period. v35 enters `REPLAN_TRAJ` at 0.5 s, before expiry and
  below 1 m displacement. The separately compiled v34 parent remains in
  `EXEC_TRAJ`, reproducing the missing early trigger. Both use the same fixture.
- **Additional assertions:** distance cannot trigger early in periodic mode;
  paused time does not trigger; failed nominal initial/retry attempts consume
  their period and keep the accepted curve; missed periods do not burst;
  a clock rewind below the last attempt re-anchors; 4 Hz is configurable;
  execution freeze suppresses the periodic `EXEC_TRAJ` transition (an already
  queued replan is not cancelled); final-goal proximity/completion, local-window expiration,
  legacy distance mode, and immediate invalid-curve-time safety remain.
  There are 28 distinct named checks in each valid-configuration log, including
  fixture/clock operations, and five separate invalid-frequency checks. The
  omitted-parameter run verifies the loaded zero default; individual scheduling
  cases set test-only FSM fields explicitly. `contract/contract_results.json`.
- **Source gate:** 118 synchronized files match local SHA-256 before the
  successful attempt. Candidate and parent native sources remain unchanged
  after compilation/tests. `remote_sync/expected_sha256.json`.
- **Return gate:** 658 files, 39,070,725 bytes, all returned SHA-256s match.
  The complete installed file set, 516 files, also matches. The returned
  gpu5070ti installation and its identity/logs replace the local candidate's
  build output; the earlier Mac build evidence is preserved separately in
  `local_build_before_remote_return/` and the existing repairs build-evidence
  directory. No v34 file was replaced. `remote_sync/return_verification.json`.
- **Frozen-parent integrity:** all 3,548 v34 current and source-snapshot files
  still match their frozen hashes.

## Failed test setup attempts retained

These changed test infrastructure only; v35 production sources did not change.

1. Local green 01: standalone CMake unnecessarily called `ament_package()`
   without a package manifest. Configuration failed before compilation/testing.
2. Local green 02: probe compiled, but ROS domain 233 exceeded the middleware's
   port range. No scheduling assertions ran. The harness now uses domain 232.
3. gpu5070ti green 03: the core valid/omitted-parameter tests and four invalid
   values passed. `std::stod("1e-310")` threw on underflow before reaching the
   FSM's invalid-period check. The test now constructs the subnormal with
   `strtod`; all five invalid cases pass in attempt 04. The first remote wrapper
   also failed while collecting a missing contract summary after that failure;
   its result/logs are retained. The wrapper now records failure without assuming
   the summary exists. `contract/attempt_green03/` and `remote5070ti/`.

Attempt 04 repeats the corrected contract and separately compiles/runs the
v34 parent. `remote5070ti_retry04/result.json` records a pass, without promoting
it to navigation acceptance.

## Remaining boundary

No new physics run or video was produced. Fixed-rate triggering does not
establish seamless PVA switching under solve/delivery latency, static-route
completion, east-end corner feasibility, or dynamic-obstacle avoidance.
Independent pre-trial review and version freeze have not been performed.
The last accepted navigation condition remains v3's empty 12 m floor; v34
remains the most recent frozen full-route trial version. No commit or push.
