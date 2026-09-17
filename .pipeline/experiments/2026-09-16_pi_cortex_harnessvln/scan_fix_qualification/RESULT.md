---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
task: .trellis/tasks/09-16-scan-terminal-accel-fix-qualification
machine: gpu5070ti (native suites on CPU in the pinned Foxy image; Isaac episodes on the RTX 5070 Ti)
---

# SCAN terminal-acceleration fix: qualification result

## Verdict

| Criterion | Status | Evidence |
| --- | --- | --- |
| AC0 validity control | pass | The original build reproduced the recorded rejection 3/3; the other 3 recorded cases were accepted 3/3 (`runs/native_suite_20260917T083723Z`) |
| AC1 one-line build | pass | `scan_04` differs from `scan_03` at `planner_manager.cpp:171` only; build passed; 380 install files, only `scan_planner_node` differs |
| AC2 gate rejections removed | pass | Original accepted 27/63, the other 36 rejected by the gate; fixed accepted 63/63; 0 fixed calls above 1.5 m/s^2 |
| AC3 single-call endpoint | pass | Fixed max 0.0438 m (limit 0.05). Follow-ups, report only: original max 0.0785 m, fixed 0.0805 m |
| AC4 occupancy grid | pass | 546 runs, 0 fixed trajectories inside an inflated cell. Finding: 8 accepted original-build trajectories with collision samples |
| AC5 seeds and random init | pass | Successes: original 218, fixed 624; no fixed-only failure |
| AC6 follow-up replans | pass | Sequences completed: original 6/15, fixed 15/15 |
| **AC7 Isaac episodes** | **fail as written** | 7/8 passed the 41 checks (one-sided 95 % lower bound 0.529). Episode 3: 40/41, failed at the goal-B stillness check (see below). SCAN hash gates and returned hashes passed in all 8 |
| AC8 claim boundary | stated | Section "Claim boundary" below |

Adopting `scan_04` is Dr Sun's decision (PRD R6). This file makes no adoption claim.

## What the evidence shows

1. **Mechanism.** With the original line, a plan that resumes after a braked stop is given the acceleration at the
   last polynomial sample as its terminal acceleration instead of about 0: 1.26-2.01 m/s^2 for sweep starts from
   x = -1.06 to -1.19 m (native sweep, polynomial init, seed 0). For resume starts between x = -1.19 and -1.11 m, the
   refined path still peaks at 1.52-1.57 m/s^2 and the 1.5 m/s^2 gate rejects every repeat (figure
   `report/figures/panel2_where_the_bug_bites.png`). With the fixed line, the path peaks at 0.54-0.60 m/s^2 at every
   resume start.
2. **No side effects in the native suite.** The fix changed only gate outcomes on the empty and far-box maps. On the
   near-box map it accepted more cases and put no path inside an inflated cell. Where both builds returned a
   single-call plan (281 calls), the fix moved the endpoint by 0.05-1.27 cm; fixed-build single-call endpoints lie
   1.7-4.4 cm from the target (original 1.4-1.9 cm), within the 0.05 m limit.
3. **The Isaac series reached the failure region.** A native replay of each episode's resume start
   (`runs/native_replay_20260917T092127Z`, VALID, own AC0 control) shows that the original build rejects the resume
   plan at 6 of 8 stops. With `scan_04`, all 6 resumed and reached goal A. Episode 3 then failed later, at goal B.

## Isaac series (8 episodes, `scan_04`, 2026-09-17 08:51-09:20 UTC)

Resume x is the driver's still-confirmed pose. The resubmitted plan started at the same pose in 6 episodes and within
0.2 mm of it in e02 and e05. Native verdicts come from the stop-pose replay of each resubmitted plan start (polynomial
init, seed 0, 3 repeats, empty map). Arrival limit 0.25 m. Non-foot contact force was 0.0 N in every episode.

| Ep | Trigger | Resume x (m) | Original at this pose | Fixed at this pose | Checks | Arrival A / B (m) | Sim / episode wall (s) | GPU peak (MiB) |
| ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |
| 1 | 0.40 m | -1.1375 | rejected (1.563) | accepted (0.590) | 41/41 | 0.186 / 0.186 | 16.4 / 22.1 | 7,136 |
| 2 | 0.40 m | -1.1289 | rejected (1.555) | accepted (0.591) | 41/41 | 0.184 / 0.186 | 16.3 / 21.7 | 7,086 |
| 3 | 0.40 m | -1.1130 | rejected (1.529) | accepted (0.592) | **40/41** | 0.189 / 0.177 | 16.3 / 21.8 | 7,262 |
| 4 | 0.40 m | -1.1373 | rejected (1.563) | accepted (0.590) | 41/41 | 0.184 / 0.167 | 16.4 / 21.7 | 7,086 |
| 5 | 0.40 m | -1.1062 | rejected (1.513) | accepted (0.592) | 41/41 | 0.192 / 0.159 | 16.2 / 21.6 | 7,134 |
| 6 | 0.40 m | -1.1301 | rejected (1.556) | accepted (0.591) | 41/41 | 0.183 / 0.193 | 16.4 / 21.7 | 7,088 |
| 7 | 0.45 m | -1.0649 | accepted (1.299) | accepted (0.595) | 41/41 | 0.175 / 0.157 | 16.2 / 21.5 | 7,133 |
| 8 | 0.50 m | -0.9948 | accepted (0.732) | accepted (0.600) | 41/41 | 0.174 / 0.183 | 16.0 / 21.1 | 7,096 |

Values in brackets are m/s^2: the gate value for a rejection, the sampled path maximum for an acceptance.

- Episode 5 resumes at x = -1.106, just outside the sweep band. The original still rejects it at the recorded y and
  yaw.
- Every episode: SCAN hash gate before and after passed (67 source, 380 install files); returned hashes matched,
  with `clouds.jsonl` and the original video remote-only (D9); walk review rendered; about 127 s host run time. The
  host was idle before each episode and after the series (ledger `isaac_series/series_ledger.jsonl`).
- Walk videos: `report/videos/e01.mp4` to `e08.mp4` (hardlinks to each run's `walk_review/walk_review.mp4`, about
  240 KB each).

### Episode 3 failure

`goal-b:raw_physics_stop_dwell` failed. One 20 ms sample at sim 14.30 s had a yaw rate of 0.1595 rad/s (limit 0.15),
so the full-rate still window before the goal-B terminal was 0.88 s against the required 1.00 s. The backend
declared arrival because its dwell check polls the latest snapshot file and did not read that sample.

Dr Sun (2026-09-17): an RL policy almost never stands perfectly still; holding the stance needs a switch to a PD
controller, and making that switch smooth is hard. The runs used the intended V12 `model_149999.pt` (sha256
`a9d31dce…d5450`, equal to `machine-dog/artifacts/2026-07-16_v12_lite3_model149999_handoff`). The Isaac runner keeps
that policy running on a zero command after a stop and has no PD stance hold.

The failure is therefore in the locomotion stop, downstream of SCAN. It is counted as a failure (PRD D11), and no
threshold was changed. Details: `isaac_series/e03_failure_analysis.md`.

## Disclosed changes to the plan

All were made by Dr Sun before the result they affect was seen, except where stated.

- AC0 (2026-09-17): validity control added; stricter only.
- D8 (2026-09-17): AC3/AC4 amended after a local Humble preview (not evidence). AC4 judges only fixed-build
  trajectories; original-build hits are a finding.
- D10 (2026-09-17): follow-up endpoints are reported, not judged. The D8 per-call rule compared calls with different
  start states. Made after the same local preview (not evidence); no remote result existed.
- D9 (2026-09-17): `--remote-only-bulk`. `returned_hashes_match` accepts exactly two absent files when the returned
  record matches the manifest. A re-review of `actual4` still gives 41/41.
- D11 (2026-09-17): run all 8 episodes; stop early only on repeated identical failures, integrity failures, or
  reset/pose-injection/contact failures. Applied: episode 3 failed, and the series continued.
- D12 (2026-09-17): 6 episodes at the 0.40 m trigger, 1 at 0.45 m, 1 at 0.50 m.
- D13 (2026-09-17): the 1.5 m/s^2 gate stays (2.0 was considered:
  `.trellis/tasks/09-16-scan-terminal-accel-fix-qualification/research/goal_tolerance_and_accel_limits.md`).
- Thresholds file history: `fec16231…` (current), `4c5f7eaf…`, `3cce793f…` (`thresholds_history/`), and the first
  local freeze `52e4d26e…`, replaced before AC0 was added and before any suite result (no copy kept; `PLAN.md`).

## Findings beyond the criteria

- The original build accepted 8 near-box trajectories with collision samples. Their first collision sample lies at
  58-59 % of the trajectory duration. SCAN's own post-optimization check covers the first two thirds of the duration
  in steps of about one voxel (0.05 m) of start-to-end distance (`bspline_optimizer.cpp:1018,1116`); the harness
  samples every 0.01 s. Why SCAN missed these samples was not isolated.
- The plotted fixed-build near-box path (`failed_run_resume`, panel 5) clears the inflated voxels by about 2 mm at
  its 0.05 s samples. The harness's own check recorded 0 hits, but the margin is at voxel scale.
- Random initialization (seeds 0-9) changed almost nothing on the empty and far-box maps, so AC5 says little about
  initialization robustness.
- Follow-up replans end up to about 8 cm from the target in both builds (maximum 0.0785 m original, 0.0805 m
  fixed). That is within SCAN's 0.1 m no-replan zone and common goal tolerances (0.10-0.25 m).
- Speed fell below 0.10 m/s within 0.14-0.18 s of the cancel in every episode. In the six 0.40 m episodes the robot
  was at x = -1.127 to -1.104 about 0.2 s after the cancel, then moved 0.4-3.1 cm back (e05: 0.7 cm forward) before
  stillness was confirmed 2.24-2.50 s after the cancel. In the 0.45 m and 0.50 m episodes it crept 2.3 and 2.9 cm
  forward after the first 0.2 s (`metrics.jsonl`).

## Claim boundary

- Simulation only (Isaac Lab on the 5070 Ti host, and native replays in the pinned Foxy image). No physical-robot
  result.
- One known-map route on a flat platform, with no placed obstacle in Isaac (D6), and simulator-truth pose. No
  SLAM, language-navigation, Pi/Cortex or vision claim.
- N = 8 episodes: 7 passed (one-sided 95 % lower bound 0.529). Six of the eight reached a stop pose where the
  original build fails.
- The fix was not checked against an unmodified official PCT-SCAN-ROS2 build and has not been reported upstream.
- Evidence label: no label is promoted. The one-line fix was exercised inside this repository's native stack in
  simulation; it is not `validated`, because AC7 failed as written.

## Report and reproduction

Commands run from `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`.

- Figures and data: `python3 scan_fix_qualification/make_report.py --stop-replay-run scan_fix_qualification/runs/native_replay_20260917T092127Z`
  writes `report/figures/*.png`, `report/report_data.json` (SHA-256 of all inputs and outputs) and `report/videos/`.
- Isaac series: `scan_fix_qualification/run_isaac_series.py --lead-authorized-execute` (driver) and
  `p2b_execution/review_two_goal.py <run> --output <run>/review.json` (review). The series ran driver version
  `6fca2efd…` (byte copy `isaac_series/run_isaac_series.executed_6fca2efd.py`). The current driver changes only the
  host probe and failure handling: the probe fails closed and splits GPU memory from utilization (the executed
  version stored `"202, 0"` in `gpu_memory_used_mib`), and every failure, including a launcher timeout or review
  error, writes a ledger line with the host state afterwards.
- Native suite and replay: `suite_worker.py`, `make_fixtures.py from-journals`, `analyze_suite.py` (see `PLAN.md`).
