# OmniVLA Lite3 receive-only distributed deployment

## Goal

Deploy the pinned `OmniVLA-original` model as a distributed, receive-only
real-robot inference path: Lite3 captures one real front-camera frame and sends
it with a language instruction to an on-demand service on `gpu40901`; Lite3
receives and records the returned trajectory. This establishes a reviewable
camera-to-VLA round trip without creating any path to robot actuation.

The user value is direct runtime evidence that the selected VLA can consume the
Lite3 camera over the newly established Wi-Fi link, rather than another static
sample-image result.

## Confirmed facts

- Dr Sun approved the distributed topology on 2026-08-19: `gpu40901` performs
  inference and Lite3 is a camera client; the first deployment is receive-only.
- The repository source is pinned at OmniVLA commit
  `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`; the official original checkpoint
  is pinned at Hugging Face revision
  `e36a84d4923c041149d441f93f3bdb7092bb5f07`.
- `OmniVLA-edge` has been reproduced locally in a non-official CPU environment.
  The pinned `OmniVLA-original` has now completed both an upstream-default and
  a language-only `move forward` CUDA forward on `gpu40901`, with finite shape
  `(8, 4)` and recorded source/checkpoint identity under task
  `08-18-omnivla-original-cuda-gpu40901`.
- Live Lite3 inspection found Ubuntu 20.04/aarch64, an RK3588 board, 3.8 GiB
  RAM, no swap, 19 GB free storage, no CUDA, and `/dev/video0` as an LRCP F1080P
  UVC capture device. It supports MJPEG at 1280x720 and 1920x1080 at 30 FPS;
  current format is MJPEG 1280x720 at 30 FPS. During approved implementation,
  `user` was added only to group `video`; a pre-existing root-owned RTSP service
  was then found to own `/dev/video0` and expose the same camera only at
  `rtsp://127.0.0.1:8554/test`.
- The direct robot network path is Lite3 `192.168.2.1` to `gpu40901`
  `192.168.2.109`. `gpu40901` keeps its default route on the USB Wi-Fi adapter;
  this task must not change either route.
- The pinned upstream output is an eight-point trajectory with four values per
  point `[x, y, hx, hy]`; X is forward and Y is left. The upstream `0.1 m`
  waypoint spacing is not calibrated for Lite3.
- No clean `machine-dog-nav` baseline or Lite3 command bridge has been imported
  into this repository. Receive-only deployment therefore does not need, and
  must not invent, a ROS or MotionSDK command interface.

## Requirements

### R1. Source and prerequisite gate

1. Local `/Users/sun/tongbu/study/phdproject/vla` remains the source of truth.
   Remote files are execution copies whose hashes are checked against a local
   deployment manifest.
2. The deployment may reuse the pinned model bytes already stored under
   `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/`, but it must not
   copy, modify, or delete other users' environments or processes.
3. No live-camera inference may run until the prerequisite CUDA task completes
   one successful `OmniVLA-original` forward pass with finite shape `(8, 4)` and
   recorded model/source identity. If that gate fails, this task stops as
   `blocked_by_original_reproduction`; it must not silently substitute the edge
   model.

### R2. Deployment topology

1. `gpu40901` hosts one serial inference process bound only to robot-facing
   address `192.168.2.109`; it is installed for on-demand use and is disabled
   and stopped by default after the acceptance run.
2. Lite3 hosts a Python 3.8-compatible client under `/home/user/` that captures
   exactly one frame per explicit invocation. There is no continuous loop,
   scheduled job, or autostart.
3. The client sends one JPEG and one UTF-8 language instruction, then records
   the response. It performs no local model inference.

### R3. Request and response contract

1. The MVP uses language-only modality. `/dev/video0` supplies the existing
   loopback RTSP service with MJPEG 1280x720 frames; the client captures one
   decoded JPEG from that fixed local stream without changing or stopping the
   camera owner. The bytes, dimensions, capture UTC timestamp, and SHA-256 are
   recorded. The acceptance invocation uses the fixed English
   instruction `move forward`; the client otherwise requires an explicit
   instruction and has no autonomous default loop.
2. The request has a versioned schema, request ID, bounded instruction length,
   bounded JPEG size, bearer token, and deadline. Malformed or unauthenticated
   requests fail before inference.
3. The response includes model/source identity, request ID, normalized finite
   trajectory of shape `(8, 4)`, upstream-default metric trajectory clearly
   marked `uncalibrated_for_lite3`, modality, inference timing, and
   `actuation_enabled: false`.
4. Lite3 only writes the response and a human-readable summary. It must not
   translate the trajectory into velocity, waypoint, joint, ROS, UDP control,
   or MotionSDK messages.

### R4. Safety and resource isolation

1. No task-owned file may import or invoke MotionSDK, a locomotion policy, ROS
   command publishing, or a robot control binary. A static safety check guards
   this invariant.
2. Camera access may add only `user` to the existing `video` group. The client
   may consume the existing loopback RTSP restream, but no camera configuration,
   firmware, robot service, or control process may be changed or stopped.
3. Before starting the model, sample free VRAM for 60 seconds and require a
   minimum of 24,576 MiB. Keep the existing per-process memory fraction cap of
   `0.45`, one request at a time, no model concurrency, and never stop or signal
   other users' jobs.
4. Server failure, network timeout, invalid trajectory, stale request ID, or
   non-finite output causes an error record and no further action. There is no
   automatic retry loop on Lite3.
5. The service binds only to `192.168.2.109`; no firewall, default route, Wi-Fi
   profile, FRP service, or public listener is changed.

### R5. Evidence and lifecycle

1. Durable code, protocol, manifests, scripts, and tests live in this
   repository. Run evidence lives under
   `.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/`.
2. Preserve the real captured JPEG, request/response JSON, service/client logs,
   environment probes, VRAM samples, hashes, latency, and remote path inventory.
3. After the acceptance run, stop the model server, prove that no task-owned
   inference or capture process remains, and confirm both SSH routes still work.
4. Deployment remains installed but on-demand. Start/stop/status commands and a
   path-scoped rollback procedure must be documented.

## Acceptance Criteria

- [x] **AC1 — prerequisite:** the pinned original source/checkpoint completes a
  successful official-CUDA forward pass and the prior task records the
  `reproduced` evidence; otherwise this task stops without model substitution.
- [x] **AC2 — local quality:** protocol, client, service, engine adapter, and
  safety tests pass locally with a fake backend; client files parse under
  Python 3.8 and server files under Python 3.10.
- [x] **AC3 — identity and guard:** remote manifest verification passes; the
  service reports the exact source commit and checkpoint revision; the 60 s
  pre-load VRAM minimum is at least 24,576 MiB and the 0.45 cap is recorded.
- [x] **AC4 — scoped service:** while running, the only listener is
  `192.168.2.109:<declared-port>`; unauthenticated and oversized probes are
  rejected, and health reports `actuation_enabled: false`.
- [x] **AC5 — real capture:** Lite3 captures one valid 1280x720 JPEG originating
  at `/dev/video0` through the existing robot-local RTSP restream, with
  timestamp and SHA-256, without changing camera settings or stopping its owner.
- [x] **AC6 — end-to-end:** one explicit Lite3 invocation sends a real frame and
  language instruction to `gpu40901`, receives HTTP success, and records a
  finite `(8, 4)` normalized trajectory with matching request ID and identities
  on both hosts.
- [x] **AC7 — fail closed:** negative tests for bad token, invalid JPEG,
  oversize body, timeout, malformed shape, and non-finite values yield no
  accepted trajectory; static checks find no actuation dependency or sender.
- [x] **AC8 — non-interference:** the original 40901 default route, Lite3 subnet
  route, FRP services, and SSH access remain healthy; no unrelated process was
  stopped or modified.
- [x] **AC9 — closeout:** server and client are installed for manual on-demand
  use but stopped after the run; process/listener probes are clean; all declared
  evidence is synced into the local experiment directory with hashes.
- [x] **AC10 — claim boundary:** a passing result may be called `integrated` and
  `validated` only for this single-frame receive-only contract. It is not a
  locomotion integration, autonomous navigation result, calibrated metric
  trajectory, performance benchmark, or real-robot motion validation.

## Out of scope

- Any motor command, standing, walking, velocity conversion, ROS command topic,
  MotionSDK sender, locomotion policy, or autonomous loop.
- Importing or modifying `machine-dog-nav` or `machine-dog`.
- Camera extrinsic/intrinsic calibration, collision checking, trajectory scale
  calibration, semantic success scoring, or control-rate evaluation.
- Running OmniVLA on the Lite3 RK3588, converting it to RKNN/ONNX, quantizing
  it, substituting `OmniVLA-edge`, training, fine-tuning, or benchmarking.
- An always-on 40901 GPU daemon or any public/relay exposure of the service.
