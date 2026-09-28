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

The mandatory native graph initializer owns the seed. Do not execute a legacy
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
