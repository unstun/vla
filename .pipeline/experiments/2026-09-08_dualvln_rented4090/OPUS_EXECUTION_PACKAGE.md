---
origin: ai+local
reviewed: false
date: 2026-09-08
status: prepared_not_dispatched
executor: Opus
---

# DualVLN BF16 inference and one simulator video

## Goal and authorization

Write all responses and `OPUS_RETURN.md` in English.

Dr Sun approved trying DualVLN inference and simulation on the rented RTX 4090, then explicitly requested that Opus execute this package. Complete BF16 model inference, one bounded simulation loop, and a playable local video. Repair ordinary setup/runtime failures within this scope without asking again.

- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Task: `.trellis/tasks/09-08-dualvln-rented4090` (`in_progress`; PRD/design/implementation plan exist).
- Owned experiment: `.pipeline/experiments/2026-09-08_dualvln_rented4090` (called `EXP` below).
- SSH: `ssh ubuntu@117.50.179.202`, or existing alias `rented4090`. Existing key authentication works; no password is needed in this package.
- Remote copy: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090` (called `REMOTE` below).
- Preserve other contributors' edits, previous locomotion directories, and the running `isaac-sim` container. No training, real-robot actuation, server purchase, global driver/framework replacement, or unrelated process termination.

## Already done — refresh, do not repeat

Snapshot: **2026-09-09 06:16:24 UTC**. Full details: `EXP/setup/opus_handoff_state.json`.

| Item | Observed state |
| --- | --- |
| Hardware | RTX 4090 24564 MiB; about 21179 MiB free; 62 GiB RAM; roughly 125G free disk |
| System | Ubuntu 22.04, driver 575.57.08, host Python 3.10 |
| Protected workload | Existing Isaac Sim 5.1.0 container; Kit PID 1324 used about 2.9GB. Re-identify before touching anything |
| Environment install | Supervisor PID 2685, command PID/PGID 2687; installing Torch/CUDA dependencies; no completion marker yet |
| Weight download | Supervisor PID 2686, command PID/PGID 2690; about 7.2GB present; shard 4 verified, shards 1–3 partial |
| Time limits | Both existing jobs have 3600-second supervisor deadlines; inspect `runs/{setup,download}/{process,meta}.json` and logs |
| Simulation preparation | `setup_sim.sh`, `download_scene.py`, Micromamba archive and scene metadata synced; **neither simulation job was launched** |
| Source sync | 607 work-copy files passed SHA-256 checks; `REMOTE/setup/initial_sync_gate.json` |
| Actual inference | **Not started. No inference probe or simulation runner has been implemented yet** |

The local `fixtures/realworld_sample_data1/` contains 152 released RGB images and `instruction.txt`. These extracted files were not synced; the verified source tar already exists remotely at `work/InternNav/assets/realworld_sample_data.tar.gz`.

## Fixed sources and interfaces

- Pristine source: `references/upstream/2026-09-08_dualvln/source/InternNav`, clean commit `7a5c62400ac45b313d9b709c740b64191556a242`; edit only `EXP/work/InternNav`.
- Checkpoint: `InternRobotics/InternVLA-N1-DualVLN`, revision `a698a9e898b4001621a319e1bc89f02ec715cc86`, original BF16, about 8.38B parameters.
- Encoder: `depth-anything/Depth-Anything-V2-Metric-Hypersim-Small`, revision `3bc65d4e14a6786a61acec16453c50e12bf5f338`; hash/size in `setup/encoder_source.json`.
- Existing patch: lazy optional agent imports in `internnav/agent/__init__.py`; recorded in `setup/compatibility.patch`. No model math or weights changed.
- Setup target: Python 3.10, Torch 2.6/cu124, Transformers 4.51, Diffusers 0.33.1, FlashAttention 2.7.3 **cu12 / torch2.6 / cp310 / ABI FALSE**. Treat setup scripts as prepared, not validated installations.
- Original fixture entry: `scripts/notebooks/inference_only_demo.ipynb`; class `internnav/agent/internvla_n1_agent_realworld.py:InternVLAN1AsyncAgent`. Supply `plan_step_gap=4`, RGB/depth/pose, and `intrinsic`. The sample uses dummy depth/pose: label this phase **open-loop**.
- Model initialization expects `checkpoints/depth_anything_v2_metric_hypersim_vits.pth` relative to its working directory. Link the verified downloaded encoder there within task-owned paths.
- Do not blindly use `scripts/realworld/http_internvla_server.py`: it hardcodes the instruction and lacks arguments supplied by the notebook.
- Simulation candidate: Habitat-Sim 0.3.3 in a separate Python 3.9 environment; public `apartment_1.glb` + navmesh, dataset revision `910c783fb954da8497ea5f811b843a76590ddddc`. See `setup/habitat_scene_source.json`. This is a small functional trial, not full paper benchmark reproduction.

## Remaining execution

1. **Take over existing jobs.** Refresh PIDs, log progress and `meta.json`; do not launch duplicate installs/downloads. Preserve verified files and `.part` files. Setup previously recovered from one NVIDIA package read timeout.
2. **Finish environment and asset verification.** Require `SETUP_COMPLETE` and `setup/original_weight_manifest.json`, confirm CUDA/FlashAttention import, and verify upstream LFS hashes. Inspect missing/unexpected checkpoint keys when loading.
3. **Implement a bounded fixture probe locally.** Reuse the original agent and preprocessing. Run a short released image sequence; retain verbatim instruction, input hashes, raw S2 text/actions, finite S1 trajectories, per-call timing, model CUDA allocation and sampled total VRAM. Do not switch precision or present constructor success as inference.
4. **Prepare the simulator.** Run the prepared setup/download scripts, fixing their ordinary compatibility issues if necessary. Preview and then freeze the initial pose, instruction and target before rollout. Retain actual RGB/depth and camera intrinsics. Keep model and simulator in separate environments/processes if needed.
5. **Implement and run the loop.** Reuse the native consumer where possible: `internnav/model/utils/vln_utils.py:traj_to_actions` maps raw S1 increments to 0.25m forward / 15-degree turns. It divides inputs by four **in place**; clone raw tensors before repeated conversion. Distinguish these raw increments from the already integrated XY path returned by the realworld agent. Record proposed actions, applied actions, collisions and realized pose. Handle look-down requests with a real camera change.
6. **Deliver video and evidence.** Save an MP4 under `EXP/runs/<run_id>/`, decode it and inspect representative frames. Provide an actual simulation video; label any fixture overlay separately. Record learned STOP, timeout and navigation failure separately. Return failed cases too.

Use unique job names; `run_job.py` rejects an existing output directory. Its options precede the job name:

```sh
# Run inside REMOTE after syncing the locally authored script/config.
python3 scripts/run_job.py --seconds 600 inference_v1 -- venv/bin/python scripts/probe.py
python3 scripts/run_job.py --seconds 3600 sim_setup_v1 -- bash scripts/setup_sim.sh
python3 scripts/run_job.py --seconds 600 scene_download_v1 -- python3 scripts/download_scene.py
```

`probe.py` above is to be implemented. Limit the initial simulation to **1800 seconds and 200 model-driven steps**. If VRAM is insufficient, preserve the failure and split placement/process lifetimes; do not kill the protected Isaac job or silently quantize.

## Sync Gate and return

Edit locally, sync only task-owned files, verify source/config/input identity before runs. Return raw logs, run metadata, environment versions, all compatibility changes, input/output manifests and video to the same local experiment. Unmodified public model bytes may remain a reproducible remote cache with revision/hash/regeneration records; unique outputs must return locally.

Write `EXP/OPUS_RETURN.md` in English with: actual result, commands/exit codes, evidence paths, peak VRAM/latency, failures, source/sync status, and remaining work. Keep the task at `review` pending lead acceptance. Stage only owned paths if committing; never include unrelated dirty work or an embedded source checkout accidentally. The lead will inspect the diff, actual model outputs, pose/action records, video and hashes.
