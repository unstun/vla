---
origin: lead_preparation+local_source_inspection+remote_checks
reviewed: false
date: 2026-09-09
status: prepared_not_dispatched
package_version: 3
lead: Codex
executor: Opus_via_manual_user_dispatch
---

# LightNav-0: continue the official case with complete, synchronized visual evidence

Read `AGENTS.md`, this entire file, then `VISUAL_SPEC.md` and `RESEARCH.md` beside
it. Write repository-facing code, documentation and the Opus return in English.
You are not alone in the repository. Preserve all concurrent edits and all old
experiment evidence. Do not stage, commit, push, or dispatch another agent/task.

## 1. Goal, authorization and claim boundary

Dr Sun asked to continue LightNav-0 reproduction on the now-running rented RTX
4090, with good visualization, and requested this researched manual Opus package.
When Dr Sun hands you this package to execute, complete the bounded work below:
repair/replace the task recorder, perform three fixed official-case repetitions,
produce complete multi-view videos and a traceable outcome analysis, and return
verified local artifacts. Repair routine implementation faults within this scope.

This file is the current execution entry point. It supersedes
`EXP/OPUS_CORRECTION_PACKAGE.md` for this continuation's output paths, visualization,
budgets and backend rules. Old packages, results and reviews stay immutable.
In particular, the recorded user decision is **official vLLM BF16 only**:
the old HF fallback is not authorized for this continuation. No FP8, quantization,
prompt variant, altered camera input, changed history, controller tuning, extra
case, new checkpoint, training, full benchmark or real-robot motion is included.

Acceptance separates: (a) genuine execution, (b) complete trustworthy visuals,
and (c) arrival/stop outcome. All three new runs may fail to reach the target;
return those failures honestly. Do not keep retrying until a successful video exists.

## 2. Paths and ownership

| Name | Absolute path / value |
| --- | --- |
| ROOT, sole source of truth | `/Users/sun/tongbu/study/phdproject/vla` |
| EXP | `ROOT/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090` |
| PKG | `EXP/continuation_v3` |
| Task | `ROOT/.trellis/tasks/09-09-lightnav0-official-demo-rented4090` |
| UP, pristine read-only source | `ROOT/references/upstream/2026-09-09_lightnav0_official_demo/source/LightNav-0` |
| Local v3 work copy | `EXP/work/LightNav-0-visual-v3` |
| SSH alias | `rented4090` (`ubuntu@117.50.179.202:22`, existing key authentication) |
| Remote EXP, R | `/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090` |
| Remote PKG, C | `R/continuation_v3` |
| Remote v3 work copy, W | `R/work/LightNav-0-visual-v3` |
| Existing model interpreter | `R/work/LightNav-0/.venv/bin/python` |
| Existing demo interpreter | `R/work/LightNav-0/mujoco_demo/.venv/bin/python` |
| Existing checkpoint | `R/checkpoints/LightNav-0` |

Owned additions: `PKG/scripts/`, `runs/`, `records/`, `analysis/`, `media/`,
`patches/`, `setup/`, optional isolated `env/`, and `PKG/OPUS_RETURN.md`.
You may edit the v3 work copy and update task metadata/notes. Lead inputs
(`EXECUTION_PACKAGE.md`, `VISUAL_SPEC.md`, `RESEARCH.md`, `research/`, package
manifest/validation) are read-only. Every old file named in
`research/legacy_frozen_manifest.json` is read-only.

Keep the two old environments, old `work/LightNav-0`, old rep_01..03, all old
records, reviews, scripts, scene/checkpoint bytes and the 5070 Ti experiment
unchanged. Use the installed interpreters without rebuilding their environments.
If extra plotting tools are needed, use a new visualization-only venv and record
its packages. Use the existing path-specific `EXP/work/` ignore for the v3 work
copy, with tracked patches and full file hashes. A large new raw-state/video
archive needs a narrow path-specific ignore plus tracked provenance/hash and
regeneration instructions; do not add extension-wide ignores.

## 3. Verified context; recheck mutable state

Read `research/remote_preflight.json` and `research/post_static_preflight.txt`.
At 2026-09-10 02:46:38 UTC the host had 24,564 MiB total GPU memory, 21,175 MiB
free, and 47 GiB disk free. The protected Isaac Sim process is **PID 1251**, not
the stale PID 1247. Its command, start tick 2380 and boot ID are saved. Protect
all unrelated workloads, not merely one numeric PID; re-identify after reboot.
Do not terminate or reconfigure `/isaac-sim/kit/kit` or its streaming service.

All 20 checkpoint files / 9,709,350,260 bytes matched their saved hashes. Source
inspection found 2,449 matching files and one expected runtime lock-file drift,
`mujoco_demo/uv.lock`. Do not propagate that drift into the new source baseline.
Model environment: torch 2.10.0, vLLM 0.19.1, Transformers 5.8.0, CUTLASS DSL
4.5.2. Demo: MuJoCo 3.11.0, aiohttp 3.14.3, CasADi 3.7.2. Ports 8050/8088 were free.
System `ffmpeg`/`ffprobe` were absent on the host in the static post-check; use
the installed imageio-ffmpeg binary for encoding when suitable. Local verified
QA tools are `/opt/homebrew/bin/ffmpeg` and `/opt/homebrew/bin/ffprobe`.

The static lead probe has **zero simulation steps and zero VLA calls**. It
verified full state save/restore, a real orthographic overhead view, and unchanged
native front pixels after restoring visualization settings. Its corrected code,
images, matrices and hashes are in `research/static_probe_02/`. First attempt
`static_probe_01` silently rendered perspective and is retained as a failed
projection assumption. Moving-state replay and the recorder are not yet implemented.

Round 1: three real model-driven episodes ended with native STOP, but the robot
remained 2.414/2.274/2.609 m from the trashcan root. Harness frame-name collisions
overwrote 31/28/32 polled frames per camera stream. Official model-input JPEGs
and raw actions remain available. See the old lead review; do not claim this
continuation begins from an accepted navigation-success result.

## 4. Frozen experimental identity

- Source: https://github.com/lightorigins/LightNav-0,
  commit `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`, Apache-2.0.
- Model: https://huggingface.co/LightOriginsHQ/LightNav-0,
  revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, original BF16.
  Weight shard SHA-256:
  `ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18`.
- Scene: bundled ProcTHOR `val_2_ceiling.xml`, original asset manifest, CC BY 4.0
  scene provenance retained in `ROOT/references/upstream/2026-09-09_lightnav0_official_demo/`.
- Robot: original kinematic TurtleBot; spawn `(6.5,13.8,0)`; no model or scene edits.
- Instruction, byte-for-byte: `move forward, then go to the trashcan on the right`.
  SHA-256: `87ef6df01a076e5d78c06ad6badab2f5f8c1c80a587d687c7a4222fe5a35427e`.
- Native front input 480x270, JPEG quality 82, original camera and 20 Hz target
  renderer cadence; model processing 256x448, original 64-frame configuration,
  SlowFast tiers, 4 Hz model timestamp basis and post-ViT pooling.
- `--task vln --backend vllm_local`; greedy decoding and shipped RVQ decoder;
  10 robot-local `[forward,left,yaw]` waypoints. Preserve the serving CLI's pinned
  max-token default and all original sampling behavior.
- Match round-1 serving resources: `--gpu_memory_utilization 0.80`,
  `--max_batch_size 8` (the pinned default), CUDA Graphs and default KV settings.
  Do not copy the separate 5070 Ti single-sequence probe's settings into this case.
- Original client, 3 s reply timeout, MPC, control cadence/limits and native STOP
  semantics remain unchanged. Overhead coordinates, radii, masks and labels are
  analysis-only and must never enter the model prompt or controller.

## 5. Budgets and execution order

Overall wall budget: 90 minutes. Model/demo service lifetime and new navigation
attempts together: at most 900 seconds. Each run's active navigation: at most
180 wall seconds or 180 decisions, followed by at most 5 seconds of post-stop
observation. Bound each harness process to 190 seconds including reset.
Static/state-rendering and final video generation get
a separate 900-second GPU-render budget after stopping the policy services.
CPU analysis/encoding stays inside the overall wall limit. Report any incomplete
part at a deadline; do not silently extend it.

### A. Adopt and freeze

1. Check local Git/task state and current remote host, GPU, disk, processes and
   listeners. Require enough free memory for the configured 0.80 engine fraction
   plus 512 MiB headroom, and at least 10 GiB disk free. Insufficient resources
   are not permission to stop someone else's process or switch precision.
2. Inspect whether v3 runs already exist. Resume verified partial work; never
   overwrite or duplicate a completed run because this package was pasted twice.
3. Verify `research/legacy_frozen_manifest.json` before changes. Rehash the
   checkpoint and save the result under `PKG/setup/`. Reuse complete assets.
4. Build the local v3 work copy from UP with `.git` and `docs/assets` excluded.
   Preserve the frozen source manifest and record the deliberate exclusion.
   Generate a source hash manifest and a patch against UP. Sync local changes
   to W; check every source/config/input hash before model execution.
5. Copy the existing `EXP/scripts/run_job.py` to `PKG/scripts/run_job.py` so its
   root-relative outputs land under v3. Keep its unique job-directory and
   process-group deadlines. Record any supervisor modifications separately.

### B. Implement capture and visualization plumbing

Use `VISUAL_SPEC.md` as the acceptance contract. Replace the old poll-based
recorder for new runs; do not merely increase `CAMERA_POLL_HZ`.

Allowed source seams in W are the demo's `simulation.py`, `vln_client.py`,
`server.py`, and a new optional capture-helper module. Changes must be
observation/logging only and disabled by default. Do not change neural code,
robot stepping, MPC optimization, existing camera settings, message fields,
session semantics or control decisions. Keep offline rendering/analysis in
`PKG/scripts/`; patch files and full manifests belong in `PKG/patches/` and `setup/`.

At the existing capture point save the original JPEG pair, frame identity,
capture pose and full MuJoCo integration state. Keep disk work off the control
thread. Add sidecar request/response/consumption mapping by session/connection,
seq, stamp and exact JPEG hash. Keep the official model server recorder enabled.
Record applied command and observed velocity separately. Explicitly retain and
label in-flight responses after native STOP.

Mandatory focused checks before a model run:

- upstream demo tests plus recorder tests for >200 variable-length index rows,
  duplicate rejection, queue/writer failure and loss reporting;
- delayed/out-of-order HTTP or snapshot data cannot be accepted as an exact
  frame-state join; seq/hash mismatch and reconnection must be handled explicitly;
- native STOP, harness stop, invalid output, disconnect, MPC error, watchdog and
  decision cap have separate termination labels;
- deterministic supplied-control replay with observation disabled/enabled has
  identical state/native JPEG outputs; this does not prove asynchronous model
  trajectories will remain identical;
- state save/restore, effective orthographic projection, geometry orientation,
  calibrated overlay and preservation of the native camera pass;
- a >=5 s artificial gap remains >=5 s in the wall-time film, and a prediction
  cannot appear before its recorded arrival time.

Then perform one <=15 s stationary recorder dry run with the model disconnected.
No manual motion is needed. Save it as `runs/harness_check`; end with a recorded
harness stop. Require zero overwritten/dropped frames, complete indices/states,
and correct timestamps before proceeding. Measure enqueue time and frame cadence;
target observer enqueue p95 <=1 ms. If timing is materially disturbed, optimize
the recording path and report the observation rather than changing policy rates.

### C. Run exactly three fixed-case repetitions

Create task-owned launch scripts under `PKG/scripts/`. Use the existing model
interpreter with `PYTHONPATH=W/src`, and the existing demo interpreter with
`PYTHONPATH=W/mujoco_demo`. Run the same upstream module entry points; the direct
demo module invocation avoids `uv run` regenerating the lock/environment.

Model command shape (shell variables must be absolute paths):

```bash
PYTHONPATH="$W/src" CUDA_VISIBLE_DEVICES=0 "$MODEL_PY" -m lightnav.serving.ws_server \
  --task vln --backend vllm_local --model_path "$R/checkpoints/LightNav-0" \
  --host 127.0.0.1 --port 8050 --gpu_memory_utilization 0.80 --max_batch_size 8 \
  --record_dir "$C/records" --ready_file "$C/runs/model_server_v3/model.ready" \
  --cam_hfov_deg 112.2 --cam_height 0.198
```

Demo command shape (enable only your documented capture observer additionally):

```bash
MUJOCO_GL=egl PYTHONPATH="$W/mujoco_demo" "$DEMO_PY" -m vln_mujoco \
  --robot turtlebot --host 127.0.0.1 --port 8088 --vln-server ws://127.0.0.1:8050
```

Run both under v3 supervisors with <=900 s deadlines and explicit metadata.
Resolve R/C/W and interpreter variables to the absolute paths above. Use a fresh
ready-file path inside the actual unique server-job directory; never accept a
ready file left by a prior process. Check the listener PID and new run identity.
Check loaded module `__file__` locations and the actual resolved configuration;
an editable install pointing to the old source must not bypass v3 instrumentation.
Clear unintended task-shell quantization/history/temperature/version-guard
overrides, recording the effective environment; do not edit global shell config.
Wait for actual model warmup/readiness before the first official instruction.

Run rep_04, rep_05, rep_06 sequentially in unique directories; each resets to the
same original spawn and uses the same exact instruction. Keep the owning `/ws`
connection open throughout the episode and post-stop observation. Never click
manual controls or send a second start from the browser. Any optional user-facing
preview stays behind an SSH localhost tunnel, e.g. local port 18088 to remote 8088.

Each run starts measured time at the instruction send, with acceptance time and
pre-start reset recorded separately. After consumed native STOP, evaluate the
two-second stillness window from `VISUAL_SPEC.md`. Preserve any last in-flight
prediction and its disposition. On timeout/error record the harness stop before
sending it. Save every started attempt, including a failed setup or recorder run;
repairs are not permission for extra unbounded model episodes.

Use an independent GPU sampler (target 0.2 s interval), record system RAM and
workload context, and report actual sample gaps. After these runs, stop only your
model/demo process groups and verify the protected workloads remain present.
Do not leave the model resident while rendering the additional camera views.

### D. Produce videos and analysis

Restore saved states in a separate MuJoCo instance and produce the complete
primary/supporting media in `VISUAL_SPEC.md`. Use the tested overhead preset;
only the separate visualization model may hide the ten named ceilings.
No state integration, invented frames, future-trajectory leakage or image
enhancement that changes scene evidence is allowed. Master films preserve wall
time; decision-review and offline-replay content carry explicit labels.

For legacy rep_01..03, generate additional derivatives only under
`media/legacy_rep_0*/`. Keep their missing-frame labels; use XY trajectory diagrams
where exact replay state does not exist. Deliver the old first-person overlays,
surviving-frame third-person derivatives and labelled overview films without
overwriting their originals. Report original and new cohorts separately.

Write `analysis/summary.json` and `analysis/summary.md` covering all six runs:
instruction/source/checkpoint/config identities; decisions; raw STOP and consumed
STOP identities; recorded stillness; terminal pose; path length and displacement;
distances to the target and dog bed; diagnostic 1/1.5/2 m memberships; observed
OPOS association/visibility; first observable divergence; server latency vs client
round trip; capture cadence and losses; GPU/RAM samples; termination and errors.
Use actual object roots from the pinned XML (ashcan approximately `(8.51724,9.35802)`,
dog bed `(9.82396,10.40950)`), not approximate values as the computational source.

Do not turn a shifted ribbon, display-derived speed, model reasoning text or a
nearest-time guess into evidence of what the controller did. Preserve uncertainty
about causal explanations. If all fixed runs fail, explain the observed sequence
with images/metrics and return it; leave model/prompt/controller interventions
for a subsequent reviewed experiment.

## 6. Sync gate and return

Before every model launch, save the source/patch/config manifests and verify
the remote execution copy against the local v3 files. Inference/model/controller
files outside the telemetry allowlist must match the pinned source exactly.

After final output generation, return one archive containing v3 scripts, patches,
setup, raw traces/states/JPEGs, model records, analysis and actual MP4s. Record
archive and per-file SHA-256; extract to the same relative local paths and check
every byte. All final source edits must exist locally in the v3 work copy, with
their tracked patch. Reuse the already complete local original checkpoint and
verify it instead of duplicating the 9.7 GB payload unnecessarily.

Run ffprobe and full ffmpeg decoding locally; watch all three new primary films
and inspect the specified keyframes. Report capture counts, distinct frames,
duplications, gaps and real playback duration. A codec check alone is insufficient.
Recheck every old frozen artifact hash and preserve original failed attempts.
Record final host GPU/process state and prove no task service remains.

Write `PKG/OPUS_RETURN.md` with:

1. Direct absolute local links to all three `overview_wall.mp4` files and share
   copies, then the six-run result table; lead with actual target/stop outcomes.
2. Source/patch identities, exact commands, versions, run IDs, exit codes,
   timeouts/budgets and resource measurements.
3. Media QA results, source-clock definitions, replay labels and recording losses.
4. Local/remote file counts and hash verification, plus legacy preservation check.
5. Deviations, failures, unresolved questions, and explicit `not staged/not committed`.

Set task metadata `continuation_execution_status=review` and reference this
return. Do not rewrite the old Opus return or mark the whole research project
complete. The lead independently reviews the diff, raw joins/states, actual
stop/pose traces, geometry, playable videos and hashes before acceptance.

| Acceptance item | Required evidence |
| --- | --- |
| Frozen setup | Correct source/checkpoint/instruction/backend; no unauthorized policy/controller change |
| Three new runs | rep_04..06 or clearly identified resumed equivalents, every attempt retained |
| Recorder | No new overwritten/dropped frames; exact JPEG/state/request/response joins |
| Native stopping | Consumed STOP separated from discarded response, timeout and harness stop; explicit sampled stillness check |
| Visualization | Three complete HD overview films plus native views, state replay and decision review; real MP4s returned |
| Target outcome | Measured terminal geometry and visual verdict, including navigation failure |
| Historical integrity | Old evidence unchanged; legacy gaps remain explicit |
| Return integrity | Every declared file locally present with matching hashes; all videos decode and are visually inspected |
| Cleanup | Task process groups ended; protected Isaac Sim and unrelated services preserved |

Package preparation is `prepared_not_dispatched`. Static probe success is not
navigation reproduction. No execution identity exists until Dr Sun dispatches
this package and Opus records the actual run context.
