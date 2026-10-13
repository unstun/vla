# Foxy SCAN controller and observation window

## 1. Scope / trigger

Applies to the v86+ component workspace and v89/v92 full Nav2 integration in the
Newton experiment (`E2`).
Dr Sun selected Ubuntu 20.04/Foxy on the existing Jetson and real pluginization.
ARM64 container checks are not Jetson or complete navigation acceptance.

## 2. Signatures

- `scan_nav2_controller::Controller` implements the exact Foxy
  `nav2_core::Controller` lifecycle, `setPlan(Path)` and
  `computeVelocityCommands(PoseStamped, Twist)` API.
- `CommandOutput::bindOutputOwner/publishCommand/stop` extends the pinned
  0.4.7 ControllerServer at actual publication, cancellation and shutdown.
- `GoalChecker` implements the Foxy API and reads the same owner/stop state.
- `P2BExecutionSafety` carries checked time, original observation time, local map
  revision, full P2B/trajectory binding and the full-curve clear verdict.
- `P2BStopEvidence` carries source-stamped authoritative `P2BAdmission` evidence.
- `grid_map.mapping_admission`: `fifo` or `nav2_observation_window`;
  `map_update_frequency`, `observation_persistence`, `maximum_buffered_clouds`.

## 3. Contracts

The client publishes a full P2B route binding, waits for the exact
`/nav2_scan/binding_ready` echo, then sends `FollowPath`. Do not substitute a sleep
for delivery acknowledgment. The echo is not permission to move. Path headers,
geometry and original goal remain bound; another owner requires measured stop.

The controller owns a separate native SCAN executor and starts no legacy command
timer. Only Nav2's output boundary consumes the computed command ticket; preserve
all identity fields. A stock server lacking the output-owner handshake cannot
authorize this plugin. A modified, replayed or expired output ticket stops it.

Body/source ages remain 100/250 ms; the new native validation lease is 100 ms.
The lease is source-stamped and bound to the current trajectory. Sensor freshness
alone cannot grant map/trajectory safety. A controller hold acknowledgment alone
cannot release ownership or make a goal succeed. Stop proof must match the old
owner, be causal after its stop request, and include measured stillness.

Load native parameter sections explicitly with Foxy's YAML parser: qualified
`/quad_0/scan_planner_node` takes precedence, otherwise `/scan_planner_node`.
Preserve all values; match the parent's simulation-clock setting. Use an explicit
typed subscription callback in Foxy. Its GoogleTest needs `SetUpTestCase`.
Use `RewrittenYaml` for the launch profile; do not rely on a mock override winning
against a conflicting parameter file. Avoid an untyped empty YAML plugin array.

For mapping, retain source stamps and exact cloud/pose pairing. Zero persistence
keeps the newest observation; a positive window uses source age against latest
reception, as Foxy does. Apply each retained SCAN observation once, preserve
immutable map publication, and count expired/replaced/capacity drops. Keep the
3D collision/support entry; the frame-only Nav2 costmap is not its replacement.

## 4. Validation / error matrix

| Condition | Required result |
| --- | --- |
| Missing, stale or mismatched binding | No plan admission |
| New owner before old measured stop | Reject admission |
| Cancel, invalid preemption, failure or shutdown | Revoke and stop old identity |
| Wrong identity/trajectory or stale safety data | No valid nonzero command |
| Computed ticket modified, delayed or reused | Stop; no substituted output |
| Path endpoint reached but original XYZ/yaw unmet | No goal success |
| Controller hold without measured stillness | Keep stopping |
| Map worker stalled | Ingress remains separately scheduled; old map does not become fresh |
| Window expires an unprocessed observation | Count evidence loss; no FIFO-equivalence claim |
| Repeated/regressed source stamp or metadata overflow | Mapper fails closed |

## 5. Good / base / bad cases

Good: exact Foxy build, real pluginlib/server checks, and native recorded map
comparison with retained failure evidence. Base: component checks pass while
full navigation remains unaccepted. Bad: call latest-only evidence loss a speedup
with equivalent maps, or call synthetic stop evidence a robot stop test.

## 6. Required tests

Use the package's plugin tests and 300-sample original-tracker comparison,
`v86/server_probe.py`, `v86/launch_probe.py`, and v87's actual Nav2 buffer,
native safety producer, transient and recorded-worker probes. The actual source
must match the composed build source and frozen manifests. Rebuild dependent
native libraries when replacing `plan_env`; static linking prevents a library
path change alone from selecting the new map code.

## 7. Wrong versus correct

Wrong: a default plain Twist output, BT cancellation success, or bounded queue
is treated as preserved command identity, physical stop, or solved navigation.
Correct: retain tagged ownership and causal stop evidence, and score observed
map changes/stale intervals independently. v87 loses occupied evidence in its
injected-stall experiment and does not replace v48 without navigation acceptance.

## 8. Full navigation contracts (v89/v92)

- The public `/navigate_to_pose` action is the mission gateway. The actual Foxy
  BT Navigator lives in `/nav2_internal`; action-base remapping alone does not
  isolate all Foxy action services. Use fully qualified YAML keys for that node.
- `PCTPlanner` implements `nav2_core::GlobalPlanner`, calls the mission-bound
  `PlanRoute` service and uses the pinned native PCT worker. Keep map identity,
  body/ground height conversion, original XYZ/yaw and action UUID correlation.
  Discard late planner results after cancellation; never fabricate a path.
- The BT executes ComputePath, BindScanRoute and FollowPath. Recovery waits for
  measured stop before replanning. The outer action also waits for measured stop
  before reporting success or cancellation. A failed stop retains ownership.
- An identical already-admitted Path is idempotent. A changed Path still needs
  exact binding. Repeated cancellation re-emits the same controller hold ack to
  tolerate cross-topic delivery order; it does not manufacture measured proof.
- `TerrainLayer` reads a body-height projection of the same completed native
  3D snapshot. Preserve original observation stamps and reject stale or wrong
  height slices. Clearing a 2D costmap does not discard native 3D evidence.
- Legacy HTTP is an optional input adapter, not another navigation supervisor.
  Preserve caller request/goal IDs; infer missing heading once from the initial
  PCT route; explicit requested yaw wins. Reject wrong map/frame and duplicate IDs.
- `base_frame` and `odom_topic` are explicit launch inputs. The Newton bridge's
  measured `world -> base` TF relay preserves pose and source stamp exactly;
  do not launch it on a robot that already owns this TF.

## 9. Validation and deployment boundaries

Run native plugin tests, native PCT planning, standard Nav2 kinematic goal/cancel,
full mission protocol (label synthetic SCAN evidence), native sensor replay, and
original Newton physics as distinct gates. The 188-scan normal replay shows
5 Hz mapping scheduling ages up to 400 ms; 20 Hz ages up to 100 ms, fuses all
188 frames and preserves the final map. Input remains 10 Hz. The separate
650 ms fault case remains stale and must stop; never loosen the 250 ms gate.

Foxy's Python 3.8/ARM64 cannot import the old x86/Python 3.10 ZeroMQ bundle.
Use the system ARM64 binding. Original terrain helpers need NumPy 1.24.4 in
an isolated, hashed target; verify their three payloads against recorded bytes
and native PCT route parity after dependency changes. Keep ROS paths when
prepending this target. Applied-state evidence must be Linux-local atomic data;
Mac bind-mounted JSON is not a substitute for verified transport/copyback.

Export with `v92/assemble_workspace.py` into a new directory. Verify source and
license hashes; do not copy an old architecture's install tree to Jetson. Jetson
inventory, sensor/TF/topic adaptation, applied-command evidence and receive-only
validation remain required. No native action success implies robot validation.

## 10. Failure-path lessons from original Newton integration

Use explicit bounded `server_timeout` BT action ports for Foxy goal/cancel
acknowledgment (v96: 1000 ms). The default short acknowledgment deadline can
abort a real action already accepted by the controller. This is separate from
body/map/safety age limits, which must remain unchanged.

A bound controller must re-acknowledge repeated cancel even before its first
spline. The legacy tracker's generation high-water can suppress that second
reply. The plugin may acknowledge its own revoked-output latch for the exact
owner, but must not claim measured stillness. Keep the no-spline cancellation
unit and full gateway protocol regressions.

Convert builtin ROS timestamps through `rclcpp::Time(stamp).seconds()` when
comparing to `Clock::now().seconds()`. Independent `sec + 1e-9 * nanosec`
arithmetic falsely classified identical 19.940670013 s source/current times as
future in the actual run. Python raw-command age uses integer nanoseconds.
Keep exact-equality, one-nanosecond-future and original 100 ms age-limit tests.
Do not introduce an epsilon or increase a safety deadline to hide this error.

## 11. Recovery notification and ownership (v128-v131)

An asynchronous negative native safety proof must remain stored after revoking
the output owner, including a proof delivered before candidate activation.
The next controller tick must expose that failure to Nav2; a normal zero command
hides it until the progress timeout. Ordinary cancellation/goal hold retains
zero-command semantics. Positive late proof never clears a revoked owner.

Recovery waiting budgets and physical-stop criteria are separate. The recorded
body may need more than4s to establish the unchanged1s continuous stillness
window. v129 allows10s at the gateway and11s at the BT transport. Missing proof,
stale body, excessive velocity/yaw, cancellation or wrong identity still prevents
owner release. Preserve the captured-stream gateway and actual BT transport tests.

New-reference admission precedes local PVA initialization: search from the latest
due measured body, not a stale/uninitialized local trajectory start_pt_. Keep
local-replan callers' prepared start and do not retime future odometry. v130's
actual native route-callback/AStar witness covers stale/nonfinite prior state and
exact due/future ordering; unknown map remains rejected in every case.

The mission retry allowance is an explicit finite policy. v131 uses6outer retries
(maximum7navigation attempts), each separated by proved stop. Never reset the
count on local failure or use retry count to waive collision/freshness checks.
Actual installed RecoveryNode/WaitForScanStop tests cover eventual success,
exhaustion and unavailable proof. The stock Foxy regular tree's6outer retries
and round-robin tree's2outer/4inner retries are distinct examples.

These contracts have direct component evidence in
`audits/2026-10-10_nav2_recovery/REPORT.md`; whole-mission acceptance remains a
separate repeated physical comparison. A successful pilot is not acceptance.
The shared v131 recorder observes existing gateway proof publications read-only;
record original identity/source stamps and separate DDS receipt order from source
time. Recorded proofs do not reconstruct exact gateway applied-sample polling.

### Post-search input refresh (v132/v133)

A goal-neighborhood search may outlive the original body/map validity window.
Before testing fallback reference points, call the existing input drain/adoption
method again. Do not renew stamps, widen deadlines, or treat a completed search
as fresh evidence. The controlled native regression advances the clock120ms
inside a stubbed failed search: newly due queued body data must become visible;
missing data and1ns-future data must still reject. Full physical acceptance is
separate. If the newest completed map remains stale, keep the rejection.

Do not conflate route receipt, route admission, first safe spline, measured stop,
or upright posture. Recorded v133stop failure has no full1s qualifying window;
zero velocity commands alone cannot release ownership. Preserve the failed
physical evidence rather than tuning the stop criteria to force completion.

### Mission inbox at native work boundaries (v136)

Expensive work shares a serialized callback group with route/cancel delivery.
Recorded v135generation4 reaches the recorder at37.636s, times out at39.655s,
and is only accepted by the FSM at40.744s. Service the real pending cancellation
and route subscriptions at FSM work boundaries, bounded by their DDS depths10/1.
Preserve original identity and cancellation high-water checks. The controller's
2s startup timeout and finite retry policy are not substitutes for delivery.

During EMERGENCY_STOP, retain a replacement until the old exit finishes. An
ordinary route callback can also arrive in that state; it must defer rather
than accept a target that the next old-exit tick clears. Cancellation wins over
the queued route and never manufactures measured stillness. All mutation stays
inside the native work group. Transport errors fail the native worker closed.

The actual DDS/FSM regression uses recorded map geometry and deliberately
selected timer ticks: old inbox unprocessed; old replacement accepted then
erased; new inbox processed, replacement preserved, canceled route rejected.
It is not a reconstruction of the full historical executor schedule. Repeated
physical runs and stop-proof audits remain separate acceptance gates.

### Pending reference admission for transient input gaps (v137)

`GridMap::planningInputsReady()` reuses the original mapper-health, completed
cloud readiness, support readiness and configured observation-age checks.
The route callback also requires the original finite measured-heading query.
Check before admission and after its computation. Missing or expired input
keeps the same route pending; failed computation restores the previous owner,
target, reference and warm-start binding. Fresh geometric failure still rejects.

The existing2s controller startup deadline bounds the pending state. Cancellation
high-water checks run first. Never renew source timestamps, admit future input,
raise the250/100ms age limits, or emit commands merely because a route is pending.
The actual native regression withholds recorded scans, then delivers their exact
original timestamps while preserving the newer torso: old route is lost, new
pending route resumes. Fresh impossible-height geometry rejects and cancellation
still removes a pending route. Original executor timing is not reconstructed.

`V132_REFERENCE_ADMISSION` logs the inner helper result. With the final readiness
gate it is not sufficient evidence of final route acceptance. Use recorded FSM
`P2BAdmission` messages and distinguish pending, accepted and controller-spline
acceptance when analyzing v137+ runs.


## 12. Controller input order and goal hold capture (v159/v160)

### Scope and trigger

TF may deliver a pose up to one source tick ahead of the controller ROS clock.
Separately, canceling the planner at the outer goal-yaw tolerance can leave the
body outside that tolerance by the time the causal stop dwell completes.

### Signatures

Keep `Controller::computeVelocityCommands(PoseStamped, Twist)`,
`Controller::onStopEvidence(P2BStopEvidence)` and `GoalChecker::isGoalReached`
unchanged. The controller uses `scan_input_time::BodyTimeBuffer` for future
deliveries and keeps the original latest-due odometry.

### Contracts

Queue future inputs with their original integer timestamps. If a fresh previous
due sample exists, use its pose AND twist; otherwise reject. Ordinary valid
historical TF queries retain their original path. Do not retime/interpolate or
increase100ms body freshness. Invalid incoming frame/value is rejected before
cache selection. Cleanup clears the queue and cached input.

Goal hold irreversibly revokes the owner. Use half the configured yaw tolerance
for tracker deadband and hold entry; keep the full configured tolerance in the
final GoalChecker, with originalXYZchecks and causal measured-stop evidence.
Never convert a goal-neighborhood stop into arrival without final qualification.

### Validation and error matrix

| Input | Required behavior |
|---|---|
| Future pose, fresh due cache | Use unchanged due source; defer future |
| Future pose, absent or expired cache | Reject; no renewed lease |
| Bad incoming frame/value, valid cache | Reject before fallback |
| Goal residual yaw0.21rad with tolerance0.25 | Continue checked yaw correction |
| Goal residual yaw0.10rad | Revoke and wait for original physical proof |
| Final residual yaw0.27rad | GoalChecker rejects |

### Good, base and bad cases

Base: v158fails recorded83.130943298s pose versus83.120948792s clock.
Good: v159selects a due sample and still rejects100ms+1ns expiry.
Bad: shifting the source stamp to now to make the input appear fresh.
Base: v159reaches goal vicinity then receives288stop proofs but yaw drifts
outside0.25rad; action remainsFAILED. Good: v160aims inside the band first.

### Tests required

Keep actual plugin regressions for source ordering, historical-query lease,
wrong frame, missing cache and exact expiry boundaries. Keep goal-capture
red/green regression and original height/yaw/physical-proof tests. Test actual
loaded libraries and source/install receipts, then original-start physics.
Localv160trial02passes route/5replacementproofs/finalhold; trial01fails.
This1/2Mac cohort does not establish Linux or general reliability.

### Wrong versus correct

Wrong: stop proofs alone imply arrival, or an inner capture band changes the
final goal tolerance. Correct: preserve proof identity AND check the requested
finalXYZ/yaw, with the stricter capture band only controlling hold entry.
