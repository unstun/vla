---
origin: ai+local_evidence
date: 2026-09-10
reviewer: Claude Fable 5.1 (lead)
status: accepted_for_public_scene_functional_test
result_label: official evaluator on custom public-scene tasks, per camera condition
stage: experiment_and_analysis
trellis_task: .trellis/tasks/09-10-internvla-n1-camera-ablation-sim
---

# Lead review: Lite3 camera-condition ablation of InternVLA-N1 DualVLN

**Verdict: accepted.** All 20 authorized runs executed under the supervisor
with exit 0 and no timeouts, on the pinned model, evaluator, scene, and
frozen episodes. The returned evidence verifies locally. The result is a
public-scene functional test on two custom episodes, five unseeded runs each,
and is reported as effect sizes between camera conditions; it is not an R2R
benchmark and not a reproduction of any published score.

Paths are relative to `.pipeline/experiments/2026-09-08_dualvln_rented4090`
unless noted; `REQ` is this request directory.

## Independently verified by the lead

- `REQ/manifest.sha256`: 1,571 of 1,571 lines OK from the local experiment
  root (rounds 1 to 3: 787, 1,091, 1,571).
- All 20 `cam_*` runs record evaluator, `eval.py`, `vln_utils`, scene,
  navmesh, and annotation SHA-256 equal to baseline `public_eval_v5`
  (0 mismatches); each `inputs.json` carries the resolved geometry of its
  condition, equal to `REQ/conditions.json`.
- `REQ/matrix_log.jsonl`: 20 records, all `exit_code` 0, `timed_out` false,
  wall 118 to 417 s against the 1,800 s deadline.
- Preflight reports: all four pass. Sensor-state height, forward offset, and
  pitch (sign included) equal the specification exactly in every condition;
  implied agent-origin-to-floor gap 0.158 to 0.163 m in all four.
- Condition summary recomputed by the lead from `progress.json` and traces
  with `REQ/summarise_conditions.py`; the baseline reproduces 3/5 and 2/5.
- Start-frame PNGs and terminal frames of successful and failed episodes
  inspected (frames extracted locally with ffmpeg from `vis_debug` and
  `vis_0`); 80 MP4s decode without error per the returned ffprobe record,
  frame counts equal recorded steps except the one step-cap episode below.

## Results (two episodes, five runs each)

| Condition | Height | Pitch | HFOV | Look-down tilt | Ep1 success | Ep1 NE m min/med/max | Ep2 success | Ep2 NE m min/med/max | Ep2 collisions min/med/max | Learned STOP | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 | 79 | 15 | 3/5 | 1.05/1.25/4.06 | 2/5 | 2.15/4.89/5.91 | 8/10/10 | 10/10 | 5/10 |
| C1 Lite3 rig faithful | 0.42 m | 20 down, fixed | 54 | 0 | 1/5 | 1.06/12.18/16.94 | 0/5 | 4.27/12.00/14.79 | 9/15/83 | 9/10 | 1/10 |
| C2 height only | 0.42 m | 0 | 79 | 15 | 3/5 | 1.26/1.42/4.68 | 2/5 | 2.88/3.06/8.47 | 7/13/19 | 10/10 | 5/10 |
| C3 FOV only | 1.25 m | 0 | 54 | 15 | 2/5 | 1.21/13.88/16.30 | 1/5 | 2.49/5.42/9.05 | 2/4/4 | 10/10 | 3/10 |
| C4 raised mount | 0.65 m | 15 down, fixed | 54 | 0 | 2/5 | 0.79/14.45/16.90 | 0/5 | 4.51/8.93/10.20 | 17/40/58 | 10/10 | 2/10 |

Observations, descriptive only:

- C2 (camera lowered to 0.42 m, everything else as in the baseline) matches
  the baseline count exactly and keeps near-miss failures (episode 1 misses
  at 3.4 to 4.7 m) and collision counts in the baseline range.
- C3 (baseline camera with the D435i field of view) loses two episodes; its
  episode-1 failures are far misses (13.9 to 16.3 m) with the agent never
  closer than 4.5 m, one run looping around the central pillar for 364 steps.
- C4 (raised 0.65 m, fixed 15 degrees down, D435i FOV) never enters the
  episode-2 goal radius in five runs, with 17 to 58 collisions and 160 to
  269 steps; terminal frames show stops at other striped chairs with the
  paintings above out of view.
- C1 (the current Lite3 rig) is the weakest: one success in ten, episode 2
  never closer than 3.5 m, one run hitting the 500-step cap with 83
  collisions, and terminal frames that contain only floor and door bases.
  Its start frame has the horizon at the top edge; the instruction landmarks
  (paintings, windows, chairs between windows) are not in view.

Interpretation, not proven: on these two episodes the camera height alone is
harmless; the narrower field of view and the fixed downward pitch each cost
successes, and their combination in the current rig makes the planner stop
at look-alike furniture or wander. With five unseeded runs per episode the
table can only show large effects, and it does.

## Anomalies and criterion revisions (all recorded before the affected runs)

- Floor z-depth check: revised after round 1 from a 25 percent ratio to a
  bound on the implied agent-origin-to-floor gap; the constant 0.16 m gap is
  a navmesh property of the start pose that applies to the baseline alike
  (`REQ/preflight/round1_failed_ratio_criterion/`).
- Tilt no-op check: revised after round 2 from bit-identical frames to a
  bounded pitch delta and changed-pixel fraction; a zero-amount look_down
  re-normalises the sensor quaternion by 1 to 2 ULP and flips 0.31 percent of
  edge pixels with the camera unmoved
  (`REQ/preflight/diag_round2_tilt_noop_c1_lite3_rig.json`).
- `cam_c1_lite3_rig_v1` episode 2 terminated at the evaluator step cap
  (`final_step_id` 501) and its videos hold 502 frames: the evaluator writes
  the frame of the last loop iteration before the cap check ends the loop,
  so cap terminations record one frame more than steps. Not a data defect;
  the frame-count rule in the package should read `steps + 1` for cap
  terminations.
- `public_eval_v1` records a different evaluator hash than v2 to v5 (known
  from the earlier public-scene review; its metrics are unaffected).
- Executor deviations (unattended drivers, ffprobe from the pinned
  environment, `__pycache__` excluded from sync) are recorded in
  `REQ/OPUS_RETURN.md`; none touched geometry, criteria, or evaluator logic.

## Mount recommendation for the parent task

1. Do not deploy InternVLA-N1 DualVLN from the current Lite3 rig
   (0.42 m, 20 degrees down, D435i colour field of view).
2. Keep the height. 0.42 m did not cost anything on this test (C2), and the
   raised 0.65 m mount with the other two factors unchanged did not recover
   (C4), so a taller stand alone is not the fix.
3. Change the pitch to level, or at most a small downward angle, and widen
   the colour field of view to about the evaluation camera's 79 degrees
   horizontal (63 degrees vertical at 4:3). The authors deployed a RealSense
   D455, whose colour field of view is wider than the D435i's; its published
   figure was not verified this session. Depth must stay aligned to the
   colour frame.
4. Before the real-robot child, run one confirmatory simulation pair with the
   real-robot protocol (fixed camera, no look-down): C5 = 0.42 m, level,
   HFOV 79, tilt 0; C6 = 0.42 m, 15 degrees down, HFOV 79, tilt 0. C2 used
   the look-down protocol, which the real robot cannot execute, so C5 is the
   missing evidence for the geometry above. This needs a new authorization of
   ten runs; the present budget is fully used.
5. If the sim pair confirms, carry the geometry into the real-robot child,
   the sensor-rig URDF, and the LightNav Lite3 adapter together.

## Limits

Two custom episodes in one public scene; five unseeded runs per condition;
D435i field of view modelled at a 4:3 profile; nominal Habitat heights with a
0.16 m navmesh-to-floor gap at the start pose; no attribution of failures to
System 1 versus System 2 beyond the descriptive trace counts.

## Post-acceptance edits by the lead

After the round-3 manifest was verified (1,571 OK), the lead edited four
request-status files, so `shasum -a 256 -c manifest.sha256` now reports them
as FAILED by design: `request.json` and `OPUS_EXECUTION_PACKAGE.md` (status
set to `executed_lead_accepted`), and the regenerated `provenance.json` and
`authored_files.sha256`. Their current hashes are in `provenance.json`. No run
directory, preflight report, log, video, or summary was modified; this
review and `RESULT.md` are new files outside the manifest.

## Round 4 addendum (lead, 2026-09-10T16:17:08Z): head-camera proxy pair C5 and C6

Verdict: accepted. Executor Opus ran ten supervised runs
(`cam_c5_head_level_v1..v5`, `cam_c6_head_down15_v1..v5`), all exit 0, no
timeout, wall 122 to 189 s, peak GPU 22,385 MiB, isaac-sim untouched.
Verified locally: `manifest.sha256` 2,211 OK / 0 FAILED from the EXP root;
all ten `inputs.json` match `public_eval_v5` on evaluator, utils, scene,
navmesh, and annotation hashes; the condition summary recomputed locally is
identical to the executor's table; both preflights passed all eight stages
with measured height 0.400 m, offset 0.270 m, pitch 0.0 / 15.0 deg, implied
floor gap 0.158 m, and a tilt no-op with pitch delta 0 and changed-pixel
fraction 0 (below the 0.003 seen at 20 deg in round 3; inside the bounds, no
criterion change). Inspected: both preflight start frames (C5 horizon at
mid-frame, C6 horizon in the upper third, table leg in the foreground at
0.40 m), the end frames of `cam_c6_head_down15_v1` episode 1 (stopped beside
the high-backed chairs, success at 0.73 m) and episode 2 (stopped beside the
row of striped chairs at 3.46 m after passing the goal), and
`cam_c5_head_level_v1` episode 1 (stopped at the gilded table, 1.94 m).
All 20 round-4 episodes ended on a learned System-2 STOP; ffprobe frame
counts equal traced steps for all 20 videos.

| Condition | Height | Pitch | HFOV | Look-down | Ep1 success / oracle | Ep1 NE median | Ep2 success / oracle | Ep2 NE median | Ep2 steps median | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 | 79 | yes | 3/5 / 3/5 | 1.25 m | 2/5 / 5/5 | 4.89 m | 107 | 5/10 |
| C2 height only | 0.42 m | 0 | 79 | yes | 3/5 / 3/5 | 1.41 m | 2/5 / 4/5 | 3.06 m | 98 | 5/10 |
| C5 head proxy, level | 0.40 m | 0 | 79 | no | 1/5 / 1/5 | 4.69 m | 1/5 / 5/5 | 5.13 m | 113 | 2/10 |
| C6 head proxy, 15 deg down | 0.40 m | 15 down | 79 | no | 5/5 / 5/5 | 0.66 m | 0/5 / 5/5 | 5.84 m | 165 | 5/10 |
| C1 current rig (for reference) | 0.42 m | 20 down | 54 | no | 1/5 / 2/5 | 12.18 m | 0/5 / 0/5 | 12.00 m | 155 | 1/10 |

Reading, effect sizes only (five unseeded runs per cell):

1. Under the fixed-camera protocol that the real robot uses, pitching the
   camera 15 deg down changes the total from 2/10 (C5) to 5/10 (C6), entirely
   through episode 1 (1/5 to 5/5, median stop error 0.66 m, SPL 1.0). A
   fixed level camera is the worst wide-FOV geometry tested. This matches
   the training views (System 1 sees look-down frames; the authors' robots
   carry a D455 at 15 deg down).
2. Episode 2 is a stopping problem, not a reaching problem: oracle success
   is 5/5 for B0, C5, and C6, while success is 2/5, 1/5, 0/5. The agent
   crosses the goal region and stops later. C6 stops later than B0 on this
   episode (median 5.84 m vs 4.89 m, 165 vs 107 steps), so the fixed
   downward camera worsens the late stop here while fixing episode 1.
3. C6 equals the baseline total on these two episodes. With n = 5 per cell,
   one or two successes are within run-to-run variation; the claim is that
   the head-camera proxy is in the baseline's range, not that it matches it.

Comparison with the current rig: C6 differs from C1 by field of view
(79 vs 54) and 5 deg of pitch and scores 5/10 vs 1/10, with median stop error
0.66 m vs 12.2 m on episode 1.

Revised mount recommendation (supersedes the round-3 wording on pitch):
use the built-in head camera as it is mounted, fixed at about 15 deg down,
with the deployment adapter centre-cropping the 1280x720 stream to HFOV 79 at
4:3 (839x629 px at the third-party focal length). Do not re-mount it level.
The D435i is not the VLA colour camera. Before the real-robot child: the
camera-only measurement (intrinsics, pitch, height, latency) to replace the
estimated geometry, and a look at stop arbitration for the late-stop
behaviour on episode 2 (related task:
`.trellis/tasks/08-19-lite3-handheld-vla-stop-arbitration`).

Geometry caveat: C5/C6 height, offset, and pitch are estimates (vendor torso
mesh bracket; one third-party calibration of a Lite3 Venture). If the
measured pitch is nearer 11 deg than 15, the C6 result is a neighbour, not
the measured geometry.

Post-acceptance edits by the lead, round 4: `request.json`,
`OPUS_EXECUTION_PACKAGE.md`, `provenance.json`, `authored_files.sha256`,
`review/LEAD_REVIEW.md`, and `RESULT.md` were edited after the executor
generated `manifest.sha256`, so those six lines are expected to FAIL on a
later manifest check; every other line must stay OK.

## Round 5 addendum (2026-09-11): fused virtual camera, c7 accepted; c8 deferred to 5b

Verdict: c7 runs ACCEPTED as evidence (all five exit 0, no time-outs, learned STOP 10/10, no CUDA OOM); c8 not run
(preflight stage 8, the lead's provisional 200 ms fusion-cost bound, at 226.5 ms; every correctness stage passed).

Lead verification (local): manifest 2,524/2,524 OK; the three pinned evaluator files hash-equal to public_eval_v5 in all five
inputs.json; fused cfg / conditions.json / plugin / fusion-module hashes identical across the five runs; each inputs.json carries
the preflight sensor state (head 0.40 m, 0.27 m, pitch_down -16.7); summary table regenerated by the executor agrees with the
progress.json files read here; c7 v1 and c5 v1 episode-1 videos inspected frame by frame.

Results (per episode, five unseeded runs; oracle = entered the 3 m radius at some step):

| Condition | Ep1 success / oracle | Ep1 NE m min/med/max | Ep2 success / oracle | Ep2 NE m min/med/max | Total |
| --- | --- | --- | --- | --- | --- |
| B0 baseline 1.25 m | 3/5 / 5 | 1.05/1.25/4.06 | 2/5 / 5 | 2.15/4.89/5.91 | 5/10 |
| c5 ideal level, head pose | 1/5 / 5 | 1.94/4.69/7.86 | 1/5 / 5 | 2.71/5.13/8.61 | 2/10 |
| c6 ideal 15 deg down, head pose | 5/5 / 5 | 0.50/0.66/0.73 | 0/5 / 5 | 3.46/5.84/8.36 | 5/10 |
| c7 fused level, head pose | 0/5 / 0 | 7.07/7.45/7.94 | 0/5 / 5 | 3.10/7.58/7.74 | 0/10 |

Reading of episode 1 (the informative one). System 2 is deterministic given the image, and the five c7 runs follow one route:
the first three System-2 outputs are identical to c5 (right x4, right x4, look-down, pixel goal 103/275 vs c5 103/267), then
at step 17 c7 emits pixel goal 103/280 where c5 emits 45/302 (far left). From there c7 walks straight ahead to the nearer set of
high-backed chairs by the first window and stops in front of one after 55-65 steps, 7.1-7.9 m from the episode goal, with zero
collisions; c5 steers left and ends 1.9-7.9 m away (1/5 success); c6 reaches 0.5-0.7 m (5/5). The c7 stop is semantically
defensible for the instruction "stop near the high-backed chairs standing between the windows" but is not the annotated goal.
So the 0/10 is one route decision repeated five times, not a breakdown: the model runs normally on the fused input.

Effect size caveat. With five runs per episode, c7 0/5 vs c5 1/5 is not distinguishable (Fisher exact p = 1); what the data
do show is (a) the fused input changes System 2's pixel goal at the first divergence point by a few pixels and then the route,
and (b) the fused level camera is clearly worse than the ideal 15-deg-down camera (c6) on episode 1, which a fused camera
cannot reach (the bottom 14 percent would be blank). Episode 2 remains the late-stop failure seen in every condition (oracle 5/5,
two c7 runs stopped at 3.10 and 3.25 m, just outside the 3.0 m radius).

Image difference at the identical start pose: c7 fused vs c5 ideal, mean abs 6.7 levels over the image; 7 percent of pixels differ
by more than 20 levels, essentially the black corners; elsewhere edge-only resampling residue (PSNR 35 dB in the head region).

Process lesson (added to the spec): the round-5 return rsync of REQ/ overwrote the lead's local edits made while the executor
was running (the 300 ms bound and the 5b package section); re-applied afterwards. Lead-owned files must be excluded from the
executor's return rsync, or lead edits must wait for the return.

Remaining authorised runs: five (c8). Round 5b dispatched with the 300 ms bound; c8 (1.3 percent uncovered) tests whether the
corner size changes the episode-1 route choice.

## Round 5b addendum (2026-09-11): c8 accepted; fused-camera conclusion

Verdict: c8 runs ACCEPTED (five runs, exit 0, no time-outs, learned STOP 10/10; preflight nine stages passed with the
300 ms bound; fused image verified as in c7). The executor subagent stopped mid-round; the lead ran steps 5-7 (see OPUS_RETURN
Round 5b) and re-derived every number below from progress.json and the traces.

| Condition (head pose, level unless noted) | Ep1 success / oracle | Ep1 NE m | Ep2 success / oracle | Ep2 NE m | Total |
| --- | --- | --- | --- | --- | --- |
| c5 ideal render | 1/5 / 5 | 1.9-7.9 | 1/5 / 5 | 2.7-8.6 | 2/10 |
| c6 ideal render, 15 deg down | 5/5 / 5 | 0.5-0.7 | 0/5 / 5 | 3.5-8.4 | 5/10 |
| c7 fused, D435i 640x480, 6.0 % uncovered | 0/5 / 0 | 7.1-7.9 | 0/5 / 5 | 3.1-7.7 | 0/10 |
| c8 fused, D435i 1280x720, 1.2 % uncovered | 2/5 / 5 | 2.0, 2.8, then 17.3-17.5 | 0/5 / 5 | 7.5-9.7 | 2/10 |

Reading. (1) Corner size decides the episode-1 route: with 1.2 percent uncovered, System 2 emits the leftward pixel goal
(46/291) at step 26 in four of five runs and 103/275 in the fifth, and all five runs reach the goal radius (minimum distance
2.0-2.8 m); with 6.0 percent uncovered (c7) none did. (2) Stop timing, not navigation, then decides success: c8 v1 and v2 stop
inside 3 m; v3-v5 pass through the goal area and keep walking for 100 more steps, ending 17 m away after a long sequence of
pixel goals, the same late-stop behaviour as episode 2 everywhere. (3) c8 equals c5 (2/10): a fused level camera with small
corners behaves like the ideal level camera at that pose; neither approaches the ideal 15-deg-down camera (c6, 5/10 with
ep1 5/5), which fusion cannot reach because the D435i does not see below -41 deg.

Effect sizes are one-instruction, five-run counts (Fisher exact, ep1: c8 vs c7 p = 0.44; c6 vs c8 p = 0.17); the
oracle-success difference on ep1 (c8 5/5 vs c7 0/5, p = 0.008) is the one statistically clear result.

Deployment implication for the decision in the parent task: if the fused route is taken on the robot, the D435i colour stream
must run at 1280x720 (or the corners must be inpainted); even then the expected performance is the level-camera performance,
not the downward-camera performance. A wide camera on the 20-deg carrier remains the only route with c6-like geometry.

Local verification (round 5b): c8 inputs.json pinned hashes equal the baseline; cfg/plugin/module hashes equal c7's;
conditions.json hash differs from c7's by the documented 300 ms bound edit; manifest verification count recorded below after
the final regeneration.

Final manifest (after uploading the lead-edited review/result/return files and the locally regenerated ffprobe counts):
2,892 lines; remote self-check OK; local `shasum -a 256 -c`: 2,892 OK / 0 FAILED (2026-09-11 08:30 UTC). Remote
`authored_files.sha256`: 26 OK. Total authorised runs used: 40 of 40.

## Round 6 addendum (2026-09-11): C9, the fused virtual camera pitched 9 degrees down

Authorization: Dr Sun, "Run C9 with the virtual camera 9° down." Five supervised runs, task total 45. Driven by the lead
directly (no executor subagent), because the round-5b executor stopped itself twice while idling on its own watcher.

Preflight (12:37 UTC, all nine stages passed): fused rgb bit-identical to the offline recompute; 71.8 pct of pixels differ
from the ideal render, so the task sensor is what the model receives; uncovered 3.30 pct (bound 0.05), head 63.6 pct
(bound 0.55), blend 1.43 pct; head-region PSNR 34.66 dB and d435-region 39.73 dB against the ideal render; virtual camera and
evaluator depth measured at 9.0 deg down, head at 16.7 deg up, D435i at 20.0 deg down, all exact; fusion 256.4 ms mean
(bound 300); implied floor gap 0.1576 m, inside the 0.158-0.163 m that every earlier condition measured.

That floor figure is the check that justified the preflight correction. The level-only expectation this round replaced would
have computed 0.687 m instead of 0.548 m and reported the gap as 0.046 m, which is inside the accepted [-0.05, 0.30] band:
it would have passed while being wrong, rather than failing.

Runs: five, all exit 0, no timeouts, 301-367 s wall, learned STOP 10/10.

### Result

| Metric | C6 ideal 15 down | C7 fused level | C8 fused level 720 | C9 fused 9 down |
| --- | --- | --- | --- | --- |
| Ep1 success / entered radius | 5/5 / 5 | 0/5 / 0 | 2/5 / 5 | 0/5 / 0 |
| Ep1 NE min/med/max (m) | 0.50/0.66/0.73 | 7.07/7.45/7.94 | 1.97/17.28/17.54 | 3.55/4.10/7.38 |
| Ep1 steps / s2 calls (median) | 69 / 17 | 58 / 17 | 167 / 41 | 62 / 15 |
| Ep1 s1_stop_mid_segment | 5 | 16 | 13 | 4 |
| Ep2 success / entered radius | 0/5 / 5 | 0/5 / 5 | 0/5 / 5 | 1/5 / 5 |
| Ep2 NE min/med/max (m) | 3.46/5.84/8.36 | 3.10/7.58/7.74 | 7.46/8.71/9.68 | 1.96/4.04/5.24 |
| Total | 5/10 | 0/10 | 2/10 | 1/10 |

C9 is 1/10 against C8's 2/10, so on the headline number the pitched camera did not pay. Two details qualify that.

**The extra black did not disturb System 1.** C9 carries 3.30 pct uncovered against C8's 1.23, yet `s1_stop_mid_segment` on
episode 1 falls to 4, the lowest of the fused set and below C6's 5, against 13 for C8 and 16 for C7. The hypothesis carried
since round 5 that uncovered pixels make System 1 stop mid-segment is not supported by this round: C7's 16 came with corner
black, C9's scattered bottom black produces the cleanest System-1 behaviour of the three. Whatever hurt C7, it was not the
uncovered fraction as such.

**Episode 2 improved, and it is the more informative episode.** C9's final navigation error is the lowest of every condition
tested at the head pose and lower than the 1.25 m baseline: median 4.04 m (min 1.96) against 8.71 for C8, 7.58 for C7,
5.84 for C6, 5.13 for C5 and 4.89 for B0. Only C2, the 0.42 m level camera with the look-down protocol, is lower at 3.06.
C9 also converts one run, which no other fused condition did on this episode.

### The limitation this round exposes

Episode-1 oracle success by condition is B0 3/5, C5 1/5, C6 5/5, C7 0/5, C8 5/5, C9 0/5, and within each condition the five
unseeded runs are near-unanimous. That pattern is not monotone in pitch, in field of view, or in uncovered fraction. It is the
signature reported in round 5: System 2 locks one route for a given image stream and the lock flips on small input changes.
With one condition per geometry, episode 1 therefore cannot separate a geometry effect from a route lock. C9 against C8 gives
Fisher p = 0.0079, and C9 against C6 the same, but both compare a condition that locked the wrong route against one that
locked the right one, which is not the same as measuring the camera.

This cuts both ways and is worth stating plainly: it weakens C6's 5/5 as evidence that 15 degrees down is better, exactly as
much as it weakens C9's 0/5 as evidence that 9 degrees down is worse. The two-episode design is the binding limitation of this
ablation on the success metric, and no number of extra runs on the same two episodes will fix it.

### Verification

Five `inputs.json`: pinned evaluator and checkpoint hashes equal the baseline `public_eval_v5` in every run; one distinct
hash across the five for `conditions.json`, `fused_camera_plugin.py` and `fused_camera.py`. The fusion core
`fused_camera.py` hashes `382eee6d...` in all fifteen c7, c8 and c9 runs, so the three fused conditions provably differ only
in configuration. ffprobe: 180 videos, no errors, every c9 frame count equal to its step count.

The round-5b manifest was re-verified against the current tree before regeneration: 2,873 of 2,892 OK, and all 19 failures
are request-directory files that round 6 legitimately changed (code, conditions, summaries, logs, provenance, review,
result). No file under `runs/` or `public_scenes/runs/` moved, so rounds 1-5 run evidence is byte-intact.

The manifest scope was previously undocumented and could not be reproduced from the round-5b file, whose 2,892 lines silently
excluded the baseline `public_eval_*` runs, other requests' runs (`zh_chairs_v1`, `video_v2`, `sim_episode_*`) and parts of
`public_scenes/data`. It is now stated explicitly and is a superset of the old one: this request's directory,
`public_scenes/configs`, `public_scenes/scripts`, `public_scenes/runs/cam_*` and `runs/cam_*`, excluding `__pycache__` and
the manifest itself.

### Conclusion for the route

C8 remains the configuration to deploy. C9 does not displace it on the current evidence, but "9 degrees down is worse" is not
established; what is established is that the success metric on episode 1 is a route lottery at this sample size, and that on
the one episode with a continuous metric the pitched camera is the best geometry tested. The decisive problem is unchanged
from round 5b and is not a camera problem: every condition reaches the goal area far more often than it stops in it.

Final manifest (round 6, after uploading the lead-edited review/result/return files and the locally regenerated ffprobe
counts): 3,190 lines under the scope stated above; remote self-check 0 non-OK; local `shasum -a 256 -c`: 3,190 OK /
0 FAILED (2026-09-11 13:20 UTC). Remote `authored_files.sha256`: 27 OK. Round-5b manifest re-verified before regeneration:
2,873 of 2,892 OK with all 19 failures in round-6-owned request files and none under `runs/`. Total authorised runs used:
45 of 45 (40 rounds 1-5, 5 round 6).
