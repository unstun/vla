# Crouched PD startup (2026-09-27)

Correction: the implemented contract below omits factory zero return and does
not satisfy Dr Sun's complete startup request. It remains a historical
preparation/stand contract. Continue from `PD_ZERO_RETURN.md` and the pinned
zeroing-source audit before changing control targets.

Stage: experiment + analysis. Dr Sun requested crouched initialization, PD
reference recovery and standing before locomotion; continuation is authorized.
This is a bounded local simulation change, not a remote or hardware run.

## Scope before implementation

Current Newton episodes initialize at the policy standing reference and infer
immediately. Add an explicit `pd_stand` startup mode: initialize crouched once,
settle, retract to the SDK preparation pose, stand to the pinned policy Q0,
check actual stability, and hand over to the existing ONNX policy. Preserve
`policy` as the legacy replay default. One physical state continues throughout;
only constructor initialization may assign the pose.

Reuse DeepRoboticsLab/Lite3_MotionSDK, main commit
`b30a3ec09619e1dd0f3cfa6c49a50eb59670f141`, MIT license. Selected source import:
`src/motionexample.cpp`, `include/motionexample.h`, README, LICENSE, CMakeLists,
and main example. Import exact raw commit bytes into the dated project reference
directory. Upstream requires C++11, Eigen, Linux SDK shared library and pthread;
original build instructions are retained in README. Locally compile only its
unchanged scalar CubicSpline method with a C ABI; no network/hardware sender
is linked. Record file hashes and extraction/build identity.

Owner seam: `Lite3Newton` explicit motor-control loop. Factor one shared physics
substep, retaining existing torque-speed saturation, contact-capacity rejection
and applied-force verification. A startup adapter owns SDK spline commands and
measured phase transitions. `flat_scene.py` forwards explicit initialization;
bounded startup qualification records full physical states and renders through
the existing replay renderer. Episode entry/gating may receive the explicit
mode once qualification passes. No SCAN/PCT algorithm or occupancy change.

Expected files: Lite3 Newton controller; SDK adapter/build wrapper; flat scene;
startup runner/tests; renderer's startup captions; episode mode plumbing and
readiness contract if required. Preserve old source snapshots and compare
legacy zero-command traces after the substep extraction.

## Prospective acceptance

- SDK spline output and derivative are consumed at 1 ms, with endpoint clamping.
  Preparation is 1 s and stand interpolation 1.5 s, using SDK gains 60/0.7.
  Final reference is policy Q0, not the SDK demonstration's different stand angle.
- Start low with folded legs, no mid-run reset, pose injection, gravity bypass,
  or ground-truth obstacle input. Actual base height must rise by at least 0.10 m.
- Before policy entry: base up >= 0.98, base z >= 0.25 m, joint reference error
  <= 0.15 rad, maximum joint speed <= 0.3 rad/s, body linear speed <= 0.03 m/s,
  angular speed <= 0.08 rad/s, sustained 0.5 s. Timeout at 8 s fails closed.
- Policy history initializes from its first measured standing observation,
  with the existing repeated-first-frame contract. Record phase, gains, desired
  velocities, policy call count, command gating and handoff time.
- After handoff, remain upright for at least 3 s on zero command. Report maximum
  joint speed, effort, target/torque changes and joint-limit excursions; do not
  imply real-robot qualification or navigation completion.
- Test early/nonzero command gating, invalid mode, timeout and stability reset;
  verify original policy golden parity and legacy physics behavior.
- Deliver a real video from recorded physical states, with phase labels and
  immutable source hashes. Failed attempts remain available.

The full static-obstacle navigation repeat and original Isaac stair A4 remain
open regardless of startup results.

## Execution clarification before the first live navigation attempt

The existing v1 applied-state parser requires a finite policy-observation error.
PD phases have no policy observation, so the host publishes body/cloud data but
withholds the applied snapshot until the first real inference. The startup
driver additionally requires explicit completed startup and retains the old
five-second/quiet-body gate. This changes neither SCAN nor the original driver.
`review_local_episode.py` must count actual policy calls separately from control
updates; its body-height threshold applies after navigation readiness in this
mode. Contact scoring remains continuous from the first physics step. Existing
legacy height scoring and original result artifacts are preserved.

The first bridge attempt found Docker stopped; its failed logs are retained.
Starting the installed local app allowed the unchanged second probe to pass.
An additional bounded static-human episode tests the real goal-driver launch.
