# TIC-VLA DynaNav single-scene smoke on RTX 5070 Ti

## Request and authorization

Dr Sun approved the proposed first official Nova Carter simulation trial on
2026-09-08: "可以，先试试吧". This authorizes necessary environment preparation
and bounded pretrained inference for this trial. It does not request training,
Spot/Lite3 integration, real-robot operation, or other scenes.

## Requirements

- Use the existing pinned TIC-VLA source and released checkpoint.
- Execute one hospital Nova Carter episode from the official example on
  `gpu5070ti`, preserving the instruction, seed, crowd count and goal threshold.
- Preserve existing processes and global software; dependencies and edits belong
  to an isolated task directory.
- The local VLA repository owns source, configuration, modifications and evidence.
- Retain actual visual evidence, raw logs, checkpoint identity, result or explicit
  failure, model/control timings, and GPU/system memory observations.

## Acceptance

- Host identity and available runtime/resources are directly checked.
- The scene renders and TIC-VLA loads the expected checkpoint strictly.
- At least one finite model trajectory is consumed by the simulated robot's
  controller, with corresponding observable simulated motion and new observations.
- The bounded episode produces its result JSON or a clearly documented runtime
  failure/timeout. Navigation success is reported independently from loop execution.
- Source/configuration and declared evidence return locally with SHA-256 checks;
  no task-owned process remains after the trial.

A dependency/import check, static scene, offline forward or missing video cannot
be reported as a passing closed-loop smoke. An incomplete run must retain its
failure evidence and accurately identify the unfinished acceptance item.

## Approved interactive extension (2026-09-08)

Dr Sun accepted the proposed push-to-talk hospital demonstration with "可以".
Extend this task with a local Chinese interface showing recognized text, the
current planned trajectory and the driven path over live third-person images.
Support the demonstrated vending-machine goal, stop and resume. Preserve the
original smoke and explicitly reject unsupported Chinese goals. Voice recognition
is an added CPU frontend, not a native TIC-VLA capability.

Acceptance: test actual audio recognition, command delivery, stop/resume and
trajectory projection; run bounded simulator validation with local video/logs
and matching source/artifact hashes. Retain a usable local launch interface.
Distinguish synthetic-audio validation from a human microphone test, and show
disconnected/stale frames rather than labeling a replay as live.

## Superseding user direction (2026-09-08)

Dr Sun explicitly removed the website and real-time requirement: "不用实时，也
不用网站，我本地说话吗，然后视频给我" and "不然太卡了吧". The deliverable is
now a local microphone/recorded-audio entrypoint, CPU transcription, one bounded
remote simulation and a local video file containing the trajectory overlay.
Stop the UI, browser test sessions and forwarding services. The online prototype
is retained only as an uncompleted exploratory artifact, not the final interface.
An actual human recording remains user input; synthetic clips must be labeled.

## Top-down video request

Dr Sun requested a top-down video. Record a new bounded episode with a fixed
overhead scene camera and the existing planned/driven path annotations. Preserve
the previous recording, model-facing camera and offline delivery. Verify actual
scene visibility, projection, video decoding and local artifact hashes.

## Direct Chinese instruction

Dr Sun requested "那直接用中文输入呗". Pass "走到自动售货机前" directly to the
navigation checkpoint and record one bounded overhead episode. Remove the
English substitution from the current local speech/text entrypoint. Preserve
original text through the request, per-run scenario, behavior and model audit.
The hospital goal scope remains unchanged. Report the observed outcome without
promoting one successful Chinese trial to general multilingual validation.

## Semantically matched Chinese/English pair

Dr Sun accepted the proposed matched-language comparison after the visibility
audit. Run one Chinese episode with "直走，并在自动售货机前停下" and one English
episode with the original full instruction. Keep scene, start, goal, crowd count,
recording camera and limits the same. Fix and record the same inference RNG seed
for both. Verify actual prompts, configuration equality except instruction,
initial image evidence and local video/artifact integrity. This is one exploratory
pair, not a statistical language comparison. Do not alter distance or occlusion
in this first pair; those are subsequent independent controls if needed.

## Frozen-input diagnosis

Dr Sun approved offline replay after discussing end-to-end diagnosis. Freeze the
initial image, history, robot state, delay and RNG seed, vary instruction language,
and compare raw model trajectories and the existing controller's desired command.
Repeat identical inputs, cross the two recorded initial images with both languages,
and replay exchanged semantic caches while holding action-head inputs fixed.
Retain original source, all outcomes and exact local/remote identities. Acceptance
is a repeatable diagnostic with explicit causal limits, not a navigation fix.

## Native metric-distance stop test

Dr Sun requested execution of the proposed Chinese instruction test: "向前直走
3 米，然后停下". Run one bounded hospital episode in an isolated copy, retain a
top-down video with measured displacement and speed, and determine whether the
model/controller stops near the commanded distance. Do not force a stop at 3 m
or count timeout/goal-threshold termination as learned stopping. Preserve the
existing vending-machine demo and all prior evidence.

## Matched metric-language pair

Dr Sun requested a Chinese/English comparison of this model. Execute a fresh
pair of the same three-meter stop task under one source manifest: Chinese
`向前直走 3 米，然后停下`; English `Go straight forward for 3 meters, then stop.`.
Use identical non-language configuration, checkpoint, seed and stopping criteria.
Preserve raw evidence and individual videos, and deliver a synchronized comparison
video. Report directional progress separately from metric-stop success; this
single pair is exploratory, not a general multilingual capability estimate.
