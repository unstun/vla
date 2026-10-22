# Local terrain search and tracking phase

## 1. Scope / trigger
v285 is a user-authorized candidate from immutable v284. Native qualification is recorded separately from the complete offline and physical acceptance. Keep 0.35 m hard radius, 0.1 s scan period/deadline, ENV225, factory control and static global route ownership. Consult the version report before promoting any behavior.

## 2. Signatures
- `bool GridMap::hasTerrainSupport() const`
- `bool GridMap::terrainSupportHeight(const Eigen::Vector3d &near, double &body_z)`
- `ASTAR_RET AStar::AstarSearch(double step, Vector3d start, Vector3d end, bool exact_endpoint, double goal_tolerance)`
- Existing `TrackingNode::cmdCallback()` and `SCANReplanFSM::planFromCurrentTraj()` signatures remain unchanged.

## 3. Contracts
`GridMap::terrainSupportHeight(near, body_z)` associates the nearest raw layer at the same XY inside the existing 0.26 m stair association bound, then requires matching selected scored elevation. Never skip an unsupported nearest layer for a farther floor. Respect the existing real support-gap mask. The returned elevation is a search proposal, not collision permission.

Non-exact local `AStar::AstarSearch` uses available support layers instead of a chord plane. XY endpoint proposals are finite, remain on support and use actual connector tangents. A zero-length endpoint has no chord orientation; any legal local heading can initialize it, but actual edges retain full collision checks. Store exact support elevations separately from voxel indices and never mutate a reached node's geometry. Exact endpoint mode retains its earlier contract; no terrain input retains the legacy search representation.

Tracker travel translation and phase use one positive smooth heading scale, from 1 to 0.2 across the existing heading thresholds. Preserve coupled translation/yaw, original terminal-only final alignment, slew and emergency/cancel ownership. A reference-mode FSM prediction can seed replanning only when within 0.15 m of odometry and unoccupied under the existing trajectory-tangent query. Otherwise use measured P/V, zero initial acceleration and invalidate the inconsistent warm seed. This does not change the retained global route.

The v284 added `repulsionCost` and `sourceSolidCostGradient` are removed in v285. Hard source assessment and ENV225 remain unchanged. Do not restore a local publication veto or a half-cell forced reset through this contract.

## 4. Validation and error matrix
| Case | Required result |
|---|---|
| Supported hill with equal-height endpoints | Bidirectional search follows each actual tread height |
| Stair corner with local endpoint tangents unlike the chord | No unbounded 3D retreat or false pool exhaustion |
| Nearest unsupported layer / true gap / live obstacle | Keep original refusal |
| Same voxel reached through another candidate | Its previously checked exact height stays fixed |
| Large travel heading error | Positive coupled translation and proportionally slower phase |
| Prediction >0.15 m away or occupied | Measured local seed; keep global owner |
| Original final XY/Z capture or emergency/cancel | Existing terminal yaw/stop contract |

## 5. Good / base / bad cases
Good: a supported corner follows legal adjacent layers and enters using its local tangent. Base: preserve the exact endpoint and no-terrain contracts. Bad: keep stepping away on a 3D chord, change a reached node's height, or infer physical success from a safe curve.

## 6. Required tests and assertion points
Use actual native GridMap/AStar and ROS-clock tracker tests, not a mirror implementation. v285 qualification records 174 native test executions, parent 0/4 versus candidate 4/4 hill/corner directions, a real pool-exhaustion parent contrast and preserved unsupported refusal. The ten unscored initial planners are development checks, not physical trials. Complete frozen 50+3 with median <=1.5 s and legal >=96% before the same ten physical attempts once. Compare errors using identical per-line counters, separating retries/mentions from terminal failures.

## 7. Wrong versus correct
Wrong: reconstruct scaled tracker phase as wall time and call the difference measured runaway. Correct: test the actual native phase and distinguish actual FSM fallback telemetry from nominal elapsed-curve diagnostics.

Wrong: infer collision-free completion from a clear failed prefix, zero command, safe reference or optimizer success. Correct: report actual arrival/PD, sampled physical support/source/raw margins, starvation and scanner results independently. Preserve frozen source, startup failures and failed trials without a success retry.

## 8. Closed v285 evidence and remaining boundary

The complete scored cohort passes 49/50 legal routes and rejects 3/3 illegal controls; admitted global median is 1.346993 s (all50 legal calls: 1.359352 s). All50 legal starts pass their unchanged extra margins. Ten physical routes run once: six reach goal/PD, five also pass sampled support/source/raw geometry over the entire recording. CD12 still crosses source solids by 0.018423 m; A04/G05/CU06/CM02 fail. Thus component qualification is not physical acceptance. See the version's full results and failure bill before reusing its mechanisms.

Identical literal log extraction gives pool mentions 90→23 and no-executable mentions 54→20, but A-star failures 44→279 and -1008 mentions 664→4915. These are retry-inclusive mentions, not independent crashes. Removal of the source cost did not remove the remaining optimizer failures. `The robot is inside an obstacle` is emitted while searching backward through occupied control points in `check_collision_and_rebound`; it is not itself a measured-trunk collision or proof of a runaway initial seed. Preserve first-error contexts and measure phase/seed behavior directly.


## 9. v286 supported-air and refinement contract (native-qualified)

### 1. Scope / trigger
This candidate supersedes the v285 local unknown-air, quantized endpoint, refinement-objective and heading-floor behavior. It does not promote a physical baseline. Native qualification passed; full offline and physical acceptance remain separate in the v286 report.

### 2. Signatures
- `GridMap::reactiveOccupancy(point, body_reference, typed)` retains its signature and 0/1 return.
- `GridMap::hasReboundEnvironmentalField() const` and `GridMap::reboundEnvironmentalCostGradient(p, yaw, gradient) const` are local rebound helpers.
- Private `AStar::ConvertToIndexAndAdjustStartEndPoints(start, end, start_idx, end_idx, goal_tolerance=0)` accepts the existing goal-region tolerance.
- `SCANPlannerManager::findGoalNeighborhoodPath(start, goal, tolerance)` retains its external signature.

### 3. Contracts
Unknown-air normalization requires in-map, zero inflation, a complete passing support/edge/layer/freshness decision and an exact source-solid free assessment. Keep original obstacle provenance. Each query shell owns its existing-format source proof cache; never share mutable query cache state. Do not enlarge the thin measured-trunk waiver.

A quantization residual is not a physical path tangent. At projected support height, check an actual adjacent support edge. For positive tolerance with terrain support, target-neighborhood search uses non-exact terrain expansion and returns a reached point inside the original 3D tolerance. Out-of-map remote goals use the existing retained-reference frontier. Strict exact and no-terrain search contracts remain.

Rebound scores unchanged ENV225 plus exact-source `max(0,(0.055-margin)/0.055)^4`. Its gradient is the analytic source gradient through the existing environmental spline sampler. The hard source radius stays 0.35 m. Refinement scores smoothness, fitness and feasibility, followed by original collision review; no environmental term is added there or to GPMP. Both travel translation and phase use `0.5 + 0.5*(1-smoothstep(u))`, with original 0.6/1.0 rad transition, terminal/slew limits and measured-seed fallback unchanged.

### 4. Validation / error matrix
| Query | Required result |
|---|---|
| Supported unknown uninflated air outside trunk waiver | Free only when source geometry and all evidence checks pass |
| Inflated/observed hit, missing support, true gap, stale input, outside map | Preserve refusal |
| Quantized endpoint near wall or stair | Test projected support and real adjacent tangent |
| Occupied goal center with reachable neighborhood | Terrain-search a reached point inside unchanged tolerance |
| Refinement environmental weight toggle | Same refinement value and gradient |
| Source margin 0.03 m / beyond 0.055 m | Positive rebound repulsion / zero added cost |
| Large heading error | Positive travel and proportional phase, floor 0.5 |

### 5. Good / base / bad
Good: unknown supported air can pass without modifying raw obstacle data. Base: real observed obstacles and support gaps retain original hard decisions. Bad: treating an unobserved voxel as a real collision, using quantization noise for yaw, or suppressing all obstacles to fix unknown air.

### 6. Required tests
The actual native 13-check repair probe fails six checks on immutable v285 and passes13/13 on v286; seven negative/control checks remain passing. Inherited174 test executions, four terrain directions, four translated/rotated clock cases and ten unscored initial planners pass. Test individual-control and rigid-translation numerical gradients. Preserve the failed development assertion receipt separately from scored calls. Require the complete53-case gate and ten single attempts for physical conclusions.

### 7. Wrong versus correct
Wrong: require one control point's Y gradient to point away from a wall; that control also changes heading. Correct: compare analytic/numerical derivatives and check repulsion under a rigid translation of the whole spline.

Wrong: call all reactive refusals unknown air. Correct: count `(verdict,voxel)` pairs in the original logs with the same extractor across versions; candidate-query warnings are not measured-body collisions.

## 11. v287 bounded local costs and native signal evidence

v287 removes the v286 exact-source rebound cost helpers and supported-air source query/cache. Local rebound uses the existing precomputed ENV225 value/gradient; refinement still excludes environmental terms. The source hard field remains in static/global admission and the independent measured-pose audit. Do not put unbounded mesh searches back into iterative local objectives or publication gates.

Both ENV225 value paths use max((target-margin)/target,0), and edge/solid gradients apply below target even at nonpositive margin. The quadratic hinge has a continuous escape derivative through zero. Native tests must check negative, zero and positive margins with finite differences for both edge and solid channels. Preserve the atlas/input format and hard0.35m profile.

Supported unknown-air normalization is a full support/layer/edge/freshness decision on an in-map, uninflated point. Preserve raw-unknown-before-inflation/contributor classification; inflation must not be inferred from a verdict6/voxel0 log pair. Keep real obstacle, unsupported, stale and out-of-map controls. No thin-trunk waiver expansion.

Check A-star start/end and neighbor pool indices at actual access, including the positive-tolerance terrain path that skips terminal adjustment. Parent Coord2Index already has all-axis allocation checks; a new access guard is not proof of the old crash cause. Test actual terminal-border/out-of-pool searches, not just a mirrored bounds predicate.

A complete clean14-package build is required when GridMap/state layouts change. Audit actual compile_commands and header resolution. The affected local packages use C++17; the inherited PCT core uses O2/C++14. Do not infer alignment failure from a missing macro, or describe all packages as identically compiled. Native allocation checks and real signal stacks are separate evidence.

The task-owned native debugger preserves fatal signal exit semantics and captures every thread's symbolized frames/registers; five zero-physics signal injections qualify that mechanism. Python children enable faulthandler. GDB g1 line symbols do not retain all local variables. Retain original and application-only error counters when debugger output could contain error literals. A fatal diagnostic stop and debugger startup can affect wall timing; report actual RTF and original clocks without retiming evidence.

The53-case gate passes49/50 legal and3/3 illegal, with admitted median1.376954s; all53 independent audits and all50 starts pass. Physical acceptance is separate: actual A04/CU06 SIGSEGVs fault in different GridMap cache lookups, while CM02 reports allocator double-free/corruption during A-star queue growth. These are fault sites, not a proven first invalid write/free or race. Snapshot query views are separate and native work callbacks are mutually exclusive; require a real concurrent/captured-input/sanitizer repro before declaring the root cause. Frozen v287 remains unchanged through its ten once-only physical attempts.

Report optimizer stage latency separately from complete local rounds. A2ms optimizer or0.2microsecond table query does not establish a<50ms full round, fresh data throughout a search, successful arrival, or clear measured geometry. Keep0.35m/0.1s unchanged and retain all failed prefixes/videos.


### Closed v287 physical boundary
All ten once-only attempts and videos are complete. Arrival/PD6/10, full recorded geometry plus arrival4/10. Inside-obstacle/no-executable mentions fall859→0 and51→9, but endpoint/A-star/-1008 rise0→27,6→25 and84→674. All5287 scans meet100ms. Common optimization-stage medians are a few milliseconds; tails remain, so do not declare every local optimization<50ms.

D07/CD12 first source-solid crossings occur under actual terminal pure-yaw commands, about0.125/0.107m from the requested goal. CD12's worst sample is later in STAND_TRANSITION. Compare first and worst crossings separately; a later zero-command stance does not prove where the incident began. Latest published curve geometry at planned heading can be clear while measured body heading crosses the envelope. Preserve measured pose, command/stance, curve age and nearest-spatial-point evidence without reconstructing the scaled tracker phase. See the complete v287 report and boundary_state/witness audits. Three native heap/container faults remain; version repair is not accepted.
