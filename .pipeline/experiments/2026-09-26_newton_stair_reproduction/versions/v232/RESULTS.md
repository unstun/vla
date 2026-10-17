# v232: native exception containment and failed-task closure

**Offline gate passed. No physics was run.** Parent navigation is frozen v230
(`e9f8bec0`); failure reference is v231 near46.686s. All four requested repairs
are in this overlay. v219/v220 remains the accepted physical source/display
pair. This version is not a claim that another full route has passed.

## Changes

1. `combineCostRebound` returns immediately when distance/rebound evaluation
   selects STOP_FOR_ERROR or STOP_FOR_REBOUND. No further feasibility or
   environmental objective is evaluated in that step. Cost callbacks latch the
   stop, and the real solver converts any convergence/ALREADY_MINIMIZED result
   to cancellation when the flag is set. Finite zero interim cost/gradient
   cannot turn a failed/rebind step into success. Refinement also cancels.
2. Environmental soft scoring falls back from unavailable native yaw to local
   lookahead/velocity, the nearest valid control-point segment, then finite
   measured yaw. Jacobians follow that selected source. Input/sample/heading/
   score/gradient nonfinite values fail normally before an invalid field query.
   Hard `collisionTrajectoryYaw`/`motionHeading`, its0.1s freshness rule, normal
   native admission and0.35m support/collision guards are unchanged.
3. One shared `callbackBoundary` contains standard/unknown exceptions, including
   exceptions during reporting/cleanup. It protects complete optimizer entries
   (setup, solver and result copy), L-BFGS callbacks, FSM timers/inputs, map
   callbacks and the NativeWorker query service. FSM failures release the
   publication lease, invalidate partial/warm work, report failed planning and
   use existing stop/retry behavior. Map-input exceptions mark the writer
   unhealthy; query exceptions return unavailable with no partial verdicts.
   These catches execute inside callbacks, before Foxy's internal thread boundary.
4. Navigation launch watches actual critical ROS child exits using
   `OnProcessExit`; the graph supervisor also watches its direct subprocesses.
   Run/epoch-bound atomic failure receipts reach MissionBridge's20ms steady
   timer, which fails/cancels the active task and rejects new work on the failed
   graph. Controller/planner/recoveries/BT lifecycle responses have a1s steady
   liveness timeout during a running Action. Session cleanup failure and late
   Action acceptance cannot erase/revive the terminal result. The graph/driver
   close the existing matching FAILED finish before normal teardown, including
   when MissionBridge itself exits. The driver retains the first terminal
   finish and checks native failure before arrival. No new recovery connector
   or PCT/SCAN constraint protocol was introduced.

## Reproduction and final tests

The initial parent-production experiment fails both new regression cases:
[red log](results/red01/regression.log). The source revisions are retained.
The first injects two58.4ms failed-search latency slots while an independent
thread advances actual ROS time from1.0s to1.1168s, with body stamp held at1.0s,
a stationary final cubic span and shared environment scoring enabled. It then
calls real native heading and environment scoring. This is deterministic search
latency injection, not a claim to have rerun the exact physical A* trace.
The second invokes real native collision/rebound evaluation to set
STOP_FOR_ERROR, then demonstrates the original erroneous continuation/throw.

Final **attempt08** builds all nine affected packages and passes:

```text
Summary: 9 packages finished [20.6s]
Summary: 186 tests, 0 errors, 0 failures, 0 skipped
```

There are **165 distinct cases**, plus21 colcon/CTest result wrappers. The
affected gate includes the inherited controller, tracking/parity, route,
shared-support/feedback, terminal/recovery, terrain/profile, event-planning,
mission, executor-shutdown and uniform-spline cases.
See [test summary](results/build/attempt08/test-result.log) and
[source/install/compile receipt](results/offline_gate.json).

New assertions cover:

- Delayed zero-tail soft scoring remains finite; the same hard heading remains
  NaN when stale. Missing finite geometry/heading fails the real optimizer.
- Actual native STOP_FOR_ERROR short-circuits; ERROR and REBOUND stay latched;
  zero objective/gradient after an exception does not imply solver success.
- Nearest-segment fallback Jacobians match finite differences; existing active
  shared-objective/L-BFGS displacement and GPMP factor derivatives still pass.
- A real two-thread Foxy executor runs throwing FSM timers (standard and unknown
  exceptions), a service that throws after partial response, subsequent successful
  service request, continuing heartbeat and a throwing failure-cleanup handler.
- A real sacrificial launch child receives SIGABRT(-6), while another child keeps
  its launch parent alive. A real loopback ROS Action is already `running`, and
  MissionBridge's ROS clock is paused at zero. The task becomes failed once,
  clears its owner, and the graph's actual finish helper writes the matching
  FAILED run/epoch/request. The test uses the real exit handler/helper; it does
  not kill a physical controller or run Newton.
- Old epoch, duplicate failure, late accepted Action, failed session cleanup,
  unresponsive-node steady timeout and actual intentional launch shutdown controls.

## Original hard rules and installed Building reference

The final replay checks **126324 original queries plus3 exact planning queries**.
Binary changes are0; rejected count stays50617/126324, and each independent
cylinder/history/other/target/torso/unknown predicate stays unchanged. The three
critical queries still reject as EdgeClearance; the physical floor remains
1.5580306959m with square-gap0.2828427125m below the unchanged0.35m guard.
See [replay comparison](results/replay_comparison_final.json).

The actual installed PCT plugin retains first-round Building admission:
**0/3821 rejected**,3413 poses, exact goal. Both legacy and shared admitted CSVs
are byte-identical to v230. Shared call is0.397276s in this one-shot probe; no
performance improvement is attributed to this repair. The atlas score reports
edge minimum0.141488m and solid minimum0.065481m; these are soft-field values,
not a new independent raw-PCD or physical clearance validation. See
[installed call](results/final_probe08/admission_probe03.log) and
[route parity](results/admission_route_parity_final.json).

The actual v232 ROS graph, with all14 required package prefixes, runs for12s
without physics and stops cleanly without a false failure receipt. The original
v231 package-prefix/interface/ldd checker is reused against the v232 install.
See [graph gate](results/graph_gate_final.json).

## Source binding and retained attempts

The final gate verifies317 composed source files,19 owned overlay source files
and607 installed files. Sixty effective header resolutions and modified CMake
package directories point to the current workspace; ldd resolves the native
controller/core/plugin libraries to the expected install. Source inventories
and SHA receipts are returned locally. RL/policy, motor settings, geometry,
normal retry/freshness/stop rules and hard thresholds were not changed.

Preserved attempts:

- red01: both parent-code exceptions reproduced.
- attempt01: Foxy message_filters lambda binding fails compilation; repaired
  using its existing member-bind registration and a guarded member callback.
- attempt02: the red-stage CMake cache selected parent headers. The entire old
  build/install cache is retained remotely; attempt03 starts from clean directories.
- attempt03: a test fixture used shared_ptr for the manager's unique_ptr API.
- attempt04: C++ regressions pass; Python uses the wrong newer ClockType import
  and launch mocks omit the new handlers. Fixed against the installed Foxy API.
- attempt05/06:185-record gates pass;06 strengthens running-Action/paused-clock.
- attempt07:186-record gate adds the fallback gradient check.
- attempt08:186-record gate repeats after complete optimizer-entry containment.
- First parallel probes use invalid domains233–235 and fail before useful ROS
  execution. Sources/logs are retained; final probes use200–202 and new output
  locations, without overwriting earlier successful checks.

Heavy builds, fixtures, replay CSVs and caches remain on gpu5070ti under
`/data/sun/vla_mppi_20261009/callback_failure_v232`. Only source, logs/XML,
compact reports and failure source revisions return locally; there are no
CMakeFiles or CMakeCache files in the local result package.

## Reproduction commands and claim boundary

`prepare_workspace.py` verifies the frozen v230 execution copy and overlays
these local sources. `build.sh attemptNN` builds/tests in the pinned
`sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4`
Foxy image. `verify_offline.py` verifies the final source/install gate;
`replay/run.sh` and `replay/compare.py` check original native inputs;
`tools/run.sh` checks installed references; `tools/graph_probe.py` checks the
actual graph without physics. Diagnostic commands and logs are version-bound.
Use new attempt/output IDs; do not overwrite the frozen evidence.

No new physical route, RL training, robot actuation, push or Git commit was
performed in this repair request. A subsequent physical execution must bind
both the v232 native install and its graph/long-route-driver sources, rather
than launching the frozen v231 runner unchanged.
