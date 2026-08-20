# Integrate TIC-VLA with the Lite3 locomotion controller

## Goal

Build the smallest complete Lite3 VLA loop:

`live RGB + navigation instruction + robot state -> TIC-VLA -> 30x2 local
waypoints -> bounded body command -> Retroid/VLA arbiter -> V12 model_149999
locomotion controller`.

The released TIC-VLA checkpoint must remain resident on the external Jetson AGX
Orin 64GB. The slow language reasoning path must run asynchronously while the
fast action expert reuses the latest model state and current image. The VLA must
never publish joint targets or bypass the existing locomotion controller.

This task is successful when the complete chain has passed replay, live shadow,
fault-injection, and a separately authorized supervised open-lane robot test.
It is not a claim that TIC-VLA is collision-safe in arbitrary environments.

## Confirmed baseline and decisions

- Use the pinned upstream TIC-VLA commit
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb` and the released checkpoint with
  SHA-256
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
- The completed Orin compatibility smoke returned finite `(1, 30, 2)` outputs.
  Its measured mean synchronous latency was 13.833 seconds. The same evidence
  measured approximately 0.15 seconds for a warm current-image feature call and
  0.012-0.014 seconds for the action expert.
- Reuse the upstream `DynaNav/ticvla.py::predict_async` architecture instead of
  inventing a new inference architecture. Its first call waits for model state;
  subsequent calls decode actions from the latest cached model state while a
  new reasoning generation runs in the background.
- Use the selected V12 `model_149999` locomotion policy as the only low-level
  controller. Its current source accepts normalized forward, lateral, and yaw
  commands and applies physical caps of `0.4 m/s`, `0.2 m/s`, and `0.6 rad/s`.
- The first TIC-VLA integration uses only forward velocity and yaw rate;
  lateral velocity is fixed to zero, matching the upstream Spot controller and
  reducing the initial calibration surface.
- The first motion profile is limited to `0.30 m/s` forward and
  `0.20 rad/s` yaw. These are integration-test limits, not new locomotion-policy
  limits.
- Retroid remains the human control path. VLA motion is permitted only while a
  configurable Retroid deadman button is held, with `R1` as the first-test
  default. Manual stick movement disarms VLA until the deadman is released and
  pressed again. The existing two-stick-button damping action remains intact.
- The first real-motion course is a cleared open lane. No wall-approach or
  obstacle-avoidance claim is allowed until an independent distance/collision
  veto is connected and tested.

## Requirements

### R1. Resident asynchronous TIC-VLA runtime

- Load the base model and checkpoint once per process and verify their pinned
  identities at startup.
- Port the already released upstream asynchronous inference path through the
  existing Orin compatibility overlays; do not modify the pristine upstream
  snapshot.
- Keep the robot at zero command until the first valid VLM model state exists.
- Continue action decoding from the latest valid model state while the next
  VLM reasoning generation is running.
- Treat reasoning text as diagnostic output only. Commands must come from the
  action-expert waypoint tensor, never from parsing generated text.
- Reset cached state, histories, sequence numbers, and commands on instruction
  change, service restart, or explicit disarm.

### R2. Live observation contract

- Implement one replay frame source for deterministic tests and exactly one
  live Lite3 RGB source selected by read-only preflight. Record URI/device,
  resolution, frame rate, timestamps, and camera orientation.
- Maintain the upstream four-frame delayed context at approximately 9, 6, 3,
  and 0 seconds plus the latest current frame used by the action expert.
- Supply `[vx, vy, yaw_rate, dx, dy]` and reasoning delay with explicit units.
  Prefer an existing odometry/pose source. If the first open-lane test must use
  command dead reckoning, label it explicitly and do not call it navigation
  validation.
- Reject missing, repeated-too-long, malformed, or stale live frames and
  invalid/non-finite robot state. Rejection produces zero command.

### R3. Waypoint-to-body-command adapter

- Accept only an exact finite `(30, 2)` waypoint array. Coordinate convention is
  upstream body/FLU: `x` forward and `y` left.
- Reuse the upstream Spot pure-pursuit conversion as the initial reference:
  arc-length lookahead, heading-error smoothing, curvature feed-forward, and
  angular feedback. Parameterize every gain and limit.
- Set `vy = 0` in the first implementation. Clamp the physical output to
  `0 <= vx <= 0.30 m/s` and `|wz| <= 0.20 rad/s`, then apply configurable slew
  limits before transmission.
- Reject non-finite, implausibly discontinuous, empty, out-of-order, or stale
  waypoint results. A rejected result must not refresh command freshness.
- Support `shadow` and `active` modes. Shadow mode performs the full pipeline
  and logs the proposed command but transmits a non-actuating command state.

### R4. Narrow Orin-to-controller protocol

- Send SI-unit body commands over a versioned UDP packet containing at least:
  schema version, session ID, strictly increasing plan sequence, source-frame
  sequence, reasoning-generation ID, mode, validity, `vx_mps`, `vy_mps`, and
  `wz_radps`.
- Limit packet size, validate every field, allowlist the configured Orin source,
  and use receiver-local monotonic time for freshness. Cross-host wall clocks
  must not decide whether a command is fresh.
- Only a newly accepted plan sequence refreshes the VLA watchdog. Replayed or
  duplicate packets cannot keep the robot moving.
- The controller converts the bounded SI command to its existing normalized
  `[forward, lateral, yaw]` interface. VLA cannot set motion state, stand the
  robot up, enter RL mode, or send joint commands.
- A VLA packet gap longer than 500 ms produces zero velocity. Invalid packets,
  source mismatch, process restart, sequence rollback, and session mismatch
  also fail to zero.

### R5. Retroid arbitration and stop behavior

- Implement one command owner at a time with priority:
  `joint-damping/stop > manual Retroid > fresh deadman-enabled VLA > zero`.
- Require a fresh Retroid stream and the deadman button for VLA eligibility.
  Retroid stream loss uses the existing 200 ms freshness watchdog and makes VLA
  ineligible.
- Any stick deflection over a configurable deadband immediately selects manual
  control and disarms VLA. VLA cannot resume until the deadman has been released
  and pressed again with centered sticks.
- Releasing the deadman commands zero. The existing simultaneous left/right
  stick-button action must still request joint damping.
- Explicit stop, controller fault, unsafe posture, invalid observation, and
  policy fault remain lower-controller responsibilities and always dominate VLA.

### R6. Staged verification

- First prove the official async inference path on Orin with retained replay
  frames: one first-generation wait followed by at least 100 fast action cycles.
- Then run protocol, adapter, watchdog, and arbitration tests without a motor
  command path.
- Run at least ten minutes of live-camera shadow mode with command, waypoint,
  frame-age, reasoning-age, and latency logs.
- Real-robot actuation requires a new explicit authorization after the shadow
  evidence is reviewed. Begin with standing/zero-command checks, then bounded
  open-lane trials no longer than 5 seconds or 0.5 m each.
- Intentionally test deadman release, manual takeover, stale VLA packets, VLA
  process exit, and Orin link loss before any autonomous free-running trial.

### R7. Source ownership and evidence

- Keep all VLA runtime code and final evidence in this repository. The remote
  Orin path is only an execution copy under
  `/home/nvidia/sun/vla_exec/2026-08-20_tic_vla_lite3_controller/`.
- Controller-side edits belong to a separately created and approved task in
  `../machine-dog`. That repository is currently dirty; implementation must
  identify an exact base and preserve unrelated changes before editing.
- Record source/checkpoint/controller identities, configs, startup commands,
  packet captures, raw logs, latency distributions, failures, and test videos.
  Sync remote evidence back locally before making an integration claim.

## Acceptance criteria

- [ ] **AC1 Identity:** startup verifies the selected TIC-VLA source,
      checkpoint, base model, compatibility overlay, controller source, and
      `model_149999` manifest.
- [ ] **AC2 Async gate:** after one initial reasoning wait, 100 replay action
      cycles complete with exact finite `(1, 30, 2)` output, no cache race or
      unbounded memory growth, and fast-path p95 latency no greater than 250 ms.
- [ ] **AC3 Input gate:** one live Lite3 RGB stream and one robot-state source
      feed the resident process; stale or invalid input reliably produces zero.
- [ ] **AC4 Adapter gate:** deterministic tests cover straight, left, right,
      zero, NaN/Inf, discontinuity, malformed shape, stale result, and slew/cap
      behavior; first-test output never exceeds `0.30 m/s`, `0 m/s` lateral,
      or `0.20 rad/s` yaw.
- [ ] **AC5 Protocol gate:** duplicate, out-of-order, wrong-session,
      wrong-source, malformed, and missing packets cannot refresh the receiver
      watchdog; a 500 ms VLA gap produces zero.
- [ ] **AC6 Arbitration gate:** automated truth-table tests and a no-motor live
      test prove damping/stop priority, manual takeover, deadman release,
      re-arm behavior, and loss of Retroid freshness.
- [ ] **AC7 Shadow gate:** a ten-minute live-camera shadow run has no accepted
      stale command, records latency/age distributions, and is reviewed before
      actuation.
- [ ] **AC8 Supervised motion gate:** after fresh authorization, at least ten
      bounded open-lane trials finish without fall, collision, unexpected mode
      transition, or command-limit breach; deadman release and manual takeover
      work through the final runtime path.
- [ ] **AC9 Claim boundary:** the result is labelled `integrated` only after the
      full Lite3 path runs and `validated` only for the stated open-lane test.
      It must not be presented as general obstacle avoidance or paper-result
      reproduction.

## Out of scope

- Training, fine-tuning, reinforcement learning, checkpoint modification, or
  paper-table reproduction.
- Replacing `model_149999`, sending VLA joint targets, or changing locomotion
  observations/rewards.
- Importing the full `machine-dog-nav` stack, rebuilding a general navigation
  framework, or adding ROS solely for this bridge.
- A new APK, web console, multi-user command system, autonomous recovery, or
  unattended operation in this first integration.
- Wall-approach, crowded-scene, stair, terrain, or obstacle-avoidance validation
  before an independent distance/collision veto exists.
