---
origin: ai+remote_execution+local_verification
date: 2026-09-09
executor: Opus
package: OPUS_PUBLIC_SCENES_PACKAGE.md
status: executed
label: official evaluator on custom public-scene tasks
---

# DualVLN through the official InternNav Habitat evaluator on public scenes

**Result label: `official evaluator on custom public-scene tasks`.** This is not
R2R, not the paper's benchmark, and not a reproduction of any published score.
The policy, the evaluator, the checkpoint and the control logic are upstream's;
the scene and the two navigation tasks are ours.

**Successful execution and successful navigation are separate conclusions, and
both are reported separately below.**

## 1. What actually executed

The official entry point ran to completion, on the GPU, five times:

```
cd work/InternNav
python scripts/eval/eval.py --config public_scenes/configs/habitat_dual_system_public_cfg.py
```

| run | exit | wall s | started (UTC) | evaluator source sha256 |
| --- | --- | --- | --- | --- |
| `public_eval_v1` | 0 | 156.9 | 2026-09-09T09:42:52Z | `0fd895d1caae31e2…` |
| `public_eval_v2` | 0 | 142.7 | 2026-09-09T09:48:35Z | `a05268d5e4fac8ab…` |
| `public_eval_v3` | 0 | 125.1 | 2026-09-09T09:51:27Z | `a05268d5e4fac8ab…` |
| `public_eval_v4` | 0 | 142.0 | 2026-09-09T09:53:32Z | `a05268d5e4fac8ab…` |
| `public_eval_v5` | 0 | 155.2 | 2026-09-09T09:55:54Z | `a05268d5e4fac8ab…` |

Total GPU evaluation time **721.9 s of the 1,800 s budget**. No run timed out.

The package asked for one pass over two fixed cases. I ran the first pass
(`v1`), then repeated the identical frozen episodes because the second run
disagreed with the first. All five passes are reported; none is discarded and
none was selected after seeing its outcome. §5 explains the disagreement.

The two evaluator hashes differ **only** in where one output label is captured
(`view_kind` in the pixel-goal trace record, see §5.3). No policy, control-flow,
environment or metric code differs between them. Both versions were checked
against the pristine upstream file: the only *removed* upstream lines in either
are the two `save_video` success conditions and the two output filenames.

## 2. Navigation results — reported unchanged

Official metrics, exactly as the evaluator wrote them to `progress.json`:

| run | ep | success | SPL | oracle success | NE (m) | steps | closest approach (m) | termination |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 1 | **1.0** | 1.000 | 1.0 | 1.05 | 81 | 0.92 | habitat episode over |
| v1 | 2 | 0.0 | 0.000 | 1.0 | 5.67 | 107 | 2.07 | habitat episode over |
| v2 | 1 | 0.0 | 0.000 | 0.0 | 3.63 | 63 | 3.63 | habitat episode over |
| v2 | 2 | 0.0 | 0.000 | 1.0 | 5.91 | 113 | 1.87 | habitat episode over |
| v3 | 1 | 0.0 | 0.000 | 0.0 | 4.06 | 67 | 4.06 | habitat episode over |
| v3 | 2 | **1.0** | 0.902 | 1.0 | 2.15 | 86 | 1.77 | habitat episode over |
| v4 | 1 | **1.0** | 1.000 | 1.0 | 1.11 | 80 | 0.61 | habitat episode over |
| v4 | 2 | **1.0** | 0.846 | 1.0 | 2.97 | 92 | 1.76 | habitat episode over |
| v5 | 1 | **1.0** | 1.000 | 1.0 | 1.25 | 81 | 1.09 | habitat episode over |
| v5 | 2 | 0.0 | 0.000 | 1.0 | 4.89 | 116 | 1.83 | habitat episode over |

- Episode 1: **3 of 5** runs successful, navigation error 1.05–4.06 m.
- Episode 2: **2 of 5** runs successful, navigation error 2.15–5.91 m.
- Ten episode-runs, five successful.

Two episodes over five repeats is a bounded functional check. It is far too
small to estimate a success rate, and I am not offering one.

**Failure mode, episode 2.** In every one of the five runs the agent came within
2.07 m of the goal — inside the 3.0 m radius, which is why oracle success is 1.0
in all five — and in three of them (v1, v2, v5) it then moved away and stopped
4.89–5.91 m out. The agent reaches the goal region and stops too late, not in the
wrong place. Its recorded path is 12.7–16.3 m against an 11.5 m geodesic, with
8–10 collisions in every run. Episode 1, by contrast, has **zero collisions in
all five runs** and a 9.0–12.0 m path against a 12.07 m geodesic.

The terminal frame of the v1 failure shows why: the agent is standing in front of
a row of striped chairs beneath large gilt-framed paintings — the landmark the
instruction names — but on the wrong wall of the castle, 5.67 m from the goal.

## 3. STOP provenance — kept separate from success

Instrumented in the evaluator as an output-only trace (§8.3):

- **10 of 10 episode-runs ended on a learned STOP**: System 2 emitted the literal
  text `STOP`, `parse_actions` turned it into action 0, and Habitat ended the
  episode. Recorded per step as `is_learned_episode_stop` with the action source.
- **0 of 10 hit the evaluator's 500-step cap.** Longest episode: 116 steps.
- **0 of 10 ended on the empty-parse fallback** (`else: action = 0`), which the
  trace records separately as `fallback_stop_no_action_parsed`.
- **0 of 10 were interrupted by the wall-clock deadline.**

Non-terminal stop-like events are counted separately and never reported as
episode STOPs: `forward_budget_exhausted` (System 1's local budget runs out,
System 2 replans) occurred 8–11 times per episode, and `s1_stop_mid_segment`
(System 1 emits STOP inside a local segment) once in v1 episode 2.

So: every episode here ended on a genuine learned stop, and half of them still
failed. Learned STOP and navigation success are independent, and the failures
are failures of *where* the policy chose to stop.

## 4. What the model actually did

- System 2's first call on each episode read the instruction and emitted the
  correct opening turn, identically in all five runs: `→→→→` for episode 1 and
  `←←←←` for episode 2. Before any
  model query I had measured, by driving the simulator's own turn actions, that
  episode 1 needs a **right** turn of about 4 × 15° and episode 2 a **left** turn
  of about 3 × 15° (`public_scenes/previews/orientation/orientation.json`). The
  policy's opening move matches the geometry in both cases.
- **Every pixel goal in all five runs came from the tilted look-down view, never
  from the level camera.** The level-view System-2 call only ever emitted arrow
  tokens, `↓`, or `STOP`; coordinates appear only in the follow-up call on the
  640×480 look-down frame. This is visible in the trace as
  `branch: look_down_followup` together with a 640×480 model input, versus
  `level_view` with a 384×384 input. It reproduces, now under the official
  evaluator, the same structural observation made earlier with the custom runner.
- Pixel goals are emitted as `row col` in Qwen2.5-VL's *processed* image space
  (644×476 for the look-down frame, from `image_grid_thw` × 14 px), and upstream
  draws the marker with those raw numbers on a 640×480 image — a sub-1 % offset,
  not a wrong view. `public_scenes/scripts/draw_pixel_goals.py` redraws each goal
  on the exact image the model was shown, with both the upstream marker and the
  rescaled one, so the difference is visible rather than asserted.

## 5. The runs disagree with each other, and why

### 5.1 The observation

Identical frozen episodes, identical configs, identical checkpoint, five runs,
five different trajectories: episode 1 succeeded in v1/v4/v5 and failed in
v2/v3.

### 5.2 The cause

From the trace, for the same episode at the same step:

- **System 2 is deterministic.** The first four calls of episode 1 produced
  byte-identical text in v1 and v2: `→→→→`, `→→→→`, `↓`, `170 203`. It is called
  with `do_sample=False`.
- **System 1 is not.** The first System-1 call on that same state returned
  `[[0.3984, 0.0586, 0.1182], …]` in v1 and `[[0.4062, -0.0718, -0.1777], …]` in
  v2, giving different action lists.

System 1 is a flow-matching diffusion policy whose initial noise comes from
torch's RNG. The pinned evaluator seeds **numpy only**
(`np.random.seed(self.local_rank)` in `internnav/evaluator/distributed_base.py`)
and never seeds torch or Python's `random`. So repeated runs of the same episode
draw different trajectories, and the navigation outcome follows.

This is a property of the pinned upstream code, not of anything added here. It
means single-run navigation numbers from this evaluator are not reproducible, and
any success rate needs repeats. I did not add a seed: seeding would change
control behaviour, which the package forbids.

### 5.3 One label bug of mine, fixed

In `v1` the trace's `pixel_goal.view_kind` field read the loop variable `action`
after it had been reassigned, so it printed `level` when the goal had in fact come
from the look-down call. The `s2_call.branch` field, captured earlier in the
iteration, was correct throughout, as is the recorded model-input size — so the
v1 conclusion in §4 is supported by v1's own data. The field is captured
correctly from `v2` onwards. Nothing but that output label changed.

## 6. Scenes: one usable, one not

Both public scenes were downloaded, verified and previewed. Measured **before**
any instruction was written and before any model query
(`public_scenes/setup/scene_feasibility.json`):

| scene | navigable area | geodesic diameter | share of navigable samples already inside the 3 m success radius | usable |
| --- | --- | --- | --- | --- |
| `skokloster-castle` | 226.7 m² | 24.05 m | 4.8 % | yes |
| `van-gogh-room` | 9.2 m² | 4.35 m | **82.9 %** | no |

**van-gogh-room is excluded, and this was decided before inference.** It is a
single small bedroom. Its longest reachable route is 4.35 m against a 3.0 m
success radius, and 83 % of everywhere the agent can stand is already "successful"
without moving. An episode there cannot distinguish navigation from standing
still. The package anticipated this case and allows a second distinct route in
the other scene, which is what I did. The scene was still previewed and those
renders are kept (`public_scenes/previews/van-gogh-room__cand06/`).

## 7. The two frozen episodes

Frozen before the first model query. Annotation file
`public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz`,
SHA-256 `49f1bff7e1623e312b303b4b938a2c821c015e8ebad001a66c01a0f72e597889`,
byte-reproducible (`mtime=0`, sorted keys). Manifest:
`public_scenes/setup/frozen_public_episodes.json`.

Scene `skokloster-castle/skokloster-castle.glb` for both.

**Episode 1** — start `[-1.9694, 0.1976, 12.8348]`, goal `[2.9776, 0.0289, 22.0349]`,
radius 3.0 m, geodesic **12.07 m**:

> Turn right and walk past the long dark wooden table. Go straight on into the
> next room with the tall bright windows. Stop near the high-backed chairs
> standing between the windows.

**Episode 2** — start `[5.6203, 0.2075, 5.2189]`, goal `[-4.6301, 0.1236, 10.1976]`,
radius 3.0 m, geodesic **11.47 m**:

> Turn left and walk into the large hall with the painted ceiling. Cross the
> checkered stone floor towards the big paintings of men on horseback. Stop in
> front of the row of striped chairs under those paintings.

Both initial goal distances are far above the 3.0 m success radius, as required.
Start separation between the two routes is 10.7 m and goal separation 14.1 m, so
they are genuinely distinct routes.

Selection rule, fixed and applied in this order, independent of any model output:

1. Only scenes passing the feasibility test in §6 are eligible.
2. Among the seeded candidates of the eligible scene (seed `20260909`, 400
   navigable samples, geodesic band 6–14 m), take the pair with the largest mutual
   start and goal separation.
3. Instructions are written from the rendered previews of those two routes; the
   left/right wording comes from driving the simulator's own `turn_left` /
   `turn_right` actions, not from reasoning about quaternion conventions.

No R2R instruction or coordinate was transplanted into these scenes.

## 8. Deviations from upstream, exhaustively

### 8.1 Habitat config — 2 lines
`public_scenes/configs/vln_public_scenes.yaml` vs upstream
`scripts/eval/configs/vln_r2r.yaml`: only `scenes_dir` and `data_path`. Camera
geometry, sensor sizes, hfov, depth range, `forward_step_size` 0.25,
`turn_angle` 15, `tilt_angle` 15, `action_space_config` v1, all six actions, all
five measurements, `success_distance` 3.0 and `max_episode_steps` 5000 are
upstream's. The `split` field still reads `val_unseen`; the derived data simply
lives under that split name so the field did not have to change.

### 8.2 Eval config — 5 fields
`public_scenes/configs/habitat_dual_system_public_cfg.py` vs upstream
`habitat_dual_system_cfg.py`: `config_path`, `output_path`, `save_video`,
`vis_debug`, `vis_debug_path`. Unchanged, *including their values*: `mode`,
**`model_path` (still the literal `checkpoints/InternVLA-N1-DualVLN`)**,
`num_history` 8, `resize_w`/`resize_h` 384, `max_new_tokens` 1024, `epoch` 0,
`max_steps_per_episode` 500, `port`, `dist_url`.

### 8.3 Evaluator — output only
`public_scenes/setup/evaluator_output_only.patch`, regenerated in one step by
`public_scenes/scripts/apply_trace_patch.py`. 172 added lines and 4 removed; the only *removed*
upstream lines are:

```
-            if self.save_video and metrics['success'] == 1.0:
-                    f'{episode_id:04d}',
```
(twice — the dual-system and System-2 save sites), replaced by
`len(vis_frames) > 0` and a filename carrying the outcome, so failed episodes
keep their video. Everything else is added: a per-step JSONL trace (applied
action, action source, learned-STOP flag, pose, distance to goal, collisions),
System-2 raw text with whole-call latency, System-1 raw trajectories captured
**before** `traj_to_actions` divides them by 4 in place, pixel goals with the
exact model-input image saved as PNG, non-terminal stop events, termination
reason and the never-reset CUDA peak. The trace edits are confined to
`_run_eval_dual_system`; `_run_eval_system2` is byte-identical to upstream apart
from the video condition.

### 8.4 Two pre-existing lazy-import shims
`internnav/agent/__init__.py` and `internnav/model/encoder/__init__.py`, deferring
optional imports that pull the absent `LongCLIP` submodule. Unchanged from the
previous task.

### 8.5 Habitat-Lab 0.2.4, not 0.3.3
See §9.

### 8.6 Three task-owned relative symlinks
See §10.

## 9. Environment: the 0.2.4 candidate is now verified

Lead review O2 required that 0.2.4 be treated as a candidate until proven. It is
now proven, at least as far as the evaluator's own requirements go.

- habitat-lab and habitat-baselines **v0.2.4**, commit
  `1639e1ae732ba1e84199a1a04b79c7243c3f8586`, installed from source into
  `official_r2r/official_env_024`.
- **habitat-sim stays at the already-verified 0.3.3 conda build.** The 0.2.4
  habitat-lab drives it without complaint through config composition, `habitat.Env`
  construction, all six actions and 10 completed episodes. No habitat-sim 0.2.4
  build was needed.
- The failed 0.3.3 environment is preserved untouched at
  `official_r2r/official_env`, with its freeze at
  `official_r2r/setup/official_env_pip_freeze.txt`. The 0.2.4 freeze is at
  `public_scenes/setup/env_024_pip_freeze.txt`.
- Everything else is unchanged from the previously verified stack: Python 3.9.23,
  torch 2.6.0+cu124, transformers 4.51.0, diffusers 0.32.2, FlashAttention 2.7.3,
  RTX 4090, bf16 supported.

The three failures that identified 0.3.3 as wrong — the missing
`agents/rgbd_agent` config group, `tilt_angle` and `action_space_config` not
being `SimulatorConfig` fields — do not occur on 0.2.4. The config composes with
`action_space_config: v1` and `tilt_angle: 15` intact.

## 10. Launch-directory paths (lead review O1)

Upstream's entry point does `sys.path.append('.')` and every relative path in its
configs resolves from `work/InternNav`. Rather than rewrite those paths, three
task-owned relative symlinks make them resolve, created and checked by
`public_scenes/scripts/link_launch_dir.sh`:

```
<EXP>/checkpoints/InternVLA-N1-DualVLN  -> ../models/InternVLA-N1-DualVLN
<EXP>/work/InternNav/checkpoints        -> ../../checkpoints
<EXP>/work/InternNav/public_scenes      -> ../../public_scenes
```

With these, upstream's own `model_path: checkpoints/InternVLA-N1-DualVLN` and the
hardcoded `MODEL_PATH_TO = "checkpoints"` in
`internnav/model/basemodel/internvla_n1/internvla_n1_arch.py` — which loads the
auxiliary Depth-Anything encoder — both resolve unchanged.

`public_scenes/scripts/preflight_public.py` **refuses to run anywhere except
`work/InternNav`**, so it tests the launcher's real path resolution. All nine
stages pass (`public_scenes/setup/preflight_public_report.json`):

```
PASS  official env versions
PASS  all paths resolve from the launch directory
PASS  auxiliary depth encoder at upstream relative MODEL_PATH_TO
PASS  InternNav official evaluator imports (not swallowed)
PASS  derived eval config loads
PASS  official habitat config composes
PASS  frozen public annotations load
PASS  scene assets match the download manifest
PASS  habitat.Env constructs and resets
ALL_STAGES_PASSED
```

The evaluator import is done directly rather than through
`internnav/evaluator/__init__.py`, which swallows that failure into a warning.

## 11. Deadline enforcement (lead review O3)

Every run went through the task-owned process-group supervisor:

```
python3 scripts/run_job.py --seconds 1800 <run_id> -- bash public_scenes/scripts/run_public_eval.sh <run_id>
```

`run_job.py` captures raw stdout/stderr, records pid/pgid, and on deadline sends
SIGTERM then SIGKILL to the whole process group. **Verified with a trivial
subprocess before the GPU run** (`runs/deadline_smoke_v1/`): a 5 s deadline
against a 600 s child that had itself spawned a `sleep 600` grandchild produced
`{"exit_code": -15, "timed_out": true, "wall_seconds": 5.0}` and left no
survivors. A deadline interruption would therefore be visible as
`timed_out: true`, distinct from a completed navigation failure. None occurred.

The launcher additionally refuses to start if the run directory already exists,
if the preflight report is absent, or if the preflight did not pass every stage —
so no run can silently inherit another run's `progress.json`.

## 12. Measurements, with their scopes

**Latency — whole-call, including look-down inference.** Timed around the
complete call, not an isolated forward pass. Look-down System-2 calls are
included in both the counts and the totals; they are 8 of 19 and 12 of 26 System-2
calls in v1's two episodes.

| run v1 | System-2 calls | S2 total (s) | S2 mean (s) | System-1 calls | S1 total (s) | S1 mean (s) | episode wall (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| episode 1 | 19 | 11.33 | 0.596 | 24 | 7.27 | 0.303 | 57.4 |
| episode 2 | 26 | 13.38 | 0.515 | 34 | 10.27 | 0.302 | 75.5 |

**Memory.** Two different quantities, kept apart:

- Process CUDA allocator peak, **never reset per step**, read at the end of each
  episode: **17,780,855,808 B = 16.56 GiB** (`torch.cuda.max_memory_allocated`).
- Whole-device usage, **sampled every 5 s** by `nvidia-smi` for the duration of
  each run: peak **22,381 MiB of 24,564 MiB**, identical across all five runs
  (25–31 samples each). This figure is the **whole GPU** and includes a
  pre-existing `isaac-sim` container holding 2,859 MiB that was running
  throughout and was not touched.

## 13. Video and frames

Per run, from the actual episodes:

- `vis_<epoch>/skokloster-castle/000{1,2}_success{0,1}.mp4` — the official
  `save_video` composite: first-person view with the synchronized Habitat
  top-down map panel, drawn from real simulator poses, with the pixel goal marked
  on the frame it was predicted from. **Failed episodes are kept**, and the
  filename carries the outcome.
- `vis_debug/epoch_0/skokloster-castle_000{1,2}.mp4` — official `vis_debug`
  first-person video annotated per frame with step id and applied action.
- `trace_0/*_goalframes/step*_model_input.png` and `*_saved_raw_view.png` — the
  exact images System 2 was shown at each pixel-goal step.

All 20 MP4s were decoded **locally**, on this machine, with ffprobe and ffmpeg:
`vis_0` composites are 1296×480 h264 and `vis_debug` are 640×480 h264, and every
file's frame count equals that episode's step count (81, 107, 63, 113, 67, 86,
80, 92, 81, 116). Representative start / early-movement / mid / late / terminal
frames were extracted to `public_scenes/decoded_frames/` and inspected:

- v1 episode 1, frame 0: first-person view of the portrait room with the long
  dark table, beside a top-down panel showing the agent marker, the fog-of-war
  cone and the green reference path.
- v1 episode 1, frame 80 (terminal): the agent is standing beside a high-backed
  chair at the window — the destination the instruction describes — and the
  top-down panel shows its traversed path ending on the reference path's end.
- v1 episode 2, frame 106 (terminal): the agent is facing *a* row of striped
  chairs beneath large paintings, but on the wrong wall; the top-down panel shows
  it crossed past the reference path's end and continued. Navigation error 5.67 m.
- Look-down / pixel-goal frames: e.g. v1 episode 1 step 35, model text
  `348 168` → row,col 348,168 in the 644×476 processed space → (167, 351) in the
  640×480 saved frame, marked on the floor ahead of the agent in the tilted view.

`public_scenes/setup/local_evidence_verification.json` records every video's
local SHA-256, codec, resolution, frame count and duration.

## 14. Local evidence and sync status

**Sync gate.** Every script, config and patch in this task was authored on the
local source of truth and pushed; each push was followed by a SHA-256 comparison
of the local and remote copy before it was used. All comparisons matched, and a
final sweep over all 20 authored files (16 scripts, 2 configs, the patched
evaluator and the two lazy-import shims) again reports **20/20 matched, 0
mismatched**.

**Return.** Every unique output was brought back to the same local relative
paths and re-hashed against a manifest taken on the remote host:

```
354 / 354 files identical, 0 missing, 0 mismatched
```

(`public_scenes/setup/remote_manifest.txt` vs
`public_scenes/setup/local_evidence_verification.json`.) That covers the five run
directories in full — traces, goal frames, progress/result JSON, GPU samples,
input hashes, exit codes and all 20 MP4s — plus the previews, the frozen
annotations, the scene assets and every script and config. **The archive for this
task is complete; nothing unique remains only on the remote host.**

Supervisor logs for every job (`stdout.log`, `stderr.log`, `meta.json`,
`process.json`) are under `runs/`, including the five evaluations, the preflight,
the environment build, the previews, the freeze and the deadline smoke test.

Scene assets carry their own provenance
(`public_scenes/setup/public_scene_manifest.json`): both `.glb` files' SHA-256
match the upstream LFS digests recorded in `setup/habitat_scene_source.json`
(`b14e29e1…` for the castle, `24570d71…` for the Van Gogh room). The two
`.navmesh` files are plain git blobs upstream with no LFS digest to compare
against, so their SHA-256 is recorded and their byte size checked against the
pinned manifest — that is a weaker check and is labelled as such.

## 15. What was not done, and open items

1. **van-gogh-room hosts no episode.** Measured and documented before inference
   (§6). It was downloaded, verified and previewed; it is not usable for a task
   the official success measure can score.
2. **This is not R2R.** The frozen R2R subset (episodes 10/11/12 of
   `2azQ1b91cZZ`) remains **unexecuted and preserved** under `official_r2r/`,
   still blocked on the Matterport3D mesh, which needs a Terms of Use signed from
   an institutional email. Nothing in this task substitutes for it.
3. **The InternRobotics annotation-copy parity issue is still open.** Untouched
   by this task; it belongs to the R2R route.
4. **No seed was added.** The run-to-run variation in §5 is upstream behaviour.
   Fixing it means seeding torch, which changes control behaviour, which this
   package forbids. It is recorded, not repaired.
5. **habitat-sim was not rebuilt at 0.2.4.** habitat-lab 0.2.4 drives habitat-sim
   0.3.3 through everything this evaluation needs, but that pairing is not one
   upstream pins or tests, and I have only shown it works for this path.
6. **Two episodes, five repeats, one scene.** A bounded functional check. It
   supports no claim about the model's benchmark performance.
7. **Only `dual_system` mode was exercised.** The `system2` path is untouched
   apart from the video-saving condition.

## 16. Status of the previous lead review

| item | status |
| --- | --- |
| **O1** launcher working directory breaks config/asset/encoder paths | **closed** — three task-owned relative links (§10); preflight now refuses to run outside `work/InternNav` and passes all nine stages there |
| **O2** compatible environment is an untested candidate | **closed** — habitat-lab 0.2.4 built, evaluator imports, config composes, `habitat.Env` constructs, and 10 episodes completed (§9). The failed 0.3.3 environment is preserved |
| **O3** launcher does not enforce the evaluation budget | **closed** — every run went through the process-group supervisor with a 1,800 s deadline, verified beforehand on a trivial subprocess (§11) |
| **O4** readiness reporting must distinguish untested stages | **closed for this route** — the preflight stops at the first failure and explicitly marks later stages `not attempted`; task metadata updated to record what executed |
| R2R scene access | **still open** — separate experiment, unchanged |

## 17. Suggested next steps

1. **Characterise the variance properly** before drawing any conclusion about
   this policy: the same two episodes, 20–30 repeats, is roughly 40–70 minutes of
   GPU time and would turn "3 of 5" into a number with an interval.
2. **Add more routes in the castle.** 226.7 m² and a 24 m diameter support many
   more than two, and the candidate sampler already enumerates them
   deterministically.
3. **Investigate the stop-timing failure.** Episode 2 entered the success radius
   in all five runs and stopped outside it in three. The traces record the
   distance to goal at every step, so the moment the policy should have stopped
   and did not is directly recoverable.
4. **R2R remains gated on the Matterport3D Terms of Use.** Nothing here changes
   that, and nothing here substitutes for it.

## Appendix — file map

```
public_scenes/
  scripts/         download_public_scenes.py, scene_feasibility.py, sample_candidates.py,
                   preview_render.py, route_orientation.py, freeze_public_episodes.py,
                   setup_env_024.sh, link_launch_dir.sh, apply_trace_patch.py,
                   preflight_public.py, trace_smoke.py, run_public_eval.sh,
                   summarise_runs.py, draw_pixel_goals.py, verify_local_evidence.py
  configs/         vln_public_scenes.yaml, habitat_dual_system_public_cfg.py
  setup/           public_scene_manifest.json, scene_feasibility.json,
                   candidates_*.json, frozen_public_episodes.json,
                   preflight_public_report.json, env_024_pip_freeze.txt,
                   evaluator_output_only.patch, run_summary.json,
                   remote_manifest.txt, local_evidence_verification.json
  previews/        7 previewed candidate routes (RGB + depth) + orientation/
  data/            scene_data/public/{skokloster-castle,van-gogh-room}/,
                   vln_ce/raw_data/public/val_unseen/val_unseen.json.gz
  runs/            public_eval_v1 … v5 (progress.json, result.json, inputs.json,
                   environment.json, exit.json, gpu_samples_every_5s.csv,
                   trace_0/, vis_0/, vis_debug/, pixel_goal_overlays/)
  decoded_frames/  frames decoded locally from the returned MP4s
runs/              supervisor logs for every job in this task
```

Task kept at `review` pending lead acceptance. Nothing staged, nothing committed.
