---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
method: WebSearch + arXiv API discovery; arXiv HTML read via WebFetch and text grep piped to stdout (no files saved); quotes checked against the HTML text
---

# Switching between an RL policy and another controller on legged robots (literature)

Labels:
- **[verified]**: mechanism and quote read in the arXiv HTML text.
- **[verified-abs]**: abstract or metadata only.
- **[lead]**: search snippet only.
- **Inference**: our reasoning for Lite3, not a claim from the paper.

## Bottom line

Many legged systems switch at run time between a learned policy and another controller: recovery/fall,
safe-stop, stance, model-based teacher, or a skill library. **No paper found changes joint PD gains at the
handover or measures the transient a gain step causes.**

They avoid the problem in four ways:
1. **Same low-level actuation on both sides.**
   - ABS: Kp 30 / Kd 0.65 for both policies.
   - Phy-DRL / Simplex line: one shared MPC layer.
   - Safe-Stop: a stop policy drives the frozen locomotion network through velocity commands.
2. **Switch only in a compatible state.** Disney waits for double support. Others use gait-phase checks,
   windowed or hysteretic gates, or separate activation and deactivation limits.
3. **Blend instead of switching.** MELA, 2502.06676 and RPG use learned gates; UEREBot blends commands.
4. **Train the second controller on the first one's exit states.** ABS samples recovery initial states up to
   5.5 m/s; RPG randomises policy transitions in training.

Naive hard switches are reported as jerky (Barkour, Lee 2019 FSM). Stability of time-varying stiffness is a
manipulator topic: Kronander & Billard 2016 bound the stiffness rate relative to damping [lead]. No legged-RL
paper applies it.

**For our hold (inference):**
- Gate entry on foot contact and body rates, not only on zero command.
- Keep Kp 20 / Kd 0.5 and a continuous target at the switch instant.
- Move the target smoothly, then raise damping before stiffness once the body is quiet.

## Summary table

| Paper | Year / venue | Robot | What switches | How it is smoothed | Evidence |
|---|---|---|---|---|---|
| ABS, He et al., 2401.17583 | RSS 2024 | Go1 | Agile ↔ recovery RL (RA value ≥ −0.05) | Same PD (Kp 30 / Kd 0.65); recovery trained from agile-like initial states | verified |
| Safe-Stop, Long et al., 2609.02358 | arXiv 2026 | G1 (sim + 150 hw trials) | Behaviour policy → learned stop policy, or damping | Stop policy commands the frozen locomotion net; K-sample window gate; speed-envelope rewards | verified |
| Stoppability monitors, Sun et al., 2603.22703 | arXiv 2026 | G1 | Nominal → fallback to a stance "MRC" | Monitor predicts whether the fallback succeeds; no transient analysis | verified (partial) |
| Bipedal character, Grandia et al., 2501.05204 | RSS 2024 | Disney biped | Stand ↔ walk RL policies | Walk→stand waits for double support; 2 past actions as input; smoothness rewards | verified |
| Barkour, Caluwaerts et al., 2305.14654 | arXiv 2023 | Barkour quadruped | Specialist policies; recovery policy | Jerks reported; distilled generalist is smoother | verified |
| ANYmal Parkour, Hoeller et al., 2306.14874 | arXiv 2023 | ANYmal | Skills chosen by a learned navigation policy | Navigation trained with skills in the loop; "smooth" (qualitative) | verified |
| Recovery controller, Lee et al., 1901.07517 | IEEE 2019 | ANYmal | Self-right / stand-up / locomotion | Learned selector; FSM transitions "often unsmooth" | verified |
| RLOC, Gangapurwala et al., 2012.03094 | T-RO | ANYmal | WBC ↔ RL recovery controller | Separate activation / deactivation limits | verified |
| Safe RL, T.-Y. Yang et al., 2203.02638 | 2022 | A1 (Laikago in sim) | Learner ↔ recovery, both via MPC | Hands back only after a predicted-safe rollout (no chattering) | verified |
| SeC / Runtime / Real-DRL: 2409.05898, 2503.04794, 2511.00112 | 2024–25 | A1 real; Go2 in Isaac Gym | DRL student ↔ physics-model teacher | Switch at the action/MPC layer; teacher dwell τ | verified; Real-DRL abs |
| MELA, C. Yang et al., 2012.05810 | Sci. Robot. 2020 | Real quadruped | Continuous expert mix | Gating network blends experts | verified-abs |
| Skill switching, W. Yu et al., 2502.06676 | arXiv 2025 | A1 | Weighted single-skill policies | Learned weights; manual switch unstable | verified |
| RPG, Xin et al., 2604.21355 | arXiv 2026 | G1 | Experts via a gate | Transition randomisation + smoothness-regularised gate | verified |
| Switch, Lau et al., 2604.14834 | arXiv 2026 | G1 | Skill-graph skills (one policy) | Buffer nodes + buffer-aware imitation | verified |
| BAT, Baek et al., 2604.01064 | arXiv 2026 | G1 | Two whole-body policies, chosen every K steps | Learned switcher; no blend at the switch | verified |
| Go2-W nav, 2606.21387 | arXiv 2026 | Go2-W | Learned stance ↔ locomotion policies | Stance policy handles stopping | verified |
| Setup policies, Tidd et al., 2101.09391 | RA-L 2022 | Sim biped | Walk → setup → target policy | Learned transition policy that also picks the switch time | verified |
| OCR filter 2412.09989; UEREBot 2602.07363 | 2024 / 2026 | Go1 / quadruped | Nominal ↔ filtered command | Smooth least-restrictive filter; threat-weighted command fusion | verified |
| Kronander & Billard, T-RO 2016 (DOI 10.1109/TRO.2016.2593492) | 2016 | Manipulators | Time-varying stiffness / damping | Stiffness-rate bound vs damping | lead |

## Per-paper notes

**ABS** (Tairan He et al., RSS 2024, https://arxiv.org/abs/2401.17583) [verified]
- **Switch:** an RA value network conditioned on the agile policy. Recovery runs when V̂ ≥ −0.05 (IX-B-1) and
  tracks a twist from a few gradient steps.
- **Actuation:** both policies use Unitree PD Kp 30 / Kd 0.65 (VIII-C-1); gains never change.
- **Recovery training:** 2 s episodes. Initial vx ~ U(−0.5, 5.5) m/s, ω ~ U(−1, 1) rad/s, roll and pitch
  ~ U(−π/6, π/6).
- **Quote (VI-C-1):** "These changes better accommodate the states that can trigger the recovery policy".
- **Code:** https://github.com/LeCAR-Lab/ABS

**Safe-Stop** (Junfeng Long et al., 2026, https://arxiv.org/abs/2609.02358) [verified]
- **Choice at a stop:** learned stop policy, or a fall policy that is just damping mode.
- **Gate:**
  - A stop-probability critic and an RA value must pass on each of the last K samples.
  - Calibrated thresholds: η_p = 0.90, η_r = −0.34 (§4.3). The ablation uses K = 5.
- **Stop policy:** "takes over by commanding velocity targets to the frozen locomotion network" (§5.1).
- **Rewards (App. A):** "smooth stop profile" and "smooth ang. vel. profile" (speed inside a shrinking envelope).
- **Results:**
  - 96.4 % stop success on 179,650 OOD initialisations, 3.89 % false-positive rate.
  - Re-falls after the stop: 0/61,540 in-distribution, 1/14,793 OOD.
  - G1 hardware, 5 clips × 30 trials: failures 3, 1, 1, 15, 28. Policy runs at 50 Hz.

**Stoppability monitors** (Yifan Sun et al., 2026, https://arxiv.org/abs/2603.22703) [verified, partial]: the
E-stop triggers a fixed fallback to a stable G1 stance; a monitor learns where that works. No transient
treatment. Quote (Fig. 1): "Emergency stops for humanoids cannot simply cut power".
Page: https://intelligent-control-lab.github.io/humanoid_stoppability/

**Bipedal robotic character** (Ruben Grandia et al., RSS 2024, https://arxiv.org/abs/2501.05204) [verified]
- **Policies:** standing ("perpetual") and walking ("periodic"), both output PD setpoints.
- **Timing:** 50 Hz policy, first-order hold to a 600 Hz actuator link.
- **Smoothing:** each policy sees the previous two actions; smoothness is rewarded.
- **Quotes (VII-A):**
  - "the policy switch is delayed until the start of the next double support phase".
  - "the switch of policies is virtually undetectable" (qualitative; Fig. 9).

**Barkour** (Ken Caluwaerts et al., 2023, https://arxiv.org/abs/2305.14654) [verified]: switching specialists
can be jerky; the distilled Locomotion-Transformer is smoother. Quote (VI-C): "the robot may exhibit jerky
motions when the previous specialist policy reaches a state".

**ANYmal Parkour** (David Hoeller et al., 2023, https://arxiv.org/abs/2306.14874) [verified]: the navigation
policy is trained with the frozen skills in the loop. Quote (II): "switches of the low-level skills are smooth
and unnoticeable on the real robot". No numbers.

**Recovery controller** (Joonho Lee et al., 2019, https://arxiv.org/abs/1901.07517) [verified]: a learned
selector picks self-righting, stand-up or locomotion. The hand-made FSM baseline waits 0.5 s for the state
estimator (II-G). Quote (III-C, FSM): "the transitions between the behaviors are often unsmooth".

**RLOC** (Siddhant Gangapurwala et al., T-RO, https://arxiv.org/abs/2012.03094) [verified]: the RL recovery
controller outputs joint position commands. It activates when any state criterion passes its activation limit;
control returns only when all are within separate deactivation limits (Table XI; values not extracted).
Quote (III-E): "RC is deactivated and the control switches back to the motion controller".

**Safe RL for legged locomotion** (Tsung-Yen Yang et al., 2022, https://arxiv.org/abs/2203.02638) [verified]:
both policies feed gait parameters to a shared MPC; hand-back waits for a centroidal rollout that predicts
safety. Quote (IV-B): "it may cause frequent switch between" the policies. 48.6 % fewer falls in sim.

**SeC-learning** (Hongpeng Cao et al., 2409.05898), **Runtime learning** (Yihao Cai et al., 2503.04794),
**Real-DRL** (Yanbing Mao et al., 2511.00112)
- **Evidence:** [verified] for the first two; Real-DRL is [verified-abs].
- **Student:** a Phy-DRL residual policy, i.e. RL action + physics-model action (2305.16614).
- **Teacher:** a linear feedback law. The coordinator hands over at the safety-envelope boundary for a dwell τ
  (SeC Remark 6.3).
- **Real A1:** uses convex MPC, so the switch sits above joint level. No transient analysis.
- **Quote (SeC §3):** "HA-Teacher has two missions: backing up safety and correcting unsafe learning".
- **Code:** github.com/Charlescai123/isaac-runtime-go2, github.com/Charlescai123/Real-DRL.

**MELA** (Chuanyu Yang et al., Sci. Robot. 2020, https://arxiv.org/abs/2012.05810) [verified-abs]: a gating
network blends expert networks online (trot, steer, fall recovery; real quadruped). Quote (Abstract): "MELA
constantly blends multiple DNNs".

**Skill-switching criteria** (Wanming Yu et al., 2025, https://arxiv.org/abs/2502.06676) [verified]
- A high-level policy outputs weights over skill policies (A1; 25 Hz policies, 1000 Hz PD).
- A manual switch "at an improper gait phase" put the rear knees near the ground.
- **Quote (4.4):** "manual switch caused dynamically instability, such as abrupt changes in estimated velocity".

**RPG** (Yucheng Xin et al., 2026, https://arxiv.org/abs/2604.21355) [verified]: experts are trained with
policy-transition and temporal randomisation; a gate over the frozen experts is regularised for torque and
contact smoothness (G1). Quote (I): "forcing each expert to learn robustness against discontinuous motions".

**Switch** (Yuen-Fui Lau et al., 2604.14834) [verified]: "we insert buffer nodes to enhance switching
smoothness and stability" (I; G1).

**BAT** (Donghoon Baek et al., 2604.01064) [verified]: an option-guided high level switches between two
whole-body policies (G1). Inertialization joins only the reference clips, not the controller switch.

**Go2-W navigation** (2606.21387) [verified]: a higher layer switches between stance, flat and rough RL
policies. Quote (4.2): the stance policy is "used for transitions such as" stand-up "and stopping from a moving
state". Its training initial states are lying-down drops.

**Setup policies** (Brendan Tidd et al., RA-L 2022, https://arxiv.org/abs/2101.09391) [verified]: simulated
biped; success 51.3 % → 82.2 % on a jump, 1.9 % → 71.2 % on sequences. Quote (I): "The setup policy also
learns when to switch to the target policy."

**OCR filter** (Albert Lin et al., 2412.09989) and **UEREBot** (Zihao Xu et al., 2602.07363) [verified]: both act
on the command, not the joints. Quote (UEREBot IV-A): "smooth transitions between path tracking and reflexive
evasion without discrete switching".

**Variable stiffness RL** (Dario Spoljaric et al., 2025, https://arxiv.org/abs/2502.09436) [verified]: the policy
outputs per-leg or per-joint stiffness, with K_d = 0.2·sqrt(K_p) (III-A, Eq. 6). Robot model not identified.

**Kronander & Billard, T-RO 2016** [lead]: per the snippet, a state-independent constraint links stiffness and
its rate to damping; some profiles are unstable even in free motion. Not read. Related [lead]: energy-tank
variable-stiffness control (Ferraguti et al.; arXiv 2604.20557).

## Mechanisms applicable to our joint-PD hold without retraining

1. **Gate entry on state.**
   - Evidence: Disney's double support; 2502.06676's phase failures; Lee's 0.5 s wait; Safe-Stop's K-sample
     window.
   - Inference: after a walking stop, keep V12 running on zero command. Enter the hold only after about
     5–10 consecutive steps with:
     - all four feet in contact;
     - |yaw rate| below a threshold;
     - small joint velocities.
   - This targets the 0.15–0.28 rad/s entries.
2. **Hysteresis and dwell.**
   - Evidence: RLOC's separate limits; Safe RL's predicted-safe hand-back; SeC's dwell τ.
   - Inference: separate enter and exit thresholds plus a minimum hold time.
3. **No actuation change at the switch instant.**
   - Evidence: every verified system keeps one PD or MPC layer across the handover.
   - Inference:
     - Enter at Kp 20 / Kd 0.5 with target = last RL target.
     - Move the target to the stance pose with a cubic or min-jerk profile. The deployment code already
       splines from the measured q and dq.
     - Raise gains only once the body is quiet, Kd before Kp.
   - Why (inference): a Kp step with position error e adds about ½·ΔKp·e² of energy (cf. Kronander & Billard
     [lead]).
   - Kd ∝ √Kp (2502.09436) is one way to couple the two gains; their constant is robot-specific.
   - Isaac delays targets by 15 ms but applies gains at once (task finding). So change gains only when the
     target already matches the measured state.
4. **Crossfade.**
   - Evidence: MELA, 2502.06676 and RPG use learned blends; UEREBot blends commands.
   - Inference: q* = (1−α)·q_RL(zero cmd) + α·q_hold, with α ramped over 0.2–0.5 s while V12 keeps running.
   - Untested; watch the yaw rate.
5. **Decelerate through the policy first.**
   - Evidence: Safe-Stop acts only through velocity commands to the frozen locomotion net, with a
     shrinking-envelope reward.
   - Inference: ramp the linear and yaw commands to zero, then apply mechanism 1.
6. **Rejoin with a consistent history.** Disney feeds the last two actions. Inference: keep seeding V12's
   action history with (q_hold − q_default)/0.25.
7. **Fallback.** Safe-Stop falls back to damping when an upright stop is judged infeasible. A damping fallback
   when our gate fails is consistent with this.

## Training-side alternatives

- **Learned stop or stance policy trained on exit states.** ABS recovery initial states; the Go2-W stance
  policy; Safe-Stop's stop policy over the frozen locomotion net, with stoppability estimators and a damping
  fallback.
- **Transition robustness in training.** RPG policy-transition randomisation plus a smoothness-regularised
  gate; Switch buffer states.
  - Inference: train V12 with random PD-hold segments that include gain ramps, so it learns post-hold states.
- **Learned transition or selector.**
  - Setup policies learn the transition and its timing (sim only).
  - Lee 2019, ANYmal Parkour, BAT and 2502.06676 train selectors or weights with the skills in the loop.
    Lee's hand FSM gave less smooth transitions.
- **Stand mode inside the policy.** Booster Gym (2506.15132, III-B) sets the gait cycle to zero for
  standing, samples "stand still" commands, and truncates sequences on command change. This is the category
  of the 2026-08-23 survey; Booster Gym was not on its list.
- **Policy-set stiffness.** Variable-stiffness action space (2502.09436).
- **Residual on the hold.** A Phy-DRL-style residual (2305.16614), here RL + PD stance hold.
- **Gain robustness.** PD-gain sampling in training (e.g., 2510.07094) [lead]. Actuator Dynamics Curricula
  (2609.09492, CoRL 2026) is tangential [verified-abs].

## Checked leads that are not switching papers

- **Single policy, no switch:** DTC (2309.15462; RL tracks MPC footholds), HOMIE (2502.13013), FALCON
  (2505.06776; one of BAT's two policies), Think on your feet (2502.18901, ICRA 2025).
- **No usable transition content:** 2512.18938 (FSM, no details), 2312.07778 (model-based, no RL),
  Shield-Loco (2606.07193; filters contact plans).
- **Not read in detail:** APT-RL (2607.13579, Sci. Robot. 2026, unified policy) [lead].
- **Isaac Lab actuator API page:** does not say whether gains are delayed; "gains apply immediately" is a task
  finding.

## Searched, nothing relevant

- **WebSearch:** RL ↔ model-based smooth transition; "policy switching"; "bumpless" transfer (only an
  energy-storage torque-bump paper); gain interpolation / jerk at a stand switch; PD gain switching torque
  jump; "stop-and-go"; humanoid damping / stand-mode handover; RL → WBC when stationary; safety-filter
  chattering / hysteresis.
- **arXiv API:** "policy / controller switching", "skill transition", "transition policy", handover / handoff,
  "mode switching", "gain scheduling", "variable impedance", blending, jerk / discontinuity, "safe stop" /
  stoppability, each crossed with legged terms.
- **Result:** no legged paper measures or fixes the transient from a joint-PD gain change, or from actuator
  latency, at a controller handover.
