---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
stage: planning
task: .trellis/tasks/archive/2026-09/09-17-isaac-runner-stance-hold
claim_boundary: "Survey only (label: surveyed). Nothing here was imported, reproduced or run. The run-data check uses the existing C1d walk runs on gpu5070ti; no new run was made."
---

# Switching a legged RL policy to a PD stance hold and back: papers, code and theory

**Question (Dr Sun, 2026-09-17).** Stop developing the entry in isolation. How do recent papers and open-source
code make the switch between an RL locomotion policy and a PD stance hold smooth?

**Method.**
- Three parallel web surveys, each with evidence labels:
  - open-source deployment code, read at pinned commits through `gh api`;
  - legged-robot papers, read in the arXiv HTML;
  - control theory.
- The main session re-read the key sources:
  - Disney biped arXiv 2501.05204 §VII-A;
  - Safe-Stop 2609.02358 §4.3 and §5.1;
  - `fan-ziqi/rl_sar@376d42c` and `DeepRoboticsLab/Lite3_rl_deploy@1c4a8f1`;
  - `NVlabs/GR00T-WholeBodyControl@7f15131`, `HybridRobotics/whole_body_tracking@cd65172`;
  - Isaac Lab `actuator_pd.py`.
- Our own C1d walk runs were also re-analysed.
- Detailed notes, all `reviewed: false`, in `.trellis/tasks/archive/2026-09/09-17-isaac-runner-stance-hold/research/`:
  - `rl_pd_switch_open_source_code.md` (17 stacks);
  - `rl_pd_switch_papers_legged.md` (about 25 papers);
  - `rl_pd_switch_control_theory.md`.
- Prior related survey (training-side stillness): `machine-dog/.pipeline/survey/zero_command_stillness_practice_2026-08-23.md`.

## Bottom line

- **Our design has no direct precedent.** No surveyed stack or paper switches automatically from an RL policy to a
  joint-PD hold on a zero command and changes the PD gains during the switch. No surveyed source reports a
  smoothness measurement for such a switch.
- **Surveyed systems avoid the problem instead:**
  - they keep the same low-level gains on both sides;
  - they switch only at a suitable moment;
  - they move the target gradually over 1–2 s from the measured state;
  - or they keep standing inside RL, as a separate balance policy or a stand-command input.
- **Control theory says torque continuity is only half the job.** Keeping the torque continuous (our
  torque-matched seed) handles the switch instant. The transient after the switch needs its own treatment.
  Raising damping before stiffness is the safe order.

## What the sources do

| Pattern | Sources (evidence) | Relevance to V12 |
|---|---|---|
| Keep the policy's gains; move only the target, over about 1 s, from the measured q to a stand pose | `fan-ziqi/rl_sar@376d42c` Lite3: key-triggered mid-walk, `fsm_lite3.hpp:86-91,204-208`; `himloco/config.yaml` sets fixed_kp/kd = rl_kp/kd = 40/1 [verified]. LimX Tron1 42/3.5 [agent-verified]. walk-these-ways rate limit [agent-verified]. ABS: one PD (Kp 30 / Kd 0.65) for both policies [agent-verified] | V12's gains (Kp 20 / Kd 0.5) are softer and less damped than every stack above. Our ramp variant, which kept close to V12's gains with a frozen target early on, gave the worst entry kicks. Moving to the default pose at Kp 20 would drop the load offset the policy holds at entry: knee target minus q is 0.24–0.31 rad (see the data check) |
| Start the stand move from the measured q and joint speed (cubic, velocity feed-forward), then step the gains | `DeepRoboticsLab/Lite3_rl_deploy@1c4a8f1` `liedown_state.hpp:98-112`, gains 100/2.5 [verified]. Most stacks use a measured-q start (legubiao, AgiBot, Booster, LimX) [agent-verified] | A manual lie-down, not a zero-command hold. A gain step caused our C1 hop |
| Switch only at a suitable moment | Disney biped 2501.05204 §VII-A: "the policy switch is delayed until the start of the next double support phase" [verified]. Safe-Stop 2609.02358 §4.3: both estimators must pass on each of the last K samples [verified]. RLOC: separate enter/exit limits [agent-verified] | Our gate already needs four loaded feet and a quiet body for 0.25 s. The data check shows the body was already quiet at every entry |
| Standing stays inside RL | GR00T WBC: \|cmd\| < 0.05 selects a separately trained Balance policy, with no dwell or blend (`g1_gear_wbc_policy.py:221-230`) [verified]. holosoma/ASAP: stand_command input with a pinned gait phase [agent-verified]. Safe-Stop: the stop policy "takes over by commanding velocity targets to the frozen locomotion network" (§5.1) [verified] | Needs training. Out of scope for this task (PRD out-of-scope list) |
| Blend instead of a hard switch | MELA (Sci. Robot. 2020) [abstract]; 2502.06676, where a manual switch caused "abrupt changes in estimated velocity" [agent-verified]; RPG 2604.21355 [agent-verified] | A timed crossfade from V12's live target to the hold target is untested for V12 |
| Re-seed the policy history on rejoin | unitree_rl_lab, AgiBot, legubiao, walk-these-ways; RoboJuDo warms the next policy for 10 steps [agent-verified] | Our rejoin is already smooth |
| Choose Kd from a damping ratio | BeyondMimic G1: `NATURAL_FREQ = 10 Hz`, `DAMPING_RATIO = 2.0`, Kp = armature·ω², Kd = 2ζ·armature·ω (`robots/g1.py:7-23` @cd65172) [verified]. Chakraborty et al. 2026 (arXiv 2609.09492) keep ζ fixed while Kp changes [agent-verified] | Kd 0.5 at Kp 20 is lightly damped (our estimate ζ ≈ 0.2). Per-group Kd (hip vs knee) is common |

**Theory [agent-verified unless noted].**
- **Bumpless transfer.** Hanus et al. 1987 [abstract] match the controller output at the switch; our torque-matched
  seed is this "realizable reference". Cheong & Safonov 2008 also require no fast transient after the switch. Zaccarian
  & Teel 2005 [abstract] bound the output mismatch after the switch.
- **Variable impedance.** Kronander & Billard 2016 (T-RO): stiffness may rise only as fast as damping allows. The
  condition was read through Liang et al. 2022 and re-derived. By the agent's own calculation, our 0.5 s ramp passes
  for any plausible joint inertia, so the ramp shape is not the limiting factor. Energy tanks (Ferraguti et al. 2013)
  [abstract] budget the energy a stiffness increase injects.
- **Dwell time and Simplex.** Hespanha & Morse 1999 (average dwell time). SeC-Learning (arXiv 2409.05898) seeds its
  safe controller from the current state and derives the hold time from the decay rate.

**Simulator fact [verified, Isaac Lab `actuator_pd.py:359-367`].** `DelayedPDActuator` delays position, velocity and
effort targets, but uses the current stiffness and damping immediately. The Lite3 MotionSDK packs Kp, Kd, target and
torque into one per-joint command (`include/robot_types.h:59-79` @b30a3ec) [agent-verified; the send path is a
prebuilt library]. On the robot, gains and targets arrive together. In our Isaac runner, a gain change reaches the
actuator 3 substeps (15 ms) before the matching target. No surveyed code compensates for this.

## Check against our C1d walk runs (main session, `isaac_runner/runs/walk_20260917T145650Z_*`)

Logged joint vectors use the articulation order: HipX ×4, HipY ×4, Knee ×4, each FL, FR, HL, HR.

| Entry (s) | Variant | Max \|yaw rate\| in 1 s | Angular speed before entry | Max \|target − q\| before entry: HipX / HipY / Knee (rad) |
|---|---|---|---|---|
| 0.40 (landing) | ramp / step1 / step2p5 | 0.363 / 0.280 / 0.178 | 0.085 | 0.201 / 0.104 / 0.285 |
| 7.40–7.52 (stop 1) | ramp / step1 / step2p5 | 0.221 / 0.063 / 0.153 | 0.094–0.174 | 0.083–0.107 / 0.081–0.219 / 0.243–0.284 |
| 15.28 (stop 2) | ramp / step1 / step2p5 | 0.179 / 0.117 / 0.073 | 0.059–0.079 | 0.097–0.106 / 0.078–0.086 / 0.288–0.311 |

- **The kick comes from the switch.** The body was already quiet before every entry (angular speed ≤ 0.17 rad/s,
  yaw rate ≤ 0.03 rad/s), and the kick begins 0.04–0.08 s after entry. A stricter body-speed gate is therefore
  unlikely to fix it. A 0.15 rad/s gate would also have delayed the best entry (step1 stop 1, 0.174 rad/s).
- **Policy activity is not the cause.** The largest target change per step in the last 5 steps before entry was
  0.03–0.06 rad at every entry. It does not separate good entries from bad ones.
- **Load offset.** At entry, V12 holds the knee targets 0.24–0.31 rad from the measured knee angle; at Kp 20 this
  offset carries the weight. The landing entry also has the largest hind-HipX offset (+0.178 HL, −0.201 HR,
  mirror-symmetric), and it is the worst entry in every variant. With three entry situations, this is only
  suggestive.
- **Damping at the switch helps.** At stops, damping at entry cut the kick: ramp was worst at both stops, and step1
  / step2p5 were better. The ramp variant starts near V12's gains with a frozen target.
- **Knee chatter not tested.** The 50 Hz logs cannot show a per-substep alternation, so the agent's explicit-step
  stability bound (knee Kd ≲ 1.45 at a 5 ms step with no armature) is untested. Logged knee speeds and torque
  ratios look alike across the variants.

## Mechanisms not yet tried (candidates, not validated for V12)

1. **Crossfade.** From V12's live target to the hold target over about 1 s, instead of freezing one policy sample,
   with damping raised at the switch. Precedents: blends (MELA, 2502.06676, RPG) and 1–2 s stand moves in code.
2. **Damping from a damping ratio, per joint group.** Hip vs knee (BeyondMimic practice), keeping the knee below the
   explicit-step bound.
3. **Delay gain changes by the actuator lag.** Would reproduce the real Lite3 packet. No code precedent; a
   simulator-fidelity fix only.
4. **Spawn-landing grace.** Enter only after the spawn landing has settled. Precedent: the machine-dog MuJoCo
   `FIXED_STAND_BOOT_GRACE_S` 1.0 s. This is a design change that must be fixed before any run, not an exclusion
   made after seeing results.
5. **Training-side, out of scope here.** A stand mode or balance policy inside RL (GR00T, holosoma, Safe-Stop), or
   training V12 with random hold segments (RPG idea).

## Open

- No surveyed source gives a validated rule for our exact case: a soft, lightly damped policy PD (Kp 20 / Kd 0.5)
  handed to a stiffer hold with a target delay.
- Any next variant is a project design choice. It must be recorded in the PRD before a run, with AC7/AC8 unchanged.
- Sources not accessible: Kronander & Billard (paywalled; condition read through a secondary source), Zaccarian &
  Teel, the ScienceDirect/Wiley pages; `qiayuanl/legged_control2` (404).
