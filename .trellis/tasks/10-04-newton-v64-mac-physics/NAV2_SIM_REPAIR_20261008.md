# Original Newton simulation repair

Dr Sun rejected component-only delivery because the actual simulation does not
walk. Continue the existing in-progress task inline. Acceptance is actual original
Building corner navigation to its requested goal, measured stop, recorded-state
video and source/runtime provenance. Jetson access is not a prerequisite for this
Mac simulation. Do not claim success from a stopped recording or fixture tests.

First reproduce the v98 initial UnknownObstacle rejection using the exact
captured cloud/body/support/clock inputs. Ranked hypotheses: (1) native manual
input draining reads body time ahead of its processed ROS clock, invalidating
measured-body free-space evidence; (2) coordinate/extrinsic mismatch; (3) planned
initial heading/curve leaves observed space. Each gets a same-input control.

Owned changes start in a new v100 directory plus this task/audit. Expected source
boundary after diagnosis: native input/clock admission and SCAN plugin execution
seams; only extend transport if its independent 100 ms failure is reproduced.
Preserve native collision/support/body/map thresholds, original robot policy,
scene, start/goal and previous frozen versions. Do not delete the current owned
runtime while the repair remains in progress. Bulk evidence is execution-only
and retained on gpu5070ti after checks; no GPU training or robot actuation.

## v100 change boundary

Real Foxy scheduling reproducer: one shared callback group yields27/27 future
body samples under the declared120ms simulated compute stall, max300ms clock
lag. A dedicated mutually exclusive planning-data group plus a two-thread
executor yields0/27 future samples while work-callback overlap remains1.
The original v98 trace shows80-95ms future body samples at native input drains.

v100 propagates an optional callback group through SCANReplanFSM,
SCANPlannerManager and GridMap initialization, assigns all native data/timer
callbacks (including the map projection) to it, and lets Foxy's own /clock
callback run in the node default group. NativeWorker owns both groups through
a two-thread executor. Default callers preserve their original group behavior.
No source timestamps, pose payloads, planner geometry, thresholds or collision
rules change. Parent source copies and build stay separate for same-input tests.
Primary reference: https://raw.githubusercontent.com/ros2/rclcpp/foxy/rclcpp/src/rclcpp/time_source.cpp
The real recorded-cloud comparison and actual physical run remain required.

## v100 physical failure and v101 boundary

v100 actually starts walking (20 nonzero policy steps, net0.466m XY) but fails
before arrival. At sim14.807s a body stamp10ms ahead invalidates heading near a
low-velocity spline endpoint; checkFullCubicTrajectory returns InvalidCurve
at sample55, causing a stop. Native clock isolation reduces but cannot guarantee
cross-topic delivery order. Final applied-state copyback passes.

v101 adds bounded source-time admission for native live-body and FSM odometry:
retain the latest already eligible original pose while a future-stamped message
waits for its corresponding actual /clock. No interpolation/restamping, no
changed100ms validity rule. Preserve every pose delivered to the map worker;
only live planning admission is delayed. Queue overflow or source regression
fails closed. Reproduce before changing implementation, then rerun physics.

## v101 actual result and v102 repair

v101 original physics failed at0.583m final XY displacement with88 nonzero control
steps and0.997 navigation RTF. It did not reach the goal. No clock transport
reconnect occurred. At the first failed replacement solve the FSM stays in
REPLAN_TRAJ; native safety marks the old trajectory false solely on that state.

v102 changes only the safety-state predicate: both EXEC_TRAJ and REPLAN_TRAJ may
renew the exact executing trajectory lease after the existing full-curve check.
Emergency/wait states, invalid/expired curves, stale body/cloud and failed map
still block. The actual native-object regression on the original recorded map
reports EXEC clear but REPLAN blocked before the fix; all negative checks remain
blocked. A first-revocation log records the precise reason/trajectory.

## v102 actual failure and v103 ticket handoff

v102 did not reach the goal. The first cancelled owner encountered actual map
age250.1ms (over the existing250ms limit), and a later recovered owner hit
nav2_command_ticket_mismatch. The latter is a compute/publish race: a newly
received trajectory invalidates the sampled old ticket before Nav2 publishes it.
The real plugin/DDS regression reproduces cancellation before the fix. v103
discards the superseded nonzero command and publishes zero under the current
identity; the next tick requires the new trajectory's fresh safety proof.
Mismatched, replayed or expired tickets and explicit cancellation retain their
existing closed behavior. v102 native map/planner remain the pinned underlay;
only the v103 controller is rebuilt in the runtime overlay.

The first post-fix full test process exited with SIGSEGV during the start of
NoIndependentCommandTimer after the new regression passed. The exact failure
log is retained. A full retry passed27 colcon entries (25 GTest cases); repeated
suite checks follow to distinguish a test lifecycle race from the ticket fix.

## v104 lifecycle shutdown

v103 was frozen without physical qualification after a repeat-suite hang. The
exact GDB backtrace shows deactivate waiting in std::thread::join while the
native executor remains in SingleThreadedExecutor::spin. Foxy spin sets its
spinning flag on entry and can overwrite a prior cancel. v104 keeps requesting
cancellation until the owned executor thread exits, then joins before releasing
nodes or plugin state. It applies to both native and controller bridge workers.

The deliberate cancel-before-spin regression covers actual Foxy single-threaded
and two-thread executors plus delayed thread entry. The full controller/parity/
shutdown suite passes29 colcon entries (26 GTest cases). The24-controller-test
suite additionally passes three consecutive repetitions. The earlier isolated
SIGSEGV remains recorded; it has not recurred, and is not independently proven
to share the cancel-before-spin cause.

Primary implementation: https://raw.githubusercontent.com/ros2/rclcpp/foxy/rclcpp/src/rclcpp/executors/single_threaded_executor.cpp
Cancellation: https://raw.githubusercontent.com/ros2/rclcpp/foxy/rclcpp/src/rclcpp/executor.cpp

## v106 outcome and v107 atomic trajectory/proof handoff

v106 completes its process with a failed Nav2 progress result at24.818s physics.
It records690 applied-state ACKs with maximum3.263ms and verified full tmpfs
copyback, so this attempt has no transport timeout. There are136 nonzero control
steps; final XY displacement0.512m. The only controller revocation is Nav2's
progress failure, not a stale-map or ticket-mismatch event.

The real plugin regression demonstrates that simply receiving a new curve zeros
commands even while the old exact curve retains fresh native safety proof. This
repeats under the30Hz spline/20Hz safety stream. v107 stages at most four curve
and proof messages, keyed by exact trajectory and owner; either DDS order works.
Only a fresh matching pair can replace the active curve/proof atomically. Old
proof is never renewed by receipt of a replacement. All original100/250ms gates,
malformed input stops, explicit cancel, and measured-stop requirements remain.
No-first-proof timeout stays100ms after the first pending curve; ongoing lease
expiry cannot be postponed by an endless stream of unproved replacements.

Initial controller regression fails before the change;30 GTests/33 colcon test
entries pass after. Final rebuild uses one clock sample for each admission/
command decision and full mission protocol verification is in progress. No
physical acceptance is yet claimed.

## v110 physical progress, v111 video, v112 intrinsic map work

v110 travels14.347m measured path,1.383m elevation gain,992 nonzero control
steps and verified copyback. It still terminates FAILED after observation age
254.860/259.857/309.830ms and one119.934ms proof gap. The30.467s v111 video is
causally replayed from914 original recorded states; full decode and three
representative frames pass review. Its final failed status stays visible.

v112 independently replays all268 actually published moving clouds. Callback
CPU17.286s matches wall17.288s; cloud-only maximum excluding startup165.319ms
occurs without a slide. Other frames combine69.517ms sliding and64.145ms cloud.
This establishes intrinsic work beyond physics contention. All per-frame map
hashes and14 rolling-boundary baseline hashes are preserved.

v113 is a candidate equivalent inflation-kernel optimization. Rebuild the same
discrete footprint as both the original offset list and contiguous Z columns.
Unmasked occupancy updates clip each column once and apply the same saturating
integer update across at most two contiguous ring spans. Masked rolling-map
updates retain the original implementation. No footprint, threshold, ray, source
frame, admission, safety, retry or timeout changes. Every moving-cloud and
synthetic-boundary map digest must match before physical execution.

## v113 physical failure and v114 boundary

v113 walks22.835m without falling, but stops about3.70m short of the requested
goal. Applied copyback passes. Two terminal safety rejections show fresh maps
(214.882/204.887ms) with expired periodic proof (114.937/104.942ms). v114 moves
actual full remaining-curve collision validation into the Nav2 controller tick,
using a pinned immutable native map, independent query caches and the exact
controller pose/clock. The native planner keeps its own safety/replanning logic.
Every command remains bound to the exact owner and trajectory. The original
body source timestamp is rechecked at publication, including checker elapsed time.
This is an execution-ownership change, not a lease extension or synthetic proof.

## v114 reached the original goal

Actual v114 trial01 reaches the requested goal and measured stop, with two protected
retries. v115 is the checked causal review video. See the current audit REPORT.md
for source-age failures, independent final position/velocity verification and
next boundaries. Main continuity/30Hz/reliability remain open; Jetson awaits access.
