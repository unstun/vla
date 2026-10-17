---
origin: github-primary-source-survey
reviewed: false
date: 2026-09-27
stage: experiment-and-analysis
status: surveyed-no-qualified-factory-homing-implementation
---

# Lite3 factory homing: expanded public-source audit

## Decision and result

Dr Sun explicitly selected strict reproduction of the factory homing movement.
Ordinary return to a crouch pose, stand-up interpolation, damping, an all-zero
URDF target, and a visually similar animation do not meet this requirement.
This supersedes the earlier request to choose between factory homing and a
separately named simulator posture-return approximation.

No inspected candidate supplies a qualified factory homing controller or a
synchronized twelve-joint factory homing trace. The expanded audit did find
the official sender implementation in the SDK's `add_python` branch. It
confirms the previous static-library finding directly in published source:
send a high-level command, wait seven seconds, then acquire SDK control.
It does not define the physical joint movement.

This is a bounded negative search result, not proof that nobody has published
such a controller. No new controller, physics run, video, or hardware command
was produced. The earlier preparation/stand results retain their narrower
meaning; factory homing remains incomplete.

## Selection criteria

A candidate must provide either:

1. An identifiable Lite3 factory homing implementation, including the joint
   coordinate convention, phase transitions, control law and completion or
   failure conditions; or
2. A trace explicitly recorded during factory homing, including firmware and
   robot identity, a synchronized trigger/status timeline and all twelve joint
   positions over the entire motion. Commands, velocities, torques/current and
   encoder-offset changes are needed to distinguish behavioral replay from
   reproduction of the calibration algorithm itself.

A client command constant, a function named `RobotStateInit`, or an unsynchronized
video does not establish either contract. A measured motion replay alone must
not be promoted to replication of the hidden encoder-calibration algorithm.

## Search coverage

Evidence directory: `2026-09-27_lite3_factory_homing_sources/` beside this report.

- Official MotionSDK: both public branches, all 44 commits reachable from the
  pinned `main`, and the empty public tag list were enumerated. All 42 distinct
  historical trees were retrieved without truncation. Excluding bundled Eigen,
  images, URDF assets and build debris, the source inventory contains 15 unique
  C/C++ source/header blobs across 11 paths. Their contents were retained and
  reviewed for the initialization call chain. The source inventory never
  contains a robot-side homing handler. Historical library binaries were not
  all reverse engineered; the earlier audit covers the current ARM/x86 pair.
- All 17 public forks and their 23 public branches were enumerated. Eight
  distinct branch heads outside official main history were examined through
  complete recursive trees and targeted source inspection. This is not an
  assertion that every line of every fork was reviewed. The user's own
  `unstun` fork/repository is not independent community evidence.
- Exact-symbol GitHub searches included `AllJointBackZero`, `31010c05`,
  `zero_position_flag`, `jy_exe`, `jy_sdk_ml` and scoped zero/homing searches.
  Chinese and English web searches supplied additional candidates. Broad
  substring matches for SQLite, printer boards, camera calibration and XGO
  robots were excluded. Search snapshots are discovery records, not proof.
- Additional source chains included official Lite3_VMC, sdk_deploy, Lite3_ROS,
  TopHillRobotics/quadruped-robot, Lite3_Model_Control, lite3-ros-sim, Lite3 API
  wrappers and navigation plugins. A research subagent inspected the listed
  community/ROS seams; the main agent inspected the official history, forks,
  simulator initialization and logger timing.

## Primary findings

### Official Python branch exposes the sender source

Repository: https://github.com/DeepRoboticsLab/Lite3_MotionSDK

Branch `add_python`, commit `e4d75a4ba10662b7349f10cadd2c40feea676bf7`, MIT.
[`src/sender.cpp:75-86`](https://github.com/DeepRoboticsLab/Lite3_MotionSDK/blob/e4d75a4ba10662b7349f10cadd2c40feea676bf7/src/sender.cpp#L75-L86)
defines both functions:

- `AllJointBackZero`: `Command(0x31010C05, 0, 0)` then `CmdDone`.
- `RobotStateInit`: the same command, `usleep(1000*1000*7)`, then command
  `0x0114` twice.

There is no joint target array or completion-status polling in these functions.
Seven seconds is a client wait, not a measured action duration. The older
`lhk6666/add_python` head `9ff0c5f81148ce6e1759c84dd890383c172ee86e` contains
the same sender blob. Original SDK build/run instructions are retained in the
downloaded README and previous pinned SDK import. They require a supported
Linux development host and real motion host; running them does not supply a
Newton implementation and was not attempted.

### A simulated function with the same name only applies damping

Repository: https://github.com/Airbotix-Technology-Pvt-Ltd/Lite3_MotionSDK

Branch `custom-gait`, commit `fae92e418c06c132cca1c82c369a579d444c92f8`, MIT.
[`include/sim_sender.h:69-84`](https://github.com/Airbotix-Technology-Pvt-Ltd/Lite3_MotionSDK/blob/fae92e418c06c132cca1c82c369a579d444c92f8/include/sim_sender.h#L69-L84)
sets position, velocity and feedforward torque to zero, but also sets **kp=0**
and kd=1, then publishes 20 times. Under the joint PD contract this applies
velocity damping, not active position return. The source comment saying zero
all joints is not an implementation of factory homing. It uses ROS2/drdds
simulation messages; there is no inspected factory trace or equivalence test.

### A data logger starts using observations after the homing call

Repository: https://github.com/openverse-orca/Lite3_MotionSDK

Branch `main`, commit `7a106cf782320211a44fe61c02e14af0922c0ffc`, MIT.
[`main.cpp`](https://github.com/openverse-orca/Lite3_MotionSDK/blob/7a106cf782320211a44fe61c02e14af0922c0ffc/main.cpp)
constructs a logger before `RobotStateInit` at line 177, but enters the main
loop only after that blocking call returns. Observation/action writes occur
inside the later policy loop. Merely constructing the logger beforehand does
not record homing. The inspected complete main/2real branch trees contain no
CSV or log artifact that establishes a homing trace. Original usage is a
Linux SDK plus gRPC policy deployment, not a factory calibration simulation.

### The official VMC simulator skips the internal motion too

Repository: https://github.com/DeepRoboticsLab/Lite3_VMC

Commit `724aa54dee0cc374bd5417c86d649fb08d4d309a`; no repository-wide license
declared in metadata. The vendored SDK has a local MIT license, and the
inspected stand-up FSM has an MIT header; that does not license every path.

`src/lite3_basic_sim_pkg/lite3_motion_sdk/src/send_to_robot.cpp` uses the same
high-level command/wait pattern. The simulator's
[`gazebo_sim_and_real.cpp`](https://github.com/DeepRoboticsLab/Lite3_VMC/blob/724aa54dee0cc374bd5417c86d649fb08d4d309a/src/lite3_basic_sim_pkg/lite3_motion_sim/src/gazebo_sim_and_real.cpp)
calls the sender before ROS initialization, then controls Gazebo joints using
`PreStandUp` and `StandUp`. It supplies no simulation-side handler for the
factory homing command. Its ROS/Gazebo standing example and the separate
stand-up FSM are not factory calibration reproduction.

### Community wrappers also delegate to the motion host

| Repository / pinned commit | Inspected entry point | Evidence boundary |
|---|---|---|
| [havarduia/lite3_api](https://github.com/havarduia/lite3_api/tree/a87f9b14acbcf02f42bfa01adfd1dd3adce99295) `a87f9b14` | `robot/lite3.py`, `protocol.py`, archived `try_stand.py` and `check_state.py` | `zero()` sends `0x31010C05`. The archived experiment watches high-level state, not synchronized joint trajectories. Its explanatory hypothesis is not an observed result. No root license declared. |
| [dimitarbez/lite3-ros-sim](https://github.com/dimitarbez/lite3-ros-sim/tree/a3fee6db1ed5e133db1bc83a86cead4c7d7f37a9) `a3fee6db` | `lite3-noetic/hardware-ws/tools/run_motion_sdk_neutral_breathing.cpp:619` | Calls `RobotStateInit`, then obtains initial angles. Stand/breathing targets are subsequent motion. The hardware-control document corroborates command semantics, not a homing trajectory. License not established for reuse. |
| [TopHillRobotics/quadruped-robot](https://github.com/TopHillRobotics/quadruped-robot/tree/4b648d32d1cc2f5ead36bce0c178e9a5f9eaae23) `4b648d32` | `quadruped/extern/deeprobotics_legged_sdk/src/send_to_robot.cpp` | Same command/wait wrapper; inspected robot call site is Lite2. No Lite3 factory movement definition. |
| [shanchaicn/Lite3_Model_Control](https://github.com/shanchaicn/Lite3_Model_Control/tree/10f01daf90f39e979646d0603bbee236663c4d06) `10f01daf` | `high_level_sim/src/lite3_basic_sim_pkg/lite3_motion_sdk/src/send_to_robot.cpp` | Same wrapper in a ROS/Gazebo model-control package. Related FullySNNforLeggedRobots and XTERY11 copies do not add a motion-host handler. |
| [DeepRoboticsLab/sdk_deploy](https://github.com/DeepRoboticsLab/sdk_deploy/tree/79e7c6ecba78b7f65d056164c3a97883909af3f1) `79e7c6ec` | `src/lite3_transfer/interface/robot/udp_interface.hpp` | Calls SDK `RobotStateInit`; service launches that transfer executable. Uses the vendor SDK library, ROS2 Foxy, C++17/Eigen/drdds. Service README declares BSD-3-Clause. |
| [DeepRoboticsLab/Lite3_ROS](https://github.com/DeepRoboticsLab/Lite3_ROS/tree/e4ab5dc1c7f3ff46274162a1ef302253936578aa) `e4ab5dc1` | `src/transfer/include/protocol.hpp`, `Jetson2Motion.cpp` | `zero_position_flag` is a received status field. The bridge does not define the robot's homing controller. |
| [automatika-robotics/emos-plugin-lite3](https://github.com/automatika-robotics/emos-plugin-lite3/tree/a2bfa4fc5d5b2f991aebe00e588cb2fef8346de4) `a2bfa4fc` | `lite3_plugin/protocol.py`, `plugin.py:741` | `STAND_ZERO=0x21010C05` is a simple UDP action. Sending success is not execution confirmation. EMOS/Sugarcoat bridge; no root license declared in metadata. |
| [syswonder/primitive-deep_robotics-lite3_quadruped](https://github.com/syswonder/primitive-deep_robotics-lite3_quadruped/tree/aa63c872affe5fd1b7d3d0a402266eaaf98ee884) `aa63c872` | `lite3_quadruped/main.py` | Sends `zero=[0x21010C05,0,0]`. A servo-angle-table comment does not match an actual angle table. Parent robot deployment `6ee45d737e061eecb5e82d08b2ec9d5c32acb6f9` depends on floating main; no root license declared. |
| [laojiahuo2003/lite3_sdk](https://github.com/laojiahuo2003/lite3_sdk/tree/cea5a5593cceea21501222644551d7b8ffadb93f) `cea5a559` | `client.py:222`, `commands/state.py`, `command_codes.py` | Python `zeroing()` sends a `ZeroingCommand`, code `0x21010C05`; received state 17 is a label. No joint motion definition; no root license declared. |

The high-level wrappers use `0x21010C05`, whereas the MotionSDK initialization
uses `0x31010C05`. This audit does not prove their robot-side behavior identical.
No wrapper was selected for control implementation or executed against hardware.
For non-selected candidates, original run instructions remain at their pinned
README URLs; they were not qualified as reproducible homing demonstrations.

## A useful existing capture tool, with limits

[armwaheed/mappo-arm-cloud-physical-ai](https://github.com/armwaheed/mappo-arm-cloud-physical-ai/blob/69d26423325c0bd8562bad7a05c6e1379efdf003/robot-stack/deep_robotics/lite3/commissioning/lite3_state_probe.py),
commit `69d26423325c0bd8562bad7a05c6e1379efdf003`, Apache-2.0, contains a
Python receive-only decoder for Lite3 high-level, joint, handle and IMU frames.
Its stated capture purpose is commissioning while an operator uses the vendor
controller. This is a possible upstream component for future observation;
the inspected file itself is not a recorded factory homing episode and its
parsers have not been tested here. Do not reimplement a receiver unnecessarily
if capture later becomes the approved route.

## What is required next

The missing input is specific: a versioned motion-host homing definition, or
a complete, synchronized factory homing recording from a compatible Lite3.
Prefer manufacturer source/configuration when available. A trace must include
before-trigger data, every phase, the completion state and the transition to
preparation. A record that starts after `RobotStateInit()` cannot fill the gap.

Once such input exists, first establish the encoder-to-URDF coordinate mapping
and source-derived acceptance tolerances. Then reproduce homing under one
continuous Newton physical state, check the measured completion gate, append
the existing preparation/stand sequence and record the verified video. Physical
calibration internals require their own observable or source contract; visual
motion matching alone is insufficient.

No further user choice about approximating the movement is pending. The user
has already chosen strict reproduction. The remaining limitation is missing
implementation/data, not authorization to investigate public sources.

## Local artifacts and integrity

- `inspected_files.json`, `branch_source_manifest.json`, and
  `additional_source_manifest.json`: pinned inspected source bytes and SHA-256.
- `sdk_history_source_manifest.json`: the 15 unique historical source blobs.
- `sdk_fork_branch_audit.json`, `sdk_diverged_source_paths.json`,
  `sdk_history_source_paths.json`: branch/history coverage and complete trees.
- `github_search_snapshots.json`: search leads, including rejected false hits.
- `verification.json`: local source-integrity check and scope checks.

The earlier ARM/x86 static inspection, coordinate audit and issue-video limits
remain in `references/upstream/2026-09-27_lite3_zeroing/FINDINGS.md`.
No source files were altered after download. Only survey/task documentation
was updated in this continuation. No new run or validation status is claimed.

## Follow-up: evidence that other users have executed the movement

Dr Sun challenged any implication that nobody has reproduced it. The distinction
must stay narrow: other users report successful use of the factory hardware
initialization; that does not by itself expose its internal movement for an
independent simulator. This audit makes no claim that nobody has done so.

The pinned `dimitarbez/lite3-ros-sim` hardware report, lines 788–871, explicitly
reports a restrained Lite3 run completing `RobotStateInit`, `PreStandUp`,
`StandUp`, a neutral hold and 19 five-second breathing cycles. This is the
author's reported hardware result, not a run independently executed here.
The full report was retrieved through GitHub's API and retained with SHA-256
in `2026-09-27_lite3_factory_homing_sources/followup_demonstrations/`. It is
positive evidence of a documented hardware workflow, not a supplied homing
trajectory. The existing issue-13 user video is another hardware example.

A different source chain led to the manufacturer's **Lite2 Motion Development
Manual V2.0 (2021-11-20)**, available as a
[third-party-hosted manual](https://www.scribd.com/document/741418600/Guia-de-Uso-Del-Robot-Cuadrupedo).
The document identifies Hangzhou Yunshenchu Technology Co., Ltd. and describes
building `jy_sdk_ml/deepras` together with `robot_common` into `jy_exe` (§4.2).
Its §4.3.4 shows `basic_motion.cpp/MotionProcess()` with `kZeroPosition`.
The manual explicitly presents only part of that branch: after 8.5 seconds,
four-leg zero-torque output, `FourLegsAngleRecord()`, and a transition to
`kWaitForStanding`. The first 0–8.5 seconds and full called implementations
are absent from the excerpt. A complete package and a Lite3 counterpart were
not obtained. The web extraction has no reliable printed-page mapping, so use
section references rather than invented page numbers. The official hosting
and the compatibility of this Lite2 algorithm with Lite3 remain unverified.

This is a more specific source-acquisition lead:
`jy_sdk_ml/deepras/src/motion/basic_motion.cpp`, the complete `kZeroPosition`
branch and its matching `robot_common` version. It does not yet qualify as a
Lite3 factory homing implementation. Exact GitHub searches for
`FourLegsAngleRecord` and `TorqueOutputDirectly` returned no matching files;
`kZeroPosition` returned unrelated editor/graphics code in this search.

A RobotStudio digital-twin article was found only as a repost on 10100.com.
It describes receiving real robot joint feedback to drive a virtual model.
The original author repository, complete source and a homing recording were
not located; this remains a discovery lead and is not technical acceptance
evidence. A community script named `warm_up.py` in
[OpenCVChina/DeepRobotDog](https://github.com/OpenCVChina/DeepRobotDog/blob/9cf9f10f6a36eed8dbe1d3f274dcb24bde394e7a/warm_up.py)
was also inspected by the research subagent: its stated pre-standing calibration
is implemented with repeated high-level stand/sit and rotation commands, not
the twelve-joint factory homing controller.

No controller, simulation, task acceptance status or physical-robot state was
changed by this follow-up. Strict Lite3 factory homing reproduction remains
unfulfilled while the complete source or trace is missing.
