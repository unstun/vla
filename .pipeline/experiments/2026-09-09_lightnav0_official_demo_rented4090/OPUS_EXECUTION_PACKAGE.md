---
origin: ai+local+official_upstream
reviewed: false
date: 2026-09-09
status: prepared_not_dispatched
executor: Opus
---

# LightNav-0: reproduce the official MuJoCo demo on rented4090

Write all responses and `OPUS_RETURN.md` in English.

## Goal and authorization

Run the released LightNav-0 checkpoint through its own MuJoCo demo, original
scene, default instruction, WebSocket client, and MPC. Return actual navigation
videos and a traceable account of stopping. Dr Sun requested this server-side
official-demo reproduction. Isolated installation, asset acquisition, bounded
pretrained inference, simulation, recording, and ordinary compatibility fixes
are authorized. No training, robot actuation, full benchmark, quantization,
driver changes, public service exposure, unrelated process termination, staging,
or commit.

- Local Source of Truth: `/Users/sun/tongbu/study/phdproject/vla` (`ROOT`).
- Own `ROOT/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090`
  (`EXP`) and `ROOT/.trellis/tasks/09-09-lightnav0-official-demo-rented4090`.
  You may append only this experiment's specific large-byte paths to `.gitignore`,
  with corresponding provenance and hashes; preserve all existing entries.
- Remote execution copy: `/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090`.
- SSH: `rented4090` = `ubuntu@117.50.179.202:22`, existing key authentication.
- Pristine source: `ROOT/references/upstream/2026-09-09_lightnav0_official_demo/source/LightNav-0`.
  Make an execution copy at `EXP/work/LightNav-0`; leave the pristine copy intact.
- Read project `AGENTS.md`, the task PRD, upstream `AGENTS.md`, and
  `.trellis/spec/backend/simulator-inference-evidence.md`. You are not alone in
  the repository: preserve concurrent changes and all previous experiments.
- Setup/download deadline: 60 minutes; model startup and all GPU evaluation
  attempts together: 1,800 wall seconds. Use a process-group supervisor, record
  PID/PGID/start identity, and terminate only this task's descendants.

The lead prepared this package but has not dispatched Opus or run inference.
Activate this dedicated Trellis task when starting execution. Keep preparation,
execution, lead review, and acceptance as separate states.

## Frozen official inputs

- Repository: https://github.com/lightorigins/LightNav-0
  commit `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c` (`main`, Apache-2.0).
- Model: `LightOriginsHQ/LightNav-0`, revision
  `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`; original BF16, no quantization.
  HF reports 4,847,825,408 stored BF16 parameters. The single weight shard is
  9,695,744,034 bytes, SHA-256
  `ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18`.
  Download the complete pinned model directory, including its RVQ decoder,
  `eval_config.json`, tokenizer, and processor. The API currently reports
  `gated=false`; try anonymous download. Do not assume a login is necessary.
- Scene: bundled MolmoSpaces ProcTHOR validation `val_2_ceiling.xml`, scene ID
  `procthor-val-2`. Assets are CC BY 4.0, attributed to Ai2, source revision
  `c89e1f5481af56fd25ef4efb76bdced9b726ec6a`. All 2,236 manifest entries passed
  local byte/hash verification. No MP3D/HM3D download is needed.
- Robot: default `turtlebot`; preserve the default spawn, camera, simulation
  timing, MPC, capture-pose alignment, and stop parsing. This robot is advanced
  kinematically; it does not establish quadruped locomotion or physical collision
  safety. Do not switch to MicroDuck, Go2, Habitat, or a custom scene.
- Instruction, verbatim from `mujoco_demo/vln_mujoco/web/index.html:48`:
  **`move forward, then go to the trashcan on the right`**.
- Model task: `--task vln`. Preserve checkpoint-resolved history, resizing,
  pooling, prompting, decoding, and action horizon (10 SE(2) waypoints).
  Do not translate, substitute a target, or select successful prompts after trials.

Preparation evidence is in `EXP/setup/`: pinned HF metadata/configs, complete
upstream file hashes, asset verification, and the lead's server snapshot.
The server snapshot found RTX 4090 24,564 MiB, driver 575.57.08, about 78 GiB
free disk and PID 1247 `/isaac-sim/kit/kit` consuming about 2.9 GiB. Recheck
identity/resource availability at execution; never stop that unrelated workload.
`uv` and `python3.11` were not found on the initial login-shell PATH.

## Execution

1. **Prepare isolated environments and verify assets.** Use Python 3.11 for
   inference and the demo's separate uv environment. Official install is
   `pip install -e ".[vllm,video]"` from the working repository, with exact
   `vllm==0.19.1`, `transformers==5.8.0`, and `nvidia-cutlass-dsl==4.5.2` pins.
   Preserve these guards; do not install into DualVLN, TIC-VLA, or Isaac Sim
   environments. Record resolved packages, CUDA availability, driver, model
   dtype, and hashes before loading. Verify every bundled scene asset remotely.

2. **Launch the official services.** Baseline commands from the working repo:

   ```bash
   PORT=8050 CUDA_VISIBLE_DEVICES=0 lightnav-serve \
     --task vln --model_path "$LIGHTNAV_MODEL_DIR" --backend vllm_local \
     --host 127.0.0.1 --gpu_memory_utilization 0.80 \
     --ready_file "$LIGHTNAV_RUN_DIR/model.ready" \
     --record_dir "$LIGHTNAV_RUN_DIR/model_records"
   ```

   ```bash
   cd mujoco_demo
   MUJOCO_GL=egl ./run.sh --robot turtlebot \
     --host 127.0.0.1 --port 8088 --vln-server ws://127.0.0.1:8050
   ```

   Set the two task-specific path variables explicitly in saved launch scripts.
   The 0.80 vLLM allocation fraction is a resource override to leave room for
   the existing workload and rendering; it is not a model change. Keep original
   context and camera settings. On an identified vLLM compatibility/OOM failure,
   the repository's official `--backend hf` in a separate isolated environment
   is an allowed, explicitly reported fallback at the same BF16/input settings.
   Preserve failed startup logs and stop only the failed task-owned server first.
   Do not bypass version guards, quantize, or silently shrink visual history.

3. **Preview and freeze before navigation.** Verify a nonblank first-person
   render and the official third-person view. Save the initial pose, resolved
   config, camera geometry, instruction, source hashes, and seeds (where
   supported) in `case.json`. Use the default spawn; document ambiguity if the
   instructed trashcan cannot be identified. Do not reposition it to help the
   model. Target annotations are for assessment only, never policy inputs.

4. **Run three fixed repetitions, retaining every attempt.** Use unique run
   directories, a fresh default robot state and reset model session for each.
   Each navigation attempt is bounded by 180 wall seconds or 180 returned model
   decisions, whichever comes first. Do not add retries solely to obtain success.
   The official page can trigger the run, or a small harness may use its existing
   `/ws` API with `{"type":"set_vln","enabled":true,"instruction":"move forward, then go to the trashcan on the right"}`.
   Keep that owner WebSocket alive for the entire episode; closing it stops
   control. Do not replace the official client, inference loop, or MPC. No manual
   driving after the start. Service readiness alone is not a navigation result.

5. **Record what the model and robot actually do.** Preserve model raw token
   text, decoded waypoints, APOS/OPOS/stop signals and decoder provenance, input
   frame IDs/timestamps, client responses, MPC desired/applied commands, poses,
   errors, and termination cause. Distinguish model-derived stop from invalid
   output, network disconnect, watchdog, operator/harness stop, or timeout.
   On a model stop, observe another two seconds without reissuing motion and
   verify zero commands and stationary pose. A stop in the wrong place remains
   a navigation failure. Empty/error outputs must not be counted as success.

6. **Return actual videos.** Use official server recording/`lightnav-render`
   for first-person evidence and record the demo's native third-person camera
   from the same run. The existing `/api/camera.jpg` and
   `/api/third-person.jpg` endpoints are available; a bounded recorder or
   output-only instrumentation is allowed. Associate paired frames with actual
   capture timestamps, stating any skew. Preserve raw model-input frames.
   Read camera calibration from the compiled model for overlays; do not use the
   renderer's generic 0.5 m height/90-degree HFOV defaults. Preserve full elapsed
   time in at least one video; the official renderer may clamp long frame gaps,
   so label its playback time base separately from wall and simulation time.
   Return first-person, third-person, and a paired MP4 for every repetition,
   including failures. Fully decode them and inspect start/motion/terminal frames.

## Sync Gate and acceptance

- Before every run, hash executed source/configs and compare the remote working
  copy to the local manifest. Save local compatibility changes and their patch
  against the pristine commit. Runtime diagnostic changes must return locally
  before acceptance. If `src/` changes, run upstream `make test` and `make check`
  in an appropriate environment; otherwise use targeted checks for the changed
  recorder/harness. Never edit policy semantics to pass the demo.
- Return every run's command, stdout/stderr, exit/timeout status, raw records,
  resource samples, source/config hashes, raw frame archive, analyses, and real
  MP4 files to the same paths under local `EXP`. Include failed setup attempts.
- Store the pinned checkpoint locally at `EXP/checkpoints/LightNav-0` as well
  as remotely, with a complete file SHA-256 manifest. Environments/caches need
  package locks and regeneration commands, not copied installed binaries.
- Produce a relative-path/size/SHA-256 return manifest after files are finalized;
  verify every local returned byte against it. Do not overwrite an earlier run
  or alter hashed reports after manifest generation. Final sync verification may
  live in a separate, explicitly unhashed verification report.
- Keep large bytes under these exact dated task paths, with path-specific ignore
  entries and provenance/recovery commands; never add extension-wide ignores.
- Report separately: environment ready; real model inference; official demo
  closed loop; task outcome; stop provenance; media verification; local sync.
  This demo has no published numerical success evaluator. Report qualitative
  target arrival and all terminal poses without inventing a benchmark score.
  It is an official-demo reproduction, not paper-score reproduction or a
  validated machine-dog deployment.

Write `EXP/OPUS_RETURN.md` with a three-run result table, exact commands and
versions, resource peaks/latencies, deviations, local video paths, all blockers,
and cleanup proof. Update task execution metadata accurately and leave it at
`review` for the lead. Do not stage or commit. Stop task-owned services after
sync; verify the unrelated Isaac Sim process remains unaffected. The lead will
inspect raw stopping evidence, videos, patches, and hash equality before acceptance.
