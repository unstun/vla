---
origin: ai+web
reviewed: false
date: 2026-09-26
---

# Newton macOS CPU policy qualification

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Task: `09-23-scan-reactive-stair-pedestrian`; stage: experiment + analysis.
Dr Sun selected Newton on 2026-09-26. The task's `NEWTON_LOCAL_PLAN.md` records
the predeclared scope, deadlines and acceptance. All runs below are local on
the Apple M5 MacBook Pro, 32 GB RAM, macOS 26.5.2, CPython 3.12.13.

## Result and scope

**Validated for this bounded flat-ground condition:** the official Go2 policy
example and a separate Lite3 `model_149999` port both execute real policy,
actuator and physics loops on the Mac. The Lite3 trial continuously stands,
walks forward, turns and stops for 12 physics seconds, with no resets.

| Evidence | Official Go2 | Local Lite3 port |
|---|---:|---:|
| Accepted run | `go2_video_v3` | `lite3_video_v2` |
| Solver inside Newton | MuJoCo-Warp on CPU | Native MuJoCo CPU |
| Actual physics duration | 8.000135 s | 12.000000 s |
| Policy / physics steps | 400 / 1600 | 600 / 12000 |
| Planar net displacement | 4.345 m | 2.675 m |
| Video | 200 frames, 8 s | 300 frames, 12 s |
| Loop wall time, including raw frame capture | 11.728 s | 18.630 s |
| Whole process wall time | 16.930 s | 24.729 s |
| Child peak RSS | 1,353,809,920 B | 1,359,413,248 B |

The Lite3 maximum tilt after the first second was 3.100 degrees; minimum base
height was 0.29846 m. Its final yaw was 61.71 degrees. Last-second average
planar speed after the zero command was 0.00511 m/s. All recorded policy/state
values were finite. Newton-to-native observation error stayed at or below
5.96e-8; applied torque matched requested torque at every one of 12000 steps.
These are measurements from one scripted trial, not a tracking benchmark.

Both videos are real Newton OpenGL framebuffer sequences, 2560x1440 H.264 at
25 FPS. The window requested 1280x720; macOS returned a Retina framebuffer.
Playback follows physics time. This is not a claim of real-time computation:
recording PNG frames slowed the loops to about 0.64-0.68 simulation seconds
per wall second. Neither Metal policy acceleration nor GPU training was tested.

Regular delivery files (not symlinks):

- `/Users/sun/tongbu/study/phdproject/vla/output/2026-09-26_newton_macos/lite3_newton_macos.mp4`
  SHA-256 `6cac753c01cbfd61be7cd62a82b808956fc3e58d6391857b3c427aa2b2e369d5`.
- `/Users/sun/tongbu/study/phdproject/vla/output/2026-09-26_newton_macos/go2_newton_macos.mp4`
  SHA-256 `4495e8ddf13df01c3dbb14a978ce4a29d1fd2eb3a1459615c3c49dd0dde68cf1`.

The earlier Isaac stair/person task remains **in progress**. This experiment
contains no SCAN curve, stairs, moving person, LiDAR/RTX sensor, VLA navigation,
training or real-robot result. The powered-off remote server was not contacted.
Next gate: a separately identified Newton scene and sensor-to-planner interface,
starting with controlled terrain and frozen planning inputs before any moving
stair/person trial. Do not transfer the archived Isaac acceptance label here.

## Source and controller identity

- [Newton repository](https://github.com/newton-physics/newton), release v1.6.0,
  commit `c2ca70bec5998062b0b2d35869865cbe3a49feee`. Source and Apache-2.0 license
  are retained under `source/`; `setup/source_ref.json` and
  `setup/SOURCE_MANIFEST.sha256.json` identify the archive and all 1150 files.
  All 746 installed Python sources match that snapshot; no upstream patch.
- [Newton assets](https://github.com/newton-physics/newton-assets), release-pinned
  commit `f8fb7abcbeba2318814a74f3eeb02780ad7925d6`. Go2 model, config and policy
  hashes are in `runs/go2_assets_v1/result.json`, verified again before v3.
  The policy SHA-256 is `c2047f8a1de062121b84f035e35837c69864d6ede2af3f111fdc7286c4769abe`.
  Asset-specific and policy licenses, plus the asset repository license, are
  also retained outside the runtime under `setup/licenses/`.
- Lite3 inputs are hash-checked copies of this VLA project's existing
  `2026-09-10_x_navdp_lite3_rented4090` experiment. `setup/lite3_inputs.json`
  records every reused file. No sibling working tree was imported or edited.
  Robot upstream: [DeepRoboticsLab/deep_robotics_model](https://github.com/DeepRoboticsLab/deep_robotics_model),
  commit `1f46ba1f86c72ddafd3d79e1e9725805c202bf2b`. The inherited manifest lists
  the earlier asset transformations; this experiment does not change that MJCF.
  The inherited robot-license field was absent; no new license claim is made.
- Existing machine-dog interface commit: `a2e98845a212bd6a2128af778cb1304eeb660f5f`.
  Lite3 ONNX SHA-256: `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.
  `policy/policy_manifest.yaml` preserves its training/export provenance.
  The 1000-frame golden trace passes with maximum error 0.00598145 against its
  recorded 0.01 limit; this does not establish a new training reproduction.

Installed runtime: Newton 1.6.0, Warp 1.17.0, MuJoCo/MuJoCo-Warp 3.12.0,
Warp-NN 0.3.1, ONNX Runtime 1.22.1, NumPy 2.5.3. The original Go2 environment
is frozen in `setup/requirements.lock`. `setup/requirements_lite3.lock` adds
the existing Lite3 adapter's ONNX Runtime with the original lock as constraints;
the six additions and unchanged Newton versions are recorded in install logs.

## Adapter changes

`scripts/record_go2.py` uses the unchanged official `Example`, replaces keyboard
input with a declared forward-command schedule, and records physical state,
actual clock, actuator force and frames. The upstream display counter advances
only 0.005 s per policy call although four physics steps advance 0.02 s.
Recording uses the measured solver clock, and logs both clocks.

`scripts/lite3_newton.py` reuses the unchanged reference `History`, constants and
quaternion routine from `references/lite3_reference/`. It preserves the 45-feature,
term-major ten-frame history, 12-joint order, PD gains 20/0.5, action scale 0.25,
velocity-dependent 24/36 Nm limits, 1 ms physics and 20 ms policy period.
It imports the pinned MJCF with a floating base, merges fixed feet, disables
self-collision and adds a friction-1.0 flat plane. This is a new simulator
condition. No contact threshold or learned policy was tuned.

The explicit solver is `SolverMuJoCo(use_mujoco_cpu=True, update_data_interval=0)`.
Public `reset(state)` then synchronizes the initial pose immediately; native
MuJoCo retains its own coordinates between steps and Newton exposes each result.
Newton hierarchical joint labels are matched by unique terminal name. Its
unnamed native direct actuators are matched by transmission joint ID, with
an asserted one-to-one order and actual force checks. Native MuJoCo coordinates
provide an independent check of the Newton world-angular/xyzw observation mapping.
The actual compiled physics model is retained as `newton_solver_model.mjb`.

The video command is fixed: 0-2 s stand, 2-6 s forward 0.5 m/s, 6-9 s forward
0.35 m/s plus yaw 0.4 rad/s, 9-12 s zero command. It does not involve a planner.

## Verification and preserved attempts

`validation/RESULTS.json` independently verifies process exits, raw frame hashes,
frame-to-telemetry time alignment, finite values, full video decode, delivery
hashes, source parity and free disk. `runs/contracts_v1/` passes six interface
regressions, including an asymmetric 90-degree yaw case, initial state sync,
motor transmission/limits, invalid inputs, bounded-run validation and golden policy.
All task-owned Python sources parse; no repository-specific linter/type checker
is configured for this experiment. Visual contact sheets are in `validation/`.

| Attempt | Outcome |
|---|---|
| `environment_v1`, `go2_assets_v1` | imports/device/source parity and pinned asset acquisition passed |
| `native_pendulum_v1` | upstream final-position assertion failed after the chosen 120 frames; retained, not resolved or relabeled |
| `native_go2_v1` | unchanged upstream CLI physics/policy and final test passed for 10 policy calls |
| `go2_video_v1` | sandbox could not see a macOS screen; no simulation video |
| `go2_video_v2` | 8 s simulation and video completed; report serialization failed on NumPy int64, exit 1 preserved |
| `go2_video_v3` | serialization fixed, lossless PNG capture, full qualification passed |
| `lite3_probe_v1` | rejected short-name assumption for hierarchical Newton joint labels |
| `lite3_probe_v2` | rejected named-actuator lookup; exported direct actuators are unnamed |
| `lite3_probe_v3` | pre-step observation check caught deferred initial native state sync |
| `lite3_probe_v4` | public reset with explicit interval 0; 2 s standing probe passed |
| `lite3_video_v1` | model export failed before motion: `mj_saveLastXML` cannot save an in-memory-compiled MjSpec |
| `lite3_video_v2` | actual MJB model export and full 12 s qualification passed |

The OpenUSD `ARCH_CACHE_LINE_SIZE` warning is retained in logs. Rendering needed
macOS display-service access outside the shell sandbox; runs remained hidden,
local, one environment, and bounded by the recorded 600 s process deadline.

## Run again and reconstruct

From the project root, with the installed isolated environment:

```bash
/Users/sun/.openviking-venv/bin/python3 \
  .pipeline/experiments/2026-09-26_newton_macos_policy/scripts/run_bounded.py \
  --run-id lite3_manual_01 --deadline 600 -- \
  /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python \
  /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_macos_policy/scripts/record_lite3.py
```

Use an unused run ID; existing runs are never overwritten. Run from a normal
macOS terminal or allow display access in an agent sandbox. The wrapper sets
all experiment caches and kills only its own process group on timeout.
`probe_lite3.py` and `test_contracts.py` use the same wrapper without display access.
Original official entry: `python -m newton.examples robot_policy --robot go2
--device cpu`; `run_upstream.py` only redirects the Warp cache into the experiment.

To reconstruct the environment, create `runtime/.venv` with Python 3.12.13 using
`uv venv --python /Users/sun/.openviking-venv/bin/python3`, then use
`uv pip sync --python runtime/.venv/bin/python --require-hashes --only-binary :all:
setup/requirements_lite3.lock` from this experiment directory, setting
`UV_CACHE_DIR` to this experiment's `runtime/uv-cache`. The lock includes exact
versions and accepted distribution hashes. Setup scripts/logs retain the
original commands, downloads and preflight. `prepare_assets.py`, through the
bounded wrapper, reacquires the release-pinned Go2 asset tree. `prepare_lite3.py`
verifies and copies the named existing VLA inputs; it does not search other repos.

## Local-only storage

Only `runtime/` and three named raw-frame directories are ignored by new rules:
`go2_video_v2/frames`, `go2_video_v3/frames`, `lite3_video_v2/frames` under `runs/`.
`setup/LOCAL_ONLY_BYTES.json` records absolute storage root, relative paths,
byte sizes, hashes and symlink targets. At the final inventory this totaled
4,463,201,573 logical bytes including duplicate hardlinks, with 20.90 GiB free.
The initial software acquisition stayed below its 5 GiB budget; raw video frames
are separate evidence. No local bytes were deleted.

Package and kernel caches can be regenerated from the lock and pinned source.
Assets are identified by pinned source and checked hashes. Raw frames are retained
locally with per-run SHA manifests; rerunning may reproduce behavior without
bit-identical graphics or timings. Do not delete those frames as if they were
ordinary caches. Code, source manifests, controller inputs, logs, telemetry,
results, final videos and failed-attempt records remain visible to Git.
No training, remote run, robot command, staging or commit was performed.
