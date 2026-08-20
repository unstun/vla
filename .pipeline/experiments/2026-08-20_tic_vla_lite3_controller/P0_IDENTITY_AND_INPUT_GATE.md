# P0 identity and live-input gate

Status: **PASS for implementation and shadow-only work**. This gate does not
authorize or evidence motor actuation.

## Local sources of truth

- VLA repository base: `f615d28f0cf7e4fa4f3186b514231223f50e5540`.
  The pre-edit worktree had 29 porcelain entries; unrelated edits are
  preserved and task paths are staged separately.
- TIC-VLA pristine snapshot:
  `references/upstream/2026-08-20_tic_vla/source/TIC-VLA`, clean commit
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
- machine-dog controller base:
  `cf9745ff34305ede6046945a8cd8ec1171b19a1e`. Its pre-edit worktree was dirty;
  the controller change is isolated in Trellis task
  `08-20-tic-vla-lite3-controller-arbiter` and does not rewrite unrelated work.

## Model identities

- Base model: `OpenGVLab/InternVL3-1B`, resolved revision
  `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`.
- TIC-VLA checkpoint: `TIC-VLA-model.ckpt`, dataset revision
  `671de608f39ccae41b66cbb24ab923c0275f8fb4`, 1,938,501,547 bytes, SHA-256
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
- Lite3 locomotion profile: V12 `model_149999`; checkpoint SHA-256
  `a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450`;
  deployed stateless-H10 ONNX SHA-256
  `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`;
  policy manifest SHA-256
  `07756a385673facbb5cd5179f86fd11c4132a32da15c5af6f13bcf0e459d26be`.

## Compatibility overlay identities

| Patch | SHA-256 |
| --- | --- |
| `0001-python38-deferred-annotations.patch` | `8f42a38ecd3e51ab53b9a66cc04c20a3d45535c2a368d7a3eabad93a985158b7` |
| `0002-inference-import-isolation.patch` | `57e32269f6cdb99446e7fca3f23bf3c40cd1376e5023314a384e7a54f347877e` |
| `0003-transformers-no-fsdp-import.patch` | `e9616be1401ea429360d70a546bcf32b0173953da4596f5be7fbc0e2601a8c9e` |
| `0004-jetson-no-distributed-query.patch` | `8692ec16da0092845b1c9cec167ac96cb8975d5939f139d23d950e16e41e8b46` |
| `0005-jetson-cuda-explicit-init.patch` | `caa3e2be60bedc3806be21e1b5b610b04ef8bfcd2d1d0d384207b9afa760d3a0` |

These are prior package-runtime overlays. The DynaNav asynchronous entrypoint
requires an additional task-local Python 3.8 overlay; it must be recorded and
hash-checked before P1 is claimed.

## Selected live sources

- Source host: Xavier `192.168.1.103`.
- RGB: existing RealSense D435i ROS2 topic `/camera/color/image_raw`,
  `sensor_msgs/Image`, 640x480, `camera_color_optical_frame`, measured about
  12.9-14.4 Hz during read-only preflight. Pixels are forwarded unrotated; the
  orientation must be visually confirmed before any future motion phase.
- State: existing Fast-LIVO2 `/aft_mapped_to_init`, `nav_msgs/Odometry`, parent
  frame `camera_init`, child frame `aft_mapped`. Stationary capture returned
  finite millimetre-scale pose and zero twist.
- Transport decision: an on-demand task-owned read-only RGB+odometry bridge is
  required because the existing Xavier-to-Orin DDS allowlist includes odometry
  but not RGB. Existing vehicle directories and services remain untouched; no
  autostart is added.
- Network source identity: Orin selected `wlP7p1s0` with local source
  `192.168.2.70`; a live accept probe proved that Xavier observes the routed
  connection as `192.168.1.120`. The bridge allowlist uses the receiver-side
  identity and must be re-probed after a network restart.
- Clock boundary: Xavier reported a stale wall clock. Capture and freshness use
  process-local monotonic time only; cross-host wall time is diagnostic data.

## Execution copies and claim boundary

- Orin execution copy:
  `/home/nvidia/sun/vla_exec/2026-08-20_tic_vla_lite3_controller/`.
- Xavier bridge execution copy:
  `/home/ysc/sun/vla_exec/2026-08-20_tic_vla_lite3_controller/`.
- Local evidence:
  `.pipeline/experiments/2026-08-20_tic_vla_lite3_controller/`.

P0 establishes identities and usable read-only sources only. It is not P1
asynchronous evidence, integration evidence, navigation validation, or motor
authorization.
