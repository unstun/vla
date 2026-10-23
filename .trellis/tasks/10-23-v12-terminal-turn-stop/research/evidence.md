---
origin: lead_analysis_with_source_check
date: 2026-10-23
method: read-only review of retained v290/v291 reports, v291 source and the V12 training sampler; no new physics
---

# Evidence: the bottleneck is V12 stopping and terminal turning, not path planning

Dr Sun's hypothesis (2026-10-23): the bottleneck is no longer global or local planning. It is that the RL policy
(V12) stops badly and that in-place turning is missing. This file records the evidence checked before the task
was written, so the next agent does not need to repeat it. All paths are repository-relative unless marked.

Let E = `.pipeline/experiments/2026-09-26_newton_stair_reproduction`.

## 1. Planning passes; failures cluster at the goal

| Evidence | Value | Source |
|---|---|---|
| v291 offline strict53 | 49/50 legal, 3/3 illegal refused, first-solve 47/49 (95.9%), median 1.421 s | `E/versions/v291/RESULTS.md` |
| v290 ten physical routes | All 5 geometry failures (D07, S04, CD12, CS03, CE03) are at the goal during turning, standing or PD hand-over. G05 is a scanner timeout. A04, CU06, CM02, CM07 pass fully. | `E/audits/2026-10-21_v290_terrain_terminal/ultra9/RESULTS_zh.md` (route table) |
| v291 paired-24 failure split | 6 complete successes; 7 scanner-deadline interruptions; 11 other failures, all terminal: 9 geometry failures and 2 arrival/PD failures (stop drift / hand-over abort) | `E/audits/2026-10-22_v291_paired24/REPORT.md` |
| Timing of the 9 geometry failures | First violation relative to the first zero command: −0.42, −0.42, −0.40, −0.34, −0.22, −0.18, 0.00, +1.64 s, and one at −11.95 s (v291 CD12 r1: first touch at 112.77 s, close to v290 CD12's 112.97 s, but its first zero command came 11.3 s later than v290's because it kept centring with small commands and recovery retries) | `E/audits/2026-10-22_v291_paired24/results/geometry_events.json` |

Selection caveat: D07/CD12 were picked because they are known stop cases, so paired-24 over-represents terminal
failures. v285 still had local-search failures on A04, G05, CU06 and CM02 (local success about 50% of attempts on
A04/G05), and v290 logs 773 `lbfgs_minus1008` and 88 `inside_obstacle` lines. Planning is not perfect; it is just
not what is failing the physical runs now.

## 2. Stop drift happens while V12 still owns the joints

From `E/audits/2026-10-22_v290_stop_timeline/REPORT.md` (v290 D07 and CD12, recorded telemetry):

| | D07 | CD12 |
|---|---:|---:|
| Wait from zero command to PD hand-over start | 12.573 s | 4.557 s |
| Net drift before PD (V12 in `STAND_SETTLING`) | 22.13 cm | 20.24 cm |
| Net drift from PD start to `FIXED_STAND` | 0.32 cm | 1.09 cm |
| Main first rejection reason | `waiting_for_four_contact` (10.974 s) | `waiting_for_four_contact` (3.298 s) |

v291's loaded-leg settling assistance did not reduce drift consistently (paired-24: 3/12 vs 3/12; A04 first-stop
median 1.48 → 8.07 cm). S04 v291 r1 started PD at 27.43655 s and aborted 0.06 s later on
`stand_transition_disturbance:linear_speed`.

## 3. V12 was never trained on the commands the terminal sends (verified in source)

V12 sampler: `/Users/sun/tongbu/study/phdproject/machine-dog/2_experiment/baseline_rebuild/go2_rl_robotlab_lite3_v12/source/robot_lab/robot_lab/tasks/go2/mdp/commands.py`,
SHA-256 `d97996f154ea4bf5c00043f5379896f95c7b434592c0e61fd70568c9502bd488`. This matches line 129 of
`references/upstream/2026-09-11_lite3_v12_locomotion/SHA256SUMS.txt` (V12 runtime source). Config:
`/Users/sun/tongbu/study/phdproject/machine-dog/artifacts/2026-07-16_v12_lite3_model149999_handoff/tracked_configs/env.yaml:2092-2310`.

Facts read from the code:
- `commands.py:186-187`: any sampled linear command with `‖(vx, vy)‖ ≤ 0.2` m/s is set to zero (yaw is kept).
- `commands.py:234-257`: the zero-command branch (probability ramps 0 → 0.1 over iterations 0-1500) zeroes only
  the linear part. Yaw keeps its uniform sample; with probability 0.2 it is replaced by a range extreme.
- `limit_vel` (probability 0.2) uses range extremes for x and y, with yaw in {min, 0, max}.
- `stand_still` and `feet_contact_without_cmd` rewards are defined but unused (stance survey, below).

Inferences, to be measured in Phase B (not yet shown in physics):
- **Low-speed dead zone.** A commanded 0 < |v| ≤ 0.2 m/s is outside V12's training. The v291 terminal centering
  command is capped at 0.15 m/s and is about 5 cm/s near the goal. In v291 CD12 r1 it commanded 5.38 cm/s for about
  2 s and the body moved 0.56 cm, with three `Failed to make progress` retries (paired-24 report, control issue 2).
- **True stand-still is rare in training.** An exact all-zero command needs the uniform yaw sample to land near
  zero, so V12 almost never practised `[0, 0, 0]`. This fits the known zero-command jitter: Isaac stand yaw rate
  −0.101 to +0.126 rad/s and 3.2 cm drift in 10 s (`machine-dog/artifacts/2026-07-18_v12_model149999_flat_standstill_diagnosis/README.md:51-73`, via the survey).
- **Pure yaw is in distribution.** Zero linear velocity with non-zero yaw is common (small-command zeroing plus
  the zero branch), so in-place turning should be something V12 can do. Its XY drift while turning is unmeasured.

Survey with the training parameters: `.trellis/tasks/archive/2026-09/09-17-isaac-runner-stance-hold/research/stance_hold_code_survey.md`
(`reviewed: false`; the two facts above were re-checked against the source on 2026-10-23).

## 4. In-place turning existed and was removed

| Version | Behaviour | Source |
|---|---|---|
| v206 | Turn-in-place mode: enter at heading error ≥ 1.0 rad, exit ≤ 0.6 rad; phase frozen while turning | `E/versions/v206/RESULTS.md`, `E/versions/v206/src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp:334-343` |
| v285 (2026-10-19) | Replaced by "keep turning while moving": positive heading scale for translation and phase; final pure-yaw alignment kept only inside the goal capture region | `E/audits/2026-10-19_v285_local_search_tracking/RESULTS.md` (change 3) |
| v291 (current candidate) | `translation_scale = 0.5 + 0.5·(1 − smoothstep)`, never below 50%; inside the 25 cm goal circle it corrects XY (`kp_pos`, cap 0.15 m/s) and yaw (`kp_yaw` 1.5, cap 1.0 rad/s) at the same time | `E/versions/v291/src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp:300-336, 371-405` |

v290 D07 (stop-timeline report): the robot entered the 25 cm goal circle at 105.354 s with 155.9° heading error.
It first crossed source solid at 106.873 s, 8.48 cm from the centre, still 92.4° off, applied command
`[-0.0081, -0.0268, 1.0]`. SCAN then issued an emergency spline at 107.313 s.

v283 already flagged the gap: pure-yaw commands from `publishStop(yaw_rate)` are never checked with a
measured-pose swept-rotation query (`E/audits/2026-10-19_v283_navigation_geometry/RESULTS.md`, "Remaining
command/physical tracking gap").

## 5. Turning at the goal pose itself is often illegal

v290 32-heading sweep at each requested goal centre (`RESULTS_zh.md`, goal-heading table):

| Goal | Margin at requested heading | Worst margin over 32 headings | Negative headings |
|---|---:|---:|---:|
| D07 | +9.26 cm | +1.36 cm | 0/32 |
| S04 | +15.00 cm | +0.47 cm | 0/32 |
| CD12 | +0.57 cm | −11.28 cm | 20/32 |
| CS03 | +10.87 cm | −6.92 cm | 16/32 |
| CE03 | +1.97 cm | −4.44 cm | 16/32 |
| A04, G05, CU06, CM02, CM07 | +15.00 cm | +15.00 cm | 0/32 |

So "stop at the goal and spin" would collide on CD12/CS03/CE03, and D07/S04 have almost no slack for V12's turning
drift. The turn has to happen at a point with full-rotation clearance before the final approach, and the robot
must then arrive already facing the goal heading.

## 6. Infrastructure failures are separate

Paired-24 lost 7/24 runs (v290 2, v291 5) and v290 lost 2/10 to the unchanged 100 ms scanner deadline on the
shared ultra9 host. Example: scan CPU 31 ms, runnable wait 69 ms, total 103 ms. These are not RL failures but
they consume trial budget. Spec: `.trellis/spec/backend/newton-lidar-deadline.md`.
