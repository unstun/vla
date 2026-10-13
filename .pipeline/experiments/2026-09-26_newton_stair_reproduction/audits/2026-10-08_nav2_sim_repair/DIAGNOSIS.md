Current result: v114 completes one original-scene navigation and measured stop,
with two protected retries. See [current report](REPORT.md); the investigation
below preserves earlier failures and causal tests. Full30Hz/continuity and
reliability acceptance remain open.

# Original Newton start rejection: v100 diagnosis

Stage: experiment + analysis. Original source parent v99; physical entry parent
v98. Dr Sun requires actual navigation and video, not component-only delivery.

## Direct evidence

- Verified extraction from the original v98 archive. First20 published scans
  retain sensor/world coordinates to1.327037e-6m max; cloud point counts match
  the original bridge and no terrain-filter/remapping substitution is applied.
- Native same-input map replay:60 original-pose/heading collision queries are
  rejected when the node clock is one real body sample behind. All60 become
  free when the corresponding real simulation clock is applied; all60 reject
  once the original100ms body freshness limit is exceeded. Map digest remains
  unchanged across each query comparison. Parent/candidate outputs match.
- Foxy executor control with a labelled120ms compute stall: shared group has
  27/27 future-body samples (max300ms clock lag). Separating clock execution
  has0/27; native-data callback overlap remains exactly1 in both conditions.
- Original v98 log independently shows body ages of-80 to-95ms immediately
  after manual input draining. UnknownObstacle/support rejection blocks seeds.

Foxy TimeSource creates its /clock subscription in the default callback group:
https://raw.githubusercontent.com/ros2/rclcpp/foxy/rclcpp/src/rclcpp/time_source.cpp
This explains how a long callback can stall clock application while a manual
DDS input take obtains newer body data. This source is a mechanism reference;
the recorded/native tests above establish the observed local failure.

## v100 implementation

The simulation/LiDAR native worker assigns all SCAN/map subscriptions and timers
(including the completed-map projection) to one mutually exclusive work group.
A two-thread executor lets Foxy's own default-group clock callbacks run while
that work executes. Real timestamps/poses, map operations, safety thresholds and
planner algorithms remain unchanged. Legacy/default callers keep their original
group. Foxy's depth message_filters has no group option, so its old single-executor
path is retained; custom-group depth construction fails explicitly.

Fourteen packages rebuilt;25 GTest cases /28 colcon entries pass. Original terrain
payload and native PCT parity, exact same-input collision results and the full
mission/cancel/stop protocol pass. These are prerequisites, not the requested
physical acceptance. v100 is frozen. Its original Newton attempt01 failed navigation: final net XY displacement0.466m,20 nonzero command steps, and verified applied-state copyback. Independent clock execution removed the larger clock lag but did not guarantee cross-topic DDS delivery order. At14.807s the newest body message remained10ms ahead of the processed clock; heading fallback returned NaN and the actual curve check returned InvalidCurve after55 samples.

The 100ms applied-state transport timeout from v98 is not relaxed. If it recurs,
use its recorded sender/receiver sequence and ACK timing to isolate it separately.
The active runtime is retained while this repair is in progress.

## v101 source-time admission

Preserve original body messages in a bounded ordered buffer. Only messages whose
source stamp is at or before the actual processed ROS clock may update live body
state. Map-worker source inputs remain unchanged. Duplicate stamps do not renew
evidence; regressions, invalid stamps and buffer overflow latch a closed state.
The original100ms freshness limit is unchanged.

The regression fails against v100 and passes against v101 on both real GridMap
and real SCANReplanFSM objects. Seven actual-object assertions and buffer boundary
negatives pass. Fourteen native packages rebuild;25 GTest cases/28 colcon entries,
native PCT and the mission/cancel/stop protocol pass. v101 is frozen. Its original Newton attempt01 failed:0.583m net XY displacement,88 nonzero control steps,0.997 actual navigation RTF, with verified applied-state copyback. No command transport reconnect occurred. Physical acceptance remains false.

## v102 active-curve safety during replanning

The first failed replacement solve leaves the native FSM in REPLAN_TRAJ. Native
safety previously required EXEC_TRAJ in addition to a clear full-curve verdict;
that falsely cancelled an otherwise valid executing curve. An actual-object
regression using the recorded first scan and a labelled stationary cubic shows
EXEC_TRAJ clear and REPLAN_TRAJ blocked for identical geometry/time. Emergency,
wait and stale-body negatives block as expected.

v102 admits a fresh full-curve proof in either EXEC_TRAJ or REPLAN_TRAJ. It does
not admit an unchecked replacement, bypass an obstacle, or extend any age/curve
limit. A first-cancel log now records the controller's exact reason/trajectory.
Component rebuild and regression are in progress; no physical success is claimed.

## Subsequent physical and lifecycle evidence

v102 still failed. It first cancelled on a genuinely stale map250.1ms old, then
a recovered owner hit a compute/publish race: receiving a replacement spline
cleared the already sampled ticket and caused nav2_command_ticket_mismatch.
v103 preserves the ticket for publication to identify it as superseded, emits
zero and requires the replacement's own fresh proof next tick. Real DDS/plugin
regression fails before and passes after.

v103 was not physically launched because repeated tests hung on lifecycle exit.
The retained GDB trace shows deactivate joining a native thread still in Foxy
spin. v104 fixes cancel-before-spin loss by cancelling until the owned thread
exits and then joining. Actual single/multithread and delayed-entry checks pass;
26 GTests, three24-test repetitions and the full mission protocol pass. An
earlier isolated SIGSEGV is retained and has not recurred; its causal link to
the shutdown race is not independently proven.

v104 physical preflight refused the legacy qualification-key mismatch; v105
accepts explicitly qualified native underlay/overlay package counts. v105 uses
identical native bytes but its physics ended incompletely at12.8015s on the
original100ms applied-state ACK timeout. Linux committed90 while the client
last acknowledged89; final hash mismatch correctly prevented copyback acceptance.

v106 moves per-step receiver audit I/O from the Mac bind mount to the already
owned Linux tmpfs, returned through the existing verified exec/tar path. Client
loading is explicit because scene imports had changed sys.path and selected the
older scripts copy. Client/server transaction timings are recorded; no original
source timestamp, reader limit or100ms ACK timeout changes. Actual ZMQ/parser
checks pass before/after under normal conditions. A labelled150ms host-log stall
reproduces the parent timeout; candidate acknowledges100/100 and retains stale,
reordered and wrong-identity rejection. This establishes the avoidable I/O
mechanism, not yet the exact cause of the prior physical timeout. v106 original
physics is running; full navigation remains unaccepted.

## v106 transport result and v107 physical result

v106 returns690 applied-state ACKs, maximum3.263ms, and verified Linux audit/
state copyback. Navigation still fails the progress checker after0.512m XY and
136 nonzero control steps. The controller zero-command regression confirms
that an unproved replacement unnecessarily clears the old still-valid proof.

v107 admits only an exact fresh curve/proof pair, retaining the old unmodified
lease meanwhile. Real plugin regressions, stale/wrong-owner negatives, original
cancel/lifecycle tests (30 GTests) and mission protocol pass. Original physics
still fails: active trajectories2 and54 hit the combined safety/observation
TTL guard, followed by a later startup timeout. It moves0.632m XY,79 nonzero
steps, and copyback verifies. Existing logs do not distinguish future proof,
expired100ms proof or expired250ms observation. v108 adds failure-only values
for those timestamps/ages; it changes no decisions, limits or cadence.

## v108 isolated actual age failure; v109 mapper cadence

Original physics confirms observation age250.101ms and259.857ms at rejection;
the corresponding exact-trajectory proof ages are35.014ms and39.978ms. These
are genuine observation expiry, not future-proof or100ms validation expiry.

A cloud-only20-vs100Hz replay does not expose the cadence delay because the
mapper sleeps between10Hz input bursts. Replaying the original105 body samples
from50Hz telemetry as well as20 actual clouds and their recorded20–40ms sensor
publication delays exposes the phase interaction: maximum sampled map age is
249.298ms at20Hz and192.239ms at100Hz. All20 clouds are applied, with no window
drops and byte-identical occupancy/inflation/ray/history map digests. The full
physical bridge body stream is not replayed; this is component evidence.

v109 changes only the mapper scheduling cap from20 to100Hz. It does not add
clouds or force100 heavy map fusions per second; body-only batches remain clean.
The native C++ bytes are v108/v102 unchanged. The250ms observation and100ms
body/proof limits remain unchanged. Original physics attempt01 is running.

## v109 physical limit; v110 proof at validated publication

v109 moves1.400m XY with202 nonzero control steps but still fails. Observation
age reaches250.101/265.107ms, and a later proof age reaches129.929ms.100Hz
mapping scheduling alone is insufficient for the complete pipeline.

The native planner already holds a publication lease from the final whole-curve
check through spline publication, but its proof was only emitted by a separate
50ms timer. v110 records the actual final check's start time, original map
observation time/revision and resulting trajectory ID. It publishes that exact
proof with the newly published curve before releasing the existing lease. The
periodic remaining-curve check remains. No validation is skipped or restamped.

The actual native planner generates a valid curve against20 recorded scans
with unchanged speed/dynamics/collision configuration. A ROS subscriber verifies
its exact bound proof20ms later without changing the original check/map times.
A solve at300ms stale body/cloud fails and invalidates the publication proof.
The state-only safety regression and30 GTests/33 colcon entries also pass.
v110 original physics attempt01 is running; full acceptance remains false.
