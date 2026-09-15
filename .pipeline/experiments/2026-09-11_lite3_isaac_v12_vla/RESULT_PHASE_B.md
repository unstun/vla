# Phase B result: the robot can see, and with two fixes the closed loop fits on one 24 GB GPU

Runs: 2026-09-14 UTC on the rented RTX 4090 (24,564 MiB). Stage: experiment + analysis.
Label: **integrated** for a robot-mounted RTX camera rendering inside the V12 policy loop. AC3's "measured
head-camera pose" is not met.

**Final verdict (after the fallback Dr Sun chose): GO on one GPU for the flat course.** One-robot PhysX buffers (F1)
and `expandable_segments` (F2) bring InternVLA-N1 plus dual-720p Isaac to a 21,690 MiB peak with System 1 exercised
(`phase_b_vla_resident_v4`). Simulation speed halves while sharing. The as-specified NO-GO below is kept because it is
what forced the fallback. Details are in "F1 + F2 co-residence" near the end.

## First verdict: NO-GO on one GPU as specified, measured

With InternVLA-N1 resident, the dual-720p Isaac probe **ran out of GPU memory during start-up**
(`phase_b_vla_resident_v2`). The VLA process held 19,464 MiB; Isaac reached 2,936 MiB. Then PhysX failed to allocate
a 512 MiB buffer and a 640 MiB contact-pair buffer and aborted the simulation, and the Vulkan renderer hit
`ERROR_OUT_OF_DEVICE_MEMORY` (`runs/phase_b_vla_resident_v2_isaac/probe.log`). The device peaked at 23,815 of
24,081 MiB usable. InternVLA-N1 itself kept running (rc 0).

The arithmetic agrees with the failure. Isaac dual-720p alone needs **7,908 MiB**, and the VLA process needs
**19,464 MiB** — and that figure is for System 2 alone (see caveat below). Together that is about **27.4 GiB against
24.0 GiB**, roughly 3.3 GiB over.

## What rendering costs (no VLA on the GPU)

Flat course, V12 policy walking at vx 0.3 m/s, 50 warm-up and 200 timed policy steps (50 Hz policy, 200 Hz physics).
GPU is whole-device `nvidia-smi` on an otherwise idle card, so it is Isaac's own footprint.

| run | cameras | camera rate | RTF | step ms mean / p95 / max | sensor read ms | GPU MiB | host RAM peak MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `phase_b_none_v2` | none | – | 0.473 | 42.3 / 47.7 / 53.7 | – | 4,943 | 3,524 |
| `phase_b_single640_hz0_v1` | head 640x480 HFOV 79 | every step | 0.382 | 52.3 / 55.4 / 61.3 | 1.07 | 7,527 | 10,313 |
| `phase_b_single640_hz5_v1` | same | 5 Hz | 0.367 | 54.4 / 59.4 / 62.8 | 0.19 | 7,527 | 9,749 |
| `phase_b_dual720_hz0_v1` | head 1280x720 HFOV 105 +16.7°, D435i 1280x720 HFOV 69 −20° RGB+depth | every step | 0.339 | 59.0 / 63.4 / 67.0 | 2.61 | 7,908 | 9,795 |
| `phase_b_dual720_hz5_v1` | same | 5 Hz | 0.330 | 60.6 / 66.0 / 74.2 | 0.42 | 7,780 | 9,631 |

What the table says:

1. **Switching rendering on is the cost, not the cameras.** It adds about 2.6 GiB and 10 ms per step. A second 720p
   camera plus depth adds only about 0.4 GiB and 7 ms more.
2. **A 5 Hz camera saves nothing.** `CameraCfg.update_period` throttles only the sensor read-out (1.07 → 0.19 ms). The
   renderer still draws every step, so step time and memory do not fall. A real saving needs rendering switched on
   only at VLA decision steps, which is a code change, not a setting.
3. **Host RAM is not a constraint.** At least 52 GB stayed available in every run.
4. RTF is below 1 even with no cameras (0.47), so the evaluation loop must run on simulated time, not wall time.

## AC3 evidence: first-person, correctly oriented, pose not measured

- **Horizon rows match the configured pitch, including its sign.** The level head camera: predicted row 240, observed
  226. The +16.7° wide camera: predicted 507, observed 485. The observed rows sit about 14–22 px above prediction
  because the whitish haze at the horizon is not counted as sky.
- **D435i depth is geometrically consistent.** Centre pixel 1.168 m implies a camera height of 0.399 m, which is the
  V12 root height plus the 0.108 m mount offset. Rows 0–39 are non-finite, as expected for sky plus ground beyond the
  30 m clip.
- **Not a chase view.** The lower 34 % of the D435i image (rows 475–719, 29.3 % of pixels) is the robot's own head
  shell, 5–9 cm from the lens.
- **Pose boundary.** The head pose `(0.27, 0, 0.09)` is approximate, from the camera ablation. The D435i pose is the
  adapter's default `--sensor-translation`, not a measured D435i mount, and its self-occlusion makes that pose unusable
  for VLA depth. The measured mount transform is required before Phase C.

## InternVLA-N1 alone, and its caveat

`phase_b_vla_resident_v2`, pinned InternNav (agent `cad22868…`, model `d7fa4cc8…`, identical to the `7a5c6240` pin),
bf16, flash-attention 2, loaded exactly as upstream's `http_internvla_server.py`. The input was the D435i RGB-D frame
from `phase_b_dual720_hz0_v1`.

- Load 96.4 s. After load: 15,990 MiB allocated, 16,462 MiB device. After warm-up: 16,660 MiB device.
- During the loop: max allocated 16,729 MiB, max reserved 18,998 MiB, process 19,464 MiB. System 2 mean 0.354 s
  alone and 0.422 s while Isaac was starting.
- **Caveat: System 1 never ran.** All 2,264 calls returned the discrete "look down" action `[5]`. The probe did not
  make upstream's follow-up `look_down=True` call, so no latent or trajectory was produced. Prior DualVLN episodes on
  this card that did run System 1 peaked about 0.9 GiB higher in allocated memory (17,054 vs 16,103 MiB,
  `2026-09-08_dualvln_rented4090/OPUS_RETURN.md` §3). The true shortfall is therefore at least what is reported here.

## Fallbacks, with what the evidence says about each

| fallback | expected effect | evidence status |
| --- | --- | --- |
| F1 Shrink Isaac: size PhysX GPU buffers for one env (or run PhysX on CPU); leaner RTX settings | Targets the exact allocations that failed (512 and 640 MiB buffers); no-camera Isaac is 4.9 GiB | not measured |
| F2 VLA allocator `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` | Prior DualVLN runs: peak reserved 19,780 → ~17,180 MiB; no model change | measured in another task, not here |
| F3 Two machines: Isaac on gpu5070ti (16 GB, ran the accepted V12 run), VLA on the 4090, over the existing TCP bridge | Removes the memory conflict completely | cross-host latency not measured |
| F4 One larger GPU (≥ 32 GB) | Removes the conflict | cost only |
| F5 Quantise the VLA | Large saving | changes model outputs; needs revalidation, last resort |
| Lower resolution or render rate | 640x480 vs dual 720p differs by 0.4 GiB; rate does not change memory | measured insufficient |

Budget for F2 plus F1 on this card:
- With F2, the VLA process would be about 17,180 MiB reserved (prior figure, System 1 included) plus about 466 MiB of
  non-allocator overhead (19,464 − 18,998 here), so about 17.6 GiB.
- Isaac dual-720p is 7,908 MiB, which makes about 25.6 GiB against 24,081 MiB usable.
- F1 must therefore save about 1.5 GiB, plus a working margin: about 2 GiB in practice.

## Runs that failed, kept as evidence

| run | what happened | fix |
| --- | --- | --- |
| `phase_b_none_v1` | the driver's `chmod -R` hit uid-1234 files left under `home/` and aborted under `set -e` before docker started | `sudo chmod` (also in `phase_a_run_docker.sh`) |
| `phase_b_none_v2` | measurement completed, then `simulation_app.close()` hung; `timeout` killed the docker client but the container kept 1.4 GiB until the lead killed it. The next run started 35 s before that kill; its timed window began 111 s after it | probe now calls `wrapped_env.close()` first (as the adapter does); driver kills a leftover container, refuses to start beside another `vla-phase-*` container, and force-stops 180 s after the result file |
| `phase_b_vla_resident_v1` | the model loads `checkpoints/depth_anything_v2_metric_hypersim_vits.pth` relative to the working directory | probe links that one file in its run directory and removes the link at exit |
| `phase_b_vla_resident_v2_isaac` | the OOM above; Isaac hung after the PhysX abort and was killed by the driver at the 900 s wall limit | none — this is the result |
| `phase_b_dual720_v12buf_v1`, `_1envbuf_v1` (first attempt) | refused at start under the 6 GB free-disk guard after a machine-dog-nav image build; no directory created, ids unused | second deletion (above), then run |
| `phase_b_vla_resident_v3` | VLA OOM in System 1: autograd on and 1280x720 input; its Isaac half then ran alone, so it is not a co-residence measurement | `torch.set_grad_enabled(False)`, 640x480 input (v4) |

Collection note: `scp -r` through the jump host managed about 0.4 files/s on the 4,539-file VLA run.
`collect_run.sh` now streams one tar archive (49 s) and builds its manifest NUL-separated, because upstream names debug
images `debug_raw_ 000.jpg`. Local and remote hashes of that run are identical.

## Host maintenance during Phase B

Approved by Dr Sun on 2026-09-14: only regenerable download caches in VLA execution copies were deleted. That was
X-NavDP `runtime/pip_cache` (535 files, 4.20 GB), plus DualVLN `mamba/pkgs/cache` (12 files, 0.93 GB) and 264 conda
tarballs (0.74 GB). Free space went from 9.3 GB to 15.0 GB. `official_env_024`, `sim_env` and the X-NavDP py311
environment still import. Record: `setup/host_cleanup_20260914/`.

A machine-dog-nav image build (`localhost/machine-dog-nav/foxy-scan:20260813`, 6.93 GB, plus build cache) then took
free space down to 3.2 GB. The next two Isaac runs refused under the 6 GB guard before creating their directories.
Dr Sun then approved a second deletion on 2026-09-14:
- the remote DualVLN `public_scenes/runs` copy (3,096 files, 2.3 GB). Every file was re-verified identical to the
  local copy immediately before deletion; the list is kept in `cleanup2_verified_remote_ablation_runs_sha256.txt`.
- the failed habitat-lab 0.3.3 environment `official_r2r/official_env` (6.2 GB unique; its freeze is local).

Free space went from 3.3 GB to 12.1 GB, and `official_env_024` still imports. The DualVLN task's records still name
those two remote paths; the local copies are now the only ones.

## Fallback decision

Dr Sun chose **F1 + F2 on one GPU** on 2026-09-14. The measurements are recorded below as they land.

### F1: one-robot PhysX GPU buffers halve Isaac's footprint and change nothing physical

The comparison uses the same probe, cameras (dual 720p, every step) and seed. `physx_gpu_cfg` in each
`camera_probe.json` records the values that were applied.

| run | buffers | GPU MiB | RTF | step ms mean / p95 | resets | root height min / mean (m) | vx last 100 steps (m/s) | PhysX buffer warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `phase_b_dual720_v12buf_v1` | V12 task: 512 MiB collision stack, 2^23 contacts, 1M patches, 2^25 aggregate pairs | 7,780 | 0.335 | 59.6 / 64.7 | 0 | 0.29991 / 0.31239 | 0.27357 | 0 |
| `phase_b_dual720_1envbuf_v1` | one_env: 64 MiB stack, 2^16 contacts/pairs, 2^15 patches | **3,956** | 0.332 | 60.2 / 63.8 | 0 | 0.29991 / 0.31239 | 0.27357 | 0 |

- The one-robot buffers save **3,824 MiB (−49 %)** at no measurable speed cost.
- Root height and forward velocity agree to every printed digit, so the smaller buffers never overflowed and no
  contacts were dropped.
- This holds on the flat course. A furnished scene has more contact pairs and must be re-checked for PhysX overflow
  warnings.

### F1 + F2 co-residence: it fits (GO on one GPU, flat course)

`phase_b_vla_resident_v4` ran with `expandable_segments:True`, one-robot PhysX buffers, autograd off and a 640x480
input. InternVLA-N1 and the dual-720p Isaac probe completed side by side: VLA rc 0, Isaac rc 0, no out-of-memory
error, no PhysX buffer warning.

| quantity | value |
| --- | --- |
| VLA process (`nvidia-smi`) | 17,728 MiB |
| VLA torch peak allocated / reserved | 17,041 / 17,262 MiB |
| Isaac process, dual 720p, one_env buffers | 3,912 MiB |
| **whole device peak** | **21,690 MiB of 24,081 usable: 2.3 GiB headroom** |
| System 1 exercised | 321 trajectories, 56 look-down queries, 61 System 2 cycles |
| System 1 call (no System 2) | median 0.280 s, p95 0.371 s |
| System 2 cycle incl. look-down and latents | median 1.784 s, max 2.468 s |
| Isaac RTF / step ms mean, median, p95 while sharing | 0.166 / 120, 84, 350 (alone: 0.332 / 60, –, 64) |
| Isaac locomotion while sharing | 0 resets; height and vx identical to the solo run |

What it means:
- **Memory is solved on this card**, with 2.3 GiB to spare on the flat course.
- **Compute is shared, not free.** With the VLA inferring continuously (the worst case), the simulation runs at half
  speed and its step time spikes during System 2. The closed loop must therefore advance on simulated time, pausing
  the simulation while the VLA thinks, rather than assume wall-clock pacing. At RTF 0.17, one simulated minute costs
  about six wall minutes.
- **The VLA-side input matters.** The input here was the D435i frame centre-cropped to 4:3 and resized to 640x480
  (HFOV 54.5°), standing in for Phase C's 640x480 camera.

### Why v3 failed, and what the Phase C client must copy

`phase_b_vla_resident_v3` (F1 + F2, but 1280x720 input and autograd on) ran out of memory **inside the VLA process**
at its first System 1 call. Torch allocated memory went from 16,014 to 23,458 MiB in `nextdit_traj.py`.
`InternVLAN1ForCausalLM.generate_traj` runs its 10-step, 32x2-sample diffusion loop outside `no_grad`, and upstream's
`scripts/realworld/http_internvla_server.py` calls `agent.step` with autograd on. The DualVLN fixture probe had wrapped
`step` in `torch.no_grad()` (`scripts/probe.py:181`), which is why it peaked at 16.2 GiB. With autograd off, v4 peaked
at 17.0 GiB.

Requirements carried into Phase C:
1. Run agent inference with autograd disabled.
2. Use `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
3. Use one-robot PhysX GPU buffers (`--physx-buffers one_env`).
4. Feed 640x480 frames. In look-down mode the agent passes the image to System 2 unresized.
5. Advance the loop on simulated time.
6. Measure the D435i mount pose (AC3).

## Claim boundary

- Measured:
  - camera render cost on the flat course;
  - that the as-specified configuration does not fit on this 4090;
  - that F1 + F2 with autograd off does fit, with System 1 exercised and 2.3 GiB headroom;
  - that sharing halves simulation speed;
  - the viewpoint and pitch of the rendered cameras.
- Not measured:
  - cost in a furnished scene. The flat course renders almost nothing and has few contacts, so real scenes can only
    use more memory, and PhysX buffers must be re-checked there;
  - the timing of a real closed loop at the VLA decision rate. v4 inferred continuously, which is the worst case;
  - cross-host latency, since F3 was not needed.
- Not claimed: navigation quality of any kind. The VLA input was one static frame, repeated.
