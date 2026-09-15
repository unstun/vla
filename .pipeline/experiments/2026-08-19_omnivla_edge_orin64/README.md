# OmniVLA-edge Jetson AGX Orin 64GB receive-only smoke

## Status

`validated` for the declared single-frame receive-only smoke.

This experiment transfers the pinned OmniVLA-edge source and weights to the
directly connected Jetson AGX Orin 64GB and runs one CUDA forward pass using an
archived real Lite3 front-camera frame and the instruction `move forward`.

## Safety and claim boundary

- Output is written to files only. No robot-control process, MotionSDK API, ROS
  publisher, navigation loop, socket sender, daemon, or autostart entry is used.
- The runner still computes the upstream example PD values for parity, but they
  are retained only as JSON evidence and are never transmitted.
- A pass supports only an OmniVLA-edge CUDA single-frame receive-only smoke on
  this Jetson environment. It does not validate collision avoidance, metric
  trajectory scale, locomotion integration, autonomous navigation, or the
  approximately 15 GB OmniVLA-original model.

## Fixed identities

- upstream source commit: `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`
- OmniVLA-edge Hugging Face revision:
  `b1361b7e24f101edea795a98b00a826b61a97394`
- edge checkpoint SHA-256:
  `f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d`
- CLIP ViT-B/32 SHA-256:
  `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`
- real Lite3 frame SHA-256:
  `c982be19a4b55213252902c4cc957a7e74903a6f253fc2378f512e0051237f09`

## Paths

- local evidence: this directory
- remote execution copy:
  `/home/nvidia/sun/vla_exec/2026-08-19_omnivla_edge_orin64`
- task specification:
  `.trellis/tasks/archive/2026-08/08-19-omnivla-edge-orin64-receive-only-smoke/`

The device ownership and storage cleanup boundary is documented in
`DEVICE_USAGE_POLICY.md`. Pre-existing vehicle-autonomy content is protected;
this experiment owns only `/home/nvidia/sun/` on the Jetson.

## Storage governance result

- Root filesystem before cleanup: 234 GB total, 210 GB used, approximately
  13 GB available, 95% used.
- Root filesystem after reviewed cache/disabled-Snap cleanup: approximately
  17 GB available, 93% used.
- Root filesystem after the deployment and run: approximately 16 GB available,
  93% used.
- Root filesystem after Dr Sun's subsequent explicit approval to permanently
  empty the desktop trash: approximately 62 GB available, 73% used.
- Task-owned remote footprint after the run: 763 MB.
- Vehicle-autonomy working directories, bag files, PCD files, models, and
  Docker objects were not modified. The 1,827 items already in the 46 GB
  desktop trash were permanently deleted only after separate explicit approval;
  the trash directories themselves were retained and verified empty.

## Execution result

- accepted run:
  `runs/20260819T144700Z_real_lite3_move_forward/`;
- input: visually checked, non-blank 1280x720 real Lite3 front-camera JPEG from
  the previously validated receive-only capture;
- language instruction: `move forward`;
- runtime: Jetson PyTorch `2.1.0a0+41361538.nv23.06`, device `cuda:0` (`Orin`);
- output: finite shape `(8, 4)`, modality ID `7` (`language only`);
- model forward: `5.0280797481536865` seconds;
- total one-shot wall time including imports, model/CLIP load, forward, and
  artifact generation: `23.198610749` seconds;
- tegrastats observed peak total system RAM: 7,922 MB; peak GR3D frequency
  utilization field: 60%; peak GPU temperature: 38.343 C;
- process cleanup: no task model process and no `tegrastats` process remains;
- non-interference: Ethernet, Jetson Wi-Fi/default route, Lite3 ping, and Lite3
  SSH port remained healthy;
- hashes: all 125 declared inputs passed remotely, and every retained accepted
  run artifact passed its local SHA-256 check.

The pre-execution directory
`runs/20260819T144200Z_real_lite3_move_forward/` records exit 127 because the
target lacks `/usr/bin/time`. Python and the model did not start in that
attempt. It is retained as failure evidence and is not counted as a forward.

## Visual and safety interpretation

The input visibly contains close obstacles, including table legs and a vehicle
wheel. OmniVLA-edge produced a generally forward trajectory, but this task did
not run obstacle collision checking, camera calibration, metric calibration,
or a robot controller. The generated trajectory must therefore not be sent to
Lite3. A separate reviewed safety-planning gate is required before any motion
test.

## Acceptance table

| Criterion | Result | Evidence |
|---|---|---|
| Fixed input identity | pass | `manifests/input_manifest.sha256`, remote check logs |
| JetPack compatibility | pass | `runs/prepare/jetpack_python_before_install.log`, `import_smoke.log` |
| Edge and CLIP load on CUDA | pass | accepted run `stdout.log`, `cuda_probe.json` |
| Finite `(8, 4)` one-shot output | pass | accepted run `outputs.json`, `validation.json` |
| Receive-only safety | pass | `runs/postflight_corrected.txt`; no control dependency or process |
| Network non-interference | pass | preflight and `runs/postflight_corrected.txt` |
| Sync-back and artifact hashes | pass | accepted run `retained_artifacts_check.log` and local experiment manifest |

Strongest justified labels: `reproduced` on this Jetson CUDA environment and
`validated` for this exact archived-real-frame, language-only, receive-only
smoke. No stronger deployment or navigation claim is made.
