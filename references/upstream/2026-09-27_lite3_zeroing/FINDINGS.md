# Lite3 return-to-zero: verified boundary

Stage: experiment + analysis. Date: 2026-09-27. This is a source audit; no
homing implementation, new physics run, encoder calibration or hardware command
was executed. The user-requested homing correction is still incomplete.

## Main finding

The previous `pd_stand` adapter omitted a separate factory initialization.
The official SDK client sends a high-level return-to-zero command; it does not
contain the per-joint target sequence needed to reproduce that movement in
Newton. Neither the inspected official deployment code nor rl_sar supplies a
replacement firmware homing trajectory. Do not claim this as a global proof
that no implementation exists elsewhere.

## Pinned sources and licenses

| Repository | Commit | License | Inspected seam |
|---|---|---|---|
| DeepRoboticsLab/Lite3_MotionSDK | `b30a3ec09619e1dd0f3cfa6c49a50eb59670f141` | MIT | `sender.h`, command schema, published ARM/x86 SDK libraries; previous import retains main/README |
| DeepRoboticsLab/Lite3_rl_deploy | `1c4a8f14c9c531903fa5a26783e3f9b99d1039d9` | BSD-3-Clause | Hardware initialization, simulator initial joints and stand-up state |
| fan-ziqi/rl_sar | `376d42c9b128f963ab08579762d5a216a976ce39` | Apache-2.0 | Lite3 real-robot constructor, FSM and default posture |

Exact downloaded bytes, canonical URLs and SHA-256 are in
`source_identity.json`. Source files and libraries are unchanged. The two
libraries were inspected statically with the installed Apple LLVM objdump,
not loaded or executed. Commands and complete output are under `analysis/`.
Original SDK build/run instructions remain in the preceding startup import;
they are hardware instructions, not a Newton homing implementation.

## What the client actually does

Both architecture libraries independently show:

1. `AllJointBackZero()` constructs command `0x31010c05` with parameter size
   zero and a null parameter pointer, then sends it.
2. `RobotStateInit()` sends the same command, calls `usleep(7000000)`, then
   sends control-acquisition command `0x114` twice.
3. It does not construct twelve joint angle targets or poll a homing-complete
   status in this function. Seven seconds is the client's wait, not a measured
   trajectory duration or proof of completion.

Relevant static addresses: x86 `AllJointBackZero` at `0x6e00` and
`RobotStateInit` at `0x6e70`; ARM equivalents at `0x6890` and `0x6928`.
SDK `ControlGet(SDK)` also uses `0x114`, corroborating the acquisition step.
The robot-side implementation handling `0x31010c05` is not present in these
inspected files. Its search/calibration/offset algorithm cannot be inferred
from the client call alone.

The official deployment `HardwareInterface` constructor calls
`RobotStateInit()`; its joint feedback method copies the twelve reported
positions directly. rl_sar's real Lite3 constructor likewise calls that SDK
method. Its get-up interpolation is subsequent posture control, not a supplied
factory homing implementation.

## Simulator coordinates and available alternative

Official `mujoco_simulation.py` initializes each leg to
`[0, -1.35453, 2.54948]` radians by assigning qpos. It does not simulate the
factory homing process. These numbers provide a concrete official simulator
initial-pose reference; they do not establish the factory zeroing trajectory
or encoder offsets.

The current pinned sensor-rig URDF has knee limits `[0.524, 2.792]` radians.
Consequently an all-zero twelve-joint target violates all four knee limits.
`analysis/zero_contract_audit.json` records all twelve ranges and the URDF hash.
The manufacturer's motion manual also gives a nonzero knee operating range
(34.5 to 156 degrees); see page 9 of
[the manual](https://www.deeprobotics.us/wp-content/uploads/2025/10/Jueying-Lite3-Motion-Development-Manual-beta-V2.0.1-0.pdf).
None of this identifies encoder homing zero with zero URDF joint angles.

## Visual corroboration and limits

[Official-repository issue 13](https://github.com/DeepRoboticsLab/Lite3_MotionSDK/issues/13)
contains a user's real Lite3 reset video; a contributor distinguishes reset
from the later stand-up operation in the replies. Browser inspection at video
times 1.936, 5.996 and 11.961 seconds shows the body on the floor while leg
postures change and return. This qualitatively corroborates a separate motion.
The video is user-supplied, has no joint-angle trace or synchronized SDK trigger,
and is not a quantitative factory acceptance reference. Do not infer exact
targets, phase order, torque limits or encoder offsets from a few frames.
Issue bodies and relevant replies are retained as retrieval snapshots.

## Earlier decision request, superseded

- Exact factory homing requires the robot-side definition or a sufficiently
  instrumented joint/command trace. No such artifact was found in this audit;
  no remote or physical-robot access is authorized by this local task.
- A distinct, explicitly named simulator return-to-pose can use the official
  simulator initial joints above, PD motion from actual joint positions, and a
  measured completion gate before standing. It must not be labeled factory
  homing or encoder calibration. Dr Sun has been asked which behavior he wants.

The old startup video remains valid only as preparation/stand evidence. The
controller was not changed while that semantic choice was pending.

## Subsequent user decision and expanded audit

Dr Sun then explicitly selected strict factory homing reproduction and required
additional GitHub investigation. No approximation choice remains pending.
See `.pipeline/survey/2026-09-27_lite3_factory_homing_upstream_survey.md` for
the expanded history/fork/community audit. It found published official sender
source in the `add_python` branch at
`e4d75a4ba10662b7349f10cadd2c40feea676bf7/src/sender.cpp`, directly corroborating
the command/wait behavior above. No qualified motion-host implementation or
full joint trace was found in that inspected set; the strict reproduction is
still incomplete. No additional controller or simulator changes were made.
