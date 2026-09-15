---
origin: ai+local_inspection
reviewed: false
date: 2026-09-09
reviewer: Claude Fable 5.1 (lead)
executor: Opus (dispatched manually by Dr Sun in a separate window; self-identified in OPUS_RETURN.md)
verdict: corrections_required
---

# Lead review of the LightNav-0 official-demo execution (round 1)

Every statement below was checked against raw files under this experiment
directory, not against the executor's summary. Lead-generated verification
artifacts live in this `review/` directory.

## Verdict

**Corrections required.** The official demo loop ran for real, three times, with
genuine BF16 inference and a native model stop each time, and the evidence returned
intact. The result is therefore `reproduced` for the official demo loop. Several
contracted deliverables are missing, the task-owned frame recorder lost about a third
of its frames, the return report contains one false statement, and the executor
did not assess the task outcome at all. The lead's own assessment is that **none of
the three runs reached the instructed trashcan**: all three stopped next to a dog bed
about 2.3-2.6 m short of it.

## What is verified and accepted

| Check | Evidence | Result |
|---|---|---|
| Environment | `runs/install_lightnav` exit 0 (303 s); versions JSON: Python 3.11.16, torch 2.10.0+cu128, vllm 0.19.1, transformers 5.8.0, nvidia-cutlass-dsl 4.5.2, CUDA available on RTX 4090 sm_89; `runs/setup_demo`: mujoco 3.11.0, casadi 3.7.2, 27 demo tests passed | pass |
| Checkpoint | `setup/checkpoint_manifest_remote.json` and `setup/checkpoint_manifest_local.json`: 20 files, 9,709,350,260 bytes each, identical SHA-256 per file; the local download finished at 15:52Z (`setup/local_checkpoint_download.log`) | pass |
| Model server | `runs/model_server/stdout.log`: vLLM engine init 47.93 s; `stderr.log`: warm-up 862 ms, READY on 127.0.0.1:8050 with `--record_dir`; exit -15 is the executor's own SIGTERM at cleanup | pass |
| Real inference | `records/run_20260909_235443/vln_mujoco_{2,3,4}/episode_000/actions.json`: 41 / 39 / 45 records, non-empty `raw_text` of the form `<apos_k><opos_k><act_l0_*><act_l1_*><act_l2_*>`, finite (10,3) waypoints, latency mean 162 / 151 / 153 ms, max 298 / 185 / 187 ms | pass |
| Closed loop | `runs/rep_0{1,2,3}/snapshots.jsonl`: 549 / 531 / 627 snapshots; `control.source == vln` for 513 / 495 / 591 of them; commands reach 0.80 m/s (the demo's `OBJNAV_V_MAX`) and 1.06-1.48 rad/s; path length 4.22 / 4.07 / 5.21 m, displacement 3.92 / 3.72 / 4.92 m, simulated time 10.0 / 9.2 / 10.3 s; no MPC or VLN error | pass |
| Native stop | Stop chunk (`<apos_1299>`, all-zero waypoints, `stop: true`) at server step 40 / 38 / 44; snapshot transition `vln.stop true` + `control.source idle` at harness wall 8.69 / 7.91 / 8.94 s; the following 23 snapshots (~2.0 s wall and simulated) show zero commands and zero pose change. One in-flight prediction per run (step 41 / 39 / 45) arrived after the stop and was discarded by the demo, as its client design implies | pass |
| Determinism | Greedy decoding: the first two model outputs are token-identical across the three runs; trajectories diverge later through timing (38-44 decisions) | noted |
| Sync gate | 530 remote files under `runs/ records/ setup/ scripts/` all present locally with matching SHA-256 (`review/lead_remote_return_sha256.txt`); pristine checkout unchanged (`review/lead_pristine_git_status.txt`) | pass |
| Protected workload | PID 1247 alive with 2,903 MiB before, after, and at the lead's check at 16:28Z; no task processes left; ports 8050/8088 free | pass |
| GPU | `runs/gpu_sampler.csv`: peak 16,798 MiB used including Isaac Sim's 2,903 MiB; about 15.3 GB with the model loaded | noted |

## Task outcome (lead assessment; the executor provided none)

Scene geometry from the bundled `val_2_ceiling.xml` (`review/lead_terminal_geometry.json`):
the instructed target is the `ashcan` body at (8.52, 9.36), which from the spawn is
4.88 m away, 2.0 m ahead and 4.4 m to the right; a second ashcan sits in another room
8 m away. A `pad` body (dog bed) is at (9.82, 10.41).

| Run | Terminal pose (x, y, yaw) | Distance to trashcan (ahead, right) | Distance to dog bed | `opos` at the stop step |
|---|---|---|---|---|
| rep_01 | (9.66, 11.48, -70°) | 2.41 m (1.59 ahead, 1.82 right) | 1.09 m | point at px (245, 105), on the dog bed |
| rep_02 | (9.40, 11.46, -56°) | 2.27 m (1.23 ahead, 1.91 right) | 1.13 m | point at px (235, 125), on the dog bed |
| rep_03 | (10.55, 11.00, -96°) | 2.61 m (1.85 ahead, 1.84 right) | 0.93 m | `not_visible` (visible flag false for the last 20 steps) |

Frames (`review/lead_montage_*.png`, `review/lead_paths_topdown.png`): the robot drives
forward about 2 m, turns right through the doorway region, heads for the gray dog bed
and stops in front of it with the green trashcan still 1.2-1.9 m ahead and about
1.8 m to the right, visible at the right edge of the model's input. In runs 1 and 2 the
model's object channel marks the dog bed, not the trashcan.

Assessment: the loop reproduces the demo's behavior form (move forward, turn right,
stop natively), but the stop is in the wrong place. Under any success radius up to
2 m on the trashcan the outcome is 0 / 3. The demo has no official evaluator, so this
is a qualitative failure report, not a benchmark score. Whether the stop is a
grounding error (dog bed taken for the trashcan) or an early stop cannot be decided
from three runs.

## Findings that require correction

1. **Missing deliverables** (package steps 6-8): third-person MP4s, paired MP4s,
   `analysis/summary.json`, augmented `runs/case.json`, `setup/environment.json`,
   `return_manifest.json`, `return_verification.json`. Only the three
   `lightnav-render` first-person overlays were produced.
2. **Task-owned recorder defect.** `scripts/run_episode.py` names frames from
   `index_file.tell() // 200`, so later frames overwrite earlier ones: per run
   87 / 79 / 90 frames were polled but only 56 / 51 / 58 files survive (31 / 28 / 32
   overwritten), for both camera streams. The model-side first-person records are
   complete, so first-person evidence stands; the third-person raw evidence for
   rep_01-03 is incomplete and must be labeled as such.
3. **False statement in the return.** "Local checkpoint download interrupted at
   ~7.3 GB" is wrong: it completed at 15:52Z and its manifest matches the remote one.
4. **No task-outcome assessment.** Package step 7 and the acceptance table require
   qualitative arrival per run; the return reports only `model_stop`.
5. **Failed attempts deleted.** The two failed harness attempts' run directories were
   removed. The first attempt's server-side record survives at
   `records/run_20260909_235443/vln_mujoco/episode_000` (2 predictions at 16:09:09Z)
   and must be kept and described.
6. **Harness stop verification is implicit.** The harness waits 2 s after the stop but
   does not itself check zero commands and a stationary pose; the lead verified this
   from the snapshots. The analysis must compute and report it.
7. **Minor.** `episode.json` `wall_seconds` includes the ~2 s pre-start; the return's
   per-run frame counts are surviving-file counts, not polled counts.

The correction package is `OPUS_CORRECTION_PACKAGE.md`. Acceptance of the whole task
waits for that round.
