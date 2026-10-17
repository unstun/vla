---
origin: ai_only
reviewed: false
date: 2026-09-26
---

# SCAN stair repair handoff

Stage: experiment + analysis. Task: `09-23-scan-reactive-stair-pedestrian`,
still `in_progress`. Dr Sun reported that gpu5070ti was powered off and asked
to archive. Remote retries stopped. No new simulation is running from this
handoff, and no automatic restart or scheduled follow-up was created.

> [未门控] The current inline instruction requires the main session to implement
> and check directly. No archive subagent or external Codex quality-gate process
> was launched. Source, result, identity and archive checks are recorded locally;
> this is not an independent archival PASS.

## Exact stopping point

`scan_33` is materialized, independently reviewed, tested and fully compiled.
Its 15 native source-method cases pass on local clang and pinned Foxy g++.
The corresponding old `scan_32` fixture has 12 predeclared failures and three
positive cases. All 93 regenerated source files match the candidate; only the
FSM `.cpp` and `.h` differ from scan32. Full Foxy build took 80.644 s, with
matching source hashes before and after.

**No scan33 install identity, real-optimizer replay, accepted curve or live
video exists.** Two install-identity capture attempts failed with SSH exit 255,
`Connection closed by 23.252.106.36 port 60023`. Their originals are preserved
in `builds/scan_33/install_identity_failed_v1/` and `install_identity_failed_v2/`.
The user then supplied the shutdown explanation; host power was not independently
measured. The next remote step is install identity capture, not another build.

## Current evidence

All repair paths below are relative to
`../experiments/2026-09-23_scan_reactive_stair/runtime_integration/repairs/2026-09-26_sequential/`.

| Candidate | Behavioral change | Confirmed outcome |
|---|---|---|
| scan28 / step12–13 | Hard cubic boundary PVA, native-feasibility timing; recorded body/world twist corrected | Old recorded input produces one accepted 93.223 s curve. Fresh live video still stands, with no navigation command. |
| scan29 / step14–15 | After strict search exhaustion, consider longer fully checked terminal edges within the original acceptance time budget | Fresh input now yields 63 checked seeds; zero moving curves. Final complete-curve check rejects the first spline at 46.347717 s. Twelve native cases pass. |
| scan30 / step16–17 | Optimizer uses the same complete sampled-curve acceptance check as manager | Seven two-stage native groups pass. Fresh input: 56 checked seeds, zero moving curves; 168 retries have zero valid paired directions. |
| scan31 / step18–19 | Actual collision-repair searches retain exact control endpoints | Sixteen native groups pass. Fresh input: 45 checked seeds, constraints grow 0→3→6, then no-valid-direction stop; zero moving curves. |
| scan32 / step20–21 | When the original plane finder finds no finite intersection, try individually checked nearest points on the matching repair route | Twenty-one native groups pass. Real map gives six clear anchors and six pairs, but original 21-rebound bound is reached; 40 checked seeds, zero moving curves. |
| scan33 / step22 | Preserve the full reference goal/duration; commit actual local time only after full success; consider up to three shorter stopping prefixes per round | Fifteen native cases, source parity, independent code review and full build pass. Real optimizer and live tests not run. |

The old corrected-input replay still produces exactly the same controls and
knots in scan29, scan30, scan31 and scan32 as in scan28. Callback counts in the
table are descriptive; slowed replay is not a timing or success-rate benchmark.

## Why the fresh curve is still unavailable

1. A checked polyline does not ensure that its fitted curve is clear. Step16
   same-time position/yaw comparisons identify WrongHeight and UnknownSupport
   at the actual continuous-curve heading; tiny geometric differences matter.
2. The old optimizer could accept a curve that its coarser check missed.
   Complete checking now rejects it inside optimization too, but useful repair
   directions were initially missing. Exact repair endpoints and guarded route
   projections restore directions without establishing convergence.
3. Step20 captured the failed optimizer's actual returned trial: it remains
   colliding. Seven interior control planes have no intersection with the
   observed two-node repair route. LBFGS cancellation rolls its local vector
   back, while this wrapper returns the last callback controls; the diagnostic
   trial must not be described as solver-accepted.
4. The live sensor-origin Unknown issue remains separate and unresolved.
   Recorded full-history maps can know a cell that the live start misses.
   No origin-cell free exemption was introduced.

Step22 tests a planning-policy change: primary1 → up to three prefix proposals
→ primary2 → primary3. The three prefix proposals share one outer budget,
including endpoint rejections. They retain the same start PVA, request zero
terminal velocity, and pass through the complete manager. The point-free
frontier is not a reachability proof. A zero terminal-velocity request is not
evidence of physical stopping. No Unknown, collision, support-height, dynamics,
optimizer iteration or final acceptance threshold was relaxed.

## Resume after Dr Sun asks to continue

Local source of truth:
`/Users/sun/tongbu/study/phdproject/vla`. Remote is an execution copy only.
Earlier bounded gpu5070ti authorization remains recorded; the current archive
request stops execution until continuation. No sibling repository writes.

1. Check the configured `gpu5070ti` alias and actual host after it is powered
   on. Historical `gpu5070ti-relay` is no longer a configured alias on this Mac.
2. Recheck local scan33 source hashes against `source_sha256.json`. Run the
   existing `p2b_execution/capture_install_identity.py scan_33`. Failed v1/v2
   captures have been moved intact to attempt directories, so the normal
   output-absent precondition is ready for the next attempt. Do not overwrite
   `build_result.json` or repeat the successful build.
3. Use `repairs/2026-09-26_sequential/run_candidate_replay.py` with
   `--build scan_33 --step step22_reference_prefix`, first
   `--run-id scan33_new_live_prefix_v1 --inputs .../step14_live_input_gap/scan28_live_inputs`,
   then `--run-id scan33_old_input_regression_v1 --inputs .../step13_replay_twist/body_reference_030_twist_fixed_inputs`.
   These are proposed unused names, not completed runs. The existing driver
   applies source/install gates, fixed Foxy image, network isolation, a 90 s
   bound and local artifact collection.
4. Check complete native acceptance, actual start/end PVA, committed target time,
   full global duration, route identity and received curve. Compare the old
   positive controls/knots. If no complete curve passes, diagnose the observed
   failure before another behavior change.
5. Only after a meaningful accepted curve, use the existing bounded right-person
   Isaac recipe with the exact accepted source/install identities and an idle
   GPU preflight. Inspect actual movement, contact, remaining-curve checks and
   timing. Record and deliver the real video. A recording of standing remains
   a failed-navigation result.

The canonical generator is
`../experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair/materialize_scan_33.py`.
The step22 contract, fixture, results and FSM diff are in
`../experiments/2026-09-23_scan_reactive_stair/runtime_integration/repairs/2026-09-26_sequential/step22_reference_prefix/`.

## Local continuation option

The Mac is Apple M5, 32 GB, Darwin arm64. Native algorithm/FSM tests already run
locally. A MuJoCo physics path is feasible in principle, with existing VLA Lite3
MuJoCo adapter source as a starting point, but no local MuJoCo installation was
found in the two inspected interpreters. Porting the full ROS planner replay,
scene, policy and sensors requires separate setup and verification. It is not a
ready substitute for the Isaac 5.1 RTX sensor / official animated-human trial.
See [local capability check](2026-09-26_scan_stair_archive/LOCAL_SIMULATION.md).
No simulator was installed or launched in response to the capability question.

## Video and archive

Latest real video is a regular local file:
`../../output/2026-09-26_stair_human/stair_scan28_right_live_no_navigation.mp4`.
It contains 364 frames, 29.12 video seconds; the simulator ran 29.08 s.
Zero moving curves and zero motion commands: **standing, not stair success**.
SHA-256: `84f66b834e63dde4bd1921b8cdce5014e5501b01808d8006d9274962f8a86f02`.

[Archive state and validation](2026-09-26_scan_stair_archive/ARCHIVE_STATE.json),
[archive report](2026-09-26_scan_stair_archive/REPORT.md), and
[artifact hash inventory](2026-09-26_scan_stair_archive/ARTIFACTS.sha256.json)
preserve the stopping point. Project hot-zone originals were copied before
refresh. No raw conversation export, deletion, staging, commit or push was
performed; the existing dirty worktree and unrelated work remain intact.
