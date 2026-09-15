# Design: OmniVLA-edge on Jetson AGX Orin 64GB receive-only smoke

## 1. Boundary and data flow

```text
local pinned source/weights/patches/real Lite3 JPEG
  -> direct Ethernet transfer with SHA-256 verification
  -> isolated Jetson pristine copy + patched work copy
  -> JetPack CUDA PyTorch + lightweight local dependencies
  -> one OmniVLA-edge forward on cuda:0
  -> raw 8x4 trajectory + figure + timing + logs
  -> evidence sync back to the local repository
```

The result terminates at files. There is no edge from the trajectory to the
Lite3 navigation or locomotion stack.

## 2. Owned paths

### Local source of truth

- source: `third_party/2026-08-18_omnivla_5182600/OmniVLA/`;
- edge checkpoint:
  `third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-edge/`;
- CLIP checkpoint:
  `third_party/2026-08-18_omnivla_5182600/checkpoints/clip/ViT-B-32.pt`;
- patch series:
  `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/patches/`;
- real Lite3 input:
  `.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/runs/real_original/20260819T103300.657356Z_61711107-9e58-4341-9c47-80e2b40f086d/frame.jpg`;
- new evidence:
  `.pipeline/experiments/2026-08-19_omnivla_edge_orin64/`.

### Jetson execution copy

`/home/nvidia/sun/vla_exec/2026-08-19_omnivla_edge_orin64/` contains:

- `pristine/`: manifest-verified pinned upstream source, never patched;
- `work/`: disposable work copy with patches `0001`--`0005`;
- `checkpoints/`: edge and CLIP files in the upstream-expected layout;
- `patches/`: exact recorded patch files;
- `inputs/`: the manifest-verified real Lite3 JPEG;
- `python_deps/`: task-local lightweight dependencies loaded only through the
  task command's `PYTHONPATH`;
- `runs/`: raw execution outputs and logs;
- `manifests/`: local-to-remote input and retained-output hashes.

## 3. Environment strategy

The live target lacks `ensurepip`, so no system `python3-venv` package is added.
First prove that system Python imports the installed Jetson CUDA build of torch
and torchvision. Install only `utm`, `openai-clip`, `efficientnet_pytorch`, and
their small Python dependencies with `--target` and `--no-cache-dir` into the
task-owned `python_deps/` directory. Only task commands add that directory to
`PYTHONPATH`. The upstream project package is not installed because its
dependency pins would replace the JetPack stack.

The work copy is imported directly through its path. `OMNIVLA_CLIP_ROOT`
points to the verified local CLIP directory and `OMNIVLA_RUN_DIR` points to the
unique run directory.

## 4. One-shot inference

The upstream edge runner expects current and goal images. For this
language-only smoke, the archived real Lite3 frame replaces only the work
copy's current image; the pinned upstream goal image remains unchanged and is
masked by the selected modality. The fixed prompt is `move forward`.

Pre-run checks validate CUDA, free disk, input hashes, imports, and work-copy
diff. The accepted invocation runs once under resource timing. Post-run checks
parse the raw JSON and require numeric finite shape `(8, 4)`, then inspect the
saved figure and confirm that no task process or listener remains.

## 5. Failure and claim policy

No dependency conflict is repaired by replacing Jetson torch. No missing disk
is repaired by deleting unrelated data. No failed edge run falls back to the
15 GB original checkpoint. Failures are retained as evidence and labelled by
the failed gate. A pass supports only `reproduced` on this Jetson environment
and `validated` for the declared one-frame receive-only smoke.
