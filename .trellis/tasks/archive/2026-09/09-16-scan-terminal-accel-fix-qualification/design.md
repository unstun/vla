# Design: qualifying the SCAN terminal-acceleration fix

All experiment paths are relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`. File references come
from the read-only fact pass of 2026-09-16 and must be re-checked when implementing.

## 1. Building `scan_04`

Facts: `backend_adapter/backend_adapter/materialize_overlay.py` hash-checks 6 source files and patches messages, FSM,
controller and launch file, but never `planner_manager.cpp`. `p2b_execution/build_scan.py <name>` only builds an
existing `builds/<name>/src`. There is no install-identity capture script.

Steps:
1. Materialize a fresh overlay into `p2b_execution/builds/scan_04/src` with the unchanged materializer (its SHA must
   still equal `69954316…`, the one that produced `scan_03`).
2. New script `p2b_execution/apply_scan_terminal_accel_fix.py`:
   - refuses unless `planner_manager.cpp` has the recorded base hash (`0c51df…`) and line 171 is exactly
     `start_end_derivatives.push_back(gl_traj.evaluateAcc(t));`;
   - replaces `t` with `time` on that line only;
   - writes `builds/scan_04/terminal_accel_fix_manifest.json` (script hash, before/after file hash, unified diff).
3. Tree check: `scan_04/src` against `scan_03/src` differs in exactly one file and one line. This also shows that the
   materializer reproduces `scan_03`.
4. `build_scan.py scan_04` (Release, Foxy image `e4aa7154…`, existing remote hash checks).
5. New script `p2b_execution/capture_install_identity.py`: hashes the remote `install/` tree into
   `builds/scan_04/install_identity.json`, in the same form the lead recorded for `scan_03`.

`scan_03` is never rebuilt or edited.

## 2. Native A/B suite

New directory `scan_fix_qualification/`. The recorded `scan_replan_diagnosis/` package and runs stay unchanged. The
suite copies the replay executable and extends it. It compiles two variants against the same installed libraries:
original (`scan_03` `planner_manager.cpp`) and candidate (`scan_04` `planner_manager.cpp`), both uninstrumented, via
the existing `-DSCAN_MANAGER_CPP=` mechanism.

Executable extensions:

| Need | Change |
|---|---|
| Obstacles | `--occupied-boxes FILE`: axis-aligned boxes marked with `grid_map_->setOccupied`, which also updates inflation. Prints `MAP_CONDITION boxes=N`. |
| Seeds, random init | Existing `--seed` and `--random-poly`. |
| Follow-up replans | `--follow-up-offsets 0.3,0.6`: after an accepted plan, take the state at each offset along the new trajectory as the next start and call `reboundReplan` again in the same manager. Later calls use the previous-trajectory branch, which reads `node_->now()`. The node therefore runs with `use_sim_time` and the executable sets the clock itself, so the offset is exact. If that proves infeasible, fall back to wall-clock timing and record the actual offset (see risk R2). |
| Endpoint | For each accepted trajectory, print the XY and Z distance from the spline end to the target. |
| Collision | Sample each accepted trajectory every 0.01 s and count samples where `getInflateOccupancy` is set. |
| Acceleration | Print the sampled maximum acceleration of the returned trajectory (same sampling as the diagnosis). |

Fixtures (`scan_fix_qualification/make_fixtures.py`, derived from recorded journals and `inputs/cases.json`):
- starts: the 4 recorded cases; the display-off and RViz failed stop poses; a sweep of the failed-resume start along
  x from -1.20 to -1.06 m in 0.01 m steps (15 poses), same target and velocity context;
- initialization: polynomial with seed 0 (3 repeats, as in the diagnosis), and random initialization with seeds 0-9;
- maps: empty; one box about 1 m beside the route; one box about 0.3 m beside the route, inside inflation reach;
- follow-ups: offsets 0.3 s and 0.6 s from every sweep pose, empty map, polynomial init.

Size: 21 starts x 13 initialization runs x 3 maps x 2 builds, about 1,640 calls, plus 30 follow-up sequences
(15 sweep poses x 2 builds, two follow-up calls each). Each call took about 0.11 s in the diagnosis, so the suite runs in minutes on CPU.

`scan_fix_qualification/analyze_suite.py` computes PRD AC2-AC6 into `comparison.json` and a short table. The
thresholds are read from `thresholds.json`, frozen and hashed before the first remote run.

## 3. Isaac launcher changes

In `isaac_runner/run_two_goal_pilot.py`:
- **SCAN hash gate.** The remote worker compares the mounted workspace with `source_sha256.json` and
  `install_identity.json` before starting, and refuses on any mismatch. Today it only checks that `install/` exists.
- **Cancel distance option.** `--cancel-displacement-m`, default 0.40 as now. The value is recorded in
  `run_request.json`. `review_two_goal.py` keeps its absolute check (displacement at least 0.4 m) whatever trigger is
  used. So only triggers of 0.40 m and above are used, and the launcher refuses a trigger that would come within
  0.3 m of goal A along the route.
- Record the GPU memory peak and total wall time. Actual4 lacks both.

## 4. Isaac series

- Episodes (PRD D12): 6 at the default 0.40 m trigger, then one each at 0.45 and 0.50 m, so 8 in total. The 0.40 m
  episodes target the original build's failure band (resume x in [-1.19, -1.11] m from the native sweep); the
  later triggers check positions further along. Stop positions also vary without a trigger change.
- Display off; the runner's own third-person video is kept. Runs are sequential, and each is reviewed with
  `review_two_goal.py` before the next one starts. Stop rule per PRD D11 (Dr Sun, 2026-09-17): run all 8; stop
  early only on the same failure twice in a row, an integrity failure, or a reset, pose injection or contact
  failure; one retry for infrastructure failures, reported separately.
- Statistics (one-sided 95 %, exact binomial): 8/8 supports a success probability of at least 0.69, 7/8 at least
  0.53, 6/8 at least 0.40. The report says so, and claims no more.
- Nothing else of ours uses the 5070 Ti GPU during the series (MIP is halted, Dr Sun 2026-09-17).

After the series, the stop pose of every new episode is replayed natively with both builds (CPU, seconds). This
shows whether the series actually reached poses where the original build fails. If no episode did, the Isaac
series says little about the fix, and the report says so.

## 5. Result visualization (Dr Sun asked for it before implementation)

Deliverables:
- One HTML report page, published as a private claude.ai Artifact.
- Static PNG copies in `scan_fix_qualification/figures/`, local-only with manifest lines.
- `scan_fix_qualification/RESULT.md` with the tables and figure references.

Every panel is generated by a script from returned files; nothing is typed in by hand.

| # | Panel | Encoding | Question it answers |
|---|---|---|---|
| 1 | Verdict table | AC1-AC8, pass/fail, evidence link | Did the fix qualify? |
| 2 | Where the bug bites | x: resume start position (m); y: sampled max acceleration of the planned path (m/s^2); original and fixed as two series; dashed line at the 1.5 gate; rejected plans drawn on the gate as crosses. Isaac stop positions as ticks on the x axis: the 4 old runs (1 pass, 3 fail) and the 8 new ones. | Does the failure depend on the stop position, and does the fix remove it across the whole range? |
| 3 | Pass/fail grid | One small grid per map (empty, far box, near box): rows are the 21 starts, columns the 13 initializations, each cell split original / fixed. Colours: accepted; rejected by the acceleration gate; rejected for another reason; accepted with a collision sample. | Does the fix change anything besides the gate rejections? |
| 4 | Endpoint distance | Strip plot per build, dashed line at 0.05 m | How far from the target do accepted paths end? |
| 5 | Top-down paths | Three cases (failing resume, near box, one follow-up sequence): target, inflated box, original and fixed paths, scale bar | What do the paths look like, and how close are they to the obstacle? |
| 6 | Follow-up replans | Max acceleration per call (1, 2, 3) per sequence, both builds | Do consecutive replans stay under the gate? |
| 7 | Isaac episode table | Episode, trigger, stop x, native verdict at that stop (original / fixed), 41/41, arrival error A and B, max non-foot force, wall time, GPU peak | Did every episode pass, and was the dangerous region reached? |
| 8 | Isaac top-down overlay | All 8 robot paths from `metrics.jsonl` `base_xyz`; start, cancel and stop points; goals A and B with 0.25 m circles | Where did the robot go, stop and arrive? |
| 9 | Isaac timeline (one episode selectable) | Speed, command, non-foot force over simulation time, with event markers: cancel, still confirmed, resubmit, arrive A, arrive B | What happened around the cancel and resubmission? |
| 10 | Walk review video, one per episode (see 5.1) | Camera view, top-down trail and timeline in one synchronized, compressed MP4 | How did the robot actually walk, stop and resume? |

The page states the claim boundary (PRD AC8) above the charts.

### 5.1 Walk review video (Dr Sun, 2026-09-17: "show me how the robot dog actually walked")

`isaac_runner/make_walk_review.py <run dir>` builds one MP4 per episode from returned or remote files:
- **Layout, 1280x720:**
  - top left: the third-person camera (`third_person_master.mp4`, 1920x1080 at 12.5 fps) scaled to 853x480;
  - top right: a top-down map with the growing robot trail and heading, goals A and B with 0.25 m circles, the
    cancel point and the stop point;
  - bottom strip: speed, command and non-foot force over simulation time, with a moving cursor and event markers
    (cancel, still confirmed, resubmit, arrive A, arrive B);
  - banner: episode ID, simulation time and current phase.
- **Sync:** each video frame's `sim_time_s` comes from `camera_frames.jsonl`, the robot state from `metrics.jsonl`,
  and the events from `pilot_journal.json`. Nothing is interpolated beyond the recorded 0.02 s state samples.
- **Size:** H.264, CRF about 30, source frame rate, target at most 2 MB per episode of about 17 s (the source
  video is 7.6 MB).
- **Placement:** on the 5070 Ti it runs after each episode ends and before the next one starts, so it never shares the
  GPU with Isaac. A prototype is rendered locally from `actual4` before any new run.

### 5.2 Local storage budget (Dr Sun, 2026-09-17: low local disk)

Measured: an `actual4` run package takes 58 MB locally. That is `clouds.jsonl` 24 MB, the original video 7.6 MB,
per-run copies of the PCT runtime and inputs about 15 MB, and journals plus metrics about 7 MB. Eight runs would add
about 460 MB. Reductions:
- The run package hardlinks the frozen PCT runtime and input files instead of copying them (same hashes, APFS/local
  filesystem only, copy fallback); saves about 15 MB per run.
- Optional `--remote-only-bulk` (default off; needs Dr Sun's yes): `clouds.jsonl` and the original
  `third_person_master.mp4` stay in the 5070 Ti execution copy, and their SHA-256 values are returned and recorded as
  remote-only. The 41 checks use `pilot_journal.json`, not these files (`review_two_goal.py:39`). With it, about
  12 MB per run plus a review video of 2 MB or less.

## 6. Adoption and rollback

- Adoption means that later pilots pass `builds/scan_04` as `--accepted-scan-build-dir`, and the HarnessVLN README
  and task records name it. The materializer default is untouched; the fix stays a separate, recorded step.
- Rollback is to pass `scan_03` again. No production file is overwritten, so nothing needs restoring.

## Risks

- R1 The candidate still uses the original sampling and least-squares fit. Its endpoint is 2.7-3.6 cm off; AC3 and
  the Isaac arrival checks bound this.
- R2 Follow-up replans depend on node time. If exact sim-time control is not possible in the single-process harness,
  offsets become approximate and are reported as measured.
- R3 The native fixtures use PCT-request poses plus 0.35 m and 3-digit native output, not full captures. The Isaac
  series is the system-level check.
- R4 The Isaac route has no placed obstacle. SCAN still receives live lidar clouds, but no avoidance criterion
  exists. Native box maps are the only obstacle evidence in this task (question Q2).
- R5 The defect sits in a file identical to the pinned upstream base. Fixing it locally diverges from upstream; the
  manifest records the divergence.

## Decisions on the open questions (Dr Sun, 2026-09-16)

- Q1 Both run budgets approved; Isaac only after the CPU step passes.
- Q2 Placed-obstacle Isaac episode deferred to a separate task.
- Q3 Endpoint limit 0.05 m.
