# Original factory homing: bounded local test

Stage: experiment + analysis, 2026-09-27.
Authorization: Dr Sun requested the local crouch, zero-return, stand test after
the original library was loaded. Physical robot access remains read-only.

## Behavior gap and owner

The existing Newton `pd_stand` controller omits factory homing. The selected
factory library contains a torque-driven zero-return phase, and its caller
performs encoder-turn correction when `RobotStateUpload.zero_position_flag`
is set. The behavior belongs to this original controller and its measured-state
adapter. It must not be replaced with a new pose interpolation.

## Smallest implementation

1. Recover the library ABI and actual caller contract from the selected binary's
   DWARF and call sites. Pin any original policy/configuration files required by
   `MotionInitial`. Record the exact zero-request toggle, state output, time,
   joint coordinate and motor output semantics.
2. Add a thin C++ caller and local container runner under
   `.pipeline/experiments/2026-09-27_lite3_factory_runtime_audit/`. Keep original
   library bytes unchanged. Compile and call only the algorithm seam in an
   isolated, network-free, device-free ARM64 Linux process. Start with bounded
   synthetic measured inputs; do not label these physics evidence.
3. If the contract and dependencies are established, connect measured Newton
   joints and IMU to that caller, apply original outputs, and preserve one
   continuous physical state. Reuse the existing Newton robot and renderer.
   An adapter may be added locally; modify shared Newton code only for a small,
   explicit motor-output entrypoint if necessary.
4. Record full-rate inputs, outputs, factory states and calibration flags.
   Verify finite values, real phase transitions, joint-limit behavior, physical
   clock, standing stability and displacement. Render the actual trajectory.

## Boundaries and stopping evidence

No physical actuation, factory service execution, calibration writes, planner
work, policy replacement, upstream source edits or library patching. Do not
relax physical model limits to force success. A joint-limit/encoder mismatch or
unresolved output contract is a failed integration result, not permission to
invent factory behavior. Preserve a diagnostic video if a complete episode
cannot be validated. Compile/probe deadlines and resource limits are recorded
by the runner. No refactor is planned.

## Acceptance boundary

Algorithm-call success, state-machine execution, Newton integration and strict
factory-motion validation are separate results. The final requires a suitable
factory reference and compatible mechanical/calibration model, not merely a
successful library load or an attractive video.
