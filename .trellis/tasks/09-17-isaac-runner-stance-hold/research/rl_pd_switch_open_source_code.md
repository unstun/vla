---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
method: read-only source reading via `gh api .../contents?ref=<sha>` at pinned commits; nothing cloned, built or run
---

# How open-source deploy code switches between RL and PD/stand controllers

**Bottom line.** None of the 17 stacks read here switches automatically from an RL policy to a *joint-PD* hold on zero
command, and none ramps Kp/Kd over time at an RL↔PD switch. Every PD hold we read steps the gains at entry.
The closest automatic zero-command switch keeps the robot on RL: GR00T-WholeBodyControl hands over to a separately
trained **balance policy** when |cmd| < 0.05, with no dwell or blend. holosoma/ASAP instead feed a `stand_command` into
one policy and pin the gait phase.

Four patterns differ from our design:
- **Hold start point.** Manual RL→stand paths usually start from the **measured q** (legubiao, rl_sar, DeepRobotics,
  AgiBot, Booster, LimX). DeepRobotics also matches the **measured joint velocity**, using a cubic spline.
- **Gains during the move.** Several stacks keep the policy's own gains while moving only the target: rl_sar's Lite3
  path (40/1), LimX (42/3.5), unitree_rl_gym, walk-these-ways.
- **Rejoin.** Stacks reset or re-seed the policy history on rejoin.
- **Delay.** No code delays gain changes to match a command delay. Real SDKs (Lite3 MotionSDK, Unitree LowCmd, LimX)
  carry gains and targets in the same per-joint command. In Isaac Lab, by contrast, only the targets are delayed.

No repo reports a numeric smoothness measurement for its transition.

## Comparison table

In the table, "meas q" = measured joint positions at entry and "step" = gains change in one tick. All rows are
[verified] at the listed commit unless marked [lead].

| repo | license | commit | trigger | hold target | gain / target schedule | damping | exit / rejoin | delay handling |
|---|---|---|---|---|---|---|---|---|
| unitreerobotics/unitree_rl_lab | Apache-2.0 | 4960b84 | joystick; RL→FixStand not configured; auto RL→Passive on bad orientation / timeout | last *commanded* q, then YAML waypoints | step Kp/Kd; piecewise-linear q over `ts` (go2 0,1,2 s) | go2 Kd 4–5 with Kp 60/80 | manual; step to policy gains; history filled with current obs, raw action zeroed | none; kp,kd,q in one LowCmd per 1 ms tick |
| legubiao/quadruped_ros2_control | Apache-2.0 | 5434c58 | manual cmd; RL→FixedDown/Passive only | meas q → stand/down pose | step Kp/Kd (80/3.5 default); q = tanh blend, exit allowed at tanh=0.905 (~1.8 s) | Kd 3.5 | manual after gate; obs default, actions 0, history cleared | none; same-tick interfaces |
| fan-ziqi/rl_sar (Lite3) | Apache-2.0 | 376d42c | key/gamepad, allowed mid-walk (RL→GetUp) | meas q → default pose | linear 1.0 s; snaps if max diff < 0.1 rad; gains = fixed_kp, which the Lite3 himloco config sets equal to RL (40/1) | Kd 1 | manual; InitRL resets obs/actions/history; old hold persists until first policy output | none; one `SendCmd` with q,dq,kp,kd,tau |
| DeepRoboticsLab/Lite3_rl_deploy | BSD-3-Clause | 1c4a8f1 | manual RL→LieDown; auto RL→damping on roll>30°/pitch>45° | cubic from meas q **and meas dq** → crouch | step Kp 100/Kd 2.5; cubic 1.5 s with velocity feed-forward | Kd 2.5 then Kd-only | StandUp → RL after 2×duration; policy obs zeroed | none; kp,q,kd,dq,tau in one matrix |
| DeepRoboticsLab/sdk_deploy (Lite3, M20) | BSD-3-Clause | 7d738b3 | same as above plus `safe_control_mode` | same | same | same | last action zeroed on enter | none |
| boston-dynamics/spot-rl-example | MIT | 3572c19 | manual (Enter); stop → BD stand controller | BD built-in stand | policy action scaled by min(0.1·k, 1) over 10 steps; gains sent only in first packet | robot-side [lead] | stop stream → BD stand [lead] | end_time = obs + 0.1 s; 5 ms extrapolation; latency key |
| mit-biomimetics/Cheetah-Software | MIT | c71c5a1 (2023) | user mode; auto velocity trigger commented out | body pos/rpy measured at entry (WBC, not joint PD) | transitionDuration 0 | n/a | n/a | n/a |
| Improbable-AI/walk-these-ways | NOASSERTION | 0e7236b | button (logging) or orientation fault, mid-run | meas q → nominal/low pose | policy PD gains unchanged; target rate-limited to 0.05 rad per 20 Hz step | policy Kd | `reset()`: actions 0, obs history 0 | none |
| NVlabs/GR00T-WholeBodyControl | NOASSERTION | 7f15131 | **automatic** \|cmd\| < 0.05 → Balance ONNX, else Walk ONNX; no dwell | balance policy output | same gains/scale; command interpolated upstream | policy | shared history and last action; instant switch | none |
| amazon-far/holosoma | Apache-2.0 | bccd4d7 | stand_command input; auto walk on non-zero velocity | policy (stand mode); WBT stiff hold at a configured pose | init ramp q += (q_def−q)·k/500; policy switch steps gains | policy / config | phase reset to [0, π]; no history reset | none |
| limxdynamics/tron1-rl-deploy-ros | Apache-2.0 | 14ac8d1 | automatic at start only (STAND→WALK) | meas q → init pose | linear 1.0 s at the **walking gains** 42/3.5 | 3.5 | action clipped so PD torque ≤ 80 N·m | none; one setCommand(q,dq,kp,kd,tau) |
| BoosterRobotics/booster_deploy | NOASSERTION | 7bb1462 | button; handover from built-in controller | meas q, primed before mode switch | prepare gains stepped; 500×2 ms linspace | config | policy.reset() | 0.1 s wait after priming |
| HansZ8/RoboJuDo | NOASSERTION | 70144b3 | manual policy switch | upper body only: meas q → pose | linear 75 steps; lower body stays on RL | policy | target policy history warmed for 10 steps before switch | none |
| AgibotTech/agibot_x1_infer | NOASSERTION | 9e0b818 | manual topic, walk→stand allowed, 1 s throttle | meas q → init pose | step to 80/1.5; linear 2.0 s (hard-coded) | 1.5 | LPF init to meas q; history filled with current obs, last action 0 | none |

## Per-repo notes (path:line at the pinned commit)

### unitree_rl_lab (main, last push 2026-05-25)
- **Transitions are YAML-only.** go2 allows Passive→FixStand, FixStand→Passive/Velocity and Velocity→Passive
  (`deploy/robots/go2/config/config.yaml:10-30`). b2, g1_23dof, g1_29dof and go2w also lack Velocity→FixStand.
  Automatic exits: bad orientation → Passive (`deploy/robots/go2/src/State_RLBase.cpp:18-23`); low-state timeout
  from any state (`deploy/include/FSM/FSMState.h:47-53`).
- **FixStand entry.** Steps kp/kd and sets `qs_[0]` to the q already in the outgoing LowCmd, i.e. the last
  *commanded* q (`deploy/include/FSM/State_FixStand.h:22-39`). Passive rewrites that q with measured q every tick
  (`State_Passive.h:41-44`). Interpolation is linear (`deploy/include/LinearInterpolator.h:9-31`); go2 uses kp
  60/80/80, kd 5/4/4, ts [0,1,2] (`config.yaml:19-26`).
- **RLBase entry.** Steps to the deploy.yaml gains (`State_RLBase.h:15-24`), then `env->reset()` in the policy thread
  (`:36`) zeroes raw actions (`isaaclab/envs/mdp/actions/joint_actions.h:78-81`) and fills each history with the
  current obs (`isaaclab/manager/manager_term_cfg.h:27-30`, `observation_manager.h:39-48`). The 1 kHz FSM
  (`CtrlFSM.h:54-55,80`) copies `processed_actions` every tick (`go2/src/State_RLBase.cpp:26-32`).
  [inference, not run] `processed_actions` is never reset, so ticks before the first policy step send stale or zero
  targets.
- **Packet.** q, kp and kd share one `lowcmd->msg_`, published once per tick (`FSMState.h:62-65`).
- **unitree_rl_mjlab** (Apache-2.0, 1425b15, 2026-04-13): `State_FixStand.h` is byte-identical [verified by diff].

### legubiao/quadruped_ros2_control (main, 2026-02-22; supports Lite3 with V12's RL gains)
- **RL exits** (`controllers/rl_quadruped_controller/src/FSM/StateRL.cpp:135-150`): cmd 1→PASSIVE, cmd 2→FIXEDDOWN,
  estimator safety→PASSIVE; no RL→FIXEDSTAND. FixedStand→RL needs `percent_ ≥ 1.5` (`StateFixedStand.cpp:13-26`).
- **FixedStand/FixedDown entry** reads measured q, commands it at once and steps kp/kd
  (`libraries/controller_common/src/FSM/BaseFixedStand.cpp:22-37`, `StateFixedDown.cpp:23-38`). `run()` uses
  `percent += 1/(1.2·f)`, `phase = tanh(percent)` (`BaseFixedStand.cpp:39-48`), so exit comes at 90.5 % of the move.
  The new state is entered one update after the decision (`RlQuadrupedController.cpp:74-93`).
- **StateRL entry** sets obs dof_pos to default and actions to 0, and clears the history (`StateRL.cpp:91-118`); every
  command carries rl_kp/rl_kd (`:373-399`).
- **Lite3 values.**
  - Rate and poses: 200 Hz, stand_pos (0,−1.0,1.8), down_pos (0,−1.22,2.61)
    (`descriptions/deep_robotics/lite3_description/config/robot_control.yaml:164-209`).
  - Stand gains: default 80/3.5 (`src/RlQuadrupedController.h:94-95`), not overridden in yaml lines 164-215.
  - Policy: rl_kp 20 / rl_kd 0.5, action_scale 0.25, decimation 4 (`.../legged_gym/config.yaml:5,18-22,37`).
  - Passive: kp 0 / kd 1 (`StatePassive.cpp:12-35`).

### fan-ziqi/rl_sar, Lite3 (main, 2026-08-16)
- **Mid-walk stand.** Key `0` or gamepad A moves RLLocomotion→GetUp (`src/rl_sar/fsm_robot/fsm_lite3.hpp:205-208`).
  GetUp records measured state (`:64-78`). When not coming from Passive, it interpolates from measured q to
  `default_dof_pos` over 1.0 s (`:88-91`). Rejoin needs `percent_getup ≥ 1` plus a key (`:102-107`); a 0.5 s
  "Policy transition" blend is commented out (`:181-182`).
- **`Interpolate`** (`library/core/rl_sdk/rl_sdk.cpp:531-587`) is linear. It jumps straight to the target if the
  first-call max|start−target| < 0.1 rad (`:544-556`), and writes fixed_kp/kd every tick (`:564-573`).
- **Gains equal the policy's.** `base.yaml` has fixed 60/1 and dt 0.005 (`policy/lite3/base.yaml:5-14`), but
  `himloco/config.yaml` sets fixed_kp = rl_kp = 40 and fixed_kd = rl_kd = 1 (`:20-35`). `ReadYaml` merges keys
  (`rl_sdk.cpp:469-488`) and `InitRL` loads config.yaml (`:225-229`), so after RL has run, GetUp keeps 40/1 and moves
  only the target. [verified by code path, not run]
- **Rejoin.** `InitRL` resets obs (actions 0, dof_pos default), outputs and history (`rl_sdk.cpp:185-208,239-245`).
  `RLControl` overwrites the command only when a policy output is queued (`:589-608`), so the hold persists for
  ≤ 1 policy period.
- **Packet.** The real Lite3 program packs q, dq, kp, kd and tau into one `RobotCmd` and one `SendCmd`
  (`src/rl_real_lite3.cpp:161-174`). The control loop runs at dt and the RL loop at dt·decimation (`:60-63`).

### DeepRobotics Lite3_rl_deploy (2026-09-15) and sdk_deploy (2026-09-17)
- **RL exits.** RL→LieDown on user mode (`state_machine/rl_control_state_onnx.hpp:135-137`); damping on user mode or
  roll/pitch limits (`state_machine/rl_control_state.hpp:113-125`).
- **LieDown** (`state_machine/liedown_state.hpp:86-121`).
  - Motion: a cubic from measured q *and measured dq* (`init_joint_vel_`, `:23-27,100-106`) to zero end velocity,
    with planned-velocity feed-forward.
  - Timing: 1.5 s (`parameters/control_parameters.h:66`), then a Kd-only phase, then zero command.
  - Gains: stepped to 100/2.5 (`parameters/lite3_control_parameters.cpp:12-13`).
- **StandUp** uses the same q/dq start (`standup_state.hpp:95-113`); RL is allowed after 2× the duration (`:139-150`).
- **Policy.** Kp 30 / Kd 1; entry zeroes `run_cnt_` and the obs (`run_policy/lite3_test_policy_runner_onnx.cpp:92-93,142-146`).
- **sdk_deploy** matches this.
  - Lite3 RL→LieDown/JointDamping (`src/Lite3_sdk_deploy/state_machine/quadruped/rl_control_state.hpp:133-137`).
  - Last action zeroed on entry (`src/Lite3_sdk_deploy/run_policy/lite3_policy_runner.hpp:165-172`).
  - M20 has the same shape (`src/M20_sdk_deploy/state_machine/quadruped_wheel/rl_control_state.hpp:134-140`).

### boston-dynamics/spot-rl-example (master, 2024-06-05)
- **Flow.** Built-in blocking stand (`python/spot/spot.py:74-85`) → Enter starts the joint stream
  (`python/spot_rl_demo.py:67-72`) → joint control activates once streaming runs (`spot.py:117-119,199-214`).
  Stopping reverts to BD's stand controller (docstring `spot.py:125`; smoothness [lead]).
- **Start ramp.** `test_scale = min(0.1·count, 1)` scales the action around the default joints
  (`python/orbit/onnx_command_generator.py:99-105`) for 10 steps (~0.18 s at ~56 Hz, `spot_rl_demo.py:45-46`). The
  raw output is fed back as last_action (`:114`).
- **Gains** go only in the first message (`:166-169`).
- **Latency.** end_time = obs + 0.1 s, 5 ms extrapolation, latency key (`:175-183`).
- **Debug hold.** Initial measured q with initial measured load as feed-forward (`:186-216`).

### Cheetah-Software, walk-these-ways, GR00T WBC, holosoma/ASAP
- **Cheetah-Software** (model-based, 2023).
  - Locomotion→BalanceStand uses `transitionDuration = 0` (`user/MIT_Controller/FSM_States/FSM_State_Locomotion.cpp:91-96,147-158`).
  - Safety gate: roll/pitch 40°, leg above hip, foot speed > 9 m/s (`:192-227`).
  - BalanceStand holds body pos/rpy measured at entry (`FSM_State_BalanceStand.cpp:36-56`); its velocity auto-trigger
    is commented out (`:85-96`).
  - The MPC stand gait captures the current xy/yaw (`Controllers/convexMPC/ConvexMPCLocomotion.cpp:119-129`).
- **walk-these-ways.** `calibrate()` steps from measured q to the nominal pose at ≤ 0.05 rad per 0.05 s
  (`go1_gym_deploy/utils/deployment_runner.py:88-108`), through `agent.step`, i.e. unchanged policy kp/kd
  (`envs/lcm_agent.py:189-205`). It is called mid-run on logging buttons or an orientation fault
  (`deployment_runner.py:159-200`), then `reset()` zeroes actions (`lcm_agent.py:219-223`) and history
  (`envs/history_wrapper.py:44-48`).
- **GR00T WBC.** `norm(cmd) < 0.05` selects policy_1 = Balance, else Walk
  (`decoupled_wbc/control/policy/g1_gear_wbc_policy.py:221-230`; order in `control/main/teleop/configs/configs.py:80`).
  Both share one history containing `self.action` (`g1_gear_wbc_policy.py:129,150-161`) and one action scale/default
  pose (`:233-236`). The navigate command arrives interpolated (`g1_decoupled_whole_body_policy.py:64-72,122`).
- **holosoma.**
  - Stand/walk gating: velocity gated by `stand_command`, auto-walk on non-zero velocity
    (`src/holosoma_inference/holosoma_inference/policies/locomotion.py:14-31`).
  - Phase: pinned to π at |cmd| < 0.01, reset on restart (`:56-67`).
  - Init ramp: `q + (q_def − q)·k/500`, optional constant `interp_gain_scale` (`policies/base.py:639-679`).
  - WBT stiff hold: configured pose and kp/kd (`policies/wbt.py:370-383,405-412`).
  - Loco↔WBT switch: steps gains, re-inits phase, no blend (`policies/dual_mode.py:128-161`).
- **ASAP** (MIT, df5320c, 2026-01-06; holosoma's predecessor): phase time × stand_command
  (`sim2real/rl_policy/decoupled_locomotion_stand.py:87-93`); same 500-step ramp
  (`sim2real/rl_policy/base_policy.py:170-175`); manual `kp_level` scaling (`:281-284`).

### LimX, Booster, RoboJuDo, AgiBot
- **LimX tron1-rl-deploy-ros** (2026-08-10).
  - STAND: linear from measured q (`robot_controllers/src/PointfootController.cpp:20-31,91-102`) over 1.0 s at the
    walking gains 42/3.5 (`config/pointfoot/PF_TRON1A/params.yaml:30-31,54`), then automatic WALK.
  - WALK: clips each action so the PD torque from current q and qd stays ≤ 80 (`PointfootController.cpp:74-82`); the
    clipped action becomes lastActions_ (`:86`).
  - The Python port (035e4c9) mirrors this (`controllers/PointfootController.py:189-198`).
- **Booster booster_deploy.**
  - Handover: publish q = measured q with prepare gains and tau 0, wait 0.1 s, switch to Custom
    (`booster_deploy/controllers/booster_robot_controller.py:380-392,439-456`).
  - Standing: the same, then 500-step linspace at 2 ms (`:471-492`).
  - Upright gate: projected_gravity z > −0.5 → damping (`:418-433`).
- **RoboJuDo.**
  - Policy switch: reset the target policy, warm its obs for 10 steps, then switch instantly with `env.reset()` and
    new gains (`robojudo/pipeline/rl_multi_policy_pipeline.py:16-81`).
  - Loco↔mimic: 75-step interpolation from measured q, upper body only (`rl_loco_mimic_pipeline.py:27-28,77-119,282`).
- **AgiBot X1.**
  - Trigger: walk_leg→stand allowed (`src/module/control_module/cfg/rl_x1.yaml:28-31`), 1 s throttle, all controllers
    restarted on entry (`src/control_module.cc:34-40`).
  - pd_stand: from measured q (`src/pd_controller.cc:46-51`), linear over a hard-coded 2.0 s
    (`include/control_module/pd_controller.h:23-24`, `pd_controller.cc:72-73,93`), stepped to 80/1.5
    (`rl_x1.yaml:209-213`).
  - "keep": holds measured q at Kp 500 (`pd_controller.cc:87-88`, `rl_x1.yaml:164`).
  - RL restart: LPF re-init to measured q; history filled with the current obs, last_action = 0
    (`src/rl_controller.cc:72-74,209-228`).

### Isaac Lab / mjlab actuator semantics and the real Lite3 packet
- **Isaac Lab** (BSD-3-Clause; develop e836331 and main b0542fe, pushed 2026-09-17).
  - **Only targets are delayed.** `DelayedPDActuator.compute` sends positions, velocities and efforts through
    `DelayBuffer`s, then applies the ideal PD with the *current* `self.stiffness`/`self.damping`
    (`source/isaaclab/isaaclab/actuators/actuator_pd.py:359-367` main, `:503-509` develop; ideal PD `:186-195`).
  - **Lags.** Resampled per env at reset (`:335-357`). While the buffer holds fewer samples than the lag, it returns
    the newest one (`utils/buffers/delay_buffer.py:160-166`).
  - **Runtime gain changes.** PhysX gains are 0 for explicit actuators (`assets/articulation/articulation.py:1765-1769`),
    and `write_joint_stiffness_to_sim` skips actuator models (`:665,694`). A change must write
    `actuator.stiffness`/`damping`, as `randomize_actuator_gains` does (`envs/mdp/events.py:541,630-649`); it then acts
    on the next substep, ahead of the delayed target.
- **mjlab** (Apache-2.0, 8ee51fb): `delay_command` delays only the three command-target fields, never feedback
  (`src/mjlab/actuator/actuator.py:151-166`). `dr.pd_gains` exists (`src/mjlab/envs/mdp/dr/actuator.py`) [lead].
- **Lite3_MotionSDK** (MIT, b30a3ec, 2026-01-17).
  - Structs: `JointCmd {position, velocity, torque, kp, kd}` (`include/robot_types.h:59-66`), 12 of them per
    `RobotCmd` (`:69-79`), one `Sender::SendCmd` (`include/sender.h:45-47`). The implementation is a prebuilt `.so`, so
    the wire format is [lead].
  - Example hold: kp 80 / kd 0.7 from measured q (`src/motionexample.cpp:70-71,88-96`).
  - Consequence: on the robot, gains and targets sent together arrive together; in our Isaac runner, gains lead
    targets by the actuator lag.

## Mechanisms we have not tried (found in code; not validated for V12)
1. **Keep the policy gains and move only the target** (rl_sar Lite3 40/1, LimX 42/3.5, walk-these-ways,
   unitree_rl_gym `deploy/deploy_real/deploy_real.py:101-127`). This removes the Kp step.
2. **Start the hold from measured q** (legubiao, rl_sar, AgiBot, Booster, LimX). unitree_rl_lab, like us, uses the last
   commanded q.
3. **Match measured joint velocity:** a (q, dq)-matched cubic with velocity feed-forward (DeepRobotics). This targets
   residual motion after walking.
4. **Shape the target schedule:** rate limits of 0.05 rad per 20 Hz step (walk-these-ways); a tanh schedule with a
   90 % exit gate (legubiao); snap-to-target within 0.1 rad (rl_sar); 1–2 s moves instead of our 0.25–0.5 s.
5. **Torque-bounded action clip** from current q and qd, with the clipped action fed back (LimX).
6. **Stand as an RL mode:** a separate balance policy switched at |cmd| < 0.05 (GR00T), or a `stand_command` input
   with a pinned gait phase (holosoma/ASAP).
7. **History at switches:** warm the next policy's history for N steps (RoboJuDo); fill it with the current obs and
   zero the last action (AgiBot, unitree_rl_lab); or zero it (walk-these-ways, legubiao).
8. **Action-magnitude ramp at policy (re)start**, `min(0.1·k, 1)` (Spot). Also **upstream command smoothing** to zero
   (GR00T).
9. **Prime the hold before the gain/owner change** (Booster); send gains only once (Spot).
10. **Delay gain changes by the target lag.** Derived, not found as code: real SDKs pack gains with targets, while
    Isaac Lab applies `actuator.stiffness` at once and the target 3 substeps later.

## Not found / dead ends
- **No gain ramp or automatic PD hold.** None of the 17 stacks switches automatically from RL to a joint-PD hold on
  zero command or ramps Kp/Kd at a switch. The only other gain changes are holosoma's constant `interp_gain_scale` and
  ASAP's manual `kp_level`.
- **No smoothness numbers or delay handling.** No repo reports a transition measurement. Delay handling at a switch is
  limited to Spot's end_time/extrapolation and Booster's 0.1 s priming wait.
- **legged_control2 is unavailable.** `qiayuanl/legged_control2` returns 404.
  - `qiayuanl/unitree_bringup` (no license, 8a0f308, 2026-08-19) switches StandbyController (80/3) ↔ OnnxController
    (35/0.5) via joystick `SwitchController` (`config/go2/controllers.yaml:5-42`, `config/go2/joy.yaml:23-40`).
  - The controller source is not readable; HybridRobotics/motion_tracking_controller (MIT, 742924f) subclasses the
    same `RlController` (`src/MotionTrackingController.cpp:8,37-50`). Bumpless behaviour is [lead].
- **Not inspected:**
  - booster_gym (superseded by booster_deploy).
  - HumanoidVerse (no deploy paths in its tree).
  - TienKung and EngineAI (no official deploy repo found by `gh search`).
  - mjschock/embodied-agent.
  - leeygang/wildrobot (no license, 0 stars): standing→walking action ramp
    (`runtime/wr_runtime/control/run_policy.py:164-191,2811-2880`) [lead].
- **unitree_rl_gym `deploy_real.py`** is boot-only (`:249-252`) and was not re-surveyed beyond that.
