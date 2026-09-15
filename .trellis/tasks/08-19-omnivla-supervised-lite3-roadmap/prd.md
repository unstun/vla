# PRD: OmniVLA supervised Lite3 real-robot roadmap

## Research stage

Current stage: **planning**. Experiment and analysis may begin only after Dr Sun
reviews the final planning summary. Real-robot actuation remains a separate
explicit approval gate.

## Goal

Produce a human-auditable OmniVLA-on-Lite3 system in which:

1. evidence, rather than the model or an AI review, lets Dr Sun judge whether
   the deployed system actually uses vision, language, and action;
2. live Lite3-to-external-Jetson Wi-Fi latency is measured and decomposed;
3. the Retroid handheld can take priority over VLA and can stop the downstream
   motion command path independently of VLA inference;
4. a pinned, previously validated Lite3 locomotion policy remains the only
   low-level controller; and
5. OmniVLA trajectories pass progressively stronger offline, shadow-mode, and
   supervised real-robot checks before autonomous motion is considered.

## Confirmed facts

- The strongest current Lite3 result is a single-frame, language-only,
  receive-only round trip through pinned OmniVLA-original. It returned a finite
  `8 x 4` trajectory but had no actuation path. One observation measured
  456.746 ms model inference and 5,029.914 ms Lite3-side end-to-end time. This
  is not a benchmark and the trajectory scale is not calibrated for Lite3
  (`.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/README.md`).
- OmniVLA-edge completed one CUDA forward on the Jetson AGX Orin 64GB using an
  archived real Lite3 frame. The forward took 5.028 s and the one-shot process
  took 23.199 s including imports/model loading/artifact work. It did not use a
  live robot-to-Jetson request and therefore does not answer the Wi-Fi latency
  question
  (`.pipeline/experiments/2026-08-19_omnivla_edge_orin64/README.md`).
- The local repository contains a Retroid `controlapp.apk` and the matching
  open-source UDP receiver on port 12121. Two APK byte variants exist, so the
  exact package identity, signature, ABI compatibility, and installed version
  must be recorded before selecting one
  (`../machine-dog/2_experiment/deployment/lite3_rl_deploy_v0/third_party/gamepad/`).
- The existing Lite3 locomotion deployment supports Retroid input, signal-safe
  shutdown, joint damping, and a 100 ms stale robot-state watchdog. Its README
  also says the physical Retroid must remain off while the web console drives,
  because full stick deflection reaches the training envelope. It therefore
  does not yet satisfy simultaneous VLA operation plus immediate handheld
  takeover
  (`../machine-dog/2_experiment/deployment/lite3_rl_deploy_v1a.1/README.md`).
- Dr Sun confirmed on 2026-08-19 that the requested low-level policy is the
  pinned V12 `model_149999` deployment, which already has checkpoint, ONNX,
  configuration, parity evidence, and hashes
  (`../machine-dog/2_experiment/deployment/lite3_rl_deploy_v1a.1/policy/model_149999/policy_manifest.yaml`).
- Upstream issue evidence already raises prompt-sensitivity, trajectory-scale,
  and velocity-clipping concerns. Current successful forwards do not resolve
  those concerns
  (`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`).

## Requirements

### R1. Human-review evidence before a VLA claim

- Produce a raw evidence pack, not a yes/no AI verdict.
- Trace camera and language inputs through the pinned source to the returned
  trajectory/action representation.
- Run counterfactual cases: same image with materially different instructions,
  and different images with the same instruction.
- Preserve raw inputs, outputs, hashes, timings, and visual overlays.
- Dr Sun decides whether the evidence justifies calling the result a working
  VLA. Until then, the project label remains a bounded OmniVLA reproduction or
  integration claim.

### R2. Live external-Jetson latency characterization

- Measure the actual Lite3 camera -> Wi-Fi -> resident Jetson service -> result
  path without motor commands.
- Separate capture/decode, encode, upload, queue, model forward, response, and
  total age-at-consumption.
- Report repeated distributions (`p50`, `p95`, maximum, failures), not one
  favorable sample.
- Measure Wi-Fi round-trip time, jitter, packet loss, and behavior under dropped
  or stale requests.
- Use results to choose among Jetson-edge, remote-original, model optimization,
  or rejection of closed-loop use. Do not preselect an architecture by name.

### R3. Handheld installation and control authority

- Select, hash, install, and document the compatible Retroid APK only after the
  exact device and APK identities are checked.
- The handheld must remain usable while VLA is enabled.
- Handheld takeover and stop have higher priority than all VLA commands.
- A stop must invalidate the last VLA command and stop the downstream command
  flow; merely terminating model inference is insufficient.
- Loss of handheld/VLA heartbeats, stale commands, malformed commands, or
  process failure must fail closed according to a reviewed state machine.
- Stop is latched until a deliberate manual re-arm; VLA cannot re-enable itself.

### R4. Pinned low-level locomotion boundary

- The VLA must not output joint targets or replace the locomotion policy.
- Pin the selected locomotion checkpoint/export/configuration/interface by
  SHA-256 and source commit.
- Validate the locomotion controller independently before accepting VLA input.
- Convert only reviewed, sanitized local trajectories into bounded body
  commands for the selected policy.

### R5. Trajectory reliability and collision safety

- Keep OmniVLA output as a trajectory for inspection and collision checking.
- Calibrate coordinate frame, camera intrinsics/extrinsics, scale, timing, and
  Lite3 footprint before interpreting the path metrically.
- Reject non-finite, stale, discontinuous, over-curved, out-of-envelope, or
  obstacle-intersecting trajectories.
- Evaluate instruction compliance, collision-free rate, progress, smoothness,
  intervention demand, and stop behavior on recorded scenes before motion.
- VLA is not the sole obstacle-avoidance or emergency-stop layer.

### R6. Staged human gates

- Execute strictly in this order: evidence audit -> latency -> handheld/safety
  arbitration -> locomotion pin -> offline trajectory validation -> stationary
  shadow mode -> supervised motion.
- Each stage produces a review packet and stops for Dr Sun's decision.
- No stage inherits a stronger claim than its direct test supports.
- Any real-robot actuation requires a fresh explicit command from Dr Sun after
  the immediately preceding safety packet is reviewed.

### R7. Source-of-truth boundary

- `/Users/sun/tongbu/study/phdproject/vla` is the only source of truth for this
  integration.
- `machine-dog` and `machine-dog-nav` remain read-only references until exact
  commits/interfaces are deliberately pinned and imported or a separate task
  authorizes edits there.
- Jetson and robot directories are execution copies. All final changes and
  retained evidence must return to the same local project paths.

## Acceptance criteria

- [ ] AC1: Dr Sun receives an OmniVLA evidence pack containing code trace,
      counterfactual inputs/outputs, raw artifacts, hashes, and an explicit
      claim matrix, then records a human decision.
- [ ] AC2: A receive-only live Wi-Fi benchmark reports stage timings, `p50`,
      `p95`, maximum, failure rate, jitter, packet loss, and stale-result rate
      for a resident Jetson service.
- [ ] AC3: The selected APK identity, signature/version evidence, install
      result, and UDP packet reception are recorded without autonomous motion.
- [ ] AC4: A tested arbitration table proves that handheld stop/takeover wins
      over VLA for normal, delayed, stale, malformed, disconnected, and crashed
      VLA cases; stop remains latched until manual re-arm.
- [ ] AC5: The exact locomotion checkpoint/export/config/source identities and
      standalone safety evidence are pinned, with the VLA-to-body-command
      interface reviewed separately.
- [ ] AC6: Offline and simulated/replayed trajectory tests report declared
      reliability metrics and preserve failures instead of filtering them out.
- [ ] AC7: A stationary live shadow-mode run records what the VLA would have
      commanded while sending no command to the robot.
- [ ] AC8: A supervised motion protocol exists with speed/distance/time bounds,
      cleared test area, observer roles, handheld takeover, independent stop,
      rollback, and explicit Dr Sun go-ahead.
- [ ] AC9: Every stage has a review packet, claim boundary, local evidence,
      source hash, remote sync proof, and an explicit proceed/stop decision.

## Out of scope for this roadmap's initial pass

- Training or fine-tuning OmniVLA.
- Direct VLA-to-joint control.
- Treating the published 0.1 m waypoint spacing as Lite3-calibrated.
- Unsupervised or high-speed real-robot operation.
- Forest deployment before indoor/controlled-path gates pass.
- Replacing the handheld or native emergency-stop mechanism with a network-only
  stop button.

## Key decisions

- Low-level locomotion identity: V12 `model_149999`, confirmed by Dr Sun on
  2026-08-19.
- First implementation child: the receive-only OmniVLA evidence audit. It must
  be completed and reviewed before the latency or control children start.
