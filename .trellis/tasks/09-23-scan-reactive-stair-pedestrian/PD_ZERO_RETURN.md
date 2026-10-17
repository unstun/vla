# Correct the missing Lite3 return-to-zero step

## Original-library Newton test, 2026-09-27

The unchanged factory library now drives a continuous 12,000-step local
episode through zero-return torque, preparation and standing. Actual-state
video: `output/2026-09-27_lite3_factory_test/lite3_factory_zero_stand_test.mp4`.
Report: `.pipeline/experiments/2026-09-27_lite3_factory_runtime_audit/SIMULATION_RESULT.md`.
This is an algorithm integration result, not validated factory calibration.
The current test supplies ideal absolute encoders; the factory caller's HipY
zero reference (-3.49 rad) lies outside the current URDF limit (-2.67 rad).
Largest displacement is 0.12448 m and the standing window also exceeds the
unchanged 0.10 m criterion. The next gate is a qualified mechanical/encoder
mapping, then the same bounded in-place trial. No physical actuation occurred.

## Factory runtime obtained, 2026-09-27

Dr Sun authorized SSH to the powered-on Lite3. Read-only inspection retrieved
the startup-selected executable/control-library candidate and its dependencies.
An isolated local ARM64 Linux test loaded the unchanged control library and
resolved `MotionInitial` and `Motion`. It did not invoke these functions or
start any robot service. See
`.pipeline/experiments/2026-09-27_lite3_factory_runtime_audit/RESULTS.md`.

The missing-program dependency is now resolved for this audit. Next verify the
ABI, coordinate/time conventions, initialization arguments and zeroing semantics
before a bounded local algorithm test and Newton adapter. Live root-process
library mappings remain unreadable with current permissions. Strict factory
homing remains unvalidated; public-source negative findings below remain
historical context, not the current acquisition blocker.

## Confirmed requirement, 2026-09-27

Dr Sun explicitly requires strict reproduction of the factory homing movement
and instructed further GitHub research. The earlier choice between this and
an approximate simulator return-to-pose is resolved in favor of strict factory
homing. Do not ask that question again or substitute crouch/stand interpolation.

Expanded audit:
`.pipeline/survey/2026-09-27_lite3_factory_homing_upstream_survey.md`.
The official `add_python` branch publishes `src/sender.cpp`, confirming only
command `0x31010C05`, a seven-second wait and SDK control acquisition. Official
main history and public fork/branch inventories plus targeted community source
inspection did not yield a qualified robot-side implementation or synchronized
factory homing trace. No controller changes or new simulation runs were made.
The next dependency is that source/data contract, not another posture choice.

## Initial audit scope

Stage: experiment + analysis, 2026-09-27. Dr Sun rejected the preparation/stand
video as missing prior zero return and authorized verification followed by a
correction. The previous `pd_stand` runs are preparation/stand evidence only.

## Scope before further changes

The behavior gap is the separate `RobotStateInit()` call in official
Lite3_MotionSDK `main.cpp:47`, omitted by the current adapter. Establish what
that call requests, what physical zero/reference it establishes, and how that
maps to the original sensor-rig URDF. Do not equate policy Q0, preparation pose,
encoder-zero calibration and an all-zero joint-coordinate vector.

Read-only source inspection first. Pin selected SDK headers and its published
x86 library under `references/upstream/2026-09-27_lite3_zeroing/`; repository
https://github.com/DeepRoboticsLab/Lite3_MotionSDK, main commit
`b30a3ec09619e1dd0f3cfa6c49a50eb59670f141`, MIT. Inspect the library statically;
do not execute its hardware sender. The original SDK dependencies and commands
are retained in the prior pinned startup import. Record file hashes and tools.
Also inspect official Lite3_rl_deploy main
`1c4a8f14c9c531903fa5a26783e3f9b99d1039d9` (BSD-3-Clause) for the simulator and
physical-robot initialization contract. It is a reference, not a policy switch.

The intended eventual owner is the existing startup controller. A zero-return
phase must have a source-backed target/coordinate definition, actual measured
completion and a refusal path before preparation/standing. Keep one physical
state and preserve legacy replay conditions. No robot actuation, remote work,
memory-budget changes or planner work belong to this correction.

Expected artifacts initially: exact upstream bytes, static inspection output,
coordinate comparison and source-backed decision. Controller, tests and video
may change only after the zero-return contract is established; an unavailable
firmware definition must be reported rather than invented.
