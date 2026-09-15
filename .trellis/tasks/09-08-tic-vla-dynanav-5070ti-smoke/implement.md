# Execution checklist

- [x] Read source, prior evidence, project constraints and applicable guidelines.
- [x] Check current host resources and authorize scope from the user's approval.
- [x] Identify a usable Isaac Sim runtime and verify imports/GPU compatibility.
- [x] Prepare task-owned dependency environment and pinned model assets.
- [x] Prepare a one-episode config and minimal visual/timing instrumentation.
- [x] Verify local/remote source, config and checkpoint identities.
- [x] Run the bounded hospital episode; inspect logs and actual rendered frames.
- [x] Apply necessary bounded compatibility fixes locally and rerun only as needed.
- [x] Retrieve result JSON, video, raw logs and resource/time evidence.
- [x] Verify local evidence hashes, review owned changes, and report exact outcome.

Checks: syntax/patch applicability for changed wrappers; runtime import checks;
strict checkpoint loading; finite trajectory/controller evidence; actual rendered
motion; episode result; task process cleanup; artifact SHA-256 equality. No model
training or broader benchmark is part of this work.

## Interactive extension

- [ ] Pin CPU speech runtime/assets and implement bounded audio decoding.
- [ ] Implement command/state contract, camera projection and simulator bridge.
- [ ] Build push-to-talk UI, live images/status and bounded start entrypoint.
- [ ] Test parsing, stop latching, stale state, projection and actual Mandarin ASR.
- [ ] Verify remote source hashes and run a bounded interactive hospital trial.
- [ ] Inspect browser, rendered trajectories, stop/resume traces and video.
- [ ] Sync evidence back, verify hashes and publish concrete launch instructions.

## Superseding offline voice-to-video delivery

The interactive checklist above was cancelled by the user's later direction;
its partial prototype and failed browser/transport checks remain documented.

- [x] Stop the task-owned website, test browsers and SSH video forwarding.
- [x] Implement a local six-second microphone / existing-audio entrypoint.
- [x] Validate real CPU recognition of explicitly synthetic Chinese test clips.
- [x] Implement detached bounded inference with no HTTP listener or live stream.
- [x] Add video packaging, raw-frame archive and local SHA-256 verification.
- [x] Validate the entire offline synthetic-audio-to-video path on 5070Ti.
- [x] Inspect the delivered video and report the human microphone test boundary.


## Top-down video follow-up

- [x] Add a selectable fixed output camera and forward the view through the batch chain.
- [x] Preserve model-facing camera, scene dynamics and previous artifacts.
- [x] Run a bounded top-down episode and retrieve its video and raw-frame archive.
- [x] Validate fixed projection, rendered scene visibility, video decoding and 243 hashes.


## Direct Chinese instruction trial

- [x] Replace fixed English substitution with validated verbatim goal text.
- [x] Add direct text input and transfer the runtime request as UTF-8 JSON.
- [x] Create a per-run scenario and audit the actual instruction at every model call.
- [x] Test Unicode preservation, missing-request failure and existing command semantics.
- [x] Complete one bounded top-down Chinese run and inspect its actual outcome (navigation failed).
- [x] Verify all local artifacts and report language capability separately from navigation success.

## Semantically matched Chinese/English pair

- [x] Predeclare full Chinese/English text, scene conditions, run order and seeds.
- [x] Preserve full Chinese wording and add validated optional inference seeding.
- [x] Test the updated request/command contract and freeze the shared source manifest.
- [x] Execute both fresh processes sequentially and retain both outcomes.
- [x] Verify matching non-language configuration, actual prompts/seeds and initial RGB evidence.
- [x] Decode/inspect both videos and verify local archived frames and result comparison.

## Frozen-input diagnosis

- [x] Freeze recorded fixtures, hypotheses, probe order and source identities.
- [x] Verify source-derived controller commands against prior runtime logs.
- [x] Run the bounded real-model replays and fixed-input cache interventions.
- [x] Verify repeats, input equality and local artifact hashes; inspect trajectories.
- [x] Record supported findings and unresolved root-cause/navigation-fix boundaries.

## Metric-distance stop probe

- [x] Pin an isolated source snapshot, request and predeclared acceptance criteria.
- [x] Add observation-only distance/speed logging and remove external stop/recovery confounds.
- [x] Test exact command propagation, rotated-frame distance and false-stop rejection.
- [x] Execute a bounded top-down simulation; retain the child-crashed first attempt and completed retry.
- [x] Retrieve video/logs, assess stopping failure and verify local artifact hashes.

## Matched metric-language pair

- [x] Freeze one shared source package, exact prompts, order and metric criteria.
- [x] Verify both requests, unchanged policy/controller and current execution assets.
- [x] Run both bounded episodes sequentially and retrieve complete evidence.
- [x] Compare actual inputs, time-aligned trajectories and stop measurements.
- [x] Decode/inspect both videos and the comparison video, verify hashes and record limits.
