# Newton stair repair contracts

## 1. Scope and trigger

These contracts cover versioned repairs v8–v27 in
`.pipeline/experiments/2026-09-26_newton_stair_reproduction` (called `E2` below).
They are component contracts. The v24 short stair trial reached native arrival
but lacked final PD hold; v26 selected the correct complete-floor route but did
not physically complete it. Historical Isaac success is a separate condition.

## 2. Signatures

- `precomputeEthStyleStepScores(TerrainSnapshot, StepScoreParameters)` in
  `plan_env/eth_step_score_adaptation.h` produces scored support separately from
  source ground elevations.
- `selectedGroundReturn(terrain, x, y, z, band)` in
  `plan_env/raw_return_classification.h` classifies measured endpoints only.
- `SCANPlannerManager::reboundReplan(...)` retains mandatory native AStar,
  initialization, optimization, PVA, dynamic and full-curve collision checks.
- `P2BAdmission` carries full command identity, `consumer`, `status`, `message`,
  `hold_confirmed` and `measured_stillness_confirmed`.
- `RosScanPort._wait_admission(identity, statuses, timeout_s, consumers)` in
  `runtime_sources/backend_ros/p2b_backend_ros/node.py` matches both identity and
  the expected consumer. The older `backend_adapter/ros_node.py` is not the
  runtime receiver for these runs.

## 3. Contracts

Missing neighboring ETH cells/scores may be skipped as in the pinned upstream
filter. This does not create support in an absent query cell or join ambiguous
building levels. Keep the existing hard step-height rejection.

Keep unscored PCT ground and scored support distinct. An invalid step score is
not evidence that a measured floor point is a new object. A raw riser point may
be recognized between a selected upper surface and an associated lower neighbor
within the existing step capability. Missing central support, unrelated floors
and objects above the mapped floor remain unclassified. Existing nonterrain
history always wins over a newly classified terrain hit.

Reference target checks use the same planned segment start and heading as seed
search. The actual measured body pose remains unchanged; the existing fresh-body
fallback still applies to nearly zero horizontal directions.

For v13–v47 the mandatory native graph initializer owns the seed. The guarded
v48 warm-start exception is defined in Section 10. Do not execute a legacy
initializer whose outputs are unconditionally discarded: an expired short curve
can leave its old arc-length indexing empty even when a first-call test passes.

Native replan exhaustion closes the same owner's command gate. It is not a
controller hold acknowledgment or physical-stillness measurement. A queued FSM
rejection cannot satisfy a wait for a controller reply. The existing stop flow
must still obtain controller hold and measured quiescence before releasing the
owner and writing a failed terminal result.

## 4. Validation and error matrix

| Input or condition | Required result |
|---|---|
| Sparse neighbor, valid central tread | May retain support |
| Missing central support, ambiguous floor, too-tall step | Block |
| Confirmed riser between associated mapped treads | Classify that measured endpoint |
| Low box, wall, post or person absent from ground map | Occupied regardless of semantics |
| Same voxel has prior nonterrain evidence | Do not waive its inflated contribution |
| Expired accepted short curve, repeated planner call | Bounded execution; valid curve or explicit failure |
| Same-owner FSM exhaustion | Close gate and request verified stop |
| FSM rejection while waiting for controller | Keep waiting for the controller |
| Controller hold but no measured stillness | No completed-stop or arrival claim |

## 5. Good, base and bad cases

Good: the captured 189-scan moving-state failure is retained as a new regression,
even after earlier 66/67-scan continuations pass.

Base: a component repair has direct red/green evidence but no successful physical
route. Its result says so explicitly.

Bad: the v9 positive-Z inflation change admitted a longer curve but missed a low
box. It was rejected and is not a parent of the subsequent accepted code changes.

## 6. Tests and assertion points

Run the focused version tests, native source/build hash checks and actual native
recorded-input replay. Relevant entries are `versions/v8/test_sparse_support.cpp`,
`versions/v11/test_failure_notice.py`, `versions/v14/test_admission_consumer.py`
and `versions/v15/test_riser_ground.cpp`. The receiver test replays the actual
v13 admission order; mock happy-path stop tests alone missed the queue bug.

Retain all eight measured geometric sensor cases, plus no-progress, out-of-map,
stale-input and historical-obstacle negatives. A successful seed is insufficient:
assert boundary PVA and the entire published curve after optimization/retiming.
Repeat an expired-curve call, not only initialization with an empty manager.

Physical acceptance requires measured route completion, final PD hold and the
version's input profile. `building_full` selects full Building geometry, with
`short_stair` as the default route. Since v25, the explicitly selected
`--building-route historical_full` uses the original complete-floor goal.

## 7. Wrong versus correct

Wrong: infer complete-building success from a long PCT path, a free endpoint,
one seed or a few moving local curves.

Correct: bind source, profile, original measurements, full native checks, physical
outcome and video to the same frozen version; preserve failures and scope labels.


## 8. Static evidence and body-reference contracts (v18–v24)

An individually rejected clock observation does not invalidate a still-fresh,
converged estimate or renew its TTL. Disconnect, identity errors and reset still
invalidate the mapping. See the separate clock bridge specification.

Preserve original float32 ground elevations separately from the original
float16 cost/dedup decision. Additional qualified surface evidence is a distinct
required input when configured, with exact ROS layout, source hash at the
publisher, world frame, positive time and freshness validation. Updating either
source clears positive terrain grants but retains conservative nonterrain
history. A configured additional source replaces the endpoint-classification
source; it must not be ORed with the previous source. Scored navigation support
continues to derive from the original selected map. A denser offline simulator
prior is not proof of equivalent real-robot map coverage.

The collision cylinders are footprint samples, not independent body reference
poses. The body-center height must satisfy the original height/layer contract.
Associate each footprint terrain cell with that center's original unscored
layer, then validate the same index/elevation in the scored map. Never skip a
closer Unknown or Unsupported layer to find a farther supported one. Missing
center/sample, source mismatch, equal-distance ambiguity, unrelated levels and
height delta greater than or equal to the existing step limit fail closed.

Only the terrain support Query.z may use the associated surface height plus
reference clearance. Actual ray occupancy, map boundaries, point XYZ, footprint
geometry, robot pose and published trajectories remain unmodified. Their actual
unknown/occupied/nonterrain-history result still controls the final decision.
Diagnostics must use the same body-reference entry as planning and safety;
otherwise an old WrongHeight print can misrepresent the current decision.

`versions/v24/regression_probe/src/body_support_contract.cpp` locks the old
WrongHeight -> corrected support height -> final Free transition, together with
15 targeted conditions. Actual v23 stopped-state replay passes through the
compiled full double-cylinder entry, not only that helper. Earlier stopped
states, eight complete unmapped fixtures and all PVA/whole-curve rejection gates
remain required before physical execution.

Known mapped low protrusions have a separate acceptance-policy boundary: the
original baseline already treats some 13cm structure as terrain. An envelope
overlap query is not evidence of physical contact or stable stepping. Do not
claim universal independent-box avoidance from the eight unmapped fixtures.

A recorded emergency hold can outlive its duration and remain visible to the
current safety callback outside EXEC_TRAJ. If recovery loops, distinguish the
actual GEN odometry start from the safety replan's old spline endpoint. This is
an observed open issue, not authorization to disable safety checks.

## 9. Route configuration and seed simplification (v25–v27)

For `map.pct_layer`, omission means the original default layer1, explicit null
means native automatic layer selection, and integers mean fixed layers.
Preserve explicit null only at this complete configuration path, including the
adapter schema and overrides. Do not turn all other omitted/null fields into
new configuration behavior. Explicit per-request layers still take precedence.
Test the actual config loader, layered client, TCP worker and native planner;
a correct config file plus a direct native call missed the v25 runtime defect.

An existing valid AStar seed may use OMPL1.7.0 reduceVertices' deterministic
front-to-back branch only after the original search, exact endpoint identity
and every returned edge pass. Use the same half-voxel, both-endpoint collision
predicate for the new connector and its heading. A blocked connector leaves
the complete seed unchanged. Shortcut success never bypasses fitting,
optimization, dynamic, boundary-PVA, minimum-cruise or full-curve checks.

`versions/v27/analyze_regression.py` locks a real blocked-direct manager case:
free endpoints, blocked direct segment, unchanged62/62/30-node seed payloads,
and the same accepted original prefix. The new stopped-state case also records
rejected long shortcuts before an accepted shorter prefix. Report sampled
collision evidence, not a continuous swept-volume or physical-contact proof.

A constant emergency B-spline is not a zero-command contract in the current
closed-loop controller: its position-error feedback can remain nonzero. Do not
skip hold safety by assuming identical control points imply stationary control.
Freshness loss during blocking retries and that hold interface remain separate
open issues; v27 changes neither.


## 10. v48 owned remaining-curve initialization

### Scope and trigger

Candidate 2 supplies a new initial guess from the manager's accepted curve.
It does not publish/restamp that old curve or alter final goal/yaw rules.

### Signatures

`setWarmStartContext(identity, goal, curve_time=-1)` binds the FSM's P2B identity
and exact final goal to the same relative time used for original start PVA.
`makeWarmStartSeed(start, velocity, acceleration, target, points, interval, reason)`
returns timed samples or rejects reuse. `invalidateWarmStart()` clears ownership.
`reboundReplanAttempt(..., optimization_attempted, allow_warm_start=false,
used_warm_start=nullptr)` retains a cold default for direct regression calls.

### Contracts

The identity string quotes run/request/goal/route/command/map IDs and includes
run epoch, generation and map revision. Reuse requires the matching accepted
trajectory ID, map instance and exact goal. Validate spline/clock/layout and
start PVA before evaluation, refresh inputs, and check the full remaining cubic
with the original heading/occupancy/support entry. A new target connector must
pass collisionFreeSegment. Preserve accepted timing in the new hard-PVA fit.
Do not import the upstream unchecked polynomial extension or linear Z rewrite.

Both warm and graph candidates run the original optimizer, retiming, minimum
cruise, final PVA/dynamics and newest complete-curve check. Warm failure clears
reuse and executes the original graph/fixed-height chain from the same inputs;
its failure counter is reset to the parent graph entry value before fallback.
Route regeneration, emergency and invalid-current-curve handling invalidate it.

### Validation and error matrix

| Condition | Behavior |
|---|---|
| Owned, current supported remaining curve | Timed initial guess; new native solve |
| Changed identity/goal/map/curve ID | Reject warm; graph fallback |
| Invalid/expired/future curve or mismatched PVA | Reject warm; graph fallback |
| Stale scan, absent support, blocked curve/connector | Reject warm; graph fallback |
| Warm fitting/optimization/final check rejects | Original graph and recovery |
| Both chains reject | No new curve; original failure/stop flow |

### Good, base and bad cases

Good: v48 build02 paired warm-only solves pass at about 3 ms and every new curve
passes independent PVA/dynamics/whole-curve assertions. Base: cold v32/v33 geometry
is exact. Bad: build01 nominal arc resampling compressed accepted timing and all
six warm optimizations rejected, including a 55–57 ms fallback tail.

### Required assertions

`versions/v48/contract/performance_probe.cpp` tests identity/ownership, clocks,
PVA drift, stale input, bounds/connector rejection, route/emergency invalidation,
real graph fallback, no publication on failure, paired identical inputs, and
new native IDs with full final PVA/dynamic/collision checks. Keep cold native and
cache regressions. Verify the versioned backend package before physical launch
and require live navigation_contract plus actual global_refresh evidence.

### Wrong versus correct

Wrong: equate a fast warm-only median with 30 Hz or lower full-loop tail latency.
Correct: report warm accept/fallback counts and full-round P95/P99/max and actual
attempt/successful-plan rates. v48's live median improved, but P95 stayed near
126 ms, P99 worsened, and actual local rate was 15.86 Hz. Separate live trajectories
are not a paired causal comparison; preserve that limitation.


## v49 bounded-solve failure boundary (2026-10-01)

v49 is a rejected experimental candidate, not a relaxation of the contracts above.
It shares one steady deadline across the local chain (20 ms compute /25 ms total),
rolls back unpublished candidates and checks complete fresh remaining curves before
continuation. Component checks pass; live trial02 still has three >33.333 ms rounds
and an unrecognized `native_solve_timeout` admission reason. The unchanged backend
only closes its matching-owner gate for `native_replan_exhausted`. Receiving an
admission message or publishing an emergency B-spline is not evidence of gate
closure, controller hold, measured stillness or terminal completion. Any future
timeout implementation must test the actual backend handler and full stop flow,
and measure atomic input-refresh/scheduling overshoots. Preserve frozen v49 and
its failed trial; see `versions/v49/RESULTS.md` in the Newton experiment archive.

## v50 upfront-search proof and measurement boundary (2026-10-01)

v50 directly inherits v48, excludes v49 and adds no stop or solve-timeout policy.
The goal-region precheck may reject only when a necessary map-bound/lattice
condition proves that no original endpoint is eligible. A possibly eligible
endpoint retains native search; zero-tolerance seed search is unchanged. Never
turn the necessary box into a collision-free or stair-support verdict. Consult
`versions/v50/IMPLEMENTATION.md`, `goal_region_bounds.h` and the recorded-map plus
exhaustive endpoint contract tests before extending it.

Profile full planning rounds, including target selection, input application and
recovery. Inclusive timers overlap and cannot be added as exclusive costs.
Observer-order replay does not reconstruct DDS batches or unpublished failed
planner state. Exact accepted geometry on paired replay is a component result,
not evidence that the original live maximum was reproduced or eliminated.

v50's paired replay maximum improves from107.481 to4.827ms, but physical trials
peak at1829.626/858.031ms and stall near the corridor corner. Its worst round spends
time in12 cold seed/optimizer attempts and40 input refreshes; goal search itself
is only0.029ms. The fresh v48 control also stalls at that corner, so the geometric
precheck is not established as the cause. Keep this unresolved distinction.

Count successful plan completions over the same complete observation interval
as attempts, including stalled time. Computing success frequency only between
first and last success hides a post-success stall. Report measured path/pauses
alongside latency, and disclose artifact-transfer or other load overlap. See
`versions/v50/RESULTS.md` and its reproducible analysis for both improvements and
failed acceptance. Do not modify frozen v50 to repair the remaining cold chain.

## v52 terrain lookup reuse (2026-10-02)

The cache stores exact raw/scored layer-vector lookups for an integer XY cell,
including missing cells, within the existing raw-contributor cache scope only.
Capacity is4096 cells; extra cells use original lookups. Clear borrowed pointers
before any input mutation replaces either snapshot and on outer scope entry/exit.
Nested scopes and empty drains retain the original outer scope. Do not cache
layer selection, freshness, occupancy, support decisions or trajectory validity.
Tests must cover signed keys, missing cells, capacity, nested scopes, disabled
parity and the actual ground/surface/cloud mutation callbacks. Compare accepted
control points and knots exactly in the paired replay.

v52's 18 idle-host cold replay rounds preserve outcomes/geometry and reduce maximum
473.514 to 422.981 ms. The live trial still measures 10.19 Hz successful planning,
711.404 ms maximum and a 46.57 s late pause, so tail/continuity/30 Hz acceptance
fails. The synchronous CPU cold chain remains the bottleneck despite a 2.04 ms
median; native controller remains 30 Hz. Inclusive profiles overlap. A busy-GPU
preflight failure is zero physics, not a failed navigation trajectory. Preserve
its record and use a new attempt ID; never stop another task's process for resources.

## v53–v57 corner continuity and physical-floor contracts

### Scope and trigger

Compatible route refresh, queued recovery input and omitted physical neighbor
floors caused repeated cold recovery at the recorded corridor corner. v53–v57
address these boundaries without v49 deadlines or changes to stop behavior.
The frozen v57 native implementation is `scan78_physical_floor_presence_v56`.

### Signatures

- `SCANReplanFSM::canPreserveReferenceBinding() const` and
  `reprojectFeasibleWindow()` qualify continuity across a route refresh.
- `recoveryTargetOccupancy(const Eigen::Vector3d &, double)` drains queued input
  through existing callbacks before the original occupancy query.
- `GridMap::reactivePhysicalFloorCallback(PointCloud2::ConstSharedPtr)` receives
  `/pct_physical_floor`; `qualifiedPhysicalFloor()` returns qualified evidence.
- `versions/v57/verify_entry_gate.py` checks actual launcher qualification keys,
  frozen source, installed native bytes and the physical input asset.

### Contracts

Bind warm eligibility to exact requested XYZ/quaternion and the complete owner,
map and accepted-curve identity. Check trajectory ID and clock type before time
subtraction. Preserve eligibility only; every reuse still validates newest
occupancy, support, connector, PVA, dynamics and the entire resulting curve.
Reproject window geometry without extending its TTL or changing growth rules.
Failed qualified refresh restores the previous reference, window and binding.

Recovery input draining preserves the round's original spline-derived start PVA
and the 250 ms cloud-age limit. Share its boundary query with diagnostics; do
not substitute the old query result for final native validation.

`PhysicalFloorSnapshot` carries elevation and raw cost, with no Support labels
or conversion to `TerrainSnapshot`. It may inform neighbor floor presence and
height association only. Central traversal and LiDAR classification still use
the unchanged selected payload. Pair source IDs, frame, grid and freshness.
Replacing physical evidence clears borrowed caches but retains unchanged sensor
stamps, selected-terrain labels and nonterrain history.

### Validation and errors

| Condition | Required behavior |
|---|---|
| No curve, clock mismatch, changed owner/goal/map or expired curve | Reject continuity before unsafe evaluation |
| Fresh queued input at recovery boundary | Apply in original order, then query |
| Missing/old/future sensor input | Original fail-closed rejection |
| Physical topic absent from configuration | Exact parent behavior |
| Configured physical evidence missing, stale, malformed or unpaired | No admission grant |
| Cost-rejected central floor, real drop, obstacle or ambiguous neighbor | Remain rejected |
| Missing launcher qualification alias | Fail entry; preserve frozen version and startup evidence |

### Good, base and bad cases

Good: compatible refresh retains a freshly validated initial guess and extends
the endpoint and absolute expiry. Base: inactive-feature cold geometry is exact.
Bad: increasing trajectory IDs while endpoint/expiry stay fixed is not continuity.
Physical presence alone never grants central traversability.

### Required tests

Keep the inherited native/cache/warm/goal/backend checks plus actual pre-curve
DDS clock negatives, nine recovery-freshness checks, 23 physical-role checks and
30 native physical/source/callback/sequence checks. Test sequential accepted
curves for spatial and expiry extension through full PVA/dynamic/safety gates.
Use the runtime entry point's real qualification fields before physical launch;
a nested component report alone did not satisfy frozen v56's legacy reader.

### Wrong versus correct

Wrong: promote native replay success or a fast median to physical continuity or
30 Hz. Correct: separately report bounded physical recordings, full-round tails,
complete-window successful Hz, observed reserve, measured motion and pauses.
Preserve frozen v53's mixed-clock failure and v56's pre-physics schema failure;
their repairs have separate integer versions.

## v57 late-run diagnosis: validate the time of trajectory continuity

The post-70-second audit reproduces repeated final-goal A* searches before warm
initialization after the start–goal pair enters the fixed 100×100×100-cell search pool.
Native replay expands up to 615/691 nodes without reaching the goal region;
the geometric precheck correctly retains a search when bounds cannot disprove
eligibility. Do not equate its positive necessary condition with reachability.

Future continuity repairs must compare old/new PVA at the same actual handover
time. `planFromCurrentTraj()` samples the old curve before solving, while
`updateTrajInfo(..., node_->now())` assigns the later completion time; the
controller resets its curve execution time on receipt. Those function bodies
remain exact v48 bytes. The unchanged-input PVA test alone missed observed
late reference-position backsteps and about one meter of longitudinal tracking
error. Keep physical tracking error, raw command speed/cadence, and sampled-
state versus publication-time continuity as separate measurements. Preserve all
original dynamics, collision, goal and stop checks when designing a repair.

The executable diagnostic is
`audits/2026-10-02_v57_after70/phase_lag.py` in the Newton experiment. It matches
consecutive observed curve IDs to wall completion times, then checks geometric
agreement before measuring the handover step. Matching only by quantized ROS
time can select the next round sharing that timestamp. This is an analysis
finding and future test requirement, not a claim that the timing gap is fixed.

## v58 endpoint evidence and v59 trajectory epoch

### Scope and signatures

The post70 repair separates repeated failed goal search (v58) from trajectory
clock alignment (v59), with frozen v57 as the parent of v58. v49 is excluded.
`goalRegionMayFitWithEvidence(..., endpoint_may_fit)` enumerates the original
necessary plane/lattice endpoint superset. `GridMap::bodyEndpointMayBeObserved`
is an optimistic necessary predicate, not a free-space decision. The manager's
private `reboundReplanAttempt` accepts an optional sampled trajectory origin.

### Contracts

A clear native footprint requires both reflected cylinder centers to be admitted.
The v58 predicate searches an outward-rounded superset of their cell pairs at
the exact query Z. Any possibly observed pair, including occupied observations,
retains native search. Near-body masking or uncertain inputs retain eligibility.
All-unknown remote endpoint evidence can reject; never cache this result across
inputs. Zero-tolerance and non-plane search remain native. Positive evidence
never grants occupancy, support, a path, or final-goal acceptance.

For v59, a curve-derived initial PVA belongs to the old curve's sampled time.
Verify current curve layout/lifetime, compatible clock and exact sampled PVA
before preserving that epoch through warm, native and fixed-height attempts.
Keep every original optimization, PVA, dynamic and complete-curve safety gate.
An already elapsed candidate cannot be committed; this is trajectory validity,
not a wall-time solve deadline. Initial/odometry restarts retain their original
origin behavior. The controller consumes elapsed time once on receipt and keeps
the existing subsequent incremental/frozen clock, command and stop functions.

### Validation and errors

| Condition | Required behavior |
|---|---|
| Any possible exact or tolerance endpoint | Keep original native search |
| New observation, map movement or self-footprint possibility | Recompute; do not reuse a negative verdict |
| Replan from a checked current sampled curve | Retain that sample epoch, including graph fallback |
| Candidate lifetime elapsed before publication | Reject before committing; existing failure flow |
| Malformed incoming timestamp | Ignore before mutating the active controller curve |
| Emergency curve or matching cancellation | Preserve existing hold/cancellation behavior |

### Cases and required tests

v58 tests 3,000 arbitrary-yaw observed footprint pairs, changed evidence, body
waivers, exact/tolerance alternatives, original search modes and 20 recorded
states with alternating enabled/disabled calls. v59 uses the actual parent and
candidate controller at 0/40/80/600 ms delivery delay, then tests incremental
phase, heading freeze/resume, emergency, cancellation and malformed/future/late
timestamps. Delayed recorded-map warm and cold replans must retain the origin,
keep original hard PVA and pass all final gates. Compare old/new PVA at one
common handover time; later reoptimized geometry need not be identical.

Keep inherited native/cache/warm/goal/freshness/physical-floor/backend tests and
the actual launcher source/install/qualification/asset gate. Source or installed
hash verification alone does not establish physical tracking or 30 Hz.

### Evidence boundary

Good: the idle-host v58 paired goal-search maximum falls 44.614 → 0.259 ms with exact outcomes; v59 component timing/PVA checks pass. Both physical recordings complete, but successful planning is 27.53/26.43 Hz and v59 has a 1.099 s late pause during a 1.237 s cold-recovery round. Bad: promote these component passes or fast medians into sustained 30 Hz or uninterrupted navigation. Preserve the earlier host-load caveat and resource-preflight failure alongside the clean replay.

In v59 analysis, parse `V59_TRAJECTORY_EPOCH` for publication time. The curve's start timestamp now denotes its sample; treating it as publication would hide the timing issue. Observer nominal expiry and receipt are not the controller's exact paused execution clock.

Use the full recorded navigation pacing wall interval for successful/attempt rates and pause coverage, including the initial navigation wait. For latency and plots, include completed rounds inside that same interval; exclude nominal planner activity after recording ends. Preserve the legacy all-log metrics separately. State whether rolling frequency uses a wall-second window even when the horizontal axis is simulation time. A video HUD's attempt rate must not be labeled successful planning frequency.


## v59 cold-recovery diagnosis: retry identity and repair failure

### Scope and current signatures

`SCANReplanFSM::planFromCurrentTraj()` samples PVA once and calls `callReboundReplan()` repeatedly. `SCANPlannerManager::reboundReplan(...)` currently recomputes the optional sample origin on each call. `BsplineOptimizer::initControlPoints(...)` returns a vector that cannot distinguish no collision from failed constraint generation. These are observed failure seams; no new API or repair is implemented by this diagnostic note.

### Required contract and validation cases

| Condition | Required regression assertion |
|---|---|
| Old curve expires between retries but initial PVA is retained | Retain its known sample origin, or explicitly resample a new state; never relabel the same old PVA as newly sampled |
| Obstacle-repair search fails on unchanged inputs | Propagate a distinguishable failure; do not interpret an empty failed repair as valid no-collision initialization |
| Clear initializer becomes colliding during optimization | Existing complete-curve and dynamics gates still decide publication |
| New connector fails but accepted remainder is clear | Distinguish candidate-extension validity from remaining-curve validity; retaining a binding is not permission to skip fresh validation |
| Physical floor exists inside a drop exclusion | Keep the original guard; physical presence alone does not grant traversability |

### Evidence and tests

The executable audit is `audits/2026-10-03_v59_cold_recovery/`: `remote_probe.py`, `analyze.py`, and `remote_floor.py`. Fixed-input native replay repeats the same failed constraint search three times per ordinary/fixed-height attempt, although its initializer was clear. The original run's seven captured seeds retain PVA (position difference <=8.9e-16m), yet final publication rebases81.027099609s to82.286407471s after parent expiry81.440673195s. Add a chained-fallback test crossing expiry; a single80ms delayed replan does not cover this path. Recheck state and timestamp at the actual consumer boundary.

Good: explicit sample-state identity through every retry and explicit repair failure, with unchanged final gates. Base: existing single-success timing checks still pass. Bad: call sampled=0 a fresh odometry restart without checking where its PVA came from. Wrong: remove the drop guard to make the connector pass. Correct: produce a connector with feasible footprint headings under that same guard.

## Checked epoch across the complete retry chain (2026-10-04)

The v59 81-second audit showed that unchanged sampled PVA was relabeled after its parent expired between FSM retries. Capture the checked sample epoch once at the same boundary that samples PVA; pass the stack-owned value through every initialization/prefix/ordinary/fixed-height attempt. Parent expiry later in the synchronous round does not make retained PVA a fresh measurement. Derivation for ordinary callers and elapsed-candidate rejection remain. Future or incompatible explicit epochs must be rejected. Refactoring residual checks must retain rejection of nonfinite derived values; replacing a positive <= condition by > is not equivalent for NaN.

Frozen v62's Mac retry regression reproduces parent rebasing by1.259307862s and verifies zero rebasing through eight actual FSM/manager calls, new-round independence, ordinary caller behavior and invalid-clock/numeric cases. It uses scripted target/solver boundaries and is not latency or physical continuity acceptance. Eight-package build and inherited Mac/recorded warm/PVA/controller/stop checks pass. Full original recorded-corner/freshness/physical-native and simulation qualification remain pending; v48 stays the reference.

## Failed optimizer constraint repair (2026-10-04)

A returned path vector alone cannot distinguish no collision from failed initialization; both can be empty, and a later failed segment can return partial paths. The v63 optional ControlPointInitializationStatus is Success for the original no-collision case, SearchFailure for the existing AStar error return, and InvalidSearchPath for the existing short-path return. Only rebound_optimize's already-colliding repair branch consumes it to return its original unsuccessful result instead of repeating optimization without useful new constraints. Successful initialization keeps the parent restart/weight schedule. This is error propagation, not a timer, safety waiver or failed-map cache. The outer native fallback, fixed-height/prefix chain and original stop protocol remain.

Actual optimizer/LBFGS regressions with scripted occupancy/search verify failed repair count3->1 and preserved success/failure and boundary controls in both height modes. Real native map/search remain in the separate inherited recorded fixtures. Frozen v63's Mac build and available suites pass; original remote corner and physics/latency/30Hz acceptance remain pending. Do not report scripted-search timings as GPU tail-latency evidence.


## Map-processing timing and replay boundary (2026-10-05)

A planning round's input scope accumulates every synchronous freshness drain.
Record its sites and distinct scan counts before interpreting it as one expensive
map update. Cloud scopes contain sliding checks; function call counts are not
actual map shifts. Empty drains do not replay a scan. Measure conversion, terrain
classification, ray traversal, occupancy fusion/inflation and outgoing-cell reset
separately, plus real shifts, processed voxels and inflation neighbor visits.

The v76 original976.721ms input scope has12refreshes/7scans and941.490msCPU.
Frozen observation-onlyv78 finds926,950voxel fusions/25,175,190inflation offset
visits and3actualslides across the seven selected scans. Six final buffer/history
digests match the unmodified map. This component hash is not full planner/PVA/
safety/continuity acceptance. The idle266.600–312.992ms batch does not reproduce
the original live multiplier; never report that difference as an optimization.

For future changes, preserve full semantic history, free-space evidence, native
inflation, support/freshness and every final gate. Compare map state and collision
verdicts at each actual decision boundary, not just the final hash. Native DDS
batching/map/cache/planner context and live load require their own trace when
the original delay is larger than an isolated replay.

## Nav2 controller-owned native validation (v114, 2026-10-08)

A periodic safety callback on the planning work group can expire during a solve
even when the completed map remains fresh. Never repair that by extending the
100 ms proof/body or250 ms observation limits, stamping receipt time, or treating
planner liveness as collision evidence. The Nav2 controller may run the same native
full remaining-curve checker at its own command decision, bound to the exact
executing owner/trajectory and actual tracker phase.

Concurrent queries require an immutable native map revision, separate query caches
and original controller pose/clock. Do not adopt that revision into the planner's
mutable read pointer from another thread. Pin publication during validation;
query-view destruction must not stop/join the map writer. Share only atomic writer
health. Native diagnostic static sets/throttles must not be touched by the parallel
query. Preserve native emergency/negative proof/cancel paths. Recheck the original
body timestamp at command publication, including time spent validating after the
compute call starts; a fresh ticket cannot renew old body data.

Evidence is v114/query_view_probe.cpp and scan_nav2_controller tests: actual map
query parity and unchanged hashes; distinct controller/native clocks; bad/future/
stale body and stale observation rejection; writer fault visibility, publication
pinning and actual writer continuation; body expiry between compute and publish.
v114 reaches the original goal and measured stop once, with two protected retries.
This does not establish repeated-run reliability or sustained30Hz/continuity.

## Reference-path retry ownership experiment (v126, 2026-10-10)

Scope: `SCANReplanFSM::planFromCurrentTraj()` in REFERENCE_PATH mode only.
`callReboundReplan(false, false, &reference_prefix_budget, t_cur, retry_origin)`
owns one full chain with three shorter-target proposals. Manager recovery still
tries warm/cold and fixed-height modes. Both legacy polynomial/random flags are
unused in the current graph initializer; v126 removes the two outer replays.
Other FSM modes, initial planning and all safety/stop thresholds remain unchanged.

| Condition | Contract |
|---|---|
| First or inner recovery attempt succeeds | Preserve original result and publication gates |
| Full chain fails | Return false to the existing FSM/safety owner; invalidate feasible window |
| Prior accepted curve exists during failure | Do not replace it with a fabricated success or retimestamp its PVA |
| Next scheduled round | May retry fresh input; do not reuse a failed-result cache |
| Map changes during the removed replay interval | No same-callback equivalence promise; require physical comparison |

Required tests compile the actual FSM/manager retry code with only target and
individual solver seams scripted. Check first success, warm-to-cold, fixed-height,
shorter-target recovery, graph/optimizer exhaustion, retained PVA/epoch, restored
height mode and fresh next-round recovery. v126's controlled exhaustion is6->4
and12->8attempts. Scripted publication is not collision/dynamics acceptance; the
separate real recorded-map native test must verify successful curve identity,
exact publication proof and stale-input rejection. Runtime results and keep/park
belong in `audits/2026-10-10_mppi_step2/REPORT.md`, not inferred from these counts.

Good: bound ownership while retaining distinct recovery modes. Base: first
success returns immediately. Bad: remove fixed-height or shorter-target recovery
to make a timing number smaller. Wrong: claim every retry sees identical inputs
because its flags are unused. Correct: acknowledge asynchronous map evolution
and compare independently initialized runs on the same host.

## Bounded reference-prefix depth at a supported turn (v147)

The original-startv144 failure stops safely at a heading-dependent support
boundary. Its actual measured heading is clear; a longer reference-window
heading places the front footprint in a cell without the current floor layer.
This does not justify lowering support gates or waiving occupied/unknown cells.

`SCANReplanFSM::callReboundReplan(..., int *reference_prefix_budget, ...)`
retains the existing halving search and shared per-round ownership. v147 uses
`kReferencePrefixProposalBudget=6` in both `planFromCurrentTraj` and the default
standalone call, replacing the two former3proposal caps. Count rejected target
proposals too. Every accepted shorter target still runs the complete manager
with original start PVA, zero terminal velocity, original reference/goal,
support/collision/dynamics/epoch/freshness and publication checks. Successful
normal planning returns immediately without consuming the extra proposals.

Required regression: reconstruct the actual435published-scan prefix, due torso
pose and generation6reference. Invoke the installed production default method,
not only a scripted budget seam. Oldv139 rejects; newv147 accepts a1.24s
shorter translation under unchanged boundary PVA/dynamics and126full-curve
samples. Require identical native map digest and captured input identities.
Ordered replay is distinct from original asynchronous scheduling and full
physical-route success. Native38component tests and original-route host/graph
checks remain required; runtime results belong in the full-route audit.
