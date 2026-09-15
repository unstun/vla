# Design: OmniVLA Lite3 receive-only distributed deployment

## 1. Boundary and architecture

The smallest deployment that answers the research question is a single real
camera request with no executor:

```text
Lite3 /dev/video0 -> existing loopback RTSP restream
  -> one-shot JPEG capture with software decoding
  -> Python 3.8 client + response validator + audit log
  -> HTTP over 192.168.2.1 <-> 192.168.2.109
  -> Python 3.10 service + token/body/deadline guards
  -> pinned OmniVLA-original engine on RTX 4090
  -> normalized 8x4 trajectory + metadata
  -> Lite3 audit log only
```

There is intentionally no downstream edge from the audit log to navigation or
locomotion. The response is an advisory research artifact, not a command.

## 2. Ownership and paths

### Local source of truth

`deploy/omnivla_lite3_receive_only/` will own:

- `protocol.py`: schema constants, request/response validation, finite/shape
  checks, and canonical JSON serialization;
- `server.py`: bounded HTTP API, authentication, serialisation lock, health,
  and audit logging;
- `engine_original.py`: callable adapter over the prerequisite task's
  manifest-verified upstream work copy and recorded 0101--0103 patch series;
  it accepts an in-memory RGB image and language instruction, returns a
  trajectory only, and adds no second patch series;
- `lite3_client.py`: one-shot direct-V4L2 or loopback-RTSP capture, request,
  response validation, and local evidence writing;
- `scripts/`: manifest, preflight, start, stop, and status helpers; source sync
  is manifest-checked during deployment, while destructive rollback remains a
  documented manual procedure requiring separate authorization;
- `tests/`: fake-engine protocol, negative, lifecycle, and safety tests.

Run evidence is separate at
`.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/`.

### Execution copies

- `gpu40901`:
  `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only/`
- Lite3:
  `/home/user/omnivla_receive_only/`

The 40901 execution copy may reference the already verified checkpoint under
`/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/checkpoints/`.
Weights are not copied to Lite3 or back to the local repository.

## 3. Protocol

### Endpoints

- `GET /v1/health`: no model output; returns schema version, readiness,
  identities, bind address, and `actuation_enabled: false`.
- `POST /v1/infer?instruction=<percent-encoded UTF-8>`:
  `Content-Type: image/jpeg`, raw JPEG body, bearer token, request ID, capture
  UTC timestamp, and image SHA-256 headers.

The service binds to `192.168.2.109` only. A random token is generated on the
execution host, stored mode `0600`, and copied directly to a mode `0600` Lite3
runtime file. The token value is never tracked or printed in evidence.

### Bounds

- one in-flight inference; a concurrent request gets `409`;
- maximum JPEG size 5 MiB;
- instruction: non-empty, valid UTF-8, at most 256 bytes;
- server request deadline and client overall deadline are explicit;
- only JPEG magic/decoder-valid data proceeds to model inference.

### Successful response

```json
{
  "schema_version": 1,
  "request_id": "...",
  "source_commit": "5182600...",
  "checkpoint_revision": "e36a84d...",
  "modality": "language_only",
  "trajectory_normalized": [[0.0, 0.0, 1.0, 0.0]],
  "trajectory_metric_upstream_default": [[0.0, 0.0, 1.0, 0.0]],
  "metric_scale_status": "uncalibrated_for_lite3",
  "inference_ms": 0.0,
  "actuation_enabled": false
}
```

The real trajectory has exactly eight rows and four finite values per row. The
example above shows schema shape only. No velocity or joint target is returned.

## 4. Model adapter

The adapter keeps source/model identity explicit, loads the model once, and
serializes inference. It reuses the upstream processor, action head, and
normalization. A minimal patch replaces hard-coded input paths and module-level
modality globals with explicit arguments.

Language-only retains upstream modality ID 7. Because the upstream two-image
batch shape still requires a goal-image tensor, the adapter supplies a
deterministic black placeholder. The modality mask is the mechanism intended
to make that slot inactive; the placeholder is an implementation detail rather
than a response field, and this deployment does not claim that prompt or mask
semantics are scientifically validated.

The upstream `0.1 m` spacing is preserved for parity and labelled uncalibrated.
The upstream PD conversion is not exposed by the receive-only API.

## 5. Lite3 camera adapter

Live preflight found that the pre-existing root-owned
`/home/ysc/rtsp_stream/start_stream.sh` already owns `/dev/video0` and restreams
the same 1280x720 front-camera stream on the robot-only endpoint
`rtsp://127.0.0.1:8554/test`. The client therefore supports direct `v4l2-ctl`
when the device is free, but the reviewed robot invocation consumes exactly one
JPEG decoded in software from that fixed loopback endpoint. It neither stops
nor reconfigures the existing camera process. `user` remains in `video` for the
declared direct-device installation path. The client verifies JPEG metadata,
records capture time and SHA-256, sends once, validates the response, and exits.
The acceptance prompt is the fixed English string `move forward`; semantic
correctness is not an acceptance claim in this task.

There is no polling, automatic retry, systemd timer, or boot service.

## 6. Failure behavior

- Prerequisite CUDA reproduction failure: stop before deployment.
- Low VRAM: do not load the model; wait only within the declared guard budget.
- Model load/inference error: HTTP error plus server audit record; client exits.
- Network timeout or connection loss: client writes an error record and exits.
- Request ID mismatch, wrong shape, non-finite number, identity mismatch, or
  `actuation_enabled` not exactly false: client rejects the response and exits.
- Camera failure: no request is sent.

No failure path falls back to OmniVLA-edge or to robot actuation.

## 7. Resource lifecycle and rollback

The service is on-demand and stopped after the acceptance run to release GPU
memory. Start checks the 60-second free-VRAM guard and installs a PID/listener
guard; stop targets only the recorded task-owned PID. Rollback is path-scoped:
stop the task-owned process, remove only the two declared execution-copy
directories if explicitly authorized, and optionally remove `user` from the
`video` group. It never touches the shared conda base, existing Wi-Fi profiles,
FRP, model checkpoint source, or another process.

## 8. Claim boundary

A fully passing real-frame round trip supports `integrated` and `validated` for
the declared receive-only contract. It does not validate model semantics,
metric scale, safety for motion, closed-loop frequency, or navigation success.
