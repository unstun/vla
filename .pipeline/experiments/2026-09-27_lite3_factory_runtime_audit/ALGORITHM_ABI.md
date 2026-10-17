# Verified original algorithm seam

The selected executable/library hashes are in `source_manifest.json`. These
findings apply to that snapshot only. Raw DWARF and disassembly remain local
under `private_snapshot/static/`.

## ABI and caller

- `MotionInitial(string const&, string const&, MotionConfig const&)` is called
  by `Controller::InitialKinetics` at executable `0x31bf8`. The two strings are
  `RobotConfig::GetFullName()` (module plus `-` plus serial) and the robot type
  from `conf/deeprcs.json`. The serial is retained privately.
- `Motion` is called at executable `0x81d9c`. Its first argument is a
  288-byte `DataLegs`, followed by 72-byte `DataGyro`, elapsed seconds, controller
  period in seconds, 552-byte `ControlCommands`, `double[140]` scope storage,
  and output `DataLegs`.
- The executable's DWARF identifies `algorithm_period_` at `Controller+0xf78`;
  the other time reference comes from `KineticsDeduce(double&)`.
- `DataLegs` groups position, velocity and torque, each in FL, FR, HL, HR order,
  each leg containing three doubles. Named URDF joints select HipX, HipY, Knee.
- `GyroDataProcess` at library `0x108618` multiplies **only** roll/pitch/yaw by
  pi/180; angular velocity passes through in rad/s and acceleration in m/s².
  The Newton adapter therefore supplies Euler angles in degrees, body angular
  velocity in rad/s and body specific force, including gravity at rest.
- `ControlCommands.is_stand` is the first one-byte union, offset 0.
  `is_zeroposition` is offset 73. `ParseCommand` case `0x0c05` at executable
  `0x7e058` toggles that byte. A constant true value is one toggle event, not a
  repeated hardware command.
- `download_parameters` is an exported 576-byte struct containing six arrays
  of 12 doubles: `kp`, `kd`, `t_ff`, `goal_angle`, `goal_angle_vel`,
  `goal_angle_comp`. `Motion` copies its position/velocity/feedforward values
  into the output `DataLegs`; the adapter also reads the original gains.
- `RobotStateUpload` is 208 bytes; `zero_position_flag` is offset `0xbd`.
  The basic phase at `BasicMotion::global_+0x20` is read for diagnostics only.
  No internal state is written by the adapter.

`factory_actor.cpp` asserts every interface size and relevant field offset.
`prepare_algorithm_inputs.py` encodes the original scalar TOML values and the
executable's defaults (`GetAlgorithmConfig`, `0x30a18..0x30bcc`,
`0x315e8..0x316dc`). Original inputs are hash-checked before initialization.

## Direct checks

`algorithm_probes/init03` invoked both functions and returned a finite first
reply. `synthetic_homing01` used frozen measured joints for 4,501 calls at 2 ms:
phase 1 → 17 → 1 → 4 → 5. The zero flag rose 4.402 s after the request and
cleared 0.1 s later; phase 17 ended after 5.502 s.

`synthetic_axis01` supplied nonzero HipX angles of +0.1 rad. The original
prepare output was +0.0972 at 0.1 s into a one-second spline, consistent with
preserving the measured sign and interpolating toward zero. This avoided a
mistaken extra sign flip at the simulator boundary. The physics trial then
verified the returned gains/targets/feedforward against the raw library replies
and native applied joint forces.

These frozen-input tests demonstrate that a zero flag/state transition alone
does **not** establish measured mechanical calibration completion.

## Calibration outside the library

In `Controller::KineticsDeduce`, executable `0x81498..0x817a8`, the zero flag
triggers integer-turn selection relative to stored references. Later code at
`0x81954..0x81c58` corrects angle readings and sets `goal_angle_comp` for motor
coordinate compensation. Constants in the selected executable are:

| Quantity | Radians | Address |
|---|---:|---|
| Left HipX reference | -0.489 | `0xc5080` |
| Right HipX reference | 0.489 | `0xc5090` |
| HipY reference | -3.49 | `0xc5098` |
| Knee reference | 2.757 | `0xc50a0` |
| Hip motor turn interval | 0.5236 | `0xc5088` |
| Knee motor turn interval | 0.3422 | `0xc50a8` |

The current sensor-rig URDF limits HipY to -2.67 rad. During the simulated
zero flag it reaches about -2.67052 rad. The verified reference discrepancy is
about 0.81948 rad; it is not corrected by changing the URDF or resetting the
simulator pose. The current trial uses ideal absolute encoders and records the
flag; it does not simulate motor turn ambiguity or apply hardware calibration.
Mechanical stops, self collision and encoder coordinate equivalence need a
qualified model/reference before strict reproduction can be accepted.

## Runtime dependencies and isolation

Twenty additional original model/configuration files are pinned by
`algorithm_inputs_manifest.json`; loading them is initialization support, not a
policy replacement. The unchanged library initializes successfully in the
previously qualified ARM64 Ubuntu 20.04 image with no network or device access.

The first actor launch exposed a no-execute temporary mount. The second exposed
the standard C++ weak pthread-link issue. The final compile retains pthread
with `--no-as-needed`, as used by the upstream
[SICK driver dynamic-library test](https://github.com/SICKAG/sick_scan_xd/blob/develop/CMakeLists.txt).
The corresponding error originates in
[GCC's thread runtime](https://github.com/gcc-mirror/gcc/blob/master/libstdc%2B%2B-v3/src/c%2B%2B11/thread.cc).
Only the temporary build mount is executable; original snapshots remain
read-only. A missing log4cplus appender warning is retained in each run log.
