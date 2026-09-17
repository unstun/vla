# SCAN Terminal-Acceleration Fix: Native A/B Suite Plan

Date: 2026-09-17. Stage: experiment + analysis (planning of step B).
Task: `.trellis/tasks/archive/2026-09/09-16-scan-terminal-accel-fix-qualification` (PRD R2, AC0 and AC2-AC6; design section 2).

## Frozen thresholds

`thresholds.json` SHA-256: `fec162317b14dfaf958930149c4a8a5709fa73caba748f4a504bd1fbfc67857c`

Second amendment, 2026-09-17 (PRD decision D10, Dr Sun). This value supersedes the D8 freeze
`4c5f7eaf39944f88ea00a17df6211498e2dab3bfa6fb103f0962e7fa5d5cabbe`. AC3 now judges only single
candidate calls (endpoint XY at most 0.05 m). Follow-up endpoints of both builds are reported per
sequence and per call, together with which sequences each build completed. They get no verdict, and
the D8 per-call rule is removed. That rule compared calls that are not comparable: after call 0 the
two builds' trajectories diverge, so call i of each build starts from a different state. Call 0 is
already judged by the single-call rule, where the fix's known endpoint shift is 1-2.5 cm. In the same
local Humble preview (not evidence), 7 follow-up calls exceeded original + 0.01 m. Four were call-0
shifts of 1.0-1.3 cm. At x = -1.09 and -1.10 m, call 1 ended 0.001 and 0.005 m from the target in
the original but 0.077 and 0.081 m in the candidate. AC6 still judges follow-up completion, and the
Isaac arrival checks (AC7) judge final position. No remote call had been made.

Amendment, 2026-09-17 (PRD decision D8, Dr Sun). The D8 value superseded the freeze
`3cce793f0cdc83fffda510ff4df1eeed6495f8a9e2823faa25819bdc2b2d4c50`. No remote call had been made. The
reason is a local harness preview on the Mac under ROS 2 Humble. That is not the Foxy target, and the
preview is not evidence. It showed both builds ending about 8 cm from the target after follow-up
replans (original 0.0785 m, candidate 0.0805 m). Those calls are accepted through the
previous-trajectory branch, which the one-line fix does not touch. Single candidate calls ended at
most 0.0437 m away. All 8 accepted trajectories inside the inflated near box were original-build
trajectories. Two rules changed:

- AC3: single candidate calls must still end within 0.05 m. In follow-up sequences that both builds
  complete, each candidate call (0, 1 and 2) could end at most 0.01 m farther than the original's call
  with the same index. Sequences that only the candidate completed were reported with their endpoints
  and not judged. D10 removed this follow-up rule.
- AC4: only candidate trajectories are judged. Original-build hits are listed under `findings`. A
  candidate rejection counts against the fix only when the original accepts the same run without a hit.

The gate, the 0.05 m limit, the zero-collision rule and AC0, AC2, AC5 and AC6 are unchanged.
`thresholds.json` records both amendments in its `amendments` list. Byte copies of both superseded files
are in `thresholds_history/` (`thresholds_superseded_3cce793f.json`, `thresholds_superseded_4c5f7eaf.json`).

The superseded value was recorded before any remote call. It replaced the first local freeze
(`52e4d26e…`, 2026-09-17), which lacked the AC0 validity control added to the PRD the same day; the
AC0 change is stricter only, and no suite result existed when it was made. `analyze_suite.py` and
`suite_worker.py` refuse to run if the file differs. The acceleration gate (1.5 m/s^2), endpoint limit (0.05 m, D7) and the
zero-collision rule come from the PRD; the file also fixes each criterion's scope. A change to any
threshold after results are seen requires a new, reviewed file and a new recorded hash, stated
beside the old one.

## Validity control (AC0)

`analyze_suite.py` evaluates AC0 before any other verdict. With the original build,
`failed_run_resume` (polynomial, seed 0, empty map) must be rejected by the acceleration gate in all
3 repeats, and `failed_run_initial`, `successful_run_initial` and `successful_run_resume` must be
accepted 3/3 each, matching `scan_replan_diagnosis/runs/native_original_20260916T180500Z`. Missing
control runs also fail AC0. On failure, `comparison.json` marks the suite `INVALID` and reports AC2-AC6
as `not_evaluated`. The recorded gate warning (1.567 > 1.500 at t = 3.5 s) is compared and reported,
but it is not a pass condition. Replay fixtures from `make_fixtures.py from-journals` always include the
four control starts, so every C5 replay carries its own control.

## What runs

Two variants of one executable, `native_suite/scan_fix_native_suite`, both compiled in the pinned
Foxy image `e4aa7154…` against the scan_03 headers and scan_03 installed static libraries, with the
same flags as the diagnosis (`Release`, `BUILD_TESTING=OFF`, `SCAN03_SOURCE_ROOT=/scan_03`):

- original: `p2b_execution/builds/scan_03/src/plan_manage/src/planner_manager.cpp` (`0c51df…`);
- candidate: `p2b_execution/builds/scan_04/src/plan_manage/src/planner_manager.cpp`, which must differ
  only at line 171 (`evaluateAcc(t)` to `evaluateAcc(time)`), match `builds/scan_04/source_sha256.json`
  and the fix manifest's `after_sha256`.

Each binary embeds the path and SHA-256 of the manager it compiled; every log line set is checked
against the expected hash.

Fixtures (`make_fixtures.py`, deterministic; `fixtures/suite_cases.json`):

| Dimension | Values |
| --- | --- |
| Starts (21) | 4 diagnosis cases; display-off and RViz failed resume poses (PCT request start + 0.35 m, last PCT waypoint as target); failed-resume sweep x = -1.20 … -1.06 m in 0.01 m steps |
| Initializations (13) | polynomial seed 0 x3 repeats; random polynomial seeds 0-9 |
| Maps (3) | empty; far box (centre 1.0 m left of the route); near box (centre 0.3 m left; the straight route is 0.149 m from its face, inside the 0.25 m inflation radius) |
| Follow-ups (15) | every sweep pose, empty map, polynomial seed 0, offsets 0.3 s and 0.6 s |

Counts: 819 single runs + 15 follow-up runs = 834 process runs per build, 1,668 in total; 30
follow-up steps per build, each with up to three attempts (FSM chain: previous trajectory,
polynomial, random polynomial). Path samples every 0.05 s are printed only for
`failed_run_resume__empty__poly_s0_r0`, `failed_run_resume__near_box__poly_s0_r0` and
`sweep_x_m1p14__empty__followup_poly_s0_r0`. Boxes are 0.3 x 0.3 m, z 1.0-3.0 m, marked with
`GridMap::setOccupied`, which updates inflation.

## Follow-up timing

Exact simulated time. `planner.yaml` sets `use_sim_time: true`, so the node clock has the ROS time
override enabled and nothing spins the node. The executable sets the override with
`rcl_set_ros_time_override` (base 100 s, then base + offset) and checks `node->now()` after every
set. At each offset the newest accepted trajectory is sampled at `now - start_time`, exactly as
`planFromCurrentTraj` and the manager's previous-trajectory branch read it. The measured offset is
printed, and the analyzer requires it to equal the fixture difference within 1e-9 s.

## Execution

```bash
python3 scan_fix_qualification/suite_worker.py --run-id native_suite_<UTC> --dry-run
python3 scan_fix_qualification/suite_worker.py --run-id native_suite_<UTC>            # prepare only
python3 scan_fix_qualification/suite_worker.py --run-id native_suite_<UTC> --execute --lead-authorized-execute
python3 scan_fix_qualification/analyze_suite.py --run-dir scan_fix_qualification/runs/native_suite_<UTC>
```

- Local sync gate: scan_03 and scan_04 manifests, one-line diff, build results, planner.yaml,
  thresholds hash, fixture and box hashes. The run package is immutable and has its own manifest.
- Remote: new directory `.../p2b/scan_fix_qualification/<run-id>` (refused if it exists), whitelist
  rsync, remote hash gate over the package, scan_03 source (67), scan_03 install (380) and scan_04
  source, then build and replay per variant with podman `--network=none`, then the same hashes again.
- Ceilings: 180 s per build, 20 s per case, 900 s per replay (expected about 2 min), 2,280 s in total.
  CPU only; no Isaac, controller, sensor publisher or GPU work.
- Return: `returned_artifacts/` with per-case logs, `cases_result.json`, build and replay logs,
  `result.json` and `artifact_hashes.json`, checked locally into `return_verdict.json`.
- Replaying later Isaac stop poses (C5): `make_fixtures.py from-journals --returned-artifacts <run>/returned_artifacts --output-dir <dir>`,
  then `suite_worker.py --fixtures <dir>/suite_cases.json --run-id native_replay_<UTC>`. The default replay
  file has 5 starts or more (4 control starts plus each resubmission), polynomial seed 0 x3, empty map.

## Facts that refine design.md

- The -y map edge is 0.5 m from the route: the native harness never feeds odometry, so the sliding map
  stays at origin (-5, -5, 0) (`grid_map.cpp:88`). A box 1 m to the -y side would lie outside the map,
  so both boxes are on the +y side. Optimizer and FSM checks treat outside-map cells as occupied
  (`getInflateOccupancy` returns -1), so this edge acts as a wall for the box maps; the live map is
  centred on the robot.
- Follow-up replans do not only use the previous-trajectory branch: `planFromCurrentTraj`
  (`scan_replan_fsm.cpp:951-977`, REFERENCE_PATH mode) falls back to polynomial and random polynomial initialization,
  which reach line 171 again. The suite runs the same chain and records every attempt.
- The uninstrumented binary prints `SUMMARY` with three decimals, because `reboundReplan` sets
  `cout.precision(3)` (`planner_manager.cpp:91`). The suite therefore prints its own full-precision
  record, using the diagnosis 1001-sample acceleration method.
- SCAN libraries are static archives (`libplan_env.a` and others), so both variants link identical code.
- The RViz failed stop is at x = -1.14889 m (fact pass: -1.1487); display-off at -1.12976 m.
- Size: 1,668 process runs rather than about 1,640 calls plus 30 sequences.

## Claim boundary

A pass supports the one-line fix at the native planner boundary for these fixtures only. Fixtures use
PCT request poses plus the frozen body height, not captured SCAN arguments; boxes are synthetic.
No Isaac, controller, physical-robot or language-navigation claim follows. Step C remains gated on
Dr Sun's approval and a pass here.

`analyze_suite.py` writes the following source facts into `boundary_notes`. They were checked in
`p2b_execution/builds/scan_03/src/` on 2026-09-17:

- The 0.3 s and 0.6 s follow-up offsets are a stress schedule, not the live trigger. In `EXEC_TRAJ`,
  the live FSM replans once the robot is 1.0 m from the current trajectory start
  (`scan_replan_fsm.cpp:893`, `fsm.thresh_replan: 1.0` in `planner.yaml`). It also replans when
  `checkCollisionCallback` finds a collision (`scan_replan_fsm.cpp:1083`) or a new target or route
  arrives.
- SCAN's own collision checks cover only the first two thirds of a trajectory
  (`bspline_optimizer.cpp:1017-1018` after rebound optimization, `1115-1116` after refinement).
  `reboundReplan` has no final collision check: `planner_manager.cpp:298` checks dynamic feasibility
  only. AC4 therefore samples each accepted trajectory independently, every 0.01 s over its full
  duration.
- SCAN's acceleration gate samples every `max(0.01, min(0.05, duration/50))` s, which is 0.05 s for
  durations of 2.5 s or more. The loop runs while `t < duration + 1e-6`
  (`planner_manager.cpp:460-464`), so the last sample usually falls before the trajectory end. The
  harness maximum uses 1001 samples and includes `t = duration`. It can therefore exceed 1.5 m/s^2
  for accepted original-build trajectories. AC2 judges this maximum for candidate calls only.
