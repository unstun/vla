---
origin: human_approved
reviewed: false
as_of: 2026-08-19
---

# Pre-run decision log: OmniVLA Lite3 receive-only deployment

This pre-run section was written before the first remote deployment process.
Results may be appended after execution; expectations below are not rewritten.

## Human authorization

Dr Sun approved the final plan after reviewing the distributed topology:
OmniVLA-original runs on `gpu40901`; Lite3 captures one real camera frame and
records the returned trajectory; no actuation path is present.

## Camera-source deviation found during preflight

After adding only `user` to `video`, direct capture returned `EBUSY`. The owner
is the pre-existing root process `/home/ysc/rtsp_stream/start_stream.sh`, which
reads `/dev/video0` at MJPEG 1280x720 and publishes the same front-camera stream
only at `rtsp://127.0.0.1:8554/test`. The deployment will consume one frame from
that fixed loopback stream with software decode. It will not stop, signal, or
reconfigure the existing camera process. Direct V4L2 remains a supported client
mode for a future period when the device is free.

The same preflight measured the Lite3 wall clock about 45 seconds ahead of
gpu40901. The task does not alter system time. End-to-end latency is computed
with the Lite3 monotonic clock, while cross-host UTC ordering is explicitly not
treated as synchronized evidence.

## Pinned identity

- source: `NHirose/OmniVLA` commit
  `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`
- checkpoint: `NHirose/omnivla-original` revision
  `e36a84d4923c041149d441f93f3bdb7092bb5f07`
- model gate: the prerequisite official-CUDA forward pass must succeed before
  the real camera may be sent to the original backend
- network: Lite3 `192.168.2.1` to gpu40901 `192.168.2.109:8765`

## Expected result

One explicit Lite3 invocation captures a valid 1280x720 MJPEG frame, sends it
with `move forward`, receives a finite normalized `(8, 4)` trajectory with the
pinned identities and matching request ID, and stores evidence on both hosts.
`actuation_enabled` remains exactly false. The server is stopped afterward.

## Failure signals

- prerequisite original-model reproduction does not complete successfully;
- source/checkpoint/deployment manifest mismatch;
- 60-second free-VRAM minimum below 24,576 MiB;
- listener is not restricted to `192.168.2.109`;
- capture, token, JPEG, timeout, identity, request ID, shape, or finite check
  fails;
- any task-owned control dependency, command sender, automatic retry, or loop;
- either SSH path, route, Wi-Fi profile, or FRP service regresses.

## Stop rules

- Do not substitute OmniVLA-edge if the original model fails.
- Do not start the real backend before the prerequisite gate and VRAM guard.
- Do not issue any robot command; stop after one real request.
- Do not signal another user's process. Stop only a PID whose command line and
  recorded PID file both identify this task.
- Leave the installed on-demand files in place but stop the model service and
  prove the listener and task-owned processes are gone.

## Claim boundary

A fully passing result can support `integrated` and `validated` only for this
single-frame receive-only contract. It cannot support a calibrated trajectory,
closed-loop navigation, locomotion integration, semantic success, performance,
or real-robot motion claim.

## Results appended after execution

The pinned prerequisite passed before live-camera inference. The deployment
source manifest and 18-test suite then passed on both the local source and the
gpu40901 execution copy. The original backend completed its 60-second VRAM
guard with a minimum of 33,701 MiB free, loaded under the 0.45 CUDA memory cap,
reported the pinned identities, and listened only at `192.168.2.109:8765`.

Before the accepted request, the live service rejected an invalid bearer token
with HTTP 401, an oversized body with HTTP 413, and non-JPEG bytes with HTTP
400. None produced an accepted trajectory.

Lite3 run
`20260819T103300.657356Z_61711107-9e58-4341-9c47-80e2b40f086d`
captured a visually valid 1280x720 frame from the unchanged loopback stream and
sent exactly one `move forward` request. The 122,721-byte JPEG has SHA-256
`c982be19a4b55213252902c4cc957a7e74903a6f253fc2378f512e0051237f09`.
The response matched request ID, source commit, and checkpoint revision; its
trajectory was finite shape `(8, 4)`, inference time was 456.746 ms, and Lite3
monotonic end-to-end time was 5,029.914 ms. It recorded
`actuation_enabled=false` and `uncalibrated_for_lite3`.

The recorded service PID was then stopped. Port 8765 and task-owned model
process probes were clean; GPU allocation returned to only the pre-existing
CARLA and IsaacLab processes. Both Wi-Fi routes, nested SSH, the two gpu40901
FRP services, and Lite3 camera PIDs 537/538/539/563 remained healthy. The
receive-only contract therefore earns `integrated` and `validated`; no broader
claim is made.
