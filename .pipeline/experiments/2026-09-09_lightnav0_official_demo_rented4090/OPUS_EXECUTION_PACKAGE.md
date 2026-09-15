---
origin: ai+local+official_upstream+remote_prestage
reviewed: false
date: 2026-09-09
status: prepared_not_dispatched
package_version: 2
supersedes: 2026-09-09T14:48Z package (git 3635579), whose contract is kept
lead: Claude Fable 5.1
executor: Opus (manual dispatch by Dr Sun in a new window)
---

# LightNav-0 official MuJoCo demo on rented4090: execution package

Write all responses and `OPUS_RETURN.md` in English. Read `AGENTS.md` first. You are
not alone in the repository: 48 paths are already dirty; preserve every concurrent
edit and every earlier experiment.

## Goal and scope

- Goal: run the pinned LightNav-0 checkpoint through its own MuJoCo demo (bundled
  ProcTHOR `val_2_ceiling` scene, default TurtleBot, default instruction, the demo's own
  WebSocket client and MPC) for three fixed repetitions on rented4090, and return model,
  control and stop traces plus verified first-person, third-person and paired videos.
- Lead: Claude Fable 5.1 (prepared and pre-staged; performed no inference). Executor: Opus.
- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla` (`ROOT`).
- Authorization (Dr Sun, 2026-09-09): isolated installation, asset and checkpoint
  acquisition, bounded pretrained inference, simulation, recording, ordinary compatibility
  fixes. `sudo apt-get install` of a build or runtime library is allowed only when a
  failure names it; record it. Not authorized: training, real-robot actuation, full
  benchmarks, quantization, driver or CUDA changes, binding services to anything but
  `127.0.0.1`, touching PID 1247 (`/isaac-sim/kit/kit`) or other processes you did not
  start, deleting any `/home/ubuntu/sun/*` content you did not create, `git add`, `git commit`.
- Owned paths: `ROOT/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090`
  (`EXP`) and `ROOT/.trellis/tasks/09-09-lightnav0-official-demo-rented4090`. Add files
  freely; do not modify or delete the lead's preparation files listed under "Verified
  context". `.gitignore` may gain only path-specific entries under `EXP/` (two exist).
- Frozen: the pristine checkout `ROOT/references/upstream/2026-09-09_lightnav0_official_demo/source/LightNav-0`
  (read-only), checkpoint bytes, the instruction, scene, spawn, cameras, MPC parameters,
  model `eval_config.json`, decoding settings, and all upstream policy/controller semantics.
- Remote copy: `REMOTE=/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090`
  on `rented4090` (`ssh rented4090`; alias in `~/.ssh/config`, key auth, `BatchMode yes`;
  never write credentials into artifacts). Sync Gate: `scripts/verify_work_copy.py` must
  pass (or list only patch-tracked exceptions) before every GPU run; every result returns
  to the same relative paths under local `EXP` and is verified by SHA-256.

## Frozen official inputs

- Repository https://github.com/lightorigins/LightNav-0 at
  `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c` (`main`, Apache-2.0). Per-file hashes:
  `EXP/setup/upstream_file_manifest.json` (2,459 files).
- Model `LightOriginsHQ/LightNav-0` revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`,
  original BF16, no quantization. 20 files, 9,709,350,260 bytes; single shard
  9,695,744,034 bytes, SHA-256
  `ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18`. Full sibling list
  with LFS hashes and blob ids: `EXP/setup/model_source.json`. `gated=false`.
- Scene: bundled MolmoSpaces ProcTHOR `val_2_ceiling.xml` (`procthor-val-2`), 2,236
  asset files verified locally (`EXP/setup/asset_verification.json`). No other download.
- Robot: default `turtlebot`, spawn `(x=6.5, y=13.8, yaw=0)`, camera `480x270` JPEG
  quality 82, kinematic integration (`mujoco_demo/vln_mujoco/robots/turtlebot.py`). It
  cannot establish quadruped locomotion or contact safety.
- Instruction, verbatim from `mujoco_demo/vln_mujoco/web/index.html:48`:
  **`move forward, then go to the trashcan on the right`**. No translation, no substitute
  target, no prompt selection after trials.
- Model task `--task vln`; checkpoint-resolved settings (`EXP/setup/checkpoint_eval_config.json`):
  64 history frames, horizon 10, `video_size [256, 448]`, post-ViT pooling, SlowFast tiers,
  `video_fps 4`. Decoding is greedy (`engine.py:30-37`, `VLN_EVAL_TEMPERATURE` unset).
  Do not set `LIGHTNAV_SKIP_VERSION_GUARD`, `--num_history_frames`, `--pool_spatial`,
  `--quantization`, or a temperature.

## Verified context

### Host and network (measured by the lead 2026-09-09 15:07-15:23Z; `EXP/setup/lead_prestage_2026-09-09.json`)

- Ubuntu 22.04.4, 16 vCPU, 62 GiB RAM, RTX 4090 24,564 MiB, driver 575.57.08, CUDA
  driver API 12.9, 73 GiB free disk. Protected workload PID 1247 Isaac Sim holds 2,859 MiB
  and listens on 8011/49100. Ports 8050 and 8088 are free. System Python is 3.10.12 with no
  pip/uv/conda; passwordless `sudo` works; gcc/g++/make and libEGL are present.
- GitHub is 10-25 KiB/s: never fetch anything from GitHub on the host. PyPI direct is
  ~0.6 MB/s; the Tsinghua mirror `https://pypi.tuna.tsinghua.edu.cn/simple` is ~19 MB/s
  (USTC ~19, Aliyun ~16). Hugging Face direct is ~15 MB/s; conda-forge ~2 MB/s.
  Mac-to-server is ~0.8 MB/s; server-to-Mac is ~0.5 MB/s for one large file and far
  slower for many small files, so always return one tar archive.

### Pre-staged on `REMOTE` (reuse; do not rebuild)

| Item | State | Evidence |
|---|---|---|
| Layout `work/ checkpoints/ scripts/ setup/ runs/ env/ tools/ records/` | created | `ls REMOTE` |
| `tools/bin/micromamba` 2.1.1 | copied, SHA-256 `0d2dd49f…604d8` | `setup/lead_prestage_2026-09-09.json` |
| `env/py311` conda-forge Python 3.11.16 + pip + uv 0.11.21 (mirror index) | built, job `runs/env_py311` exit 0 in 41 s | `runs/env_py311/{meta,process}.json`, `setup/py311_conda_list.txt` |
| `work/LightNav-0` from `setup/lightnav0_src.tgz` (SHA-256 `6acc1715…4db835`; excludes `.git` and `docs/assets`) | extracted; 3,094 macOS `._*` files deleted; verified 2,449 matched / 0 mismatched / 0 missing / 0 extra, 10 ignored (`docs/assets`) | `setup/work_copy_verification_initial.json` (pre-cleanup), `setup/work_copy_verification_clean.json` |
| `checkpoints/LightNav-0` | **complete**: job `runs/download_ckpt` exit 0 in 544 s (15:18-15:27Z, ~17.8 MB/s); all 20 files verified (19 by git blob id, the shard by LFS SHA-256) | `runs/download_ckpt/{meta,stdout.log}`, `setup/checkpoint_manifest_remote.json` (20 files, 9,709,350,260 bytes) |
| `scripts/install_lightnav.sh`, `scripts/setup_demo.sh` | pushed, **not executed** | `EXP/scripts/` |

### Pre-staged locally

- `EXP/scripts/run_job.py` (process-group supervisor: `runs/<name>/{stdout.log,stderr.log,process.json,meta.json}`),
  `download_checkpoint.py` (resumable curl, LFS SHA-256 and git-blob verification),
  `verify_work_copy.py`, `setup_py311.sh` (done), `install_lightnav.sh`, `setup_demo.sh`.
- Local checkpoint copy: `download_checkpoint.py` is running on the Mac (started 15:17Z,
  ~2.5 MB/s, about 65 min), log `EXP/setup/local_checkpoint_download.log`, manifest
  `EXP/setup/checkpoint_manifest_local.json` on completion. If it is not complete when you
  need it, re-run the same command from `EXP` (it resumes) in the background:
  `python3 scripts/download_checkpoint.py setup/model_source.json checkpoints/LightNav-0 setup/checkpoint_manifest_local.json`.
- `.gitignore` already ignores `EXP/checkpoints/` and `EXP/work/`. The Trellis task is
  already `in_progress` (`task.py start` done); `meta.execution_status=prepared_v2_not_dispatched`.
  Set it to `executing` when you start and `review` when you return.
- Lead-owned preparation files (do not modify): `EXP/README.md`, this package,
  `EXP/setup/{asset_verification,checkpoint_config,checkpoint_eval_config,github_tree,model_source,preparation_manifest,preparation_validation,server_preflight,upstream_file_manifest,lead_prestage_2026-09-09}.json`,
  `EXP/setup/server_preflight.*.log`.

### Demo and server facts you will depend on (pinned source, verified by reading)

- Demo HTTP/WS (`mujoco_demo/vln_mujoco/server.py`): `GET /api/health` (JSON snapshot),
  `GET /api/camera.jpg`, `GET /api/third-person.jpg` (503 while warming up; both frames
  share one `stamp_ns` and the capture pose), `WS /ws` (JSON text; the `Origin` header,
  if sent, must match the host). Messages: `{"type":"set_server_url","server_url":...}`,
  `{"type":"set_vln","enabled":true,"instruction":...}`, `{"type":"set_vln","enabled":false}`,
  `{"type":"stop"}`, `{"type":"reset"}` (robot back to spawn, VLN stopped). Replies are
  `command_result`, plus `runtime` snapshots pushed whenever the runtime signature changes
  (`pose`, `velocity`, `command`, `sim_time`, `camera.stamp_ns/fps`, `vln.{state,connected,sequence,error,waypoints,latency_ms,visible,stop,apos_state,opos_state,apos_px,opos_px}`,
  `mpc.{state,error,solve_ms,command,parameters}`, `control.{manual,auto,locked,source}`).
- Control ownership: the socket that sends `set_vln enabled:true` owns control; closing it
  stops VLN. Keep that socket open for the whole episode.
- Native stop (`server.py` `update_loop`): when a result has `stop is True`, the server
  zeroes the command, drops `auto_owner`, resets the MPC and stops the client; the snapshot
  then shows `control.source == "idle"`, `vln.state == "IDLE"` and **`vln.stop == true`
  retained**. A harness or page stop (`set_vln enabled:false`, `stop`, `reset`) goes through
  `stop_vln()`, which clears `vln.stop` to `null`. `mpc.error` (e.g. `missing robot pose
  for VLN capture timestamp`) and `vln.state == "ERROR"` are separate failure signals.
  Commands decay to zero after 0.35 s without refresh (`simulation.py` `COMMAND_TIMEOUT_S`).
- Client loop (`vln_client.py`): one WebSocket connection to the model server per
  `set_vln` start, `clientId` `vln_mujoco`, one pending frame at a time (frames are offered
  at 20 Hz, the model sees one per round trip), 3 s per-response timeout, `reset` sent
  when the connection ends. A new connection is a new model session and a new recorder
  connection directory (`recorder.py` `begin_connection`, exclusive dir names).
- MPC (`mpc.py`): 10 Hz, horizon 5, `OBJNAV_V_MAX 0.8 m/s` is the speed limit used for
  VLN (`mpc.py:433`), `W_MAX 3.0`, IPOPT. Waypoints are projected with the capture-time pose.
- Camera geometry (`turtlebot.py`, `model.py`): body at `z = 0.033`, camera at body
  `(0.090, 0, 0.165)`, `fovy 79.865°`, frame 480x270. Compute at run time from the compiled
  model: `hfov = 2*atan(tan(fovy/2) * 480/270)` (about 112.2°), height about 0.198 m, and
  pass them to `lightnav-serve --cam_hfov_deg --cam_height` (overlay only; the model never
  sees them). The third-person camera is fixed to the robot body (`pos -0.65 0 0.50`,
  `fovy 65`): a chase view, not a static world camera.
- Server (`src/lightnav/serving/ws_server.py`): warm-up runs before the port binds;
  `--ready_file` is touched when listening. `--record_dir` writes
  `run_<ts>/<label>/episode_NNN/{manifest.json,image_<step>.jpg,actions.jsonl -> actions.json}`
  with `raw_text`, `waypoints`, `stop`, `visible`, `pointing`, `latency_ms`, `step_dt_ms`
  per prediction and the client's JPEG bytes verbatim (`docs/VISUALIZATION.md`).
  `lightnav-render <dir>` makes `traj_pointing.mp4`; its `realtime` timeline clamps a
  step's repeat count to 1-20 frames, so long gaps compress. Version guard: vllm `0.19.*`,
  transformers `5.8.*` (`inference/vllm_utils.py:20-21`).

### Open questions

- vLLM 0.19.1 with the PyPI cu12.8 torch 2.10.0 wheel on driver 575 / sm_89 is expected
  to work but is untested here. A `nvidia-cutlass-dsl`/`quack` import error at engine start
  means the pin was not honoured; check `pip freeze`, do not bypass the guard.
- GPU budget: weights 9.7 GB BF16 plus vLLM cache at `--gpu_memory_utilization 0.80` of
  24 GB, with Isaac Sim's 2.9 GB and MuJoCo EGL rendering on the same GPU. If startup OOMs,
  first retry at 0.70 (resource override, not a model change), then the documented
  `--backend hf` fallback in a separate isolated venv at the same BF16 settings; report it.
- Whether the "trashcan on the right" is visible from the default spawn is unknown.
  Preview and document; do not move the robot, the object or the instruction.
- uv resolves transitive versions; they may differ from pip's. Record the freeze and the
  SHA-256 of `torch`, `vllm`, `transformers`, `nvidia-cutlass-dsl` wheels from
  `env/uv_cache` against PyPI's published digests (`https://pypi.org/pypi/<pkg>/<ver>/json`).

## Remaining work

Run every remote command through `python3 scripts/run_job.py --seconds N <name> -- <cmd>`
from `REMOTE` (unique job names; failed jobs stay). Author scripts locally under
`EXP/scripts/`, push with `rsync -a EXP/scripts/ rented4090:REMOTE/scripts/`, and keep
local and remote identical (`sha256sum` both sides before a run). Set
`PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple` for any install.

1. **Adopt state.** Confirm `runs/download_ckpt/meta.json` shows exit 0 and
   `setup/checkpoint_manifest_remote.json` lists 20 files / 9,709,350,260 bytes; re-check
   the shard size and SHA-256 with `sha256sum` before loading. Never start a second download.
   Confirm `setup/work_copy_verification_clean.json` passes and `env/py311/bin/uv --version`
   prints 0.11.21. Re-run `nvidia-smi` and `ps -p 1247` and save them to
   `setup/environment_before.txt`. Check the local Mac download log likewise.

2. **Install the official environments.**
   `run_job.py --seconds 2400 install_lightnav -- bash scripts/install_lightnav.sh`
   (uv venv at `work/LightNav-0/.venv`, `-e ".[vllm,video]"`, freeze to
   `setup/pip_freeze_lightnav.txt`, prints versions JSON and `LIGHTNAV_INSTALL_COMPLETE`;
   it asserts `torch.cuda.is_available()`). Then
   `run_job.py --seconds 900 setup_demo -- bash scripts/setup_demo.sh` (`uv sync --extra dev`
   in `mujoco_demo`, freeze to `setup/pip_freeze_demo.txt`, runs the demo's own pytest
   suite under `MUJOCO_GL=egl`, prints `DEMO_SETUP_COMPLETE`). Save the versions JSON,
   `nvidia-smi -q`, and wheel digests to `setup/environment.json`. Expected pins:
   `vllm==0.19.1`, `transformers==5.8.0`, `nvidia-cutlass-dsl==4.5.2`, `torch==2.10.0`.

3. **Launch the official services** as two supervised jobs (long deadlines; you stop
   them yourself at the end). Save both launch scripts under `scripts/`.

   ```bash
   # scripts/launch_server.sh (job model_server, --seconds 7200)
   cd REMOTE/work/LightNav-0
   PORT=8050 CUDA_VISIBLE_DEVICES=0 .venv/bin/lightnav-serve \
     --task vln --model_path REMOTE/checkpoints/LightNav-0 --backend vllm_local \
     --host 127.0.0.1 --gpu_memory_utilization 0.80 \
     --ready_file REMOTE/runs/model_server/model.ready \
     --record_dir REMOTE/records \
     --cam_hfov_deg <computed> --cam_height <computed>
   ```

   ```bash
   # scripts/launch_demo.sh (job demo_server, --seconds 7200)
   export PATH=REMOTE/env/py311/bin:$PATH UV_PYTHON=REMOTE/env/py311/bin/python \
     UV_PYTHON_DOWNLOADS=never UV_DEFAULT_INDEX=$PIP_INDEX UV_CACHE_DIR=REMOTE/env/uv_cache
   cd REMOTE/work/LightNav-0/mujoco_demo
   MUJOCO_GL=egl ./run.sh --robot turtlebot --host 127.0.0.1 --port 8088 \
     --vln-server ws://127.0.0.1:8050
   ```

   Compute the two camera values with a small script in the demo venv
   (`from vln_mujoco.robots.turtlebot import build_model` → `model.cam_fovy`, `cam_pos`
   plus the body height) and record them. Wait for `model.ready`; record server startup
   wall time, warm-up log lines, and a 1 Hz `nvidia-smi --query-gpu=memory.used,utilization.gpu`
   sampler job (`gpu_sampler`, 1 Hz, whole session). Verify `GET /api/health` and that
   `camera.jpg` and `third-person.jpg` are non-blank (save both, report mean and std of
   luma). Service readiness alone is not a navigation result.

4. **Freeze the case** in `runs/case.json`: instruction text and its SHA-256, spawn pose
   from the health snapshot, camera geometry, model manifest hash, resolved eval config,
   server and demo versions, source verification report hash, decoding settings, wall and
   simulation clocks, and the preview image hashes. Note any ambiguity about which
   trashcan is meant; never reposition anything.

5. **Run three fixed repetitions** with a task-owned harness `scripts/run_episode.py`
   (demo venv; aiohttp is available). Per repetition `rep_01..rep_03`, unique run dir:
   - connect `/ws`, send `reset`, confirm the pose returns to spawn and `vln.state IDLE`;
   - start an output-only recorder task polling `/api/camera.jpg` and
     `/api/third-person.jpg` at 10 Hz, storing every JPEG verbatim with wall-clock
     `received_utc`, the response `stamp_ns` if exposed, and a `frames.jsonl` index;
   - send `{"type":"set_vln","enabled":true,"instruction":"move forward, then go to the trashcan on the right"}`
     and log every `runtime` and `command_result` message with wall time to
     `snapshots.jsonl` (pose, velocity, command, MPC solve, VLN sequence/latency/stop/
     pointing/waypoints, control source);
   - terminate on the first of: native stop (`vln.stop == true` with `control.source idle`),
     `vln.state ERROR` or non-empty `mpc.error` for more than 5 s, 180 s wall, or
     `vln.sequence >= 180`; after a native stop keep observing 2 s without sending anything
     and verify zero commands and a stationary pose; only then send `set_vln enabled:false`
     if control is still active (that is a harness stop; label it);
   - write `episode.json`: termination cause (`model_stop | invalid_output | disconnect |
     mpc_error | watchdog_timeout | decision_cap | harness_stop`), decision count, start
     and end poses, path length, total wall and simulation time, and the model-server
     episode directory that this repetition produced (match by time and `seq`).
   Do not add retries to obtain a success; keep every attempt. No manual driving.

6. **Records and videos** (`scripts/make_videos.py`, decode-check everything):
   - first-person: `lightnav-render` on each repetition's episode directory (overlay of
     waypoints/pointing/HUD on the frames the model saw), timeline `realtime`, state that
     its playback time base is clamped; keep `actions.json` and every `image_*.jpg`;
   - third-person: encode the recorder's frames with their wall timestamps (constant 10 fps
     with duplication, or VFR via ffmpeg concat) so full elapsed time is preserved;
   - paired side-by-side MP4 per repetition with a wall-clock label and the decision index;
   - decode every MP4 (frame count, distinct-frame count, size) and save start, mid and
     terminal PNG frames for visual inspection; inspect them yourself.

7. **Analyse** (`scripts/analyze.py` → `analysis/summary.json` and a Markdown table):
   per repetition decisions, latency mean/max from records, MPC solve times, stop
   provenance, distance travelled, final pose and heading, qualitative arrival at a
   trashcan (from the terminal third-person frame; annotations on copies only), GPU
   memory peak from the sampler (model-only after warm-up versus with demo running), and
   whether repetitions diverged despite greedy decoding.

8. **Return and clean up.** Stop `demo_server` then `model_server` by their recorded PGIDs
   only; confirm `ps -p 1247` still runs and its GPU memory is unchanged. On the host,
   `tar czf` one archive of `runs/ records/ setup/ analysis/ scripts/` (exclude
   `checkpoints/`, `env/`, `work/`), scp it once, extract into local `EXP` at the same
   relative paths, and write `EXP/return_manifest.json` (relative path, bytes, SHA-256 of
   every returned file, generated after all files are final). Verify every local byte
   against the remote manifest; put that verification in a separate unhashed
   `EXP/return_verification.json`. Save any change to `work/LightNav-0` as
   `setup/compatibility.patch` against the pristine checkout (diff -ruN) and re-run the
   work-copy verification with the patch's files listed as exceptions; if `src/` changed,
   also run upstream `make test` and `make check` in the inference venv. Write
   `EXP/OPUS_RETURN.md`, set task meta `execution_status=review`, do not stage or commit.
   Leave `env/`, `checkpoints/`, `work/` on the host.

Repair ordinary failures within scope (pins, EGL, fonts, a missing library, a harness
bug). Return to the lead any change to the case, the instruction, the model settings,
the controller, or the acceptance criteria. Deadlines: installation 60 min of wall
time after adoption; model startup plus all navigation attempts 1,800 s of GPU time.
If a deadline is exceeded, report it as a deviation rather than cutting evidence.

## Acceptance checks

| Check | Pass condition |
|---|---|
| Environment ready | `LIGHTNAV_INSTALL_COMPLETE`, `DEMO_SETUP_COMPLETE`, demo pytest passing, versions JSON with the four pins, `cuda_available true` |
| Checkpoint | remote and local manifests each list 20 files / 9,709,350,260 bytes with 0 mismatches |
| Real model inference | server records with non-empty `raw_text`, finite `(10,3)` waypoints, `latency_ms > 0` for every predicted step |
| Official closed loop | `snapshots.jsonl` shows `control.source vln`, non-zero MPC commands, increasing `vln.sequence`, and a pose that changes |
| Stop provenance | each repetition's termination cause is one label with the raw snapshot lines that justify it; a native stop shows 2 s of zero commands and a stationary pose |
| Task outcome | qualitative arrival reported per repetition with terminal poses; failures reported as failures |
| Media | three first-person, three third-person and three paired MP4s decode, frame counts recorded, start/mid/terminal PNGs inspected |
| Sync gate | pristine checkout untouched; work copy verified; `return_manifest.json` matches every local byte; commit status "not staged" |
| Protected workload | PID 1247 alive with unchanged GPU memory before and after |

## Return

`EXP/OPUS_RETURN.md` with: a three-run result table; exact commands, job names,
exit codes and wall times; versions and wheel digests; GPU peaks and latencies; the
stop-provenance evidence per repetition; local video paths and their SHA-256; every
deviation and failed attempt; the compatibility patch summary; sync-gate results;
cleanup proof; open issues. Label the result `reproduced` only for the official demo
loop itself; it is not paper-score reproduction and not a machine-dog deployment.

The lead verifies the raw `snapshots.jsonl` and server `actions.json` per repetition,
the decoded videos and terminal frames, the compatibility patch, the work-copy and
return manifests, and the protected-process evidence before accepting.
