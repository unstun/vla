# Implementation plan: OmniVLA-edge Orin 64GB receive-only smoke

## Phase 0 — live preflight and fixed inputs

- [x] Confirm direct Ethernet SSH to the Jetson, hardware identity, JetPack,
  CUDA PyTorch, memory, system-disk free space, Ethernet/Wi-Fi routes, and
  Jetson-to-Lite3 reachability.
- [x] Select the pinned edge checkpoint, CLIP checkpoint, source snapshot,
  recorded `0001`--`0005` patch series, and archived real Lite3 frame.
- [x] Exclude the approximately 15 GB original checkpoint because the system
  volume has only about 13 GB free.

## Phase 1 — local bundle and remote verification

- [x] Inventory the nearly full Jetson system disk, protect all pre-existing
  vehicle-autonomy content, remove only reviewed regenerable caches and disabled
  Snap revisions, and establish `/home/nvidia/sun/` as the sole VLA-owned
  namespace. Free space increased from approximately 13 GiB to 17 GiB.
- [x] Create the local experiment directory, execution scripts, input manifest,
  and claim-boundary note before model execution.
- [x] Create the exact remote execution layout without touching unrelated
  paths; record a before-state inventory.
- [x] Sync only declared source, weights, patches, and input over Ethernet.
- [x] Verify every remote input against the local SHA-256 manifest and record
  disk usage.

## Phase 2 — JetPack-compatible environment and model smoke

- [x] Create the path-scoped `python_deps/` directory and prove task commands
  use it together with the installed Jetson CUDA torch/torchvision builds.
- [x] Install only missing lightweight Python dependencies with no pip cache;
  record resolved versions and imports.
- [x] Copy pristine source to `work/`, apply patches `0001`--`0005`, record the
  exact diff, and arrange checkpoint paths expected by the runner.
- [x] Run import and weight-load smoke checks on `cuda:0`; stop on any identity,
  dependency, CUDA, memory, or disk failure.

## Phase 3 — single-frame receive-only run

- [x] Place the archived real Lite3 JPEG at the work copy's current-image path
  while preserving and hashing the original bundled sample.
- [x] Run exactly one accepted CUDA forward with instruction `move forward` and
  resource timing; retain stdout, stderr, environment, raw JSON, and figure.
- [x] Validate finite shape `(8, 4)`, device identity, model/CLIP/input hashes,
  and record peak resource use.
- [x] Confirm no result was sent to the robot and no task-owned process,
  listener, service, or scheduled job remains.

## Phase 4 — sync-back and closeout

- [x] Recheck Ethernet SSH, Jetson Wi-Fi/default route, and Lite3 SSH
  reachability without changing configuration.
- [x] Sync logs and outputs to the local experiment directory, generate and
  verify a retained-artifact manifest, and visually inspect the input/output
  figure.
- [x] Update the acceptance table and task status with the exact claim boundary;
  review local diff and preserve all unrelated user changes.

## Stop rules

- Stop before model execution on hash mismatch, CUDA loss, incompatible import,
  route regression, or insufficient disk.
- Stop after a model error, OOM, wrong output shape, or non-finite value. Do not
  retry with changed weights or changed JetPack packages.
- Never start a control process, navigation loop, robot-motion sender, daemon,
  or autostart entry in this task.
