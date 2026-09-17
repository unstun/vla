# Native suite comparison: native_replay_20260917T092127Z

Validity: **VALID**. Overall passed: **True** (integrity True). Thresholds sha256 `fec162317b14dfaf958930149c4a8a5709fa73caba748f4a504bd1fbfc67857c`.

| Criterion | Status | Key numbers |
| --- | --- | --- |
| AC0 | pass | failed_run_resume acceleration_gate/acceleration_gate/acceleration_gate; failed_run_initial accepted/accepted/accepted; successful_run_initial accepted/accepted/accepted; successful_run_resume accepted/accepted/accepted |
| AC2 | pass | runs 36; original accepted 15, gate rejections 21; candidate accepted 36 |
| AC3 | pass | single-call max endpoint XY m {'original': 0.018891917427418574, 'candidate': 0.035469272936540265} (limit 0.05, candidate over 0); follow-up report only: completed {'original': 0, 'candidate': 0}, max endpoint XY m {'original': None, 'candidate': None}, calls over 0.05 m {'original': 0, 'candidate': 0} |
| AC4 | not_applicable | runs 0; candidate hits 0; counted candidate rejections 0; not counted (original accepted with a hit) 0; finding: original-build hits 0 |
| AC5 | not_applicable | groups 0; totals {'original': 0, 'candidate': 0}; candidate-only failures 0 |
| AC6 | not_applicable | sequences 0; completed {'original': 0, 'candidate': 0} |

| Kind | Map | Init | Build | Runs | Accepted | Gate rejections | Other rejections | Accepted with collision | Max acc (m/s^2) | Max endpoint XY (m) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single | empty | poly_s0 | candidate | 36 | 36 | 0 | 0 | 0 | 0.600140 | 0.035469 |
| single | empty | poly_s0 | original | 36 | 15 | 21 | 0 | 0 | 1.477884 | 0.018892 |

## Follow-up endpoints (report only, D10)

Endpoint XY (m) of the accepted attempt per call; "-" when that call was not accepted.

| Sequence | Original completed | Original calls 0/1/2 | Candidate completed | Candidate calls 0/1/2 |
| --- | --- | --- | --- | --- |

## Findings (not acceptance criteria)

Accepted original-build trajectories with collision samples (AC4 scope): 0. accepted original-build trajectories with collision samples; reported, they do not decide AC4

Anomalies: 0. Claim boundary: Native planner-only A/B at the SCANPlannerManager boundary in the pinned Foxy image with recorded-pose fixtures and synthetic boxes; not an Isaac, controller, physical-robot or language-navigation result.

Boundary notes:

- Follow-up offsets 0.3 s and 0.6 s are a stress schedule, not the live trigger. In EXEC_TRAJ the live FSM replans once the robot is 1.0 m from the current trajectory start (scan_replan_fsm.cpp:893, fsm.thresh_replan 1.0 in planner.yaml) or when checkCollisionCallback finds a collision (scan_replan_fsm.cpp:1083); new targets and routes also trigger a replan.
- SCAN's own collision checks cover only the first two thirds of a trajectory (bspline_optimizer.cpp:1017-1018 after rebound optimization, 1115-1116 after refinement), and reboundReplan has no final collision check (planner_manager.cpp:298 checks dynamic feasibility only). AC4 therefore samples every accepted trajectory independently over its full duration, every 0.01 s from t = 0.
- SCAN's acceleration gate (checkDynamicFeasibility) samples every max(0.01, min(0.05, duration/50)) s, i.e. 0.05 s for durations of 2.5 s or more, while t < duration + 1e-6 (planner_manager.cpp:460-464), so its last sample usually falls before the trajectory end. The harness maximum (1001 samples including t = duration) can therefore exceed 1.5 m/s^2 for accepted original-build trajectories.
