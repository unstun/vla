# Newton crouched PD startup

Original-library follow-up (2026-09-27):
`.pipeline/experiments/2026-09-27_lite3_factory_runtime_audit/ALGORITHM_ABI.md`
records the separately verified factory ABI. Its bounded Newton trial can
stand, but mechanical calibration and the 0.10 m in-place check remain unmet.
The factory zero flag also occurs with frozen joints; it is not a measured
completion gate. Do not promote this into the navigation startup default.
`_motor_substep(feedforward_torque=...)` adds the original library's twelve
finite feedforward torques before the existing torque-speed limit. Omitting
that argument preserves previous behavior. Native float32 clock continuity is
checked against float32 recurrence, not a double-precision step product.

Status correction (2026-09-27): this implemented contract covers preparation
and standing only. It omits the independent factory return-to-zero operation
requested by Dr Sun. Do not call it a complete homing/startup solution. The
verified SDK/firmware boundary and unresolved target definition are recorded in
`references/upstream/2026-09-27_lite3_zeroing/FINDINGS.md`.

## 1. Scope / Trigger

Scoped to the bounded macOS Newton flat-scene experiments, introduced on
2026-09-27. Do not infer stair or hardware qualification. The source import is
DeepRoboticsLab/Lite3_MotionSDK `b30a3ec09619e1dd0f3cfa6c49a50eb59670f141`
(MIT), under `references/upstream/2026-09-27_lite3_pd_startup/`.

## 2. Signatures

`Lite3Newton(..., startup_mode="policy")` and
`FlatSceneRobot(..., startup_mode="policy")` preserve legacy behavior.
`run_local_episode.py --startup-mode pd_stand` selects the new mode and requires
a geometry-only flat scene. Its bridge probe runs 8 seconds; legacy probes
remain 3 seconds. Build the native scalar adapter with
`2026-09-26_newton_macos_policy/scripts/build_sdk_spline.py` first.

## 3. Contracts

- Initialize the original sensor-rig URDF once, at z=0.14 m and SDK preparation
  joints `[0,-70,150]` degrees per leg. Use the pinned SDK degree constant.
- `crouch`: 1 s damping at Kp=0, Kd=0.7 lets the folded robot settle on the floor.
- `prepare`: 1 s from measured joints to SDK preparation pose, Kp=60, Kd=0.7.
- `stand`: 1.5 s from measured joints to pinned policy Q0, Kp=60, Kd=0.7.
  Q0 differs deliberately from the SDK demo's final `[0,-42,78]` degree pose.
- Both moving phases call the unmodified compiled SDK `CubicSpline` each 1 ms.
  Desired velocity uses its next-position finite difference, as `SwingToAngle`.
- `settle`: Kp=80, Kd=0.7. Require base up >=0.98, z>=0.25 m, joint error
  <=0.15 rad, max joint speed <=0.3 rad/s, body linear speed <=0.03 m/s and
  angular speed <=0.08 rad/s continuously for 0.5 s. Timeout at 8 s.
- `handoff`: start ONNX on the first actual standing observation with the
  existing H10 repeated-first-frame history. Blend PD torques to policy gains
  20/0.5 over 0.25 s, using the SDK scalar spline for the blend weight.
- `policy`: release navigation commands. Earlier requests are recorded and
  replaced by zero at the motor/policy seam. No pose reset after initialization.
- Shared `_motor_substep` retains torque-speed limits, contact-capacity rejection,
  every-substep contact scoring and native applied-torque verification.
- Telemetry records `controller_phase`, `policy_calls`, `effective_command`,
  gains, target velocity and `navigation_ready`.
- The old applied-state v1 schema requires a real policy-observation error.
  Publish no applied snapshot during PD-only control; body poses and scans still
  flow. The first snapshot is permitted once policy inference has actually run.
- Applied snapshots add `control` fields: `startup_mode`, `phase`,
  `navigation_ready`, `policy_observation_valid`. The startup driver wraps the
  verified geometry-driver snapshot; it requires all four fields to confirm
  completed startup before applying the original five-second/stillness gate.
  Preserve the original geometry driver and its source identity.
- Navigation-height scoring starts at `navigation_ready` for this explicit
  mode; low body height during crouch is intentional. Full-rate obstacle
  contact scoring spans the entire run. Legacy height scoring still spans all
  physics. Report control updates and actual policy-inference calls separately.

## 4. Validation & Error Matrix

| Condition | Result |
|---|---|
| Unknown startup mode | Reject before simulator creation |
| SDK source/library identity mismatch | Reject; no fallback interpolation |
| Invalid/nonfinite command | Reject before inference or physics |
| Stability interrupted | Restart the 0.5 s dwell |
| Standing gate absent at 8 s | Timeout; no policy/navigation release |
| Crouch/prepare/stand/settle command | Record request, effective command zero |
| Missing startup fields or handoff phase | Startup driver refuses readiness |
| Building or semantic-tracker PD launch | Reject unsupported condition |

## 5. Good / Base / Bad Cases

Good: continuous crouch-to-stand physics, measured stability, then actual policy
inference and declared handoff. Base: default `policy` remains the prior run
condition. Bad: lift the base by assigning its pose, fill missing policy evidence
with a success flag, or call a startup-only movie navigation validation.

## 6. Required Tests

Compare the SDK scalar output and finite-difference velocity with independent
SciPy Hermite interpolation, including clamped endpoints. Test interrupted
stability, low-body/posture rejection, timeout, invalid modes and startup-driver
refusal. Compare the extracted legacy motor loop to its saved pre-edit source
under zero and nonzero commands; require identical states and torques. Preserve
the policy golden trace. Physical qualification must record startup phases,
body rise, >=3 s stable policy operation, effort/joint limits, full-rate contact
scoring and an actual-state video. Runtime bridge evidence must confirm that
PD-only states never publish a fake policy observation.

## 7. Wrong vs Correct

Wrong: the robot is quiet while lying down, so send the goal; initialize a policy
history from zeros to satisfy the snapshot parser.

Correct: require the measured standing gate, initialize policy history from the
first real standing observation, and retain missing applied readiness until
that observation exists. Report startup and navigation outcomes separately.
