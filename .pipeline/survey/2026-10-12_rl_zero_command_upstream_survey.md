---
origin: ai_only
reviewed: false
---

# Zero-command standing is a locomotion capability

Stage: experiment + analysis. Status: **surveyed**. No policy, navigation,
gain, training configuration or frozen version was changed. No new simulator
episode or upstream program was executed.

Update 2026-10-13: that execution statement describes this source survey only.
Subsequent v179/v182 diagnostic simulations are recorded separately. The v179
speed selection missed the existing project minimum planned cruise; its results
must not be generalized to nominal-speed stopping. See the correction below.

## Correction to the previous repair proposal

The v177 audit proves that the stop command reached the locomotion layer and
the fixed-standing transition did not occur. It does not prove that enabling
that transition, relaxing its contact gate, or latching individual legs would
produce stable stopping on stairs. The policy, contact dynamics, terrain and
handoff controller must be separated before choosing that repair.

The proposed per-leg handoff remains an **unvalidated hypothesis**, not the
selected next implementation. The preliminary 2 cm / 10 s hold target was a
proposed project target, not an upstream demonstrated capability or an industry
acceptance standard.

## Seven primary repositories, with configuration tracing

Commit pins, source hashes, licenses, README entry points and execution limits
are in `references/upstream/2026-10-12_rl_zero_command/repository_manifest.yaml`.
Five additional repositories supplied 31 selected text files. The earlier
legged_gym and official Lite3 references were re-read; one pinned legged_gym
configuration file was added. Related implementations are not independent
experimental evidence.

| Repository and inspected pin | Actual source behavior | Limit for the present problem |
|---|---|---|
| [legged_gym](https://github.com/leggedrobotics/legged_gym/tree/8fa29acc6fd1910c3d9659eef6310bdd301cde0a), `8fa29ac` | `legged_robot.py:872-901`: velocity-error reward, air-time reward disabled at low translational command, optional default-joint-pose penalty. `legged_robot_config.py:146`: base `stand_still=-0.0`. | A function named stand-still is not necessarily enabled. It penalizes posture error, not accumulated world-position drift. This base default does not establish every robot configuration's behavior. |
| [robot_lab](https://github.com/fan-ziqi/robot_lab/tree/500399ed75f510aeaff28705a8ce736c514dbec3), `500399e` | Go2 rough config enables `stand_still=-2`, `joint_pos_penalty=-1`, zero-command foot contact reward `0.1`, and `feet_slide=-0.1`. Base config gives posture multiplier 5 at low command and low measured speed. | This explicitly trains zero-command behavior. Current `feet_slide` subtracts body translation before its velocity cost (`rewards.py:574-585`); it must not be described as a world-frame position lock. This is not the direct V12 ancestor. |
| [unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab/tree/4960b84732b0c2ec593dccbfe963fda1bcd7b1e3), `4960b84` | Go2 config uses nominal standing sampling probability `0.1`, 10 s resampling, posture penalty `-0.7` with standing multiplier 5 when command is exactly zero and body speed <=0.3 m/s, and a foot-slide penalty. Deployment Go2 YAML separates `FixStand` and `Velocity`. | Sampling probability is not a measured fraction of successful stationary training steps. The inspected Velocity state's transitions do not automatically return to FixStand on zero velocity. Dedicated `stand_still()` exists but is not this Go2 config's active reward term. |
| [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab/tree/1425b15f73bd4095f0df53709d7c389c3eb9e790), `1425b15` | Base velocity config has 5% standing sampling, `stand_still=-1`. Go2 narrows the allowed posture variation during standing. Gait/contact timing reward is disabled at low total command. | `feet_slip` is also multiplied by a moving-command mask (`rewards.py:267-294`), so it is inactive at zero command. Its presence cannot be cited as a zero-command anti-slip guarantee. No inspected benchmark qualifies arbitrary stair stops. |
| [Walk These Ways](https://github.com/Improbable-AI/walk-these-ways/tree/0e7236bdc81ce855cbe3d70345a7899452bdeb1c), `0e7236b` | Training script sets gait frequency 2-4 Hz. `_step_contact_targets()` advances phase using that separate frequency input. Deployment has a separate nominal-pose calibration sequence. | Zero translational/yaw command does not by itself zero gait frequency in the inspected phase update. Calibration is not demonstrated automatic braking from an arbitrary stair contact state. Do not claim the robot inevitably steps or drifts without running its policy. |
| [Isaac Lab](https://github.com/isaac-sim/IsaacLab/tree/4f718b8fed4a24ac5fe53dfde35ff70dd70058f7), `4f718b8` | Velocity command generator first updates heading, then enforces all three components zero for sampled standing environments (`velocity_command.py:176-192`). Generic core velocity config uses 2%. | Command generation only; this cannot guarantee a trained policy's stopping accuracy. This is the current develop snapshot targeting Isaac Sim 6.1, not our frozen runtime version. |
| [official Lite3 sdk_deploy](https://github.com/DeepRoboticsLab/sdk_deploy/tree/9ea6ee94bfe90c9a36f5799d39f8dc1d821128db), `9ea6ee9` | Separate StandUp joint-target interpolation and RL control. `RLControlState::GetNextStateName()` remains RL unless another explicit mode is requested. | The stand-up sequence repeats nominal leg geometry, not a terrain-aware static equilibrium solver. It is not evidence that abruptly holding the present joints on stairs is safe. |

## Evidence from the source bound to our actual checkpoint

The current bridge declares machine-dog source commit
`8c3fdffa84b85be0704a10ea5b2533817d543822` and checkpoint SHA-256
`a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450`,
task `Wave-C-Stairs-V12-Lite3-v0`. These were read from
`runtime_sources/bridge/lite3_sim_bridge/run_isaac_v12_fallback.py:84-103`.
The sibling repository was inspected with `git show` at that exact commit;
its working tree was not used or modified. Five immutable blob identities and
bounded excerpts are retained in `local_v12_source_evidence.json`.

Three concrete source findings:

1. `tasks/go2/mdp/commands.py:233-259` calls its branch zero command but only
   clears `commands[..., :2]`. Yaw has already been sampled and is not reset;
   a subset is subsequently assigned a limiting yaw command. Its nominal
   curriculum endpoint 0.1 is therefore **not evidence of 10% fully stationary
   three-axis commands**, and the branch also has a remaining-time gate.
2. `tasks/lite3/env_cfg.py:354-442` does not connect the available `stand_still`
   function. Hip and thigh/knee posture penalties both have
   `stand_still_scale=1.0`, so their multiplier does not strengthen for standing.
   This does not mean that there is no incentive to stop: velocity tracking
   and other regularizers remain active.
3. The actor observation group (`env_cfg.py:125-172`) contains angular velocity,
   gravity, commanded velocity, joint state and previous actions with history.
   It has no explicit remembered world-space parking target. Inference: a
   velocity-only request does not instruct this actor to return to a position
   from which it has already drifted. Internal inference/history is not ruled
   out by this observation-interface finding.

The original training run's resolved configuration, overrides and sampled
command histogram were **not** established in this survey. Source deficiencies
are strong investigation leads, not proof of the fraction of true stops the
checkpoint experienced, nor proof of the sole cause of v177 drift.

As an illustrative calculation only, an exponential velocity reward with
sigma 0.25 retains `exp(-0.06^2/0.25) = 0.9857` of its maximum at 0.06 m/s
error, while constant motion at that speed covers 0.9 m in 15 s. This is not
the measured total reward or a reconstruction of the observed trajectory.

## Revised next experiment, before a controller repair

Keep the policy, gains, joint mapping, action history and contact model fixed.
Measure stop capability without navigation replanning, using short scripted
move-to-zero transitions on flat ground, a supported landing, and relevant
stair contacts. Use multiple approach speeds, directions and gait phases;
do not initialize the robot into an arbitrary unstable pose and call that a
faithful reproduction. Separate total braking displacement from subsequent
drift. Record base pose/speed, world-frame foot velocity, contact force, joint
targets and torque limits. Preserve the original full-route failure evidence.

Compare policy-only and the current automatic hold on the same host under
matched conditions. Interpret outcomes conditionally:

- Drift during policy-only flat-ground tests points first to zero-command
  capability or inference/deployment mismatch; verify the original training
  configuration and command distribution before proposing retraining.
- Stable flat stops but failed stair stops point toward contact/terrain
  coverage, feasible static support and policy limitations at those poses.
- Policy-only holds while automatic hold worsens behavior points toward the
  handoff design. Then a carefully bounded controller change is justified.
- Both fail at the same physical support geometry: establish whether that
  pose can stand at all before demanding zero motion there.

Do not loosen map/contact gates or force a frozen posture as a substitute for
this diagnosis. Retraining, a dedicated standing skill, or a support-aware
whole-body controller are possible later branches, not changes selected by
this source survey. Formal training and real-robot actuation remain unstarted.

## Evidence limits and reproduction

`inspect_sources.py discover` resolves metadata and commits; `fetch` obtains
only the selected UTF-8 files. No downloaded code is executed. Per-file hashes
and an offline verification receipt are retained with the manifest. Sources
are reference material, not integration. No stop success rate, 2 cm guarantee,
cross-simulator equivalence or real-robot conclusion was established here.

## Minimum-speed correction, 2026-10-13

Dr Sun identified a missing precondition in the diagnostic design. The existing
project contract specifies 0.6 m/s planned cruise, while v179 used only
0.2/0.35/0.5 m/s. The prior move from those results to a general model-stopping
diagnosis and standing-controller remedy was unjustified. v179 is retained as a
low-speed control. v182 changes only command amplitude to 0.6/0.8/1.0; its
`RESULTS.md` reports the completed cohort and actual walking speed.

The upstream command path was present in the inspected files but omitted from
the earlier interpretation. At robot_lab commit 500399ed75f510aeaff28705a8ce736c514dbec3,
`mdp/commands.py:43-47` zeros horizontal commands with norm at most 0.2 m/s.
`velocity_env_cfg.py:106-117` selects this threshold command generator. Standing
sampling and reward configuration are additional, distinct mechanisms. Neither
this threshold nor that project's policy performance is automatically transferable
to Lite3. This is source inspection, not a reproduced upstream stopping result.

The checkpoint's archived V12 `env.yaml` was subsequently read from the sibling
handoff artifact (read-only); it enables dynamic command resampling. Its pinned
`commands.py` excludes a dynamic interval around zero separately for X and Y,
based on remaining commanded distance and episode time. The initial ordinary
bound implied by the archived terrain dimensions is approximately 0.200 m/s per
axis, and special command branches can overwrite samples. This is distinct from
the project 0.6 m/s planned-cruise rule. The actual sampled-command histogram and
an exact universal stable walking threshold are not established. See
`versions/v182/results/minimum_speed_source_audit.json` and
`versions/v179/results/training_command_config.json` in the Newton experiment.

The higher-speed flat cohort has no late excursions over the descriptive 5 cm
flag (versus 4/12 low-speed stops), with a maximum 3.67 cm (versus 31.15 cm).
The stair scene retains 4/12 flags and a maximum 10.08 cm; speed also changes the
stopping location there. These results support conditioning the diagnosis on
walking speed; they do not identify the sole cause or validate the navigation
hold path. No model, stand takeover or training change was selected.
