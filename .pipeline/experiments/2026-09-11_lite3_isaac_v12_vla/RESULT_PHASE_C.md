# Phase C result: InternVLA-N1 drives the walking Lite3 end to end (C.1-C.5)

Runs: 2026-09-14 UTC on the rented RTX 4090. Stage: experiment + analysis.
Label: **integrated** for the closed loop. It runs:

    language instruction -> InternVLA-N1 (System 2 + System 1) -> upstream MPC/PD -> bridge clamp and watchdog
    -> V12 policy -> PhysX -> rendered RGB-D -> back to the VLA

and it produces AC6's evidence.

**Not validated as a navigator:** none of the six real episodes succeeded (0/6). AC7's failure characterisation (C.4,
below) is done over those six episodes, and C.5's independent review corrected it (see "Lead review" at the end).

The short answer:
- **Locomotion held:** no falls.
- **The bridge clamp and watchdog were never needed, and never exercised.**
- **Two kinds of failure:**
  - the model said STOP with the target behind the robot;
  - in one run the robot passed an obstacle too close. That is the stack's failure: nothing plans for the robot's
    body width.

  The contact monitor that caught the collision is a simulator measurement, not a safety layer the robot has.

## What was built (C.1, C.2)

All code is task-owned, in `phase_c/`, with pinned code unmodified. The rules behind it are design Decisions 5-7 and the
AC5 amendment in `prd.md`.

| file | role |
| --- | --- |
| `lockstep_protocol.py` | the pinned bridge `protocol.py` plus `IMAGE_FRAME_V1` and `STEP_REQUEST_V1`; the only differences are in `lockstep_protocol.diff` (see `PROTOCOL_COPY.md`) |
| `isaac_lockstep_server.py` | V12 scene via the pinned adapter's `_configure_environment`, one-robot PhysX buffers, head RTX camera (640x480, HFOV 79, RGB + depth), chase camera, landmark boxes. Commands pass through the bridge's `LatestCommandState` on the simulated clock; contact goes through `SubstepContactMonitor`. It advances only on request. |
| `vla_lockstep_client.py` | upstream's Go2 client on the lockstep clock: JPEG and uint16 depth encoding, look-down follow-up, trajectory to world with odometry at image time, pinned `controllers.py` MPC and PD at 0.1 s ticks, plan applied after the measured latency, next image after max(L + 0.05, 0.3) s |
| `fake_lockstep_server.py`, `test_lockstep_local.py` | GPU-free test double using the pinned clamp and watchdog; 4 tests: scripted episode, latency timing, clamp and watchdog trip at 250 ms simulated, stale-command rejection |
| `../scripts/phase_c_run_episode.sh` | host driver: guards (disk, GPU idle, no other vla-phase container, checkpoint and `controllers.py` hashes), sampler, both processes, video |

An independent code review found and fixed five defects before any GPU run:
1. relative paths broke after the client's `chdir`;
2. the depth-anything symlink leaked when the client exited on an error;
3. a V12 fall reported the reset pose;
4. a server crash left the client waiting;
5. substep contact times were up to one policy step early.

It also caught that `trajectory_tovw` cannot run on the shipped trajectory (below). I verified each fix by reading it and re-running the tests, and made three further
changes of my own: the plan now applies at the measured latency (upstream `planning_thread`) rather than at the
period's end, a warm-up call as upstream's server makes, and a safe zero command if an MPC solve fails. CasADi 3.7.2 is
installed only in this task's `pydeps/` (`setup/phase_c_pydeps.json`).

## Smoke run with a scripted agent (`phase_c_smoke_scripted_v1`)

This run tested the real Isaac side with canned VLA answers.

- **Result:** both processes exited 0 and both sides recorded `client_end`.
- **Contact monitor:** inspected all 560 physics substeps (4 per policy step) and saw 0 N non-foot force.
- **Command path:** 30 requests, 0 watchdog events, 0 sequence gaps, 0 clamped steps, and no step ever stale.
- **Motion:** the MPC walked the robot 0.39 m at up to 0.40 m/s.
- **GPU:** Isaac with both cameras used 3,832 MiB.
- **Placement:** the robot started at (0.02, 0.005) facing +x. The head camera shows the red box straight ahead, blue on
  the left and green on the right, as the episode places them.

## The first real episode (`phase_c_red_box_v1`, C.3)

Episode `c_red_box_ahead_v1`: "Walk to the red box and stop in front of it." The red box starts 3.98 m straight ahead;
success means the model stops within 1.0 m of the box centre.

**What happened** (`analysis/phase_c_red_box_v1_topdown.png`, `analysis/phase_c_red_box_v1_frames.jpg`, videos in
`runs/phase_c_red_box_v1/isaac/{chase,head}.mp4`):

1. System 2's first answer was `←←←←`, a 60° left turn, although the box was dead ahead. The PD controller turned the
   robot to about 30°.
2. The following look-down cycles returned pixel goals (`206 311`, `526 253`, `451 265`, ...). System 1 turned these
   into trajectories, and the MPC tracked them. The robot straightened out on a line about 1.0 m north of the box.
3. It passed the box on its left. Closest approach was 1.05 m at t = 15.1 s, just outside the success radius. The box
   was already about 65° to the right at 14.0 s and 90° at closest approach, outside the 79° field of view; the head frame
   at that moment shows empty floor. (An earlier draft said 63° at closest; the logged yaw gives 90°.)
4. It kept walking. The STOP image was taken at 26.5 s at (6.9, 0.65); STOP took effect at 27.0 s at (7.09, 0.61),
   3.15 m from the box, and the episode ended 3.17 m away after the 1 s hold. In the STOP image the box was 151° to the
   right, behind the robot. This is a late stop, but not the Habitat ablation's pattern, where runs reached the radius
   first (see C.4).

**Loop evidence, all from the logs:**

| quantity | value |
| --- | --- |
| termination | `client_end` after the model's STOP and a 1 s PD hold; both processes exit 0 |
| decisions / simulated time | 44 decisions over 28.0 s simulated (1,400 policy steps, 5,600 contact substeps) |
| System 2 cycles | 9 (the agent's own `test_data/*/llm_output_*.txt`); 7 of them with look-down |
| System 2 cycle with look-down + latents | median 1.75 s wall -> plan applied after 18 ticks |
| System 1-only decision | median 0.263 s, max 0.316 s -> 3 ticks old plan + 1 tick new plan, a 0.4 s simulated decision period |
| commands | MPC v up to 0.40 m/s, PD w up to 0.50 rad/s; clamp (0.75 / 0.35 / 1.0) never engaged |
| locomotion | on policy steps with applied vx > 0.20 m/s: applied 0.364 m/s mean, body 0.319 m/s (88 %, as Phase A); height 0.294-0.330 m; no fall, no reset. (`phase_c_analyse.py` uses \|vx\| or \|wz\| > 0.05 instead and gives 0.318 / 0.280, also 88 %.) |
| safety layer | 0 watchdog events, 0 sequence gaps, 0 N non-foot contact, no case failure, no MPC solve failure |
| GPU | whole device 21,565 MiB at the end with both processes resident |

## Defects found in the evidence, and what was done

- **System 2 detection (fixed for later runs).** The client inferred System 2 calls from a change in `last_s2_idx`. The
  warm-up call leaves it at 1: `step_s2` increments the step index at line 191 before `step` copies it at line 134, and
  `reset()` does not touch it. Decision 1 sets it to 1 again, so that System 2 call went unflagged, and its `llm_output` is
  missing from `decisions.jsonl`. The agent's own text files recover it (`←←←←`). The client now counts `step_s2` and
  `step_s1` calls directly through instance wrappers, and a test covers it.
- **`trajectory_tovw` never produces a value.** Upstream's real-world agent returns an (x, y) trajectory, while
  `trajectory_tovw` reads `subgoal[2]`, so every call raises IndexError. The error is recorded in each decision. The
  method is dead code upstream, not a baseline.

## Failure characterisation over six episodes (C.4, AC7)

The set is Dr Sun's choice, "5 episodes: red x3, blue, green", plus C.3's `phase_c_red_box_v1`, which finished about 20
minutes earlier. The five C.4 runs ran as one supervised chain on 2026-09-14, from 07:48 to 08:10 UTC.
- **Held constant:** all six share the course, start pose, server, protocol, driver and both checkpoints.
- **Varied:** the instruction, and the client revision. `phase_c_red_box_v1` ran the earlier client, which lacks only
  the System 2 call counter (`setup/phase_c_executed_source.json`).
- **Run integrity:** every run exited 0 on both sides, no unrelated container changed, and each was collected with a
  manifest (0 non-OK entries).

The analysis is `scripts/phase_c_analyse.py`, one script for all six runs. Outputs are `analysis/phase_c_summary.json`
and `analysis/<run>_topdown.png`. The C.5 review recomputed every table value with independent code.

| run | instruction target | outcome | closest to target | STOP at | distance at STOP | distance at episode end | S2 cycles | path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `phase_c_red_box_v1` | red, 3.98 m ahead | STOP, fail | 1.05 m at 15.1 s | 27.0 s | 3.15 m | 3.17 m | 9 (log: 8) | 7.6 m |
| `phase_c_red_box_v2` | red | STOP, fail | 1.22 m at 15.4 s | 34.8 s | 6.04 m | 6.07 m | 11 | 10.6 m |
| `phase_c_red_box_v3` | red | STOP, fail | 1.12 m at 14.7 s | 30.9 s | 4.73 m | 4.76 m | 10 | 9.0 m |
| `phase_c_red_box_v4` | red | STOP, fail | 1.15 m at 16.7 s | 23.4 s | 2.45 m | 2.50 m | 8 | 6.7 m |
| `phase_c_blue_box_v1` | blue, 3.89 m front-left | STOP, fail; **inside the radius 16.6-20.8 s** | 0.80 m at 18.3 s | 38.0 s | 5.39 m | 5.41 m | 17 | 10.5 m |
| `phase_c_green_box_v1` | green, 4.29 m front-right | **non-foot contact with the blue box** at 17.9 s, no STOP | 4.22 m at 2.9 s | - | - | 5.41 m (at contact) | 8 | 3.9 m |

Success is 0/6. Oracle success (ever within 1.0 m) is 1/6, the blue episode. The red v1 S2 count comes from the agent's
text files; its `decisions.jsonl` under-reports decision 1 (see "Defects" above).

### AC7's three questions

1. **Does the robot fall?** No: 0 falls and 0 resets in 177.0 s simulated (8,850 policy steps). The minimum root
   height per run was 0.292-0.297 m.
2. **Do commands saturate the clamps?** The bridge clamp (0.75 m/s, 1.0 rad/s) never engaged: 0 clamped policy steps in
   every run. The upstream controllers saturate at their own, lower limits instead:

   | controller limit | share of time at the limit | runs |
   | --- | --- | --- |
   | MPC `v_max` 0.40 m/s | 47-53 % of policy steps | all six |
   | MPC `w_max` 0.40 rad/s (`controllers.py` line 15) | 6.1 / 3.9 / 2.2 / 12.7 / 2.6 / 14.5 % of control ticks | red v1-v4, blue, green |
   | PD `max_w` 0.50 rad/s | 0.5-12 % of policy steps | all six |

   The binding limits are upstream's, not the bridge's. The clamp and the 250 ms watchdog were never exercised on the
   GPU; their trip behaviour is tested only in the GPU-free double (`test_lockstep_local.py`).
3. **Does the 0.2 s command-history lag matter at the VLA's decision rate?** It is visible, but none of the failures
   traces to it.

   **Step responses.** Steps from rest (|command| below 0.05, then above 0.2 held for at least 0.5 s), read from
   `isaac_steps.jsonl`, which logs velocity after each 20 ms step:

   | | 63 % of the command reached | 90 % reached |
   | --- | --- | --- |
   | forward speed | after 100-180 ms | after 240-440 ms |
   | yaw rate | after 60 ms | after 60 ms |

   **Cross-correlation, for comparison.** Over the whole episode it peaks at 80 ms for forward speed and 40 ms for
   yaw rate. The forward peak is flat across 60-120 ms, and closed-loop feedback biases it low (the MPC re-solves from
   measured odometry every 0.1 s), so it understates the forward lag.

   **Decision periods, simulated time:**
   - a System 1-only decision takes 400 ms (inference latency median 0.262-0.269 s);
   - a look-down System 2 cycle takes a median 1.8-1.9 s. Green's lower System 2 median, 1.5 s, comes from 0.6 s
     arrow-action cycles.

   **Comparison.** Forward speed takes about as long to settle as one System 1 decision period, and far less than a
   System 2 cycle. On average the body reaches 86-89 % of the commanded forward speed while moving, as in Phase A.

   **What the lag does not explain.** No run fell or failed a solve. Every failure below is explained by
   what the model saw or decided, or by body clearance.

The safety counters recorded zero events in every run: 0 watchdog events, 0 sequence gaps, 0 MPC solve failures. The
whole GPU ended at 21,535-21,565 MiB.

### Failure modes observed

1. **Sideways pass, then STOP with the target behind the robot (5 of the 5 episodes that ended with STOP).**
   - **Red, all four runs:** the robot passes the box on its left, closest 1.05-1.22 m at 14.7-16.7 s, with the box
     82-90° to its right.
     - The box centre left the head camera's ±39.5° view at 10.1-11.8 s (1.7-2.1 m away); its last corner left at
       12.3-14.0 s (1.3-1.6 m). Both angles are measured from the camera origin, 0.27 m ahead of the base.
     - STOP came 6.7-19.4 s after closest approach, 2.45-6.04 m from the box.
   - **Blue:** the robot was inside the success radius for 4.2 s, but the box was 56-118° to its right the whole time,
     never in view. The one System 2 cycle inside the radius (image at 18.1 s, 0.81 m) saw the box at 80° right. It is
     the same sideways pass as red, not a failure to stop on a visible target.
   - **At STOP, and at every repeated pixel goal, the target was 57-164° to the right**, out of view: red v2's four
     `261 297` answers, red v3's and v4's `318 295` pairs, and blue's `436 278` pair.
   - **Not the Habitat late stop.** In the camera ablation, late-stopping runs had reached the success radius (oracle 5/5
     on episode 2). Here red never reached it, and every STOP was issued with the target out of view.
2. **Body-clearance collision (green).** The target was front-right, but the robot walked north-east, towards the blue
   box.
   - **The plan in force:** decision 27, applied at 16.3 s. The look-down cycle of decision 28 had not been applied when
     the episode ended.
   - **The plan did not enter the box.** Its world trajectory passes 0.13 m outside the box's north-west corner (2.70,
     2.80) and ends north of it at (2.85, 3.05).
   - **Tracking it:** the MPC commanded its full right turn (−0.40 rad/s) at 16.4-16.7 s, then 0.14-0.24 m/s while
     cutting towards the path. Yaw fell from a 63.9° peak at 15.5 s to 34.1° at contact.
   - **Contact:** at 17.9 s, the front-right hip link (its joint at about (2.59, 2.84), 0.12 m from the corner) struck the north-west corner at
     514 N. The contact monitor ended the episode (`nonfoot_contact_above_threshold`); the chase frame
     `runs/phase_c_green_box_v1/isaac/frames/chase_000895.jpg` shows it.
   - **Cause: the stack's, not only the model's.** The MPC treats the robot as a point, System 1's path leaves less
     clearance than the robot's half-width, and nothing between them adds a footprint margin. The bridge clamps only
     speed. On hardware this would be a collision.
3. **The first System 2 answer ignores the instruction (6/6).**
   - **What was seen:** every episode's first answer was `←←←←`, a 60° left turn, whether the target was ahead (red),
     front-left (blue) or front-right (green). All six warm-up calls, on a black image with the instruction "hello",
     also returned `←←←←`.
   - **Why it is not leftover state:** upstream decodes greedily (`do_sample=False`, line 224), and `reset()` clears
     the image list, conversation history and step index (lines 87-92). The source is
     `internnav/agent/internvla_n1_agent_realworld.py` in `references/upstream/2026-09-08_dualvln`.
   - **Status:** a single-course observation, not a tested model property.
4. **Repeated pixel goals.** red v2 returned `261 297` four times in a row, and red v3 and v4 repeated `318 295`.
   - `318 295` and `318 442` also recur across runs and instructions.
   - x = 318 is within 2 px of the image's centre column.
   - Each repeat came with the target out of view (failure mode 1).
5. **System 2 frequency is fixed by `plan_step_gap = 4`.**
   - **Effect:** away from arrow actions and look-downs, System 2 runs on every 6th decision, about 3.8 s, or about 1.1 m of travel
     at the measured body speed. This bounds how quickly the model can say STOP.
   - **Where the value comes from:** the client's `--plan-step-gap` defaults to 4 (`vla_lockstep_client.py` line 203).
     The value is from upstream's `scripts/notebooks/inference_only_demo.ipynb`.
   - **Upstream's server would not run as shipped:** the pinned `http_internvla_server.py` defines no
     `plan_step_gap`, while the agent reads `args.plan_step_gap`. Its warm-up call also omits the required
     `intrinsic` argument.

### Variance

**Where it comes from.** Physics is deterministic: the base pose at policy steps 15 and 60 is identical across all four
red runs, to the logged precision. Two other things vary:
- **Rendering:** the first head frames are near-identical but not byte-identical (mean absolute difference 0.19 grey
  levels, maximum 9-11).
- **Wall-clock latency changes the tick counts:** red v4's decision 1 ran 4 ticks against 3 in the other runs, and
  decision 8 ran 18 against 17.

By step 100 the poses differ. Unseeded System 1 sampling is therefore one source of run-to-run variance among several.

**What varies, across the four red episodes.** The first two System 2 answers (`←←←←`, `206 311`) were identical in all
four, and the answers diverged from the third. The closest approach varies by only 0.17 m (1.05-1.22 m); everything
after it varies much more:
- STOP time: 23.4-34.8 s;
- distance at STOP: 2.45-6.04 m;
- path length: 6.7-10.6 m.

The approach is repeatable; when the model says STOP is not.

## Claim boundary

- Six episodes on one course: four repeats of one instruction, and one each of two others. InternNav's System 1
  sampler is unseeded, so repeats differ. 0/6 is a characterisation, not a success rate.
- The flat course has only primitive boxes. Neither lighting nor texture is a realistic interior.
- The head camera pose is approximate, and the D435i is not used.
- Pose is simulator truth: no localisation error.
- The lockstep timing emulates the real robot's latency. It does not include network, camera exposure or motor
  latency beyond the V12 policy's own dynamics.
- The bridge clamp and watchdog were never exercised in a GPU run; their trips are shown only against the GPU-free test
  double. The contact monitor is a simulator measurement with no counterpart on the robot.
- The client reconstructs upstream's Go2 deployment and is not upstream's runnable code. Upstream's pinned
  `http_internvla_server.py` cannot start as shipped (no `plan_step_gap`, and a warm-up call without `intrinsic`), so
  `plan_step_gap = 4` comes from upstream's notebook.
- Model identity is checked by `config.json` and the weight index against the DualVLN weight manifest. The 16 GB of
  weight shards were not re-hashed at C.5.
- The runs do not embed source hashes. Which bytes ran is reconstructed in `setup/phase_c_executed_source.json`, from
  upload-time hashes and a host re-hash.

## Lead review and evidence return (C.5, 2026-09-14)

**Verdict: accepted after corrections.** Label: **integrated** (unchanged). Nothing here is validated.

**Review.** An independent reviewer, working read-only, recomputed every number from the raw jsonl with its own code.
It returned `corrections required` with 14 findings. I re-derived each finding from the logs before applying it.
- **Numbers:** the C.4 table, the totals and the C.3 table all matched.
- **Corrections, all applied above:**
  1. green struck the north-west corner, not the south-west;
  2. green is a body-clearance failure, not a trajectory drawn into the box;
  3. the summary line overclaimed a "safety layer";
  4. blue was a sideways pass with the target never in view;
  5. MPC turn-rate saturation was missing;
  6. the cross-correlation lag understates the forward-speed response;
  7. latency and period ranges needed tighter definitions;
  8. C.3's tracking filter was undefined;
  9. distances at STOP versus at episode end;
  10. the out-of-view check at every STOP and repeated goal;
  11. sources of variance;
  12. `plan_step_gap`;
  13. which code ran;
  14. `last_s2_idx` is left at 1, not 0.
- **Definition I changed:** the time the box leaves the view. The reviewer reported 13.4-14.4 s; that figure depends on
  the definition, so I give both centre and last-corner times measured from the camera origin.

**Acceptance criteria (lead judgement; the PRD boxes stay for Dr Sun):**

| criterion | verdict | evidence |
| --- | --- | --- |
| AC5 (as amended) | met | The client passes instruction, RGB, depth, pose and intrinsics to the agent (`vla_lockstep_client.py`). MPC and PD run at 0.1 s ticks (`ticks.jsonl`). Received equals applied on all 8,850 policy steps through `LatestCommandState`. `trajectory_tovw` is logged, as an IndexError. |
| AC6 | met | `phase_c_red_box_v1`: chase and head videos plus `decisions.jsonl` (instruction, System 2 output, trajectory), `ticks.jsonl` (commanded velocity) and `isaac_steps.jsonl` (body state). Decision 1's System 2 text is recovered from the agent's files; later runs log it directly. |
| AC7 | met, on this course | Falls, clamp and controller saturation, and command lag against decision periods are all answered above. The characterisation covers one flat course with primitive boxes. |

**Evidence return:**
- **Collection:** all 26 phase A-C run directories are local. The seven Phase C manifests re-verify (0 non-OK).
- **Analysis:** `phase_c_summary.json` regenerates byte-identically.
- **Sync gate:** 13 of 13 code files on the host equal local. The InternNav files on the Phase C path equal the pinned
  commit `7a5c624`.
- **Tests:** the four local tests pass on the current code.
- **Git:** nothing is staged or committed.

**Commit gate: approved by Dr Sun on 2026-09-14 and written to `.gitignore`.** The commit still waits for the staged-diff
review at E.2. Dr Sun also decided that no upstream report is filed, and that Phase D adds a body-clearance margin taken
from an existing open-source implementation after a comparison survey, not hand-built (`prd.md` decisions 4-6).
- **Size:** 9,439 Phase B/C and task files, 179.8 MB, are unstaged.
- **Proposed ignores:** path-specific entries for this experiment only, with the SHA-256 of every ignored file already in
  the tracked `manifest.sha256` of its run:
  - `runs/phase_c_*/isaac/frames/` and `runs/phase_c_*/client/decision_frames/`: saved camera frames;
  - `runs/phase_*/**/test_data/`: the agent's debug images and text;
  - `runs/phase_b_*/**/*.npy`: Phase B depth and colour arrays.
- **Result:** 371 files (30.1 MB, including 14 videos of 12.0 MB) tracked, and 9,068 files (149.7 MB) local-only.
- **Storage:** once ignored, those bytes exist only at this local path and, until deleted, in the rented 4090's run
  root.
- **Regeneration:** rerunning a run id is not bit-reproducible (unseeded System 1, RTX rendering, wall-clock tick
  counts).
