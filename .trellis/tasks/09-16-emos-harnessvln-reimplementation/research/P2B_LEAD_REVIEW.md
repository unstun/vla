# P2B Lead Review (In Progress)

This is actual PCT/SCAN/Isaac integration work, following user authorization to
implement the next step. The executors use gpt-5.5 / medium. No physical
actuation is authorized. The first pilot uses the geometry-audited flat
platform, freshly computed native PCT routes, two arrivals and one interrupted
attempt in one persistent episode; see p2b_execution/inputs/pilot.json.

## Initial runner review: corrections required

The materialized source compiled and its three local tests passed, but source
review found: finish-request wall freshness expires before one simulation
second of stillness at low real-time factor; external success is not recognized
by the native exit-code function; malformed finish JSON can throw instead of
being rejected; non-finite bounds bypass validation; and external finishing
can precede an applicable tilt check. These were returned to the runner worker.
Default-off flags and substring assertions do not prove legacy parity or
correct continuous execution.

## Initial backend review: incomplete implementation

The first return contains contract modules and fifteen passing local tests,
but no actual rclpy runtime binding; run_adapter.py only renders a contract,
ScanPort methods remain unimplemented, and the SCAN patches are sketches.
This does not satisfy P2B and was returned for executable implementation.

Source review also found the PCT worker initially returns the wrapper's
display-offset Z as body-reference Z and never sets the native reference
height. The corrected implementation must reproduce the inspected baseline
conversion through native optimizer heights. A shared mutable PCT planner
must be serialized across server threads.

## Lead-owned qualification

- Scene and map match the declared native baseline hashes and now have local
  VLA copies with tracked input_manifest.json and regeneration script.
- All 217 pinned V12 runtime files match the existing server execution copy.
  An earlier SSH banner timeout is preserved; the subsequent qualified check
  passed. The 26 MB checkpoint matches the pinned hash separately.
- The native PCT wrapper and three Python extension binaries match the prior
  qualified baseline. Ten non-system ELF dependencies and pinned Python source
  are captured locally under a path-specific ignore with exact hashes.
- First isolated PCT computation failed because the lead launcher overwrote
  ROS PYTHONPATH. The launcher now prepends its source while retaining the
  sourced Humble paths; original failure output is retained.

No new continuous Isaac episode has passed yet. Keep import, contract tests,
native compute, ROS runtime and articulated-motion evidence separate.

## Actual native C++ qualification

Captured overlay scan_01 built successfully in the pinned real Foxy image;
every source hash matched before and after compilation. The independent live
controller probe used actual generated ROS messages and the compiled native
controller with synthetic odometry, no robot. Two of six checks passed:
valid splines produce nonzero control and a newer generation can execute.
Four failed: distinct controller hold receipt, cancelled-spline suppression,
protection against old cancel/spline messages, and cancellation before spline
arrival. Raw commands, acknowledgements, logs and returned-file hashes are in
p2b_execution/builds/scan_01/controller_probe_01/. This candidate is rejected
for motion use; the backend executor is correcting these transitions.

The actual rclpy/HTTP binding has been assigned to a third independent
gpt-5.5/medium worker in backend_ros/** while the first worker completes native
patches and shared contracts. The runner worker may execute only its bounded
stand qualification under the explicit limits in P2B_DISPATCH.json. Lead owns
the full two-goal pilot and acceptance.

## scan_02 and real standing qualification

scan_02 compiled with source equality and passed five of the six real C++
controller checks. The stronger stale-spline case exposed a remaining defect:
the callback assigns trajectory geometry before rejecting its old identity,
so the echoed new identity can conceal changed motion direction. The lead
changed only the probe's stale trajectory geometry, not its criterion, and
returned the demonstrated defect for repair. No motion pilot uses this build.

The runner worker then executed stand_20260916T152235Z_p2b_fix1 successfully.
The lead independently verified all 24 returned artifact hashes, the actual
patched source identity, raw metrics, and video decoding/frame content:

- 153 consecutive control records, 3.06 simulation seconds, zero admitted
  command throughout; no reset/pose-write attempt and zero non-foot force.
- External request accepted and a 1.02-sim-second post-request stillness window;
  maximum speed 0.01572 m/s and absolute yaw rate 0.09714 rad/s in that window.
- Command observation error is zero and actual runtime imports resolve to the
  pinned V12 source. The H.264 video has 39 frames, 3.12 seconds at 12.5 FPS;
  playback duration is not substituted for the simulation clock.

Lead metrics/video review is in p2b_execution/qualification/stand_lead_review/.
Accepted claim: actual articulated V12 standing, Foxy bridge transport and
external finish path. This is not PCT/SCAN navigation or a two-goal result.

## scan_03 and native PCT IPC acceptance

The lead captured scan_03 from materializer SHA-256
69954316fefce140574b26b54e2b76ad4a2148d01e7ca76c9effa8e10cbf0ce5.
The pinned Foxy build and source-equality gates passed. The same strengthened
real C++ controller probe now passes all six checks, including old-geometry
rejection and cancel-before-spline tombstones. Evidence is in
p2b_execution/builds/scan_03/controller_probe_03/result/. This qualifies the
controller boundary for a bounded simulator pilot, not continuous navigation.

The separate native Humble PCT process and actual PctIpcClient RPC produced
two ten-point routes with endpoint XY errors of 0.041495 m and 0.045661 m.
Unavailable, timeout and unsupported optimize=false cases fail explicitly.
Returned hashes match in backend_adapter/qualification/pct_ipc_20260916T153430Z/.
The lead reran all 20 current adapter tests after persistent stop/poll_stop
was implemented. The earlier Foxy test result covered 17 tests; do not label
that result as validation of the later three tests.

## Full pilot package review in progress

The first prepare-only pilot candidate is rejected for execution: its driver
uses applied_cmd/speed_mps instead of the verified applied_command and
horizontal_speed_mps schema; it accepts generic HTTP success as readiness;
it silently changes native velocity caps; and generated background shell
commands contain invalid '& &&' syntax. The controller odometry remap is also
missing. These demonstrated source defects were returned to the runner worker
before any full-motion Isaac start. The candidate is retained as prepared
evidence, not a runtime result.

The ROS worker is completing real Foxy startup/HTTP qualification and persistent
stop-flow integration. Arrival must be checked against the original requested
target after measured stillness, and terminal success must be accepted by the
P2A core before appearing in the HTTP ledger. No complete two-goal result has
been obtained at this review point.

## ROS binding gate and first full-pilot authorization

Current backend_ros node SHA-256 75bac0bae2b40018f59d98edd7984ec3f2534283740055a453f48278aa7254a7
and runtime SHA-256 8b5a02000d922b201030dab9d92435297f42300b73eb7cc63a6394d2bef20d67
match the actual Foxy CPU qualification source. Five startup/HTTP/raw-message
checks passed; 30 source files matched the remote copy. The lead reran all
21 local tests with the required backend_ros/backend_adapter PYTHONPATH.
An initial direct unittest invocation omitted that subprocess environment
and failed the CLI import test; this was a test invocation issue, not a
successful runtime claim. The corrected invocation passed all 21 tests.

The lead freshly verified all 67 scan_03 source files and captured 380
installed-file hashes in builds/scan_03/install_identity.json. Full-pilot
authorization is one continuous episode, 45 simulation seconds / 1200 wall
seconds, the native speed_1p0 limits, no physical actuation or model calls.
The runner worker must first pass exact-container CPU startup/import checks,
freeze a new package, verify source equality and check GPU/port availability.
Failed attempts must return evidence; further physics retries require lead
inspection. This is internal execution gating under Dr Sun's existing
authorization, not a new user approval requirement.

## First full-pilot startup failure

The exact-container CPU preflight for
two_goal_20260916T155842Z_p2b_actual2 passed. The lead inspected the import,
planner INIT, controller-ready and running backend logs, plus all nine returned
hashes. Its local 390-file package manifest also matched.

The subsequent Isaac start failed before producing a physics state or connecting
the bridge: the generated route metadata set statistics.arc_length_xy_m to
null, but the preserved native runner converts that field with float(). The
runtime_error.json contains the direct TypeError and line 760 traceback. This
is a rejected startup attempt, not a completed navigation episode. GPU returned
to idle and the runner process exited.

The wrapper nevertheless continued waiting for a first snapshot. At 16:05:57
UTC the lead sent SIGINT only to that run's exact remote_worker.py process
(PID 171404) so its finally cleanup and artifact return could run. The executor
must derive the metadata length from its declared points, detect early runner
exit, preserve the failed candidate, and freeze a new one. One bounded retry is
authorized under the same scene, goals, policy, control caps and thresholds.

## First continuous simulator attempt: missing odometry

After the metadata correction, actual3_retry1 executed 45 simulation seconds
but did not submit any navigation goal. The lead captured live /state and the
final simulator snapshot: service event_seq=0, jobs empty, no plan history,
scan_port last_body_pose_age_s=null and gate last_measurement=null. The body
remained near its spawn with zero applied command. This cannot satisfy P2B.

Source inspection identifies a concrete transport contract mismatch: the frozen
Foxy bridge publishes /quad_0/body_pose with qos_profile_sensor_data
(BEST_EFFORT), whereas the new RosScanPort subscribes using integer depth 50
(the default RELIABLE policy). The native C++ planner/controller already use
SensorDataQoS. The ROS executor must match the existing publisher and run a real
Foxy BEST_EFFORT odometry publisher/subscriber smoke. The earlier missing-input
startup tests did not cover this required positive path. Source freeze and that
new check precede one further bounded retry; no control or acceptance threshold
change is authorized by this diagnosis.

## Cross-container transport diagnosis and actual4

The corrected BEST_EFFORT subscription passed the actual single-container
Foxy test. However, the actual3 C++ planner also lacked odometry despite its
already-correct SensorDataQoS. A second, two-container CPU test isolated the
remaining deployment issue. In cross_container_20260916T161849Z, default IPC
isolation delivered none of 198 published samples; adding --ipc=host delivered
fresh [0.42, -0.24, 0.35] odometry with age 0.042 s. Both sides had effective
ROS_DOMAIN_ID=94 and ROS_LOCALHOST_ONLY=1 after sourcing; the source gate matched
all 32 files. The lead inspected these positive and negative raw results.

The lead added --ipc=host only to the bridge and backend ROS containers and
recorded this configuration in env_identity.json. The root reran 23 runner
tests and verified the GPU had no compute jobs, no active containers and all
four execution ports free. The next bounded attempt is root-executed:
two_goal_20260916T162236Z_p2b_actual4. Its physical/acceptance settings remain
unchanged. The runner wrapper now detects process exit and records bounded
cleanup failures without losing result/hash artifacts.

## Final bounded acceptance: actual4 passed

The root executed actual4, verified its 500-file local package before execution
and checked all 34 normally returned raw-artifact hashes. The independent
review_two_goal.py passes all 41 checks. It directly correlates PCT request
starts, HTTP terminal timestamps and original requested targets with the raw
826 consecutive physics control records. It does not accept service prose or
an empty owner as sufficient success.

The continuous episode took 16.52 simulation seconds / 22.26 physics-loop wall
seconds and travelled 3.919 m. Cancellation was triggered after 0.419 m;
the three stop events each have a 1.02-simulation-second qualifying raw window.
Goal A and B XY errors at confirmed stops are 0.179 m and 0.154 m, below the
frozen 0.25 m limit. Maximum non-foot force is zero; reset, pose-write and
pose-injection counters are zero; applied-command observation error is zero.
The post-cancel PCT start agrees with the independent physics pose within
0.12 mm. No route was replayed from the frozen reference artifact.

The original H.264 video is 1920x1080, 207 frames at 12.5 FPS. The root inspected
frames at 6 and 14 seconds: the articulated robot and Building geometry are
visible, with the original low-contrast material rendering. There are no added
goal markers. Playback length is 16.56 seconds, distinct from simulation time.

Cleanup used the documented SIGKILL fallback for processes that ignored SIGTERM;
all removals succeeded and the final four port checks are free. This happens
after successful physical completion. Final evidence lives in
isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4/ and
p2b_execution/qualification/actual4_lead_review/; P2B_RESULT.md is the human
readout. Rejected attempts and manual recovery limitations remain recorded.

Accepted claim: integrated and validated native spatial navigation on this
single known-map/truth-pose flat-platform pilot. Pi-to-real-service execution,
actual Cortex runtime, language parsing, RGB-D grounding, graph memory, real
SLAM, integrated map/reconnect fault cases and physical deployment remain open.
The overall Trellis task stays in_progress.
