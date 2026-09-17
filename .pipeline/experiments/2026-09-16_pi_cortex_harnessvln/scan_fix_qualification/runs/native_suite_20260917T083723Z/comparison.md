# Native suite comparison: native_suite_20260917T083723Z

Validity: **VALID**. Overall passed: **True** (integrity True). Thresholds sha256 `fec162317b14dfaf958930149c4a8a5709fa73caba748f4a504bd1fbfc67857c`.

| Criterion | Status | Key numbers |
| --- | --- | --- |
| AC0 | pass | failed_run_resume acceleration_gate/acceleration_gate/acceleration_gate; failed_run_initial accepted/accepted/accepted; successful_run_initial accepted/accepted/accepted; successful_run_resume accepted/accepted/accepted |
| AC2 | pass | runs 63; original accepted 27, gate rejections 36; candidate accepted 63 |
| AC3 | pass | single-call max endpoint XY m {'original': 0.019058254653176437, 'candidate': 0.04381532784741372} (limit 0.05, candidate over 0); follow-up report only: completed {'original': 6, 'candidate': 15}, max endpoint XY m {'original': 0.07853679131345487, 'candidate': 0.08053408485933798}, calls over 0.05 m {'original': 4, 'candidate': 12} |
| AC4 | pass | runs 546; candidate hits 0; counted candidate rejections 0; not counted (original accepted with a hit) 0; finding: original-build hits 8 |
| AC5 | pass | groups 63; totals {'original': 218, 'candidate': 624}; candidate-only failures 0 |
| AC6 | pass | sequences 15; completed {'original': 6, 'candidate': 15} |

| Kind | Map | Init | Build | Runs | Accepted | Gate rejections | Other rejections | Accepted with collision | Max acc (m/s^2) | Max endpoint XY (m) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| follow_up | empty | poly_s0 | candidate | 15 | 15 | 0 | 0 | 0 | 0.839390 | 0.080534 |
| follow_up | empty | poly_s0 | original | 15 | 6 | 9 | 0 | 0 | 1.532777 | 0.078537 |
| single | empty | poly_s0 | candidate | 63 | 63 | 0 | 0 | 0 | 0.595581 | 0.043732 |
| single | empty | poly_s0 | original | 63 | 27 | 36 | 0 | 0 | 1.532777 | 0.018892 |
| single | empty | random | candidate | 210 | 210 | 0 | 0 | 0 | 0.595583 | 0.043732 |
| single | empty | random | original | 210 | 90 | 120 | 0 | 0 | 1.532777 | 0.018892 |
| single | far_box | poly_s0 | candidate | 63 | 63 | 0 | 0 | 0 | 0.595581 | 0.043732 |
| single | far_box | poly_s0 | original | 63 | 27 | 36 | 0 | 0 | 1.532777 | 0.018892 |
| single | far_box | random | candidate | 210 | 210 | 0 | 0 | 0 | 0.595583 | 0.043732 |
| single | far_box | random | original | 210 | 90 | 120 | 0 | 0 | 1.532777 | 0.018892 |
| single | near_box | poly_s0 | candidate | 63 | 60 | 0 | 3 | 0 | 0.601508 | 0.043815 |
| single | near_box | poly_s0 | original | 63 | 9 | 3 | 51 | 0 | 0.771551 | 0.019042 |
| single | near_box | random | candidate | 210 | 204 | 0 | 6 | 0 | 0.601888 | 0.043815 |
| single | near_box | random | original | 210 | 38 | 3 | 169 | 8 | 1.532778 | 0.019058 |

## Follow-up endpoints (report only, D10)

Endpoint XY (m) of the accepted attempt per call; "-" when that call was not accepted.

| Sequence | Original completed | Original calls 0/1/2 | Candidate completed | Candidate calls 0/1/2 |
| --- | --- | --- | --- | --- |
| sweep_x_m1p06__empty__followup_poly_s0_r0 | True | 0.0142 / 0.0667 / 0.0244 | True | 0.0244 / 0.0655 / 0.0216 |
| sweep_x_m1p07__empty__followup_poly_s0_r0 | True | 0.0147 / 0.0705 / 0.0281 | True | 0.0255 / 0.0693 / 0.0254 |
| sweep_x_m1p08__empty__followup_poly_s0_r0 | True | 0.0153 / 0.0743 / 0.0319 | True | 0.0267 / 0.0730 / 0.0291 |
| sweep_x_m1p09__empty__followup_poly_s0_r0 | True | 0.0159 / 0.0011 / 0.0381 | True | 0.0280 / 0.0768 / 0.0328 |
| sweep_x_m1p10__empty__followup_poly_s0_r0 | True | 0.0166 / 0.0049 / 0.0419 | True | 0.0293 / 0.0805 / 0.0365 |
| sweep_x_m1p11__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0307 / 0.0075 / 0.0424 |
| sweep_x_m1p12__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0321 / 0.0112 / 0.0461 |
| sweep_x_m1p13__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0336 / 0.0149 / 0.0498 |
| sweep_x_m1p14__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0351 / 0.0186 / 0.0535 |
| sweep_x_m1p15__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0367 / 0.0223 / 0.0572 |
| sweep_x_m1p16__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0384 / 0.0260 / 0.0610 |
| sweep_x_m1p17__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0401 / 0.0297 / 0.0647 |
| sweep_x_m1p18__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0419 / 0.0332 / 0.0684 |
| sweep_x_m1p19__empty__followup_poly_s0_r0 | False | - / - / - | True | 0.0437 / 0.0370 / 0.0721 |
| sweep_x_m1p20__empty__followup_poly_s0_r0 | True | 0.0164 / 0.0432 / 0.0785 | True | 0.0170 / 0.0432 / 0.0786 |

## Findings (not acceptance criteria)

Accepted original-build trajectories with collision samples (AC4 scope): 8. accepted original-build trajectories with collision samples; reported, they do not decide AC4

| Case | Init | Call | Collision samples | First collision t (s) | Duration (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| sweep_x_m1p08__near_box__rand_s4_r0 | rand_s4_r0 | 0 | 22 | 2.0300000000000007 | 3.488955900572605 |
| sweep_x_m1p10__near_box__rand_s0_r0 | rand_s0_r0 | 0 | 9 | 2.06 | 3.512850608901794 |
| sweep_x_m1p10__near_box__rand_s1_r0 | rand_s1_r0 | 0 | 9 | 2.06 | 3.512850608901794 |
| sweep_x_m1p10__near_box__rand_s2_r0 | rand_s2_r0 | 0 | 9 | 2.06 | 3.5124413958189966 |
| sweep_x_m1p10__near_box__rand_s3_r0 | rand_s3_r0 | 0 | 9 | 2.06 | 3.513636432525442 |
| sweep_x_m1p10__near_box__rand_s4_r0 | rand_s4_r0 | 0 | 11 | 2.0500000000000003 | 3.512265726863414 |
| sweep_x_m1p10__near_box__rand_s5_r0 | rand_s5_r0 | 0 | 9 | 2.06 | 3.5133734141169723 |
| sweep_x_m1p10__near_box__rand_s7_r0 | rand_s7_r0 | 0 | 9 | 2.06 | 3.512620864854621 |

Anomalies: 0. Claim boundary: Native planner-only A/B at the SCANPlannerManager boundary in the pinned Foxy image with recorded-pose fixtures and synthetic boxes; not an Isaac, controller, physical-robot or language-navigation result.

Boundary notes:

- Follow-up offsets 0.3 s and 0.6 s are a stress schedule, not the live trigger. In EXEC_TRAJ the live FSM replans once the robot is 1.0 m from the current trajectory start (scan_replan_fsm.cpp:893, fsm.thresh_replan 1.0 in planner.yaml) or when checkCollisionCallback finds a collision (scan_replan_fsm.cpp:1083); new targets and routes also trigger a replan.
- SCAN's own collision checks cover only the first two thirds of a trajectory (bspline_optimizer.cpp:1017-1018 after rebound optimization, 1115-1116 after refinement), and reboundReplan has no final collision check (planner_manager.cpp:298 checks dynamic feasibility only). AC4 therefore samples every accepted trajectory independently over its full duration, every 0.01 s from t = 0.
- SCAN's acceleration gate (checkDynamicFeasibility) samples every max(0.01, min(0.05, duration/50)) s, i.e. 0.05 s for durations of 2.5 s or more, while t < duration + 1e-6 (planner_manager.cpp:460-464), so its last sample usually falls before the trajectory end. The harness maximum (1001 samples including t = duration) can therefore exceed 1.5 m/s^2 for accepted original-build trajectories.
