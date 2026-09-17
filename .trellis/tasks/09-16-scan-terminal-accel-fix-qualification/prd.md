# Qualify the SCAN terminal-acceleration fix

## Goal

Decide with evidence whether the one-line SCAN fix can become the accepted SCAN build for the native
PCT -> SCAN -> Lite3 V12 navigation base. Stage: experiment + analysis. Parent:
`09-16-emos-harnessvln-reimplementation`.

## Background

- Defect (frozen `scan_03`, `src/plan_manage/src/planner_manager.cpp:171`): polynomial initialization supplies the
  acceleration at the last sample before the polynomial end, `evaluateAcc(t)`, as the terminal acceleration. At the
  failed resume pose this is 1.778 m/s^2 instead of about 0. Refinement keeps it, and the unchanged 1.5 m/s^2 gate
  rejects every candidate. No spline reaches the controller, so the backend raises `initial_heartbeat_missing` and
  stops the robot. It is a replan rejection, not a collision.
- The file's hash equals the pinned PCT-SCAN-ROS2 base (`1cf45a1c`); the defect was not verified against an
  unmodified official build.
- Candidate: `evaluateAcc(time)` (true end). Native replay, empty grid, seed 0, polynomial init: original 9/12,
  candidate 12/12. The refined candidate ends 2.7-3.6 cm from the target; the original ends 1.6-2.0 cm away.
- Isaac: `actual4` passed once (braked stop x = -1.091, terminal acceleration 1.478, just under the gate). Three later
  runs stopped at x = -1.130, -1.149 and -1.142 and failed at resubmission. Only the last was replayed natively.
- Evidence: `.pipeline/handoffs/2026-09-16_harnessvln_local_archive.md`,
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/RESULT.md`.

## Decisions

- D1 (Dr Sun, 2026-09-16) Foundation first: qualify this fix before Pi/Cortex work continues.
- D2 (Dr Sun, 2026-09-16) Separate child task. Nothing runs on the 5070 Ti before Dr Sun approves the run budget.
- D3 The 1.5 m/s^2 gate, heartbeat and odometry deadlines, arrival and stillness thresholds, and the 41 continuous-
  episode checks stay unchanged. No threshold is relaxed after a result is seen.
- D4 `scan_03`, its source tree and every existing run package stay unchanged. New work uses new build and run IDs.
- D5 (Dr Sun, 2026-09-16) Plan and run budget approved: step B (CPU build and native suite on the 5070 Ti host, about
  30 min) and step C (8 Isaac episodes, about 30-40 min, about 7 GB GPU), C only after B passes.
- D6 (Dr Sun, 2026-09-16) A placed-obstacle Isaac episode is a later, separate task.
- D7 (Dr Sun, 2026-09-16) Endpoint limit 0.05 m (AC3).
- D8 (Dr Sun, 2026-09-17) AC3 and AC4 amended after a local harness preview (Mac, ROS 2 Humble, not the Foxy
  target, not evidence). The preview showed both builds ending about 8 cm from the target after follow-up replans
  (original 0.0785 m, candidate 0.0805 m; single-call candidate at most 0.0437 m), and 8 accepted original-build
  paths inside the inflated near box (candidate 0). The amendments below are disclosed in the report.
- D9 (Dr Sun, 2026-09-17) Isaac runs use `--remote-only-bulk`: `clouds.jsonl` and the original
  `third_person_master.mp4` stay in the 5070 Ti execution copy with SHA-256 recorded locally; the compressed walk
  review video is returned. The review's `returned_hashes_match` check accepts exactly these two files as absent
  when `remote_only_artifacts.json` records hashes equal to the manifest's (Dr Sun, 2026-09-17: narrow check
  change, disclosed); the other 40 checks are unchanged, and a re-review of `actual4` still gives the same 41/41.
- D10 (Dr Sun, 2026-09-17) Second AC3 change: follow-up endpoints are reported, not judged. The D8 per-call rule
  was flawed: call 0 is already judged as a single call (the fix's known endpoint shift is 1-2.5 cm), and after
  call 0 the builds' trajectories diverge, so call i of each build starts from a different state. Preview numbers
  that triggered it: 7 follow-up calls over original + 0.01 m (call 0 shifts of 1.0-1.3 cm; call 1 at x = -1.09 and
  -1.10: original 0.001 and 0.005 m, candidate 0.077 and 0.081 m).
- D11 (Dr Sun, 2026-09-17) Isaac stop rule: run all 8 episodes and report the success count with its exact bound
  (8/8 >= 0.69, 7/8 >= 0.53, 6/8 >= 0.40, one-sided 95 %). Stop early only on the same failure in two consecutive
  episodes, an integrity failure (SCAN hash gate, returned hashes), or a reset, pose injection or contact-guard
  failure. An infrastructure failure (SSH, sync, container start before the episode begins) gets one retry under a
  new run ID and is reported separately, not counted as a navigation result.
- D12 (Dr Sun, 2026-09-17) Episode split: 6 at the 0.40 m cancel trigger, 1 at 0.45 m, 1 at 0.50 m. Reason: the
  native sweep showed the original build fails only for resume x in [-1.19, -1.11] m; 0.40 m cancels stopped at
  x = -1.091 to -1.149 on 2026-09-16 (3 of 4 inside the band), while later triggers should stop further along,
  mostly outside it.
- D13 (Dr Sun, 2026-09-17) The 1.5 m/s^2 acceleration gate stays; raising it to 2.0 was considered and not taken
  (`research/goal_tolerance_and_accel_limits.md`). Isaac runs approved to start after the launcher review.

- D14 (Dr Sun, 2026-09-17) Adopt `scan_04` as the accepted SCAN build after reviewing the report
  (https://claude.ai/artifact/VSTvZquqTiA4iGuwWabJ6v, `scan_fix_qualification/RESULT.md`), with AC7 recorded as not
  met as written (7/8; episode 3 failed the goal-B stillness check). Dr Sun's explanation: an RL policy almost never
  stands perfectly still; holding needs a smooth switch to a PD controller, which is hard. The runs used the
  intended V12 model_149999. A PD stance hold is a separate locomotion task, not opened yet.

## Requirements

- R1 Build `scan_04` from the same pinned source and overlay as `scan_03`, plus exactly the one-line change applied by
  a recorded, hash-checked step. The source difference from `scan_03` is exactly that line.
- R2 Native A/B suite, original (`scan_03` source) against candidate (`scan_04` source), same inputs:
  1. the 4 recorded fixtures, plus fixtures from the other two failed stop poses and a stop-position sweep around
     the failing region;
  2. random initialization and several seeds;
  3. a non-empty occupancy grid (obstacles away from and near the route);
  4. follow-up replans (at least two consecutive replans in one planner instance);
  5. the endpoint distance of every accepted trajectory, reported for both builds.
- R3 The Isaac launcher verifies the remote SCAN workspace hashes, not only that `install/` exists, and records the
  build identity in the run package.
- R4 Repeated continuous Isaac episodes with `scan_04` (cancel, confirmed stop, resubmit, arrive A, arrive B),
  including episodes whose cancel point differs, so that stop positions vary.
- R5 Each run returns raw events, controller and physics evidence, video, GPU memory, wall time and verified hashes.
- R6 Adoption (recording `scan_04` as the accepted build) happens only after Dr Sun reviews the results.

## Acceptance Criteria

Thresholds below are frozen at plan approval. The endpoint limit (AC3) was chosen knowing the 3.55 cm observation;
it is derived from the 0.25 m arrival tolerance, not tuned to the candidate.

- [x] AC0 Validity control (added 2026-09-17, stricter only): in the native suite the original build must reproduce the
      recorded failure. For `failed_run_resume` (polynomial, seed 0, empty map) all 3 repeats are rejected by the
      acceleration gate, and the other 3 recorded cases pass 3/3 each, as in `native_original_20260916T180500Z`.
      Otherwise the suite is invalid and no other native verdict is used. Passed in `scan_fix_qualification/runs/native_suite_20260917T083723Z` (5070 Ti host, Foxy, 2026-09-17; 1,675 returned files hash-verified).
- [x] AC1 `scan_04` source differs from `scan_03` source in exactly one line; build and install hashes are recorded. Passed: one line differs (`tree_compare_scan_03.json`); `scan_04` build passed (74 s, same 74 upstream warnings); install identity 380 files, only `scan_planner_node` differs from `scan_03`.
- [x] AC2 Native: the candidate returns a trajectory in every fixture where the original does, plus every
      acceleration-gate rejection case; every accepted trajectory's sampled maximum acceleration is at most 1.5 m/s^2. Passed: original 27/63 accepted (36 gate rejections), candidate 63/63.
- [x] AC3 Native endpoint (amended 2026-09-17, D8 then D10): every accepted candidate single-call trajectory ends
      within 0.05 m of its target (XY). Follow-up replan endpoints of both builds are reported, not judged;
      follow-up completion is judged by AC6 and final position by the Isaac arrival checks (AC7). Passed: single-call candidate max 0.0438 m. Follow-up (report only): original max 0.0785 m, candidate 0.0805 m.
- [x] AC4 Native, occupancy grid (amended 2026-09-17, D8): no accepted candidate trajectory has a sample inside an
      inflated occupied cell. Original-build hits are reported as a separate finding. Candidate rejections are
      reported, and count against the fix only when the original accepts the same case without a hit. Passed: 546 runs, 0 candidate hits. Finding: 8 accepted original-build trajectories with collision samples.
- [x] AC5 Native, random initialization and seeds: the candidate's success count is at least the original's in every
      case group, and any candidate-only failure is explained before continuing. Passed: successes original 218, candidate 624; no candidate-only failure.
- [x] AC6 Native, follow-up replans: the candidate completes every sequence the original completes, and every
      sequence the original fails only at the acceleration gate. Passed: sequences completed original 6/15, candidate 15/15.
- [ ] AC7 Isaac: every approved episode passes the 41 checks in `p2b_execution/review_two_goal.py` (only the D9
      remote-only rule changed) and the remote SCAN hash gate passes. The series follows D11; the report gives
      the success count, its bound, and a walk video and native stop-pose replay for every failed episode.
      **Not met as written (2026-09-17):** 7/8 passed (one-sided 95 % bound 0.529); episode 3 failed 40/41 at the
      goal-B stillness check (RL policy on zero command, no PD stance hold); SCAN hash gates passed in all 8; native
      replay: original rejects the resume plan at 6/8 stops, fixed accepts 8/8. `scan_fix_qualification/RESULT.md`.
- [x] AC8 The report states the claim boundary: simulation only, one route on a flat platform with no placed
      obstacle, N episodes (with the binomial lower bound), no physical-robot or language-navigation claim.
      Stated in `scan_fix_qualification/RESULT.md` (Claim boundary), lead judgement; awaiting Dr Sun's review.

## Out of Scope

- Placed obstacles in the Isaac scene (D6).
- Pi/Cortex services, grounding, memory, SLAM, real-robot runs.
- Reporting the defect upstream.
