# OmniVLA edge on Jetson AGX Orin 64GB receive-only smoke

## Goal

Transfer the pinned OmniVLA-edge and CLIP weights to the directly connected Jetson AGX Orin 64GB, build a JetPack-compatible isolated execution copy, and validate one CUDA single-frame receive-only inference with no actuation.

## Requirements

### R1. Fixed local inputs and claim boundary

1. `/Users/sun/tongbu/study/phdproject/vla` remains the only source of truth.
   The Jetson copy is an execution copy whose inputs and outputs are checked by
   SHA-256.
2. Use the pinned OmniVLA source snapshot at commit
   `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`, the pinned
   `OmniVLA-edge` checkpoint at Hugging Face revision
   `b1361b7e24f101edea795a98b00a826b61a97394`, the locally stored CLIP
   `ViT-B-32.pt`, and the recorded patch series `0001`--`0005` from the prior
   offline smoke.
3. Do not download, transfer, or run the approximately 15 GB
   `OmniVLA-original` checkpoint in this task. Live preflight found only about
   13 GB free on the Jetson system volume.
4. A passing result is a single-frame CUDA `receive-only` inference result. It
   is not robot actuation, autonomous navigation, collision avoidance,
   controller integration, a performance benchmark, or original-model parity.

### R2. Network and remote isolation

1. Transfer only over the direct Ethernet path to the Jetson AGX Orin 64GB at
   `192.168.1.5`; preserve the Jetson Wi-Fi connection and its route to Lite3.
2. Use the isolated execution root
   `/home/nvidia/sun/vla_exec/2026-08-19_omnivla_edge_orin64/`. Do not modify
   system Python packages, robot files, network profiles, boot services, or
   unrelated user data.
3. Record before/after Ethernet, Wi-Fi, default-route, Jetson GPU, and Lite3 SSH
   reachability evidence. No network configuration changes are authorized.

### R3. JetPack-compatible environment

1. Reuse the installed Jetson-specific PyTorch `2.1.0a0+41361538.nv23.06` and
   torchvision `0.16.1`; do not install upstream CUDA 12.1 wheels or replace
   the JetPack stack.
2. Create a path-scoped Python environment that can see the installed
   Jetson-specific packages, then install only the missing lightweight runtime
   dependencies with pip cache disabled.
3. Keep the pristine source copy unchanged. Apply the recorded patch series to
   a separate work copy and record its diff and hash inventory.

### R4. One-shot CUDA test

1. Use the real Lite3 camera frame previously archived by the validated
   receive-only task, together with the fixed English instruction
   `move forward`. Preserve the exact input image and its SHA-256 in this
   experiment record.
2. Run exactly one accepted model forward after import/load smoke tests. CUDA
   must be available and the model must execute on `cuda:0`.
3. Record raw output JSON, rendered trajectory figure, wall/resource timing,
   environment information, logs, input hashes, and output validation.
4. Require a finite trajectory of shape `(8, 4)`. Do not translate or forward
   any result to ROS, MotionSDK, locomotion, navigation, sockets, or robot
   control processes.

### R5. Evidence and stop rules

1. Sync durable run evidence back to
   `.pipeline/experiments/2026-08-19_omnivla_edge_orin64/` and include a local
   manifest covering every retained artifact.
2. Stop before inference on input hash mismatch, CUDA unavailability,
   incompatible imports, insufficient free disk, route regression, or model
   load failure. Stop after inference on OOM, non-finite output, or wrong shape.
3. Leave no model process, capture process, listener, scheduled job, or
   autostart service running after the one-shot test.

## Acceptance Criteria

- [x] **AC1 — identity:** source, edge checkpoint, CLIP file, patch series, and
  real Lite3 frame match the local manifest on the Jetson before execution.
- [x] **AC2 — compatibility:** a path-scoped environment imports the installed
  Jetson CUDA PyTorch/torchvision and all required OmniVLA-edge dependencies
  without replacing the JetPack packages.
- [x] **AC3 — model load:** the patched work copy loads the pinned edge and CLIP
  weights on `cuda:0` and records exact software/hardware identities.
- [x] **AC4 — one-shot inference:** exactly one accepted forward on the archived
  real Lite3 frame and `move forward` instruction yields a finite `(8, 4)`
  trajectory, raw JSON, figure, and timing evidence.
- [x] **AC5 — receive-only safety:** static and runtime evidence shows no robot
  command/control dependency, sender, listener, persistent process, or
  autonomous loop was introduced or left running.
- [x] **AC6 — non-interference:** the direct Ethernet SSH path, Jetson Wi-Fi
  route, and Jetson-to-Lite3 SSH reachability remain healthy after the run.
- [x] **AC7 — closeout:** the declared evidence is synced to the local source of
  truth, hashes verify, remote disk usage is recorded, and the result is
  labelled only as an edge CUDA single-frame receive-only smoke.

## Notes

- Parent task: `08-19-omnivla-lite3-receive-only-deployment`.
- This child task deliberately evaluates a different deployment target and
  model variant; it does not revise the completed original-model result.
