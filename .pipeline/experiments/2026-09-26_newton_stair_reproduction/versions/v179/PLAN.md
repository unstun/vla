# v179: policy-only move / stop / restart diagnosis

Stage: experiment + analysis. Dr Sun authorizes repeated flat and stair tests
with the current model, navigation disconnected, and review videos.

The single logical change from v177 is the experimental command source and
controller ownership: deterministic body-velocity scripts replace navigation;
the existing factory startup and smooth REJOIN finish before automatic standing
is detached. All measured zero-command windows are policy-only, Kp20/Kd0.5.
No model, observation, action history, torque limits or original physics code
changes. A read-only contact observer survives detachment. No state reset occurs
within a trial. This is a diagnostic protocol, not a navigation repair.

Owned paths: this version's protocol, standalone runner, bounded launcher,
analysis, tests and immutable source manifest. Inherited physics uses v40 CPU
solver graph, the same current ONNX and sensor-rig URDF as v177. Flat uses an
empty triangle floor with friction1; stairs use the original full Building mesh
and a declared flat approach before the first flight. The start is a diagnostic
start, not a claim of replaying the full-route failure's exact hidden state.

Six conditions per terrain: speeds0.2/0.35/0.5m/s, two predeclared first-walk
durations at each speed. Then10s zero,3s walk,10s zero. These are varied scripted
conditions, not six random-seed replicates. Factory initialization, all failures,
and both stops remain recorded. Fall/invalid-state/timeout aborts preserve partial
evidence. A stop that is never reached is not a stop failure or pass.

Report braking displacement in the first2s separately from later drift, maximum
excursion and actual speed/yaw. Report measured contact forces and world foot
motion, using finite-difference displacement with persistent contact separately
from swing. No universal2cm acceptance claim. Late-window XY excursion over5cm
is a predeclared diagnostic flag, alongside all continuous values; it is not a
robot safety or industry qualification.

gpu5070ti admission currently held:18.29GiB available and two GPU tasks. Use the
already authorized Mac CPU exception, one process at a time, >=10GiB free disk,
>=8GiB available RAM,12GiB child RSS cap,600s wall deadline per trial. Do not
weaken the remote20GiB/no-other-GPU-task gate or stop unrelated jobs.

Temporary raw root: `/private/tmp/vla_policy_stop_20261012`. Budget2GiB. Durable
archive target: `/data/sun/vla_mppi_20261009/policy_stop_v179_mac/`. Return source,
compact JSON/CSV/report, archive identities, and review MP4s (target<150MiB).
Verify every returned hash and remote raw archive before rendering. Rendering
uses recorded states without advancing physics and gets a separate version.

Preflight: source/snapshot hashes, pinned golden model inputs, phase tests,
current environment/version and original startup contracts. Actual physics
determines the result; tests do not establish stopping. No formal training or
hardware actuation. Do not infer a learned-policy-only cause from Newton alone:
deployment/simulator dynamics remain alternative causes without a cross-simulator
comparison.
