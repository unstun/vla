# v133 failed-pilot diagnosis and support-map repair

Stage: experiment + analysis. Local VLA repository is authoritative. Heavy
execution and raw captures remain on gpu5070ti under `/data/sun/vla_mppi_20261009`.
Repeated physical acceptance is still being evaluated; see the final results
section when the fixed batch closes. No robot or training run was performed.

## Identified failure

The target is frozen `v133_candidate_attempt02`, not a selected successful run.
Its first stop leaves an almost upright body. PD rejoin begins at 36.731 s,
but the left-front foot moves into a real seam in the original Building mesh.

| Recorded time (s) | Left-front foot XYZ (m) | Body tilt | Observation |
| --- | --- | --- | --- |
| 35.892 | 7.614, 5.940, 4.548 | 1.6 deg | Supported beside the seam |
| 36.492 | 7.602, 5.935, 4.548 | 0.9 deg | At the edge; foot sphere still contacts it |
| 37.091 | 7.576, 5.916, 4.500 | 2.2 deg | Foot has descended into the seam |
| 37.291 | 7.561, 5.904, 4.432 | 4.6 deg | No same-floor triangle below this XY |
| 37.491 | 7.553, 5.894, 4.264 | 18.9 deg | Foot below the adjacent floor |
| 42.009 | 7.498, 5.864, 4.196 | 29.3 deg | Tilted zero-command settling |

The foot position is computed from **recorded body transforms**, using the same
frozen Newton shape/body mapping and authored 22 mm foot sphere. Vertical rays
through the original static triangles show a roughly 7 cm seam, while the 10 cm
PCT floor cell reports ground around 4.533 m throughout it. The original static
samples also show the gap; a sampled maximum height is not whole-cell support.
See `results/floor02/floor.png`. Contact forces refer to the preceding control
boundary, so they are not restamped as simultaneous video-state forces.

The final source-age rejection at 41.664 s occurs after the support loss. The
retained final-stop stream never completes the unchanged one-second stillness
window. Longer waiting or extra retries cannot create floor under the trapped
foot. This explains this failed episode; it does not attribute every historical
failure to the same seam or establish that all rejoin dynamics are correct.

## Direct native regression

The replay loads 255 original published scans, original support payloads and the
due measured torso pose at 36.651485443 s. The actual native common collision
query returns permit in v133 and reject in v134 for the same pose:
`(7.77828, 5.96572, 4.81972), yaw 2.59343`.

This reconstruction does not reproduce original asynchronous map scheduling.
The sensor recorder's `/quad_0/lidar_pose` is an optical-frame pose, not the
torso; the first preparation used that field and was not used for the regression.
`input02` uses actual telemetry torso data with its original timestamp. Both
native comparisons bind the same input identity and executed probe.

## Changes and rejected intermediate

**v134** adds a negative-only static support-coverage mask. The offline generator
processes all 150,500 existing floor records against the pinned original mesh,
sampling 16 points per 10 cm cell at 25 mm spacing. It finds 10,082 partial cells.
The native immutable mask uses the existing cylinder radius and conservative
cell extent. It cannot grant support or waive live sensing/ownership checks.

Solid floor, a 7 cm gap, a permitted 20 cm step and a 40 cm drop exercise the
real generator. Actual mask tests cover the failed position, a clear landing,
different floor, malformed identity, missing input and invalid query. All 14
packages build, 38 existing native tests pass, and actual graph/host/writer
checks pass. v134 freezes 3,050 source pairs and 618 runtime inputs.

Its three fixed physical pilots all fail without falls, after 0.802 / 0.800 /
0.789 m. Do not adopt v134 alone. The local planner now rejects locations while
the global PCT reference still traverses those same forbidden regions. The
initial hypothesis of overly conservative local coverage was refined after
checking the actual global paths; a compatible global route is feasible.

**v135** keeps exact v134 native code and the same veto. It raises traversal
costs in an isolated copy of the PCT map and adjusts only affected gradients.
No elevations or existing positive support payloads change. The yaw-independent
global radius is 0.35 + 0.18 = 0.53 m, enclosing both local cylinders. Costs are
only raised; 3,219 formerly traversable layer cells become blocked.

Actual installed PCT finds routes with both inputs. A 25 mm sampled, two-cylinder
check has 100 vetoed queries out of 2,290 on the original route and 0 out of
2,412 on the new route. Route length changes from 26.342 to 27.759 m. This is
route geometry evidence, not physical acceptance. The first generation attempt
used NumPy 2 pickle module names incompatible with Foxy's NumPy; preserve that
failure. The selected map is generated in the actual Foxy environment.

The candidate uses separate map epoch `stair_reactive_coverage_v135`. The mission
driver reads the selected backend map identity. Baseline retains original v133
map/native behavior. Both arms use v135 host; source and map hashes are checked
before each run. v135 freezes 3,090 source pairs and 618 runtime inputs. Its
38 native tests are explicitly reused from the byte-verified v134 install;
global-route and final map/identity/graph tests are new v135 evidence.

## Scope and repeat protocol

This is a correction to the simulator's pre-existing static map. The live graph
never receives mesh queries, feet, future states or a route-specific hole mask.
No assertion is made that a robot without this prior map detects an unseen gap.
Finite 25 mm samples are not a proof against arbitrarily small holes. The original
scene, policy, physics, sensor timing, map/body freshness limits and measured-stop
criteria are unchanged. No MPPI adaptations are added.

Three fixed candidate pilots precede the six-fresh-runs-per-arm ABBA comparison.
See `REPEAT_PROTOCOL.md`. Preserve every failure. The original v133 pilot and
earlier v114 comparisons remain separate denominators. Main 30 Hz, general
navigation, Jetson and hardware acceptance are separate from this repair.

## Subsequent recovery-dispatch repair

v135's fixed pilots produce two arrivals (27.716/27.761m) and one failure
(25.399m), with no falls. The failed robot is upright at its final pose and
has safely passed the original upper-landing seam. Do not start the v135
formal comparison or call the whole system repaired.

In that failure, generation4 is received at37.635944s, the controller times
out at39.654835s, and the FSM accepts it only at40.744236s, immediately followed
by the cancellation already issued for that attempt. Generation3 receives no
FSM acknowledgment before its depth-one topic is superseded. The original
two-second controller deadline expires while the shared native work group keeps
processing the old plan. An initial unready-map rejection also consumes a retry.
The final stop occurs at72.447s from a254.860ms observation age, after all seven
attempts have been consumed. None of these facts permits relaxing freshness.

**v136** services the actual queued mission subscriptions at FSM work boundaries,
cancellation first, bounded by DDS depths10/1. It also defers a replacement
through the old EMERGENCY_STOP exit; the old code can accept a new target and
then clear it on that exit. Every original callback identity/high-water check
remains, and all mutation stays within the serialized work group.

The actual DDS/native FSM regression uses562 original scans and the due torso
pose from the failed later route, with deliberately selected timer ticks. Old
nativev134 leaves the queued route unprocessed and changes an accepted target
from present to absent across emergency exit. Newv136 services it, defers then
preserves the replacement, and rejects a canceled queued route. This isolates
the work-boundary behavior; it does not reproduce the entire historical executor
schedule. All14packages/38native tests and host/graph/writer gates pass. v136
freezes3,133source pairs and618runtime inputs.

Its proposed comparison now isolates nativev134 versus nativev136, both with
the same v135 corrected static map and v136 host. See
`REPEAT_PROTOCOL_V136.md`. The v135 and original-map counts remain separate.

## Freshness and local-envelope repairs

The v136 fixed batch finishes 2/3 without falls. The third run exhausts its
attempts after route admission computations outlive the original 250 ms map
freshness gate (observed ages 254.860--269.852 ms). It is a transient-input
failure, not proof that the route is geometrically impossible.

**v137** leaves the same reference pending when original map/body inputs are
unavailable or expire during admission. It restores previous state when a
computation cannot be admitted. Fresh impossible geometry still rejects;
canceled references never revive. The existing two-second controller deadline
and six-retry limit remain. Actual native stale-to-fresh replay distinguishes
v136 (reference lost) from v137 (same reference resumes); cancellation and
fresh geometric rejection pass. All 14 packages/38 native tests pass.

Its three pilots again finish 2/3 without falls. The failed run accepts all
seven references promptly, then remains upright at (7.885,6.511,4.828). A
progress timeout is followed by repeatedly rejected local curves. At the first
replacement, the optimizer accepts a curve whose controller-lookahead footprint
is vetoed at t=0.878170478: body (7.684185,6.569040,4.828249), front cylinder
(7.517968,6.499961), yaw -2.74771449. Seed/control-polygon tangent checks differ
from the final 0.8 s lookahead heading. The stopped body is inside the global
0.53 m all-heading envelope, although its current heading is supported.

**v138** adds that same 0.53 m envelope to local collision queries and retains
the original cylinder veto. It is a prevention change for fresh episodes, not
an escape method from an already-invalid pose. No global-map bytes, optimizer
gains, safety age limits, retry counts, policy or physics change. On the same
346 recorded scans and due torso state, the actual installed query changes the
trapped position from permitted to blocked. A 6,800-query position/heading sweep
preserves every old rejection, adds 608 rejections, and leaves 3,808 clear.
Map reconstruction digests match. All 14 packages/38 native tests and actual
host/graph/output checks pass. Frozen identity: 3,219 source pairs, 618 inputs.
Its three fixed pilots all fail at the initial pose, with only 1.18 mm of settling motion and no falls. The all-heading local veto is rejected. It does not proceed to a formal comparison.

## Full-curve optimizer feedback (v139)

Return to v137 local occupancy, leaving v138 rejected. A raw initial-seed fit
also fails the original collision/dynamics/minimum-cruise checks; bypassing the
optimizer is not a valid recovery. Actual native reconstruction on 346 captured
scans reproduces v137 rejection from the failed start/target boundary state.

v139 adds a bounded nearby free-footprint witness for the controller-heading
collision and feeds constraints into the mutable cubic controls using the
existing rebound cost. Fixed endpoint controls are untouched. Build01 passes
38 component tests but fails the captured-case regression: post-optimization
minimum-cruise refinement reintroduces a collision at t=1.128804425. Preserve
its workspace and results. Build02 feeds final post-refinement collisions back
as well, bounded to two additional complete attempts, retaining the original
boundary PVA, execution epoch and all final gates. The completed actual native
regression now accepts a curve, checked again against all 567 full-curve samples,
boundary PVA and dynamics, while v137 rejects the same map and boundary inputs.
All 38 native tests, seven hint-boundary checks and host/graph/output checks pass.
Frozen identity: 3,220 source pairs, 618 runtime inputs. The fixed three physical
pilots finish 3/3 with measured final PD hold and no falls. A final runner-output
BrokenPipeError is preserved; a separate gate verifies every closed outcome
hash without rerunning/replacing a pilot. The fixed six-fresh-runs-per-arm
comparison is complete; its denominator excludes the pilots.

## Timing boundary

Completed fresh candidate trials already show retained latency spikes: attempt04
has mean14.384ms, p9516.493ms, p99384.033ms and maximum556.913ms. This repair
is not tail-latency elimination or sustained30Hz acceptance. A low-speed pause
summary includes final hold/settling; do not label every such interval a recovery
attempt. Match original cancellations, stop proofs and replacement owners to
attribute actual mid-mission recovery.

## Final repeated physical results

The fixed comparison completes all12fresh trials: parent nativev137 arrives5/6,
new nativev139 arrives6/6, neither arm falls. The three earlier v139 pilots arrive
3/3 and remain a separate denominator. Candidate physical gate passes for this
Building scenario. Sample size does not establish a general success-rate effect.

All11candidate replacement owners have the actual recorded causal stop proof
before the new route, matching original identity, source stamps and measured-
stillness flags. Cancel-to-proof wall intervals are1.075--1.314s; proof-to-next-
route intervals0.042--0.095s. Original applied-sample polling is not reconstructed.
Candidate fresh runs exercise1,730sampled feedback events and34post-refinement
feedback events. The controlled same-input regression is separate from these
fresh asynchronous physical trials.

The single formal control failure stops after1.516m with an upright low body;
it receives all seven routes but cannot produce replacement local curves.
Its first revoke is scan_safety_rejected followed by scan_trajectory_missing.
Do not claim that every control failure across this lineage has the same cause.

The raw original v133 failed trial is reverified. All30new trials (18pilots,
12fresh comparison runs) retain5,389,007,279raw bytes on gpu5070ti and are rehashed
against their capture indexes. All six frozen source/native identities pass.
The returned bundle has569files/13,813,981bytes; every byte and every frozen
qualification-check hash is verified locally. See final_verification.json and
SCENARIO_ACCEPTANCE.json. Failed runs and failed diagnostic/build attempts remain.

Final timing limit: fresh candidate p95 values range10.487--22.763ms, but maximum
round time reaches706.406ms in attempt09. Main sustained30Hz/tail-latency,
general navigation, unseen-gap detection, Jetson and robot gates remain open.
The physical scene/policy/positive-map payloads are unchanged; this branch adds
negative static coverage and bounded recovery/optimization fixes. It prevents
entering the original unsupported pose, not escaping any arbitrary already-
unsupported pose. Main task remains in_progress; broader v48 reference and
retained MPPIv122/hostv125 remain. No steps2--5 promotion, training or actuation.

No Git commit: the pre-existing index.lock and unrelated staged/dirty paths are
preserved. The local frozen source, changes.patch and verified provenance are
available for human review.
