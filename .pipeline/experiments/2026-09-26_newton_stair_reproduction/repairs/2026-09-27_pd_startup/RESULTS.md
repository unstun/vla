# Crouched PD startup: local result, 2026-09-27

Stage: experiment + analysis. The implemented preparation/stand sequence passes
its bounded flat tests, but the requested startup is incomplete: Dr Sun pointed
out that a separate return-to-zero step must precede standing. The prior claim
that the requested startup was complete is withdrawn. Static-obstacle navigation
and original Isaac stair A4 remain open. No remote execution, training, or
hardware actuation took place.

## Correction: missing return-to-zero step

The pinned official `main.cpp:47` calls `RobotStateInit()` before
`PreStandUp()` and `StandUp()`; its comment explicitly identifies joint return
to zero and control acquisition. The local adapter implemented the latter
preparation/stand stages and omitted that independent initialization step.
Calling preparation or policy Q0 "zeroing" was incorrect. Existing runs and
their physical measurements remain unchanged, but do not validate joint homing.
The SDK zero pose, its relationship to URDF joint coordinates, and whether
Dr Sun intends return to a calibrated zero or encoder-zero calibration must be
resolved before changing control targets. No all-zero URDF angle vector or
pose reset is justified by the current evidence.

## What changed

The explicit `--startup-mode pd_stand` mode begins with folded legs, settles
onto the ground for one second, uses PD preparation for one second, stands over
1.5 seconds, checks actual stability and blends into the existing ONNX policy.
`policy` remains the legacy default. The policy Q0, weights, saturation, physics
step, sensor geometry and SCAN/PCT/controller algorithms are unchanged.

The scalar interpolation is the unmodified compiled `MotionExample::CubicSpline`
from [official Lite3 SDK commit b30a3ec](https://github.com/DeepRoboticsLab/Lite3_MotionSDK/blob/b30a3ec09619e1dd0f3cfa6c49a50eb59670f141/src/motionexample.cpp).
Source/license/dependencies/original instructions and adaptations are recorded
in `references/upstream/2026-09-27_lite3_pd_startup/IMPORT.md` at the project root.
Local sequencing follows SDK preparation/stand durations and gains; final Q0,
initial damping, measured gate and policy handoff are explicit adaptations.

One physics state continues through all phases. The shared motor substep uses
the existing effort/speed limits and contact-capacity guard. PD phases perform
no policy inference. The H10 policy starts from its first measured standing
observation, then torque commands crossfade for 0.25 seconds.

The v1 applied-state contract needs a real policy observation. The host therefore
withholds applied readiness during PD while continuing body/cloud publication.
The startup driver additionally checks explicit phase/readiness fields and then
uses the original stillness gate. Navigation-height scoring starts after
readiness in this explicit mode; full-rate contact scoring remains continuous.

## Direct evidence

| Run | Outcome |
|---|---|
| `pd_startup_contract_v2` | 8 tests pass: SDK vs independent SciPy interpolation, boundary rejection, stability interruption, timeout/posture rejection, exact PD torque blend, invalid mode, driver readiness, and legacy physics parity |
| `pd_startup_existing_contracts_v1` | Existing six policy/history/motor interface checks retained; see its recorded result |
| `pd_startup_flat_v1` | 8,000 physical steps, all 11 declared startup checks pass; early positive velocity requests blocked |
| `pd_startup_bridge_v1` | Failed before physics: local Docker engine stopped. Logs retained |
| `pd_startup_bridge_v2` | 8,000 steps with real sensor/ROS bridge; 190 actual policy snapshots; original reader/copyback and four invalid-input negative controls pass |
| `pd_startup_human_live_v1` | Goal accepted at 7.35965 s, one short curve at 7.45964 s, 93 nonzero command updates; interrupted at about 10.14 s by a recorded Docker OOM |

The startup-only and bridge runs have exactly matching recorded joint states
and torques at all 400 control updates. Physics phases start at 0/1/2/3.5/4.2/
4.46 seconds: crouch, prepare, stand, settle, handoff, policy. Measured torso
height is about 0.05 m after passive settling and 0.294 m at the end. Policy
operation remains upright for more than 3 seconds after handoff. Applied torque
mapping error is zero; maximum observation mapping error is 1.12e-8.

Important physical limitation: the initial passive landing briefly exceeds a
MuJoCo soft knee limit by 0.010822 rad (0.620 degrees) at 0.113 s. This is retained
in `validation.json`, not silently clamped or hidden. Maximum joint speed is
5.596 rad/s; requested motor effort never exceeds the declared envelope
(peak ratio 0.252). Maximum 1 ms torque change during handoff is 0.914 Nm.
These measurements are not a hardware safety qualification.

The unchanged navigation stillness gate first holds continuously from 6.83969
to 7.35965 s. Startup does not remove that existing gate or establish faster
planning. The real goal-driver run confirms release after standing, but it is
not a successful avoidance run: the single curve ends near x=0.475 m; last
fully logged body x is 0.495 m and the goal is x=3.0 m. Docker emitted an `oom`
event, the backend exited with signal 9, and the final applied-state copyback
failed its exact acknowledgment match after an interrupted transfer. Preserve
all three facts. No later stop or arrival is verified. The OOM's allocation
source has not been diagnosed; do not infer it from the kill event alone.

## Video

`output/2026-09-27_newton_pd_startup/lite3_crouch_pd_stand.mp4` at the project
root is a regular file: 101 frames, 8.08 s, 1280x720 H.264, SHA-256
`1d4b7c92e308c53019d1d115bfe52bcd5372b0916c4f534587302c2dfb21ef4e`.
It renders actual recorded states from `pd_startup_flat_v1`, using
`pd_startup_video_v2`; no synthetic robot trajectory or physics rerun is used.
Frame hashes, complete video decode and visual inspection are recorded.
The eight-second movie is startup-only; it does not depict the failed human
navigation run. The earlier wider-camera render is retained as v1.

## Reconstruction and next gate

Use the existing Newton environment and bounded runner. Build the SDK scalar
adapter using `2026-09-26_newton_macos_policy/scripts/build_sdk_spline.py`, then
run `qualify_pd_startup.py` and `test_pd_startup.py`. All run requests contain
their exact absolute commands and source snapshots. Render with
`render_episode.py --source-run pd_startup_flat_v1` in a new run directory.
The selected native build remains `scan42_geometry_v9`, with
`geometry_smac_approach_flat.yaml` and the original 5 GiB container cap.

Raw frames are retained under two exact `.gitignore` paths. Per-file SHA-256,
size, storage location and provenance are in `setup/LOCAL_ONLY_BYTES.json`;
videos, state traces, logs, SDK source and review records remain visible.
The SDK binary belongs to the existing policy experiment's ignored runtime
and has a reproducible compiler/source/binary identity copied into this folder.

Next: diagnose the native run's memory allocation using recorded process and
upstream code evidence, then repeat the complete flat scene with explicit
startup. Separately continue the known short-curve/replanning issue. Do not
change occupancy, geometry, planning limits or resource budgets merely to turn
this interrupted result into a success. The source changes remain uncommitted
alongside the pre-existing experiment work; the parent task remains in progress.
