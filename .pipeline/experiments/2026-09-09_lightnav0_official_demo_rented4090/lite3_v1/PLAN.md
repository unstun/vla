# Lite3 simulation adapter and bounded LightNav trial

Stage: experiment + analysis. Authorized by Dr Sun's request to change the
RTX 4090 simulation to Lite3. This is simulation only.

## Contract and scope

Keep LightNav-0 revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, vLLM 0.19.1,
BF16, the pinned ProcTHOR scene, capture-aligned MPC, and the exact instruction
`move forward, then go to the trashcan on the right`.

Add a Lite3 RobotBackend in the separate `work/LightNav-0-lite3-v1` copy.
Import the official Lite3 MJCF from commit
`1f46ba1f86c72ddafd3d79e1e9725805c202bf2b`, transformed using the committed
machine-dog v12 asset builder, and the hash-pinned model_149999 FP32 ONNX export.
The walking policy consumes 450 floats (45D x H10, term-major oldest-first),
emits 12 raw actions, and runs at 50 Hz. Its target is q0 + 0.25 * action,
with q0=(0,-0.8,1.6) per leg, kp=20, kd=0.5, and the v12 torque-speed limits.
Reset clears previous raw action and history; the first valid observation
repeats into every history slot. Command is [forward, 0, yaw] in m/s and rad/s.

MuJoCo integrates physical joint torques and contacts at 1 ms, five substeps
per existing 5 ms demo tick. No kinematic base teleporting occurs after reset.
The adapter maps robot collision masks to contype=2/conaffinity=13: the source
0/1 masks cannot contact ProcTHOR's structural floor (type 8). This enables
robot/environment contact while preserving disabled robot self-contact.
The robot starts at (6.5,13.8,0.35), heading zero. The new body-mounted camera is
at (0.24,0,0.08) in the torso, horizontal, 480x270, vertical FOV 79.865 degrees.
Nominal ground height is 0.38 m at the v12 standing height; record its actual
pose. The changed body, dynamics, and camera make this a new trial, not a
controlled TurtleBot-equivalence claim.

Navigation STOP clears navigation commands; the walking policy continues
receiving zero velocity so the physical quadruped can maintain balance.
Record requested velocity, observed motion, tilt, height, inference failure,
native STOP, harness timeout, fall, and recorder failure distinctly.

Owned changes: this directory, the separate work copy, and a Lite3 note in the
existing task metadata. Preserve all v3 and legacy evidence. Do not alter
machine-dog or machine-dog-nav, train a policy, or actuate hardware.

## Execution and acceptance

1. Verify imported assets/policy; unit-check history, quaternion transform,
   action mapping, invalid outputs, and reset behavior.
2. Run a model-disconnected supplied-command smoke: standing, forward walking,
   turning, then zero command. Require finite state, height >=0.15 m, upright
   body, forward displacement, and actual turning. Record any drift at zero.
3. Only after that gate passes, run one original-instruction episode, bounded
   to 180 seconds or 180 decisions plus at most five seconds of STOP observation.
   Supervisor bounds the total model/demo service window to 600 seconds, with
   process-group cleanup and no retries for a better navigation outcome.
4. Return original camera frames, state/command/model traces, metrics, and a
   locally decoded video. Report navigation success independently of integration.

Local VLA is the source of truth. Sync task-owned files to
`/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090/` on
`rented4090`; compare every work-copy and input hash before execution. Keep
the existing Isaac Sim processes untouched. Record source manifests and patches,
and copy all run evidence back to the same local relative paths before claims.
