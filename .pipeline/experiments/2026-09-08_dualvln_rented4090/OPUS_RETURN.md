---
origin: ai+remote_execution
reviewed: false
date: 2026-09-09
status: executed_pending_lead_review
executor: Opus
package: OPUS_EXECUTION_PACKAGE.md
---

# DualVLN BF16 inference and one simulator video — execution return

## 1. Headline result

All three requested deliverables were produced with recorded evidence.

| Deliverable | Status | Primary evidence |
| --- | --- | --- |
| BF16 model inference | Done | `runs/inference_v5/probe_record.json` |
| One bounded simulation episode | Done (2 episodes: raw render, then auto-exposed) | `runs/sim_episode_v{1,2}/episode_record.json` + `episode_analysis.json` |
| Playable local video | Done, decoded and frame-inspected | `runs/sim_episode_v1/episode_v1.mp4`, `runs/sim_episode_v2/episode_v2.mp4` |

**Evidence labels (per `AGENTS.md`).** The upstream open-loop notebook demo is
`reproduced`. The closed-loop Habitat episode is `integrated` — upstream model
behaviour runs inside a loop built in this repository — but it is **not**
`reproduced` (upstream evaluates on MP3D R2R via habitat-lab, not on the public
`apartment_1` test scene) and **not** `validated` (no acceptance test was
declared for it, and the model never emitted a learned STOP).

### What the model actually did

**BF16 inference is real, not a constructor success.** 8,383,538,891 parameters
loaded, **100 % `torch.bfloat16`**, with `missing_keys`, `unexpected_keys`,
`mismatched_keys` and `error_msgs` all empty. No precision was changed and no
quantisation was applied at any point.

Over 40 released fixture frames the model produced its documented behaviour: an
initial in-place rotation (`→→→→`), explicit look-down requests (`↓`), pixel
goals (`463 215`, `215 206`, `271 205`, `491 210`) and 23 finite System-1
trajectories with path lengths **1.76–2.97 m (mean 2.33 m)**. The upstream
notebook states the trajectory length should be "about 2 m", so this matches.

**In simulation the model navigated a real route.** In episode v2 it drove
itself from the living room, through a doorway, into the dining room:
geodesic distance to target **5.46 m → 1.08 m at the closest approach**, ending
at 2.55 m, 6.65 m of path travelled, **0 collisions**.

## 2. Honest scoring of the simulation episodes

Both episodes ran to the 200-step cap. **Neither emitted a learned STOP**, so by
the upstream Habitat VLN `Success` measure (inside the radius *and* the agent
called STOP itself) **both are failures**. `episode_record.json` in these two
runs carries a `success` field that tests final distance only; use
`episode_analysis.json`, which reports every criterion separately.

| Metric | v1 (raw render) | v2 (auto-exposed input) |
| --- | --- | --- |
| Termination | `step_cap` (200) | `step_cap` (200) |
| `success_upstream_stop_based` | **false** | **false** |
| `success_final_distance_only` | false | true (2.55 m < 3.0 m) |
| `oracle_success_min_distance` | false | true (1.08 m < 3.0 m) |
| Learned STOP emitted | no | no |
| Geodesic start → end | 5.46 → 4.97 m | 5.46 → 2.55 m |
| Geodesic minimum reached | 4.97 m | **1.08 m** |
| Path length travelled | 0.50 m | 6.65 m |
| Distinct XZ positions | 3 | 27 |
| Collisions | 0 | 0 |
| Forward / left / right / look-down | 2 / 48 / 149 / 1 | 27 / 52 / 112 / 9 |
| S2 calls / S1 calls | 50 / 1 | 43 / 8 |
| Pixel goals produced | 1 | 9 |

**Failure characterisation.** v1 spun almost in place for the whole episode.
Diagnosis with evidence (`setup/exposure_diagnosis.json`): all 200 v1 model
inputs average mean luma **40.1** (range 22.5–60.0), while the 152 released
real-world fixtures this checkpoint was demonstrated on average **120.1**
(range 96.3–139.9) — roughly 3× under-exposed and far out of distribution.
That is a defect in my simulator setup, not a model result. Habitat's
`DEFAULT_LIGHTING_KEY` was tried first and made it *worse* (luma **18.5**,
`runs/light_test/`), so v2 instead applies a per-frame auto-exposure gain to the
**model input only** (target luma 118.6, clipped at 4×; applied gain min 1.18,
mean 2.97, max 4.0, with 50 of 200 frames at the ceiling), emulating the
auto-exposure of a real RGB-D camera such as the D455 that produced the
fixtures. Observation PNGs on disk remain the unmodified render, and the gain is
recorded per step as `exposure_gain_applied_to_model_input`. This transform is
**not part of upstream** and must be treated as a deliberate deviation.

**A structural finding worth keeping.** In both episodes **every** pixel goal
(1 in v1, 9 in v2) came from the *tilted-down* System-2 call, never from the
level-camera call. The level camera only ever emitted turn tokens or the
look-down request `↓`. This matches the upstream evaluator's design, where the
model asks to look down and then places the waypoint on the floor view, and it
confirms that the real camera tilt implemented here (2 × 15° down, query,
2 × 15° back up) is load-bearing rather than cosmetic.

## 3. Peak VRAM and latency

Sampled `nvidia-smi` totals include the protected Isaac Sim container
(2,903 MiB), which was left running and untouched throughout.

| Run | Torch allocated after load | Torch peak allocated | Torch peak reserved | Device total at peak |
| --- | --- | --- | --- | --- |
| `inference_v5` (fixture probe) | 15,990 MiB | 16,191 MiB | 19,780 MiB | 23,154 / 24,564 MiB |
| `sim_episode_v1` | — | 16,103 MiB | 17,168 MiB | 20,847 / 24,564 MiB |
| `sim_episode_v2` | — | 17,054 MiB | 17,188 MiB | 20,867 / 24,564 MiB |

The model and headless Habitat-Sim shared the single RTX 4090 without OOM. The
simulation runs used `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, which
cut peak *reserved* memory from 19,780 MiB to ~17,180 MiB.

| Run | S2 calls | S2 mean / max | S1 calls | S1 mean / max |
| --- | --- | --- | --- | --- |
| `inference_v5` | 21 | 0.726 s / 1.613 s | 19 | 0.313 s / 0.355 s |
| `sim_episode_v1` | 50 | 0.619 s / 1.213 s | 1 | 0.316 s / 0.316 s |
| `sim_episode_v2` | 43 | 0.584 s / 1.222 s | 8 | 0.310 s / 0.331 s |

Model construction plus weight load: **4.97 s** (16.9 GB, warm page cache).
Episode wall time: v1 67.9 s, v2 77.7 s for 200 model-driven steps each.

## 4. Commands and exit codes

Every run went through `scripts/run_job.py` (process-group deadline + raw logs).
Full logs are under `runs/<job>/{stdout.log,stderr.log,meta.json,process.json}`.

| Job | Exit | Wall | Note |
| --- | --- | --- | --- |
| `download` | 0 | 882.5 s | Pre-existing job, adopted not restarted |
| `setup` | **-15** | 1947.7 s | Pre-existing job, **deliberately SIGTERM'd** — see §6 |
| `scene_download_v1` | 0 | 6.8 s | Habitat scene + navmesh, LFS SHA-256 verified |
| `sim_setup_v1` | 0 | 89.1 s | `SIM_SETUP_COMPLETE`, habitat-sim 0.3.3 |
| `setup_finish_v1` | 0 | 15.2 s | `SETUP_COMPLETE` + FlashAttention kernel check |
| `fix_diffusers_v1` | 0 | 21.6 s | diffusers 0.33.1 → 0.32.2 |
| `resolve_imports_v1` | 0 | 4.4 s | dependency probe; **false pass** — probe too shallow |
| `resolve_imports_v2` | killed | — | installed `pydantic`, then looped on the local `internnav` package name; stopped by hand, no `meta.json` |
| `inference_v4` | 0 | 24.1 s | `PROBE_COMPLETE`, superseded — bad S2/S1 label (§6.7) |
| `inference_v5` | 0 | 30.8 s | **`PROBE_COMPLETE`** — the BF16 result |
| `sim_smoke_v1` | 0 | 14.1 s | 8-step loop validation before the full run |
| `sim_episode_v1` | 0 | 80.4 s | **`EPISODE_COMPLETE`** raw render |
| `sim_episode_v2` | 0 | 89.6 s | **`EPISODE_COMPLETE`** auto-exposed |
| `video_v1` / `video_v2` | 0 | 5.6 / 5.7 s | **`VIDEO_COMPLETE`** |

Reproduction commands (run from `REMOTE`):

```sh
python3 scripts/run_job.py --seconds 1500 inference_v5 -- venv/bin/python scripts/probe.py \
  --scene-dir fixtures/realworld_sample_data1 --model-path models/InternVLA-N1-DualVLN \
  --out runs/inference_v5 --max-frames 40
python3 scripts/run_job.py --seconds 1800 sim_episode_v2 -- env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  venv/bin/python scripts/sim_runner.py --episode setup/episode_apartment1_v2.json \
  --model-path models/InternVLA-N1-DualVLN --out runs/sim_episode_v2 --max-steps 200 --max-seconds 1700
python3 scripts/run_job.py --seconds 550 video_v2 -- venv/bin/python scripts/make_video.py \
  --run-dir runs/sim_episode_v2 --out runs/sim_episode_v2/episode_v2.mp4 --fps 4
```

Runs that failed and were repaired are kept in §6 rather than hidden.

## 5. Evidence paths

Local (this experiment directory) unless marked remote.

- **BF16 inference**: `runs/inference_v5/probe_record.json` — verbatim
  instruction + its SHA-256, per-frame input SHA-256 for all 40 images, raw S2
  text, parsed actions, pixel goals, full S1 trajectory arrays with finiteness
  checks, per-call latency, VRAM, parameter dtype census, checkpoint loading
  info. Raw stdout/stderr alongside.
- **Episodes**: `runs/sim_episode_v{1,2}/episode_record.json` (per-step pose,
  yaw, proposed vs applied action, collisions, geodesic-to-target, S1
  trajectories, exposure gain, observation paths) and `episode_analysis.json`
  (unambiguous scoring).
- **Video**: `runs/sim_episode_v1/episode_v1.mp4`
  (SHA-256 `b4b6aa4a2c89d3b5d01c8a8979017e09dd4d1f4365bf3873c9ca08eed6a73272`,
  9,401,697 B) and `runs/sim_episode_v2/episode_v2.mp4`
  (SHA-256 `e4d702e942f838703e4b4db7830cbc2577460adf22398509138f304defd6dba3`,
  9,554,153 B). Both are **actual simulation video** — every frame is a Habitat
  render from the episode, overlaid with step id, inference branch, proposed and
  applied actions, geodesic distance, exposure gain, the S2 text, the pixel goal
  marker and an S1 trajectory inset. No fixture imagery is mixed in.
- **Video verification**: `runs/sim_episode_v*/video_verification.json` — each
  MP4 was re-decoded after writing: 200 frames written, 200 decoded, 199
  frame-to-frame distinct, 480×640×3. Frames 0/83/110/125/154/171 of v2 were
  additionally rendered to `runs/sim_episode_v2_video_frame_check.png` and
  inspected by eye.
- **Route figure**: `runs/episode_paths_topdown.png` — both episode paths drawn
  on the navmesh top-down view with start and target.
- **Frozen episode specs**: `setup/episode_apartment1_v1.json`,
  `setup/episode_apartment1_v2.json` — start pose, yaw, instruction, target,
  success radius, sensor config and intrinsics, all frozen *before* rollout, each
  naming the preview image used to choose it.
- **Previews used to freeze the episode**: the two frames the specs name are
  local — `runs/preview2_obs/p2_a_start_00000_rgb.png` (start pose) and
  `p2_e_00004_rgb.png` (target), plus `p2_d_00003_rgb.png` (the doorway) and the
  navmesh top-down `topdown_h-1.60.png`. The full preview sweeps (16 poses in
  `runs/preview_obs/`, 10 route poses in `runs/preview2_obs/`) stay remote.
- **Weights**: `setup/original_weight_manifest.json` — 17 files, 16.87 GB, every
  upstream LFS SHA-256 re-verified after download, **0 mismatches**.
- **Environment**: `setup/environment.json`, `setup/pip_freeze.txt` (71 pinned
  packages), `setup/sim_explicit.txt`.
- **Exposure diagnosis**: `setup/exposure_diagnosis.json` (full-set luma
  statistics for the fixtures, the raw render and Habitat default lighting, plus
  the applied-gain distribution) with the rejected default-lighting render in
  `runs/light_test/`.
- **Observations**: `setup/observation_manifest.json` lists all 864 observation
  PNGs (408 for v1, 456 for v2; 102 MB total) with per-file SHA-256 and size.
  **The PNG bytes themselves remain remote** — see the claim boundary in §8.

## 6. Failures encountered and how each was repaired

Nothing here was silently worked around; each is reproducible from the logs.

1. **FlashAttention wheel download stalled at ~25 KiB/s** (GitHub release asset,
   191 MB → ~2 h, past the supervisor deadline). Measured the rate, SIGTERM'd
   the `setup` job (hence `exit=-15`), downloaded the wheel from the **same
   authoritative GitHub URL** on the local workstation, verified it as a valid
   zip, and pushed it to `setup/wheels/`. Remote SHA-256 matches the local
   download exactly: `64ba4ed4a8c4c9b79d8a0959ebe3ffd6f7ea707ae222dbebe6a864237ac0e475`.
   `scripts/setup_finish.sh` then completed the original script's remaining
   steps and ran a live FlashAttention kernel check on GPU. The 191 MB wheel
   itself stays remote at `REMOTE/setup/wheels/` — it is a public artifact
   re-obtainable from the pinned GitHub URL and verified by that SHA-256.
2. **`diffusers==0.33.1` crashed during model construction.**
   `LuminaNextDiT2DModel._set_gradient_checkpointing() got an unexpected keyword
   argument 'enable'`. Root cause: InternNav vendors its **own**
   `LuminaNextDiT2DModel` (`internnav/model/basemodel/internvla_n1/nextdit_traj.py:295`)
   carrying the pre-0.33 signature, so upstream's own
   `requirements/internvla_n1.txt` pin is internally inconsistent. Upstream's
   `requirements/habitat_requirements.txt` pins **0.32.2** for the Habitat path —
   which is the path reproduced here — so the pin was moved there rather than
   patching model code. Gradient checkpointing is training-only and does not
   affect inference numerics.
3. **`ModuleNotFoundError: internnav.model.basemodel.LongCLIP.model`.** LongCLIP
   is an unfetched git submodule, eagerly imported by
   `internnav/model/encoder/__init__.py` but unused on the DepthAnything path.
   Applied the same PEP 562 lazy-import shim already recorded for
   `internnav/agent/__init__.py`. See §7.
4. **`pydantic` missing.** Installed; it is in `internnav`'s own
   `requirements/core_requirements.txt` but not in the package's setup script.
5. **Triton JIT failed to build the FlashAttention rotary kernel** — `gcc` could
   not find `Python.h`. Installed `python3.10-dev` (build headers only; no
   driver, framework or CUDA change, and the Isaac container was untouched).
6. **v1 episode navigation failure** — under-exposed render, diagnosed and
   addressed in §2. v1 is retained in full as the failed case.
7. **Two record-accuracy defects in my own harness, found and fixed:** the S2/S1
   branch label was off by one (`last_s2_idx == episode_idx - 1`; a look-down S2
   call does not advance `episode_idx`), corrected with an explicit flag and the
   probe re-run — this is why `inference_v5` supersedes `inference_v4`. And
   `episode_analysis.json` initially under-counted pixel goals as 0 because they
   arrive via `look_down_output_pixel`; the analysis now counts both sources and
   marks `llm_output_raw` as stale on non-S2 frames.

## 7. Source and sync status

- **Pristine source untouched.** `references/upstream/2026-09-08_dualvln/source/InternNav`
  at commit `7a5c62400ac45b313d9b709c740b64191556a242` was not modified.
- **`diff -rq` of pristine vs `work/InternNav` reports exactly two differing
  files**, both lazy-import `__init__.py` shims, both captured in
  `setup/compatibility.patch`:
  - `internnav/agent/__init__.py` (pre-existing, from the package)
  - `internnav/model/encoder/__init__.py` (added this session, item 6.3)

  **No model math, architecture, precision or weight file was changed.**
- **Sync gate.** All scripts and specs were authored locally and pushed with
  `rsync`; SHA-256 was compared local vs remote before each run. One rsync
  mistake early on copied `scripts/` contents into the remote root; the ten
  stray files were removed immediately and re-synced to the correct paths.
- **Local `git`**: the whole experiment directory is still untracked
  (`?? .pipeline/experiments/2026-09-08_dualvln_rented4090/`). **Nothing was
  staged or committed** — left for lead review, per the package.
- **Protected workload preserved.** The Isaac Sim container ran throughout
  (2,903 MiB, PID 1324 re-identified before every GPU run) and was never touched.
  No training, no real-robot actuation, no server purchase, no driver or
  framework replacement.

## 8. Claim boundaries

- The fixture probe is **open-loop**. Depth is the upstream notebook's dummy
  constant 10 m plane and pose is identity, exactly as released. It is evidence
  of correct BF16 inference and of the dual-system output format — **not**
  navigation evidence.
- The Habitat episode is a **small functional trial on the public
  `apartment_1` test scene**, not the paper benchmark. No MP3D/R2R data was
  used, no SR/SPL/NE benchmark number is claimed, and n = 1 episode per
  condition.
- **Both episodes are failures under the upstream stop-based success measure.**
  v2's favourable distance numbers must always be quoted together with
  "no learned STOP, terminated at the step cap".
- The v2 auto-exposure gain is **my addition**, not upstream behaviour. Any
  comparison against upstream numbers must account for it.
- The instruction and target for the episode were **written by me** to match the
  previewed scene; they are not from an annotated VLN dataset, so the model was
  never scored against ground-truth human instructions.
- **102 MB of observation PNGs remain on the remote** at
  `REMOTE/runs/sim_episode_v{1,2}/obs/`. The return link measured ~27 KiB/s
  downstream, making a full pull impractical this session. Every file is listed
  with size and SHA-256 in `setup/observation_manifest.json`, and all 400 frames
  are visible in the two MP4s that *are* local. This is a deliberate, recorded
  gap, not an omission.
- Latency figures are for a single RTX 4090 shared with the Isaac container and
  include Python/PIL overhead; they are indicative, not a benchmark.

## 9. Remaining work

1. Pull the 102 MB of observation PNGs when a faster link is available, and
   verify against `setup/observation_manifest.json`.
2. Investigate the **missing learned STOP**. The model reached 1.08 m from the
   target and then drifted away instead of stopping. Worth checking whether the
   instruction phrasing ("stop at the dining table"), the absent semantic
   annotations in `apartment_1`, or the `plan_step_gap`/queue cadence is
   responsible.
3. Reduce the **80-step opening spin** in v2 (steps 0–79 were pure rotation).
   Compare against upstream's own `forward_action > MAX_STEPS` re-plan guard,
   which this loop does not implement.
4. Replace the ad-hoc auto-exposure with either a properly lit scene or a
   scene whose baked exposure is in distribution, so the input transform can be
   dropped entirely.
5. Run more than one episode and more than one scene before any quantitative
   claim; current n = 1 per condition.
6. Decide whether to fetch the `LongCLIP` and `diffusion_policy` submodules, or
   keep the lazy-import shims as the standing local modification.
7. Lead decision needed on the diffusers pin: this experiment moved to upstream's
   `habitat_requirements.txt` value (0.32.2). If a future task needs
   `internvla_n1.txt` (0.33.1), the vendored `nextdit_traj.py` signature must be
   patched instead.

Task remains at `review` pending lead acceptance.
