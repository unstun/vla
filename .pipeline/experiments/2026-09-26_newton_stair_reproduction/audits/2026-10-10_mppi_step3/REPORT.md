# MPPI adaptation 3: independent native trajectory validation

Stage: experiment + analysis. Decision: **park v127 after physical failure; retain native v122 / host v125**.
The declared early-stop rule applies. No second pair or adaptations 4–5 ran.
Native parent v122, host parent v125, candidate v127. Step 2's v126 remains
parked and is not an ancestor of the new native or host snapshot. Compilation,
component execution, CPU Newton simulation and full-data analysis run on
**gpu5070ti**; local source/configuration and returned evidence are authoritative.

## Change

`NativeTrajectoryValidator` provides independent boundary-PVA, sampled velocity/
acceleration, native map collision and publication-epoch checks. It returns
explicit validation failure or the existing full-curve collision report.
The manager, FSM safety check and Nav2 controller consume this shared interface.
The interface is stateless: original owners retain map refresh ordering, source
clocks, publication/query leases, failure recovery, command binding and stopping.
Existing primitive checks and arithmetic are retained. There is no new 2D
collision approximation, hard timeout, retry reduction or safety threshold.

Candidate checks and executing-remainder checks deliberately use separate entry
points. A remaining trajectory must retain its actual phase and cannot be
rechecked against a new candidate start boundary or a rebased epoch. Existing
kinematic validation still precedes final map refresh; publication epoch is
still checked after collision work. Minimum-cruise repair stays in the planner.

This takes the separation between optimization and validation from the locally
inspected Nav2 MPPI optimizer at bcc9c48cf468588559d01942b72d511a6b990891. It is
an independent native validation interface, not a copy of its modern ROS plugin
or planar implementation. Runtime validator replacement and soft objective
plugins are outside this increment.

## Component results

14 packages compile, and all 36 original plugin component tests pass remotely.
The actual v122 and v127 executables agree on all 341 PVA/dynamics/epoch cases
and 35 real-map collision cases, including rejection metadata and sample counts.
Successful native control points, knots and duration are bit-identical. Separate
publication/stale-input and controller snapshot/clock/pose/map-fault/publication-
pin tests pass on both installs. Tested curve and map state remain unchanged.
The candidate's real ten-child ROS graph starts, and source/variant/image and
host/container writer-ownership checks pass. See `component/contracts/result.json`.

The first fixture build omitted one header; the second baseline run passed but
its merged stdout verdict fragments interleaved with ROS diagnostic lines. The
final fixture writes explicit separate JSONL records, identical by SHA-256 across
arms. Native implementation and binaries did not change during these test-only
repairs. Both attempts remain recorded in `early_attempts.json`.

## Declared evidence and decision boundary

See `../../versions/v127/PLAN.md`, written before implementation and execution.
Require parent/candidate fixed-input verdict and successful-curve equivalence,
original safety/proof regressions, full component build, then up to two separate
same-host original-corner pairs. Keep only with two candidate arrivals/holds,
no falls, median P95 <=1.10x baseline and median longest pause <=baseline+1 s.
A candidate navigation failure can stop early and parks this version. This is a
modularity/testability change; faster navigation is not an expected claim.
One or two trials cannot establish population reliability or Jetson readiness.

## Physical results and direct failure evidence

One same-host pair completed with verified copyback/retention and no falls.
The native interface passed all fixed-input comparisons, but the candidate did
not satisfy the separate navigation gate. No causal regression is established
by this single asynchronously executed pair.

| Metric | Native v122 baseline | Native v127 candidate |
|---|---:|---:|
| Arrival and measured PD hold | Passed | Failed |
| Measured path | 26.417 m | 23.793 m |
| Simulation end, including startup | 64.556 s | 58.759 s |
| Completed / successful rounds | 1013 / 996 | 918 / 913 |
| Failed rounds | 17 | 5 |
| Mean / P95 solve | 2.910 / 7.891 ms | 3.342 / 4.139 ms |
| P99 / maximum solve | 23.186 / 137.096 ms | 25.338 / 234.655 ms |
| >60 ms rounds (successful / failed) | 4 (3 / 1) | 7 (4 / 3) |
| Longest measured low-speed interval | 9.795 s | 10.094 s |
| Emergency transitions | 7 | 10 |
| Actual real-time factor | 0.999979 | 0.999978 |

The baseline also pauses before eventual arrival. Its successful completion in
this pair is not evidence of general stability. The candidate has fewer failed
planning rounds and a lower P95, yet fails the mission: neither measure can
replace arrival and measured hold.

The candidate's original log (`postmortem.json`) records a recovered startup
`scan_trajectory_missing` at trajectory 0. Later, at simulation time 44.067409515 s,
controller validation sees observation time 43.807552338 s: age 0.259857177 s exceeds
the unchanged 0.25 s rule and emits `scan_safety_evidence_stale`. Subsequent
recovery ends with `Failed to make progress` and `Navigation failed`. This is
not the same terminal ordering as step 2, and no final missing-trajectory event
is inferred from that earlier experiment.

The maximum 234.655 ms round is an earlier event at simulation time 31.114528656 s,
with 7 solver attempts and a final native seed-search rejection on a fresh
observation. It is not itself the later stale-evidence or progress-check abort.
All 918 completed candidate rounds have matching diagnostic classification.

Apply the predeclared candidate-failure early stop: keep the frozen implementation
and test evidence but do not select v127 for the next adaptation. Fixed-input
verdict/curve equivalence is demonstrated; the complete physical keep criterion
is not. Retain native v122 / host v125. A controlled replay of the divergence,
including sensor/map timing, would be needed to attribute the physical difference
to this extraction. That investigation and adaptations 4–5 are not executed here.

## Scope and workflow closeout

Source ancestry and the original retry functions were checked against v122;
none of v126 is in v127's frozen source ancestry. No safety threshold, robot
command path or optimizer is changed. The broader v48 reference and main task
remain in progress. Source/results remain local and reviewable; no commit or
archive of the incomplete main task was attempted because the pre-existing
`.git/index.lock` remains present and was explicitly preserved.

## Reproduction and storage

`versions/v127/build_remote.py` composes a separate 647-file export from the
verified v122 source and overlays only the four recorded native paths.
Original v122 install remains `/data/sun/vla_mppi_20261009/candidate/install`;
v127 is `/data/sun/vla_mppi_20261009/step3_v127/install`. All 14 packages are
rebuilt, including dependencies affected by the new header. A frozen host source,
qualified native receipts and identical Foxy image are required before physics.

`versions/v127/contract/run_remote.py --attempt N` runs the component comparisons.
`versions/v127/run_comparison.py --variant {baseline,candidate} --attempt N`
runs one bounded physical trial and analyzes its closed capture. Run these on the
execution copy with `/home/sun/vla_exec/envs/newton_worker/bin/python` (the build
wrapper also works with system Python). Original CPU solver, geometry, startup,
sensors and safety timers are preserved. Raw/build data stay on gpu5070ti; return
only compact results, CSV and SHA-256 locators. Keep failed attempts. Steps 4–5
are not executed; broader v48 reference/main acceptance remain unchanged.

Final verification: 40 returned files / 1,621,194 bytes match server hashes and sizes. All 2,840 frozen source/snapshot pairs and 618 inputs remain exact, and both native installs were rechecked. Owned trial processes/containers are closed. Raw trial bytes retained remotely: v127_baseline_attempt01=207,059,747, v127_candidate_attempt01=185,867,323. See `closeout_manifest.json` and `final_verification.json`.
