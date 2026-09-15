# Implementation plan: OmniVLA Lite3 receive-only deployment

## Phase 0 — prerequisite and snapshots

- [x] Return to task `08-18-omnivla-original-cuda-gpu40901`, let the existing
  environment/download work finish, and complete its declared original-model
  forward-pass gate without relaxing shared-host VRAM rules.
- [x] Sync that task's evidence locally and record the exact successful run,
  source/checkpoint identities, environment, peak VRAM, and process cleanup.
- [x] Confirm the forward gate succeeded on the first original-model attempt;
  no fallback or `blocked_by_original_reproduction` path was used.
- [x] Re-probe Lite3 camera, route, clock, disk, Python, `video` group, and
  `gpu40901` address/GPU/listeners. Save verbatim preflight evidence locally.

## Phase 1 — local implementation and tests

- [x] Load `trellis-before-dev`, then create
  `deploy/omnivla_lite3_receive_only/` without editing the pristine third-party
  snapshot.
- [x] Implement versioned protocol validation and canonical audit records.
- [x] Implement a fake backend and bounded HTTP service with bind-address,
  bearer-token, size, UTF-8, JPEG, concurrency, deadline, and identity guards.
- [x] Implement the Python 3.8-compatible Lite3 one-shot capture/client. It must
  have no control dependencies and no retry loop.
- [x] Implement the minimal upstream callable-engine adapter and document every
  changed computation boundary; do not alter weights, normalization, action
  head, waypoint spacing, or controller constants.
- [x] Add start/stop/status, preflight, and manifest scripts using explicit
  absolute remote paths; document manifest-checked sync and a separately
  authorized manual path-scoped rollback instead of shipping a destructive
  rollback helper.
- [x] Tests: valid round trip; bad token; oversized body; invalid JPEG; empty or
  oversized instruction; busy server; timeout; request-ID mismatch; identity
  mismatch; malformed shape; NaN/Inf; `actuation_enabled != false`; capture
  failure; static forbidden-import/sender scan.
- [x] Run local unit/integration tests, Python 3.8 syntax compatibility for
  client/shared files, Python 3.10 checks for server files, and shell checks.

## Phase 2 — sync and 40901 service smoke

- [x] Create the local evidence directory and pre-run decision log before the
  first deployment run.
- [x] Generate a local SHA-256 source manifest, sync only declared files to
  `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only/`, and verify
  the manifest remotely before execution.
- [x] Build a fresh work copy from the pinned pristine source plus recorded
  original and deployment patches; verify its diff allowlist and syntax.
- [x] Run fake-backend HTTP tests on `gpu40901` first, bound to
  `192.168.2.109`; prove no listener exists on `0.0.0.0` or the relay-facing
  address.
- [x] Generate the runtime token without printing it. Sample VRAM every five
  seconds for 60 seconds; require minimum free >= 24,576 MiB.
- [x] Start the real backend with memory fraction `0.45`, one model instance,
  one request at a time, and a task-owned PID record. Verify health and record
  model-load time, VRAM, listener, identities, and unrelated-process snapshot.

## Phase 3 — Lite3 installation and real-camera round trip

- [x] Sync the client/shared files and verified client bundle to
  `/home/user/omnivla_receive_only/`; verify exact hashes on Lite3.
- [x] Add only `user` to group `video` and reconnect. Direct open is correctly
  denied as busy because the pre-existing RTSP service owns `/dev/video0`;
  preserve that service and record the before/after group and owner state.
- [x] Prove one valid 1280x720 JPEG can be read without root from the fixed
  loopback RTSP restream using software decode; do not stop the camera owner.
- [x] Copy the runtime token directly from 40901 to Lite3 with mode `0600`
  without printing or tracking its value.
- [x] Run client negative tests against the fake service and a real-camera fake
  round trip; confirm no camera request reaches inference when capture
  validation fails. This is protocol evidence only, not model evidence.
- [x] With the robot stationary and no control program started, explicitly run
  one capture/request using the reviewed instruction `move forward`. Save the JPEG,
  request metadata, response, client log, server log, timestamps, hashes,
  trajectory shape/finite audit, inference latency, and end-to-end latency.
- [x] Sync the real-frame evidence back to the local experiment directory and
  visually inspect the frame for a non-blank, non-corrupt camera view.

## Phase 4 — safety, non-interference, and closeout

- [x] Stop only the task-owned server PID and prove the port is closed, GPU
  allocation released, and no task-owned client/capture process remains.
- [x] Recheck `gpu40901` default route, Lite3 route, both FRP services, outer
  `ssh gpu40901`, and inner SSH to Lite3; compare against preflight.
- [x] Run full local tests and the static forbidden-control scan against the
  exact synced source manifest.
- [x] Write experiment README/decision log with acceptance table, verbatim
  deviations, identities, evidence links, start/stop/status instructions,
  installed remote paths, and claim boundary.
- [x] Run `trellis-check`, update project status/spec only where durable facts
  changed, and review the complete diff. No commit is made in this closeout:
  the prerequisite task explicitly says no git add/commit, and the pre-existing
  user-owned `AGENTS.md` change remains untouched.

## Stop and rollback points

- Stop before model load if prerequisite identity, source manifest, checkpoint
  manifest, route binding, or VRAM guard fails.
- Stop before real capture if fake-backend protocol/safety tests fail.
- Stop after one real request; no continuous loop is authorized.
- Do not delete deployment directories during normal closeout. If rollback is
  requested, first stop the recorded PID, verify exact target paths, and remove
  only task-owned execution copies; group-membership rollback is separate.
