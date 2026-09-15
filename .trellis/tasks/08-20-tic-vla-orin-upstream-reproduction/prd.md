# Run the released TIC-VLA checkpoint on Jetson AGX Orin 64GB

## Goal

Run the official released TIC-VLA pretrained weights directly on the existing
Jetson AGX Orin 64GB and retain auditable evidence of at least one real CUDA
inference. Do not train, fine-tune, actuate the robot, or modify protected
vehicle files or the Jetson system runtime.

The maximum claim is **imported upstream plus an Orin pretrained-weight
compatibility smoke**. This is not a reproduction of the paper, DynaNav,
training, the official x86 dependency stack, Go2 deployment, or Lite3
autonomous navigation.

## Confirmed facts and human decisions

- Dr Sun selected the direct-Orin route on 2026-08-20. Skip `gpu40901`.
- Use only the released upstream checkpoint; perform no training, fine-tuning,
  reinforcement learning, or full-dataset download.
- Pin <https://github.com/ucla-mobility/TIC-VLA> `main` at commit
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
- The upstream license is the UCLA Academic Software License, limited to
  academic/nonprofit research and prohibiting further transfer.
- Use the official `TIC-VLA-model.ckpt`, approximately 1.94 GB, with published
  SHA-256
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`,
  plus the upstream-selected InternVL3-1B base model.
- The released training/evaluation implementation represents an action as 30
  two-dimensional waypoint offsets. For a batch of one, the expected action
  tensor is `(1, 30, 2)`, unless source inspection proves a different contract.
- The official environment declares Python 3.10+, PyTorch 2.8.0+cu128, and
  torchvision 0.23.0+cu128. The target Orin currently has JetPack 5.1.2,
  Python 3.8.10, and Jetson PyTorch 2.1.0, so an exact environment reproduction
  is impossible without a risky system change.
- The Orin has approximately 63 GB free storage and 61 GiB RAM. VLA owns only
  `/home/nvidia/sun/`; vehicle/autonomous-driving directories are protected.
- The Lite3 route remains available, but this task must not send commands,
  start listeners/servers, use ROS/SDK control, or move the robot.

## Requirements

### R1. Pin source and asset provenance

- Import one pristine local snapshot under
  `references/upstream/2026-08-20_tic_vla/source/TIC-VLA`.
- Record repository URL, branch, commit, license, upstream instructions,
  checkpoint URL and SHA-256 in
  `references/upstream/2026-08-20_tic_vla/repository_manifest.yaml`.
- Preserve the imported source unchanged. Apply every compatibility edit as a
  numbered patch to a separate work copy.
- Do not download the full TIC-VLA dataset.

### R2. Preserve the Orin environment and storage

- Reuse the JetPack-provided PyTorch/CUDA stack. Do not replace system Python,
  PyTorch, CUDA, JetPack, drivers, or global packages.
- Put source, models, dependencies, caches, inputs, patches, manifests, and run
  outputs only under
  `/home/nvidia/sun/vla_exec/2026-08-20_tic_vla_orin_pretrained/`.
- Keep task dependencies isolated and keep at least 10 GiB free on the root
  filesystem.
- Do not inspect, edit, move, or delete protected vehicle or autonomous-driving
  content.

### R3. Establish a truthful pretrained inference gate

- First compile/import the adapted code without downloading large assets.
- Inspect the checkpoint structure on CPU and record all state-dict keys,
  missing keys, unexpected keys, and shape mismatches. Never conceal an
  incomplete load with an unexplained `strict=False`.
- Then prove that the checkpoint and required base model load on CUDA.
- Use the retained Lite3 camera image as an explicitly labelled offline test
  fixture. If delayed/current images must both be present, repeat that single
  image and provide neutral robot state; do not describe it as an official
  DynaNav sample or a live temporal sequence.
- Run one warm-up followed by three measured serial forward passes.
- Require a language output and a finite waypoint tensor matching the verified
  upstream contract, expected `(1, 30, 2)`.

### R4. Retain reproducible evidence

- Store commands/configuration, dependency inventory, input provenance, hashes,
  stdout/stderr, checkpoint-load report, language output, waypoint arrays,
  warm-up result, and all three measured repeats.
- Record model loading time, VLM reasoning latency, action-expert latency where
  separable, end-to-end latency, peak CUDA memory, temperature, and power data
  available from the Jetson.
- Sync all final source overlays, manifests, logs, and results back to
  `.pipeline/experiments/2026-08-20_tic_vla_orin_pretrained/` before making a
  runtime claim.

### R5. Enforce receive-only safety and non-interference

- The executable must write predictions to files only. It must expose no
  robot-command publisher, socket listener, network service, daemon, autostart,
  ROS command, SDK command, or `/cmd_vel` path.
- Record preflight and postflight route/process/storage checks.
- Stop before execution if source inspection discovers a sender/listener or if
  isolation cannot be proved.

## Acceptance criteria

- **AC1 Provenance:** pristine source, pinned commit, license, asset URLs, and
  hashes are recorded locally.
- **AC2 Isolation:** all remote changes are confined to the owned task path,
  system packages are unchanged, and at least 10 GiB remains free.
- **AC3 Checkpoint integrity:** the downloaded checkpoint hash matches the
  published SHA-256 and the complete state-dict compatibility report is saved.
- **AC4 Real CUDA forward:** one real Orin CUDA forward returns a language
  result and finite waypoint output with the source-verified shape.
- **AC5 Repeat evidence:** one warm-up and three serial measured forwards are
  retained with latency, memory, temperature, and available power evidence.
- **AC6 Honest claim:** the report explicitly limits the result to an Orin
  pretrained-weight compatibility smoke.
- **AC7 Non-interference:** static inspection and runtime checks find no robot
  command sender/listener and postflight checks show no protected or persistent
  system change.
- **AC8 Sync-back:** the local repository contains the final compatibility
  overlays and complete evidence; no result exists only on the Orin.

## Out of scope

- `gpu40901`, exact official x86 stack reproduction, full DynaNav simulation,
  paper-table reproduction, and downloading the full released dataset.
- Training, fine-tuning, reinforcement learning, distillation, or checkpoint
  modification.
- Live camera streaming, Wi-Fi latency conclusions, trajectory-scale
  calibration, waypoint-to-velocity conversion, collision veto, locomotion,
  APK work, or any real-robot motion.
- Cleanup of other users' or pre-existing Jetson files.
