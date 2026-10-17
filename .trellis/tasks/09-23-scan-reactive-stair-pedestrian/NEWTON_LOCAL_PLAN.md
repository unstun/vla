# Local Newton policy qualification

2026-09-26; stage: experiment + analysis. Dr Sun selected Newton after review
of the macOS options. This authorizes a project-local isolated installation
and bounded simulation/inference trials. Remote Isaac work remains stopped.

## Behavior gap and boundary

The Mac currently has source-level planner tests but no demonstrated Newton
policy-plus-physics run. First establish an official single-robot CPU policy
example with actual state change and recorded simulation frames. Then assess
the existing Lite3 ONNX and robot-interface port using the same evidence gates.
This is a new simulator condition, not a continuation of the identical Isaac
RTX/official-human experiment or acceptance of SCAN33.

Owned paths: `.pipeline/experiments/2026-09-26_newton_macos_policy/` for setup,
pinned upstream source, local adapters, runs, hashes and results; the existing
task's metadata and this plan; a narrowly scoped local-runtime ignore entry
with provenance if needed. Existing VLA Lite3 adapters are read-only references
until reused through explicit identity and interface checks. No sibling edits,
global environment changes, training, real robot, remote startup or commits.

## Source and design

Start from the official Newton v1.6.0 release. Resolve the tag commit, retain
Apache-2.0 license and exact source/archive/package hashes before execution.
Use a local Python3.12 virtual environment. Keep downloads, package and kernel
caches, model assets and rendering outputs inside the experiment directory.
Pin installed versions and record compatibility patches; preserve each failed
attempt. Original documented entry: `python -m newton.examples robot_policy
--robot go2 --device cpu`; verify it against the selected source version.

The physics loop and policy are the upstream implementation. A small wrapper
may capture actual state/action/clock and framebuffer evidence and supply an
explicit fixed velocity request in place of keyboard input. Any such change
is recorded and does not imply an unmodified upstream command. Do not change
contact/dynamics thresholds or replace dynamics with kinematic pose playback.

## Execution and acceptance

1. Pin and inspect source/dependencies; record environment/disk preflight.
2. Install only the selected CPU/example dependencies in the isolated directory;
   keep at least10GiB disk free. Initial acquisition budget is5GiB.
3. Run import/device and a bounded upstream physics smoke, with explicit CPU
   device, one environment and per-process deadline at most600s including cold
   kernel compilation. Record failures without changing their verdicts.
4. Run a policy trial of at most15sim seconds and600wall seconds. Require finite
   policy I/O, increasing physics step/time, actual applied controls and changed
   robot state. Record contacts/base attitude and report falls rather than hiding
   them. A motion command need not establish tracking quality or stair success.
5. Record actual simulator frames, encode an ordinary local MP4, verify decoding,
   inspect frames, and report video/simulation/wall durations separately.
6. Only after the upstream platform path works, adapt Lite3 using the existing
   pinned ONNX/robot interface; preserve observation history/order, joint mapping,
   PD gains, limits and timestep. It is a separate run and evidence label.

The first useful delivery is a verified local policy/physics video plus source,
environment and run identity. An environment import alone is not completion.
The full stair/person task remains in progress unless its own declared gates
are subsequently exercised and pass in an explicitly identified simulator.

## Lite3 port contract (after Go2 platform qualification)

Reuse the existing VLA `2026-09-10_x_navdp_lite3_rented4090` inputs after checking
their recorded hashes. Robot upstream commit is `1f46ba1f86c72ddafd3d79e1e9725805c202bf2b`;
the imported machine-dog interface commit is `a2e98845a212bd6a2128af778cb1304eeb660f5f`.
Keep the existing `7030ba47…6581b` ONNX policy, 45-feature observations, term-major
10-frame history, 12-joint order, 20/0.5 PD gains, velocity-dependent 24/36Nm
limits, 1ms physics and 20ms policy period. Do not retrain or tune the policy.

The explicit local solver choice is Newton `SolverMuJoCo(use_mujoco_cpu=True)`;
the preceding Go2 example used MuJoCo-Warp on CPU. Import MJCF with a free base,
collapse fixed foot joints, disable self-collision, preserve direct motor
actuators, and add a flat ground plane (friction1.0). This is a different physics
condition from Isaac. Retain the full named-joint mapping and exported solver
model. Independently check Newton observations against native MuJoCo coordinates
and compare requested with actual actuator force at every physics step.
Use the supported `update_data_interval=0` option: public `reset(state)` pushes
initial joint state into native MuJoCo immediately, which then retains its own
coordinates between steps. The default interval1 defers that initial sync to
the first physics step and is unsuitable for a pre-step cross-representation
observation assertion. This changes state synchronization, not motor/contact
thresholds. Exported direct actuators have no names in1.6.0; resolve their
transmission joint IDs and require a one-to-one ordered match.

Before video, check the existing 1000-frame golden trace at its recorded0.01
max-absolute policy tolerance and run a2s zero-command probe. Then record one
continuous12s trial:0–2s stand,2–6s vx0.5m/s,6–9s vx0.35m/s+yaw0.4rad/s,
9–12s zero command. No resets or trajectory playback. Qualification requires
finite state/action, a measured advancing solver clock, nonzero applied forces,
at least0.2m planar displacement, and after1s base height>0.20m and upright-axis
cosine>cos(30deg). Report last-second planar speed separately; do not infer
navigation stopping or stair performance from this scripted velocity trial.
