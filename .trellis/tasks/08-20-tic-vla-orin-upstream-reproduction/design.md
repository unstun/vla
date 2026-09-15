# Design: direct Orin TIC-VLA pretrained inference

## System boundary

```text
official repository + official model assets
                 |
                 v
local pristine snapshot + provenance manifest
                 |
                 v
numbered compatibility patches -> remote task-local work copy
                 |
retained Lite3 RGB fixture + repeated delayed/current frame + neutral state
                 |
                 v
      InternVL3-1B reasoner -> TIC-VLA action expert
                 |
                 v
 language text + finite (1, 30, 2) waypoint file + measurements
                 |
                 v
       local evidence sync-back and review
```

There is deliberately no connection from model output to a robot-control API,
ROS topic, velocity command, socket service, or actuator.

## Owned paths

Local source of truth:

- Pristine upstream:
  `references/upstream/2026-08-20_tic_vla/source/TIC-VLA`
- Provenance manifest:
  `references/upstream/2026-08-20_tic_vla/repository_manifest.yaml`
- Runtime evidence:
  `.pipeline/experiments/2026-08-20_tic_vla_orin_pretrained/`

Remote execution copy:

- Root: `/home/nvidia/sun/vla_exec/2026-08-20_tic_vla_orin_pretrained/`
- Children: `pristine/`, `work/`, `models/`, `checkpoints/`, `python_deps/`,
  `hf_cache/`, `inputs/`, `patches/`, `runs/`, and `manifests/`.

No other remote path is owned by this task.

## Compatibility strategy

1. Preserve the upstream snapshot exactly and derive a separate work copy.
2. Reuse Jetson PyTorch 2.1 and CUDA. Do not install upstream PyTorch 2.8 or
   CUDA 12.8 over the JetPack runtime.
3. Audit Python 3.10-only syntax/APIs against Python 3.8. Every required source
   change becomes a small, ordered patch such as
   `0001-python38-compat.patch`; the manifest records its reason.
4. Install only pure-Python/runtime dependencies into `python_deps/` or a
   task-local virtual environment that exposes the system Jetson PyTorch.
5. Run syntax compilation and import smoke before model downloads.
6. Inspect checkpoint metadata and tensors on CPU before allocating CUDA, then
   perform CUDA loading and inference serially to control peak memory.
7. If a dependency requires an incompatible binary wheel or the port changes
   model semantics, stop and report the incompatibility instead of changing
   system packages or inventing a replacement model.

## Input and output contract

The first fixture is the retained Lite3 image at:

`.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/runs/real_original/20260819T103300.657356Z_61711107-9e58-4341-9c47-80e2b40f086d/frame.jpg`

The run manifest must state that this is a single, offline, non-official
fixture. Delayed/current frames are repeated copies and robot state/ego-motion
values are neutral placeholders. The fixture can test execution and tensor
contracts only; it cannot establish temporal reasoning, navigation semantics,
path quality, or safety.

Expected outputs are the upstream language response and a batch-one,
30-step, two-coordinate waypoint tensor. The source-inspected interface is
authoritative if it differs. Raw arrays must be retained before any plotting or
summary.

## Execution gates

1. **Provenance gate:** commit/license/assets and local pristine hash inventory.
2. **Isolation gate:** remote ownership, free space, routes, processes, and
   absence of a task-local service or actuator path.
3. **Import gate:** Python compilation and imports on the Orin.
4. **Checkpoint gate:** published file hash plus complete state-dict report.
5. **CUDA load gate:** model and required base assets load without modifying
   the system environment.
6. **Inference gate:** warm-up then three serial measured forwards; all required
   outputs are finite and saved.
7. **Postflight gate:** no persistent listener/daemon, no protected-path or
   route change, sufficient storage, and evidence synced back locally.

Each gate must pass before proceeding. Failures remain evidence and do not get
relabeled as a successful reproduction.

## Rollback and claim policy

Rollback is limited to removing the task-owned remote directory after evidence
has been synced and after separate cleanup approval. Existing system and
vehicle files are never cleanup targets.

Passing all gates permits only this claim: the pinned released TIC-VLA
checkpoint completed a bounded receive-only compatibility smoke on this Jetson
AGX Orin. It does not validate the official environment, paper results,
asynchronous live execution, Lite3 control, collision avoidance, or safety.
