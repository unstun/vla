---
origin: pinned-upstream-code-inspection
reviewed: false
date: 2026-09-27
stage: experiment-and-analysis
status: surveyed-with-one-cpu-unit-test-executed
---

# Can lite3-ros-sim supply the missing factory homing movement?

## Result

Parts of the startup sequencing and feedback handling are useful references.
The inspected project does not supply a factory homing implementation for our
Newton simulation. Its real-robot runner delegates that phase to the vendor
SDK. Its active Gazebo entry point sets the body and joint state directly,
then uses ordinary posture/stand control.

Do not copy the whole project into the current experiment or change the
strict-factory-homing requirement. No motion-controller changes were made by
this review. The raw inspected source snapshots, dependency trees, manifests,
and CPU-only check are in `2026-09-27_lite3_ros_sim_reuse_sources/`.

## Exact source graph

The parent repository is publicly accessible according to current GitHub
metadata, although its README still describes a private repository.

| Component | Repository and pin | License evidence | Relevant role |
|---|---|---|---|
| Workspace / hardware runner | [dimitarbez/lite3-ros-sim](https://github.com/dimitarbez/lite3-ros-sim/tree/a3fee6db1ed5e133db1bc83a86cead4c7d7f37a9), `a3fee6db1ed5e133db1bc83a86cead4c7d7f37a9` | No root license found; `emotion_bot_lite3_hw/package.xml` declares GPL-3.0-only. The tools directory is outside that package, so its scope must not be silently inferred. | Hardware sequencing, shared telemetry and watchdog |
| Active simulator submodule | [dimitarbez/Lite3_VMC](https://github.com/dimitarbez/Lite3_VMC/tree/c405287e1ac19bbbe9deedbf3493a0bb94cfab09), `c405287e1ac19bbbe9deedbf3493a0bb94cfab09` | `quadruped/package.xml` and inspected action/example headers declare MIT; `emotion_bot_ros/package.xml` declares GPL-3.0-only; no universal root license declared. | Gazebo robot initialization and posture controller |
| Emotion subsystem submodule | [dimitarbez/emotion-bot](https://github.com/dimitarbez/emotion-bot/tree/7ae69828038c2f3563fc00d17fbfb2e3927abf57), `7ae69828038c2f3563fc00d17fbfb2e3927abf57` | GPL-3.0 LICENSE; preserve exact license text for any future selected reuse. | Emotional state generation, not factory homing |
| Clean reference submodule | `dimitarbez/Lite3_VMC`, `724aa54dee0cc374bd5417c86d649fb08d4d309a` | Path-specific upstream licenses | The previously surveyed clean VMC reference; not the active modified simulator |

The parent gitlink SHAs, not the branch names in `.gitmodules`, identify the
reviewed simulator and emotion versions. All retrieved recursive trees were
untruncated. Root metadata alone would have missed the package-specific MIT
and GPL declarations.

Original workspace instructions are `git clone --recurse-submodules`, then
`make -C lite3-noetic build`, `start`, and `bootstrap`. The normal environment is
ROS Noetic/Gazebo in a Linux Docker workspace; it is not a native Newton/macOS
control interface. Original verification targets include `verify-emotion` and
`verify-hardware-offline`. Neither complete suite nor any ROS/Gazebo/hardware
launch was run here. The hardware runner additionally depends on installed
vendor SDK headers/libraries, Linux shared-memory feeds and a real motion host.

## Actual hardware startup path

File: [run_motion_sdk_neutral_breathing.cpp](https://github.com/dimitarbez/lite3-ros-sim/blob/a3fee6db1ed5e133db1bc83a86cead4c7d7f37a9/lite3-noetic/hardware-ws/tools/run_motion_sdk_neutral_breathing.cpp).

1. Establish exclusive ownership, passive joint/IMU feedback and a separate
   robot-state feed. Explicit `--execute` is required for its command path.
2. Line 620 calls `sender.RobotStateInit()`; no local per-joint homing controller
   runs during that blocking call.
3. Lines 621–633 wait for fresh finite feedback, with a bootstrap path if needed,
   and capture measured joint positions. The `PHASE_COMPLETE robot_state_init`
   log follows feedback readiness; it is not a local verification of the entire
   factory joint trajectory or encoder calibration.
4. Lines 636–650 call the official `PreStandUp` for 1 second and `StandUp` for
   1.5 seconds, capturing measured joint positions between phases.
5. Hold the stand target for 1 second, then enter the separate breathing motion.
   The target is `[0,-42,78]` degrees per leg, with holding gains 80/0.7.

Useful transport logic lives in `RunPhase`: feedback age above 100 ms pauses
trajectory advancement and holds the prior command; above 250 ms aborts.
Recovery requires 20 distinct samples with age at most 20 ms. State 8 and
nonzero error flags stop the runner. These are this deployment's tested values,
not automatically appropriate Newton or future robot defaults.

An important incompatible detail is `BootstrapSdkFeedback` (lines 376–400):
it zeroes all command positions and sets Kp=60/Kd=0.7 for at most 250 ms.
Do not transplant that command into our URDF, whose knee coordinate zero is
outside the recorded joint limits. Its use after a physical factory reset does
not establish the encoder-to-URDF mapping required for our simulator.

## Actual Gazebo startup path

The active launch file loads Gazebo, spawns the URDF and waits for the robot
model and joint controllers. `sim_ready_runner.py` then launches
`example_lite3_sim`; this is a separate path from the hardware runner above.

In [example_lite3_sim.cpp](https://github.com/dimitarbez/Lite3_VMC/blob/c405287e1ac19bbbe9deedbf3493a0bb94cfab09/src/examples/example_lite3_sim/example_lite3_sim.cpp):

- Line 153 calls `ResetRobot`.
- That function sets body position to `[0,0,0.3]`, orientation to identity and
  body velocity to zero using `/gazebo/set_model_state`.
- It directly sets twelve joint positions using
  `/gazebo/set_model_configuration`: hip-abduction signs alternate around
  0.167136 rad; thigh is -0.934969 and knee is +2.54468 rad.
- This is simulator initialization, not a controller moving the joints through
  the factory homing sequence.

The stand FSM calls `Quadruped::Action::StandUp`, implemented in
[`qr_action.cpp:50`](https://github.com/dimitarbez/Lite3_VMC/blob/c405287e1ac19bbbe9deedbf3493a0bb94cfab09/src/quadruped/src/action/qr_action.cpp#L50).
It reads the current motor angles, linearly interpolates to `standUpMotorAngles`
and then holds the target. There is no factory homing phase in this routine.

The simulator's internal convention must also be respected: `robot.yaml`
declares all twelve `joint_directions=-1`, and `qr_robot_lite3_sim.cpp` applies
that mapping to feedback and outgoing commands. The internal stand target
`[0,+0.86,-1.7]` radians must not be copied as raw URDF targets.

Finally, `emotion_bot_ros/scripts/safety_bridge.py:420–446` contains optional
simulator recentering that writes body x/y with `SetModelState`. That is separate
from the startup reset. It is unsuitable for importing into a navigation trial
whose motion must follow continuous physics. Preserve that boundary even if a
visual demonstration using the feature looks stable.

## Reuse decision against our current implementation

| Upstream component | Current Newton experiment | Decision |
|---|---|---|
| Read actual joints at each preparation/stand transition | `PDStartup.advance()` already captures `q` | Already covered; another implementation is unnecessary |
| Official preparation/stand trajectory and PD control | Pinned official SDK cubic spline is already compiled and used; final pose is our pinned policy Q0 | Keep the existing source-backed path; do not replace it with the VMC linear blend just to use this repository |
| Hardware feedback pause/recovery and phase logs | Local motor loop is driven synchronously by the physics clock; bridge readiness is separate | Useful reference for an asynchronous transport integration, not a homing implementation or immediate local fix |
| Stand hold before the next behavior | Local controller already requires measured body/joint stability before policy handoff | Keep the measured gate; a fixed one-second hold alone is not stronger evidence |
| Factory homing | Still absent from both the local Newton adapter and the inspected Gazebo path | This repository does not close the missing behavior |
| Gazebo initial-state assignment and body recentering | One initial physical state, then continuous Newton dynamics | Do not treat direct state assignment as reproduced calibration or navigation |
| Emotional breathing, stomps and hops | Outside the requested startup/navigation correction | Do not import unrelated behavior |

The smallest useful reuse does not currently require replacing the local motor
controller. The missing module remains a source-backed factory homing action
definition and coordinate/completion contract. The user's strict requirement
is not relaxed by selecting this repository for inspection.

## Direct check performed

The unmodified upstream `test_motion_sdk_safety.cpp` was compiled with macOS
Clang in C++17 mode and executed successfully (build exit 0, run exit 0).
It tests the stop-state predicate and bounded, finite breathing trajectories.
It contains no ROS, UDP or hardware execution. Exact command, source SHA-256,
stdout/stderr and result are retained under the evidence directory's `checks/`.

This demonstrates that those pure CPU components can execute locally. It does
not test factory homing, the full watchdog/runner, standing dynamics, Gazebo,
Newton integration or physical hardware. The complete workspace is `surveyed`;
only this named upstream unit test has been executed here.
