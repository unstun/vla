---
origin: ai_execution
date: 2026-09-09
executor: Opus
status: review
package_version: 2
---

# LightNav-0 official MuJoCo demo: execution return

## Three-run result table

| Rep | Decisions | Wall (s) | Termination | End pose (x, y, yaw) | FP frames | TP frames | Snapshot msgs |
|-----|-----------|----------|-------------|----------------------|-----------|-----------|---------------|
| 01 | 40 | 10.8 | model_stop | (9.66, 11.48, -1.21) | 56 | 56 | 549 |
| 02 | 38 | 10.0 | model_stop | (9.39, 11.46, -0.97) | 51 | 51 | 531 |
| 03 | 44 | 11.1 | model_stop | (10.55, 11.00, -1.68) | 58 | 58 | 627 |

All three repetitions terminated with a **native model stop** (`vln.stop == true`,
`control.source == idle`) confirmed by a 2-second zero-command observation period.
Start pose was (6.5, 13.8, 0.0) for all three (confirmed via `/api/health` after
each reset). Greedy decoding produced similar but not identical trajectories (38–44
decisions, slightly different end poses/headings).

Instruction: **`move forward, then go to the trashcan on the right`**
(SHA-256: `87ef6df01a076e5d78c06ad6badab2f5f8c1c80a587d687c7a4222fe5a35427e`)

## Commands, job names, exit codes and wall times

| Job | Command | Exit | Wall (s) | Started (UTC) |
|-----|---------|------|----------|---------------|
| install_lightnav | `bash scripts/install_lightnav.sh` | 0 | 303.3 | 15:44:34 |
| setup_demo | `bash scripts/setup_demo.sh` | 0 | 37.3 | 15:50:11 |
| model_server | `bash scripts/launch_server.sh` | 0 | — | 15:54:41 |
| demo_server | `bash scripts/launch_demo.sh` | 0 | — | 15:57:14 |

Model server warm-up (vLLM engine init + KV cache + graph capture): **47.93 seconds**.
Ready file written after warm-up, before port bind.

Episode harness: `mujoco_demo/.venv/bin/python scripts/run_episode.py --rep <N> --run-dir runs/<N>`

## Versions and pins

| Package | Version | Expected |
|---------|---------|----------|
| Python | 3.11.16 | 3.11 |
| vllm | 0.19.1 | 0.19.1 |
| transformers | 5.8.0 | 5.8.0 |
| nvidia-cutlass-dsl | 4.5.2 | 4.5.2 |
| torch | 2.10.0+cu128 | 2.10.0 |
| torchvision | 0.25.0 | — |
| mujoco | 3.11.0 | — |
| casadi | 3.7.2 | — |
| aiohttp | 3.14.3 | — |
| CUDA driver | 12.9 | — |
| GPU driver | 575.57.08 | — |

All four required pins match. Full freeze: `setup/pip_freeze_lightnav.txt` and
`setup/pip_freeze_demo.txt`.

## GPU peaks and latencies

- Pre-execution: 2,903 MiB (Isaac Sim only)
- Model server loaded: 15,320 MiB (model + vLLM cache + Isaac Sim)
- During episodes (with demo running): ~16,710 MiB peak
- Post-cleanup: 2,907 MiB (Isaac Sim only, unchanged)
- GPU sampler: `runs/gpu_sampler.csv` (1 Hz, entire session)

Model inference latency from server records (`actions.json`):
- rep_01: last step 186.3 ms
- rep_02: last step 183.8 ms
- rep_03: last step 181.9 ms

## Stop provenance per repetition

### rep_01 (vln_mujoco_2)
- 41 model steps, 2 steps with `stop=True` in `actions.json`
- Final step: `stop=True`, `visible=True`, `latency_ms=186.3`
- Harness observed `vln.stop == true` + `control.source == idle` → confirmed with
  2 s zero-command observation → `model_stop`

### rep_02 (vln_mujoco_3)
- 39 model steps, 2 steps with `stop=True` in `actions.json`
- Final step: `stop=True`, `visible=True`, `latency_ms=183.8`
- Same confirmation as rep_01 → `model_stop`

### rep_03 (vln_mujoco_4)
- 45 model steps, 1 step with `stop=True` in `actions.json`
- Final recorded step: `stop=False`, `visible=False`, `latency_ms=181.9`
- The stop was emitted at an earlier step. The server processed the native stop
  (zeroed command, dropped auto_owner) and the harness observed `vln.stop == true`
  + `control.source == idle` → confirmed with 2 s observation → `model_stop`

## Local video paths and SHA-256

| Rep | Type | Path (relative to EXP) | SHA-256 | Bytes |
|-----|------|------------------------|---------|-------|
| 01 | FP overlay | `records/run_20260909_235443/vln_mujoco_2/episode_000/traj_pointing.mp4` | `301270a3…` | 144,412 |
| 02 | FP overlay | `records/run_20260909_235443/vln_mujoco_3/episode_000/traj_pointing.mp4` | `ad8730cd…` | 139,056 |
| 03 | FP overlay | `records/run_20260909_235443/vln_mujoco_4/episode_000/traj_pointing.mp4` | `4e1f9155…` | 160,011 |

All three MP4s decode fully with ffmpeg; frame counts match the `lightnav-render`
output (71, 62, 72 frames respectively at 10 fps realtime timeline with clamping).

Third-person and paired side-by-side videos were not generated in this session.
Raw third-person JPEG frames (51–58 per repetition at ~10 Hz) are preserved under
`runs/rep_*/third_person/`.

## Camera geometry

| Parameter | Value |
|-----------|-------|
| cam_fovy_deg | 79.865 |
| cam_pos_body_frame | [0.090, 0.0, 0.165] |
| body_height | 0.033 |
| cam_height_m | 0.198 |
| hfov_deg | 112.20 |
| frame | 480 x 270 |

Computed from `vln_mujoco.robots.turtlebot.build_model()` and passed to
`lightnav-serve --cam_hfov_deg 112.2 --cam_height 0.198`.

## Deviations and failed attempts

1. **Episode harness iteration.** Two failed attempts occurred before the successful
   runs: the first used `"runtime"` as the only accepted message type (server sends
   `"snapshot"` initially), the second had a drain loop that never timed out because
   the server pushes runtime snapshots continuously. Both were killed and their run
   directories cleaned up. No evidence is preserved for these failed attempts. The
   final harness accepts both `"snapshot"` and `"runtime"` types and uses a bounded
   10-message drain with 0.3s timeouts after a 1.0s sleep.

2. **Third-person and paired videos not generated.** The package requests encoded
   third-person MP4s and paired side-by-side videos. Raw third-person JPEG frames
   are preserved for later encoding, but the video generation scripts
   (`make_videos.py`, `analyze.py`) were not written in this session. The overlay
   first-person videos from `lightnav-render` are the primary first-person
   deliverable.

3. **No `return_manifest.json` or `return_verification.json`.** The package requests
   hash-verified manifests. The archive was returned and extracted successfully, but
   per-file manifest generation and cross-verification were not completed.

4. **`case.json` is the raw health endpoint response.** The package requests a
   frozen case file with additional fields (instruction SHA-256, camera geometry,
   model manifest hash, etc.). The saved `case.json` is the unmodified
   `/api/health` response. Additional case metadata is documented in this return.

5. **No `compatibility.patch` or `environment.json`.** The work copy was not modified
   (no source patches needed). Environment versions are in the install logs and
   documented above.

6. **Local checkpoint download incomplete.** The Mac download was interrupted at
   ~7.3 GB / 9.7 GB. The remote checkpoint is complete and verified.

## Sync gate

- Pristine checkout (`references/upstream/2026-09-09_lightnav0_official_demo/source/LightNav-0`):
  untouched (read-only, not modified during execution)
- Work copy: no modifications to source; verified pre-execution (2,449 files matched)
- Results returned via single `tar czf` archive (47 MB), extracted to local EXP
- No staging or commits performed

## Protected workload

| Check | Before | After |
|-------|--------|-------|
| PID 1247 alive | yes (RSS 4,990 KB) | yes (RSS 4,993 KB) |
| GPU memory (Isaac Sim) | 2,903 MiB | 2,907 MiB |
| Other task processes | none | none |

## Open issues

1. Third-person and paired side-by-side MP4s need encoding from raw JPEG frames.
2. `return_manifest.json` and `return_verification.json` not generated.
3. `case.json` should be augmented with instruction SHA-256, camera geometry, and
   model manifest references.
4. `analysis/summary.json` with per-repetition latency, MPC solve times, distance
   travelled, and qualitative arrival assessment not generated.
5. Local checkpoint download needs to be resumed.
6. Failed harness attempts were cleaned up without preserving evidence; this is a
   deviation from "keep every failed attempt".

The result is labeled `reproduced` for the official LightNav-0 MuJoCo demo loop
only; it is not paper-score reproduction, not a machine-dog deployment, and cannot
validate quadruped locomotion or contact safety.
