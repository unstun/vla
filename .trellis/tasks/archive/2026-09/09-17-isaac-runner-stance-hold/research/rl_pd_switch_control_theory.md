---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
method: WebSearch discovery + WebFetch of abstract/HTML pages (PDF text only where the fetch tool cached it); local read of V12 actuator/URDF records; own arithmetic in a scratch script
---

# RL-to-PD stance-hold switching: control theory and practice (literature note)

Status: `surveyed` only; nothing is reproduced or validated on Lite3. Evidence tags: [verified] = primary
text or code read; [verified-2nd] = exact condition read in a secondary source and re-derived by us;
[lead] = abstract, index or snippet only. One verbatim quote is used (copyright limit); other key points
are paraphrases.

## Bottom line

The literature splits a switch into two parts: continuity at the switch instant, and the transient after
it. Our torque-matched target covers only the first part. It is the textbook "realizable reference" /
state-reset device (Hanus 1987; Cheong & Safonov 2008). Sources in the same family say continuity alone is
not enough: Cheong & Safonov also reset fast states, Zaccarian & Teel bound the L2 output mismatch after
the switch, and Vrančić et al. (2024) show post-switch defects that the reset does not remove. The
variable-impedance condition of Kronander & Billard (2016) is only sufficient, and our calculation says our
0.5 s smoothstep passes it for any plausible joint inertia. The yaw oscillation is better explained by a
lightly damped mode (our estimate: ζ ≈ 0.2 at Kp 20 / Kd 0.5) excited by momentum present at entry, plus
the energy a stiffness ramp injects (rate ½·K̇p·δ², δ = displacement from the entry posture). Practice
points to three changes:
- choose Kd from a damping ratio (Kd = 2ζ√(Kp·I)) rather than as a fixed number;
- raise damping before stiffness, since a damping increase only dissipates energy;
- gate entry on a small-energy set, as Simplex/SeC handovers do, with a dwell time sized from the decay rate.

One caution: Isaac Lab flags explicit PD actuators as numerically fragile, and V12 has zero armature. Our
bound limits an unloaded knee to Kd ≲ 1.45 at a 5 ms step, so Kd 2.5 on knees needs a check.

## Summary table

| Source | Year | Rule (short) | Evidence | Implication for us |
|---|---|---|---|---|
| Hanus, Kinnaert, Henrotte | 1987 | Condition the controller with a "realizable reference" so its output equals the actual plant input | [lead] | q_hold is a realizable reference for the new gains; it acts at the switch instant only |
| Peng, Vrančić, Hanus | 1996 | "Conditioned transfer" is preferred to plain bumpless transfer (PID) | [lead] | Same family; the abstract states no post-switch guarantee |
| Vrančić, Huba, Bisták, Oliveira | 2024 | "Short-sightedness" of conditioning comes from the limits, not the anti-windup; it appears even with P control | [verified] | Torque limits (hip 24, knee 36 Nm) can still shape the transient after a matched entry |
| Graebe & Ahlén | 1996 | Bidirectional transfer posed as a tracking problem; no steady-state assumption | [lead] | Supports treating entry as tracking the pre-switch torque |
| Turner & Walker | 2000 | LQ-optimal bumpless transfer; reduces to Hanus in special cases | [lead] | Continuity vs post-switch error is a tunable trade-off |
| Zaccarian & Teel | 2005 | L2 bound on the post-switch mismatch between the actual output and an ideal target response | [lead] | Judge entry by post-entry excursion (yaw-rate L2), not torque continuity |
| Cheong & Safonov | 2008 | Bumpless = (a) u continuous at t_s AND (b) fast controller states reset to zero | [verified] | Analogue of (b): do not carry fast, lightly damped motion across entry |
| Sundström, Bauer, Guzmán, Hägglund, Soltesz | 2026 | Incremental PID changes parameters without bumps; with ki = 0 (P/PD) that is usually neither possible nor desired | [verified] | A PD gain change is meant to change the response; continuity needs an explicit offset |
| Kronander & Billard | 2016 | For H x¨ + D x˙ + K x = 0: ∃α>0 with D ≻ αH, K+αD−α²H ≻ 0, K˙+αD˙−2αK ≺ 0 | [verified-2nd] | Our ramp passes for H < 0.28 kg·m²; not the limiting factor |
| Ferraguti, Secchi, Fantuzzi | 2013 | An energy tank pays for stiffness variation, so passivity holds for any stiffness profile | [lead] | Our ramp injects ½K˙p·δ²; gate or budget it |
| Hespanha & Morse | 1999 | Switching among stable systems stays stable if switching is slow on average | [verified] | Size the dwell/lockout from the decay rate |
| Liberzon (book); Della Rossa & Tanwani | 2003; 2025 | τ* = sup ∫_s^{χ(s)} dr/Ψ(r); the linear case gives ln μ/λ | [lead]; [verified] | Our τ* ≈ 0.14 s < existing timers |
| Sha (Simplex) | 2001 | A verified safety controller and a decision module guard a complex controller | [lead] | RL = complex controller, stance hold = safety controller |
| Cao, Mao, Cai, Sha, Caccamo (SeC) | 2024 | Hard switch when sᵀPs ≥ ε; teacher target = χ·(current state); teacher dwell from the contraction rate | [verified] | Seed from current state (done); gate on an energy-like set; dwell from decay |
| Phan et al. (Neural Simplex) | 2020 | Reverse switching back to the neural controller, plus retraining | [lead] | Rejoin has precedent; no smoothness rule found |
| Mehmood et al. (Black-Box Simplex) | 2022 | Runtime checks replace static verification of the baseline controller | [lead] | No handover-smoothness rule |
| Colgate & Schenkel | 1997 | A sampled virtual wall is passive if b > KT/2 + \|B\| | [lead] | KT/2 = 0.15 at 5 ms: not binding for Kp 60 |
| Isaac Lab actuator docs | current | Explicit actuators can be numerically unstable; armature helps | [verified] | V12 armature is 0: check Kd 2.5 on knees |
| Chakraborty et al. | 2026 | Kp = M·ωn², Kd = 2ζ√(Kp·M); ζ = 1 held while stiffness changes (Spot, 60 → 40) | [verified] | Scale Kd with √Kp during the ramp |
| BeyondMimic G1 config (Liao et al.) | 2025 | Kp = armature·ωn², Kd = 2ζ·armature·ωn; ωn = 2π·10 Hz, ζ = 2; implicit actuator | [verified code] | Practice: over-damped joint PD with modelled reflected inertia |
| legged_gym A1; unitree_rl_gym deploy | 2021+; current | A1 uses Kp 20 / Kd 0.5; deploy ramps the target linearly for 2 s at fixed gains, then switches gains instantly | [verified code] | Common practice ramps targets, not gains |
| ros2_control JTC | current | Option to seed the controller state from the last command on activation | [verified] | Same "seed from last output" idea; no gain blending |

## Per-source notes

**Hanus et al. 1987**, Automatica 23(6):729–739, DOI 10.1016/0005-1098(87)90029-X [lead].
- The controller receives a "realizable reference", so its state stays consistent with the actual plant
  input. Automatic initialisation then gives bumpless transfer.
- What stays continuous is the plant input. Nothing is guaranteed after the switch; Walgama et al. (1992,
  cited in Vrančić 2024) call this short-sighted.
- Mapping: q_hold = q + (Kp_old/Kp_new)(T_old − q) is exactly a realizable reference for a stateless PD.

**Vrančić et al. 2024**, IFAC PID 2024 preprint, https://skoge.folk.ntnu.no/prost/proceedings/PID-2024/0066.pdf [verified].
- Short-sightedness (overshoot under two-sided limits) also appears with a pure P controller. The cause is
  the limitation itself, so it must be handled by other means.
- Mapping: a torque-matched entry can still saturate; watch knee torque and the speed derating.

**Zaccarian & Teel 2005**, Automatica 41(7):1273–1280, DOI 10.1016/j.automatica.2005.02.003 [lead; paywalled].
- Defines bumpless transfer as an L2/l2 bound, after the switch, on the mismatch between the plant output
  and an ideal target response; covers saturation.
- Mapping: measure ∫ yaw_rate² dt over the ramp, not only the torque jump.

**Cheong & Safonov 2008**, IFAC World Congress, p. 14415ff, DOI 10.3182/20080706-5-KR-1001.2555 [verified, pp. 1–3].
- Definition 1 requires u continuous at t_s and the new controller's fast states reset to zero. The
  authors add (b) so there are "no rapid transients immediately following controller switching".
- They note that Arehart & Wolovich (1996) ensured continuity but ignored post-switch transients.
- Mapping: our PD has no controller state, so the fast state carried across entry is the plant's own
  momentum. Enter when it is small, or remove it with damping first.

**Sundström et al. 2026**, arXiv:2604.15918, §3.7 and Table 2 [verified].
- The incremental form gives bumpless parameter changes when ki ≠ 0; Table 2 marks P/PD as not bumpless.
- Åström & Murray (*Feedback Systems*, PID chapter) say a bump can be avoided by changing the state together
  with the parameters [lead: search snippet; the Caltech PDF failed a TLS check].

**Kronander & Billard 2016**, IEEE T-RO 32(5):1298–1305, DOI 10.1109/TRO.2016.2593492 [verified-2nd].
- The original is paywalled. The inequalities were read in Liang et al. 2022, Front. Neurorobot.
  16:789842 (DOI 10.3389/fnbot.2022.789842), Lemma 1 / Eq. (3), for H θ̃¨ + D(t)θ̃˙ + K(t)θ̃ = 0 with H a
  constant SPD target inertia.
- Our scalar re-derivation matches: V = ½H(ẋ+αx)² + ½(K+αD−α²H)x² gives
  V˙ = −(D−αH)ẋ² + ½(K˙+αD˙−2αK)x².
- With constant D, the condition reduces to K˙/K < 2α < 2D/H (sufficient only).
- In this Lyapunov function a rising D tightens the bound, yet physically raising damping only dissipates
  energy.

**Ferraguti et al. 2013**, ICRA pp. 4948–4953, DOI 10.1109/ICRA.2013.6631284 (from index) [lead].
- A tank stores dissipated energy; stiffness may change only while the tank can pay for it.
- Abu-Dakka & Saveriano (arXiv:2010.06246, §3.1) [verified] describe both approaches qualitatively and give
  no damping-ratio rule.

**Hespanha & Morse 1999**, 38th CDC pp. 2655–2660, DOI 10.1109/CDC.1999.831330 [verified, pp. 1–4].
- Average dwell time: N_σ(t,τ) ≤ N0 + (t−τ)/τ_D. Theorem 2 proves a finite τ_D* exists; the jump factor is
  V_p ≤ μV_q (Eq. 8).
- The explicit τ_D* is proved in their ref. [19]. The result assumes a common equilibrium, which our switch
  lacks.
- **Della Rossa & Tanwani** (arXiv:2405.03560; ESAIM COCV 2025), Prop. 2 [verified], give
  τ* = sup_s ∫_s^{χ(s)} dr/Ψ_ε(r). With ρ = λs and χ = μs this is ln μ/λ (our reduction). Liberzon,
  *Switching in Systems and Control* (Birkhäuser 2003), states that form [lead].

**Cao et al. 2024 (SeC-Learning Machine)**, arXiv:2409.05898, Eqs. 9, 12 and 22 [verified]; Unitree A1.
- Hard switch (no blending) to the model-based teacher when sᵀPs ≥ ε.
- The teacher's target is χ·s(k) with χ ∈ (−1, 1), i.e. seeded from the current state.
- The teacher keeps control for τ ≥ ⌈(ln δ − ln e*ᵀP̂e*)/ln β⌉ steps; the student's unsafe actions are
  corrected in its replay buffer.
- Mapping: gate entry on a quadratic energy-like set (body rates and joint velocities) and size the
  minimum hold from the measured contraction rate.

**Colgate & Schenkel 1997**, J. Robotic Syst. 14(1):37–47,
DOI 10.1002/(SICI)1097-4563(199701)14:1<37::AID-ROB4>3.0.CO;2-V [lead].
- The inequality b > KT/2 + |B| (b = physical damping, T = sample period) was read as restated in Ghavifekr
  et al., Robotica 36(4) 2018 (arXiv:2008.06685). The extracted symbols were partly garbled.
- The same review cites a less conservative stability form, b > KT/2 − B.
- Kd bounds under feedback delay (Insperger, Milton & Stépán 2013): [lead], not read. They do not apply to
  the Isaac loop, where only the target is delayed.

**Isaac Lab actuator docs** (https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/actuators.html)
[verified].
- The implicit PhysX PD adds numerical damping; explicit models can be numerically unstable; raising
  `armature` helps.
- Local fact: V12 runtime `default_joint_armature` is 0.0 for all 12 joints (`machine-dog/artifacts/2026-08-20_lite3_official_published_config_zero_action_diagnosis/tracked_logs/remote_runtime/runs/v12_locked_baseline/smoke/v12_locked_baseline_1steps.json`;
  the record does not name its machine).
- `Lite3Actuator` subclasses the explicit `DelayedPDActuator`, with a delay of 0–4 substeps.

**Other citations (details in the table).**
- Peng, Vrančić, Hanus 1996, IEEE Control Syst. Mag. 16(4):48–57, https://ieeexplore.ieee.org/document/526915/.
- Graebe & Ahlén 1996, IEEE TCST 4(1):92–99, https://ieeexplore.ieee.org/document/481772/ (needs plant knowledge, per Cheong & Safonov).
- Turner & Walker 2000, Automatica 36(8):1089–1101, https://www.sciencedirect.com/science/article/abs/pii/S0005109800000212.
- Sha 2001, IEEE Software 18(4):20–28, DOI 10.1109/MS.2001.936213. Phan et al., NFM 2020, arXiv:1908.00528. Mehmood et al., NFM 2022, arXiv:2102.12981.
- Chakraborty et al. 2026, arXiv:2609.09492, Eq. 3. BeyondMimic: Liao et al., arXiv:2508.08241; code `HybridRobotics/whole_body_tracking` `robots/g1.py`, unpinned `main`.
- legged_gym `legged_gym/envs/a1/a1_config.py` (master); unitree_rl_gym `deploy/deploy_real/deploy_real.py` (main); ros2_control JTC parameters page (rolling).

## Worked numbers for our gains (our calculation, not from sources)

Assumptions: physics step h = 5 ms; u = 3τ² − 2τ³ with τ = t/0.5 s; Kp 20 → 60; the `ramp` variant moves
Kd 0.5 → 1.0 on the same u; zero armature; inertias from the Isaac Lite3 URDF (shank 0.153 kg, COM 0.122 m
from the knee, iyy 9.1e-4).

1. **Ramp rate.** K˙p,max = 40·1.5/0.5 = 120 N·m/(rad·s) at t = 0.25 s. The largest K˙p/Kp is 3.52 s⁻¹, at
   t = 0.156 s.
2. **Kronander test.** We need max_t K˙/(2K − D˙) < α ≤ min_t D/H.
   ramp: α ≥ 1.80 s⁻¹, so H < 0.28 kg·m²; step1: α ≥ 1.76, so H < 0.57; step2p5: H < 1.42.

   Estimated inertias (unloaded knee ≈ 0.004, HipY ≈ 0.011 rough, yaw-mode equivalent 0.06–0.12 from
   item 3) are all below the bounds, so the ramp's shape and rate pass this sufficient test.
3. **Mode model.** The observed 0.35 s period gives ω = 17.95 rad/s. If one joint-space stiffness
   dominates, I_eq = Kp/ω² = 0.062 (Kp 20) to 0.124 (Kp 40), and ζ = Kd·ωn/(2Kp) with ωn ∝ √Kp.

   | Kp | Kd 0.5 | Kd 1.0 | Kd 2.5 | Critical Kd |
   |---|---|---|---|---|
   | 20 | ζ 0.22 | ζ 0.45 | ζ 1.12 | 2.23 |
   | 60 | ζ 0.13 | ζ 0.26 | ζ 0.65 | 3.86 |

   - Amplitude ratio per cycle, exp(−2πζ/√(1−ζ²)): 0.24 at ζ 0.22, 0.04 at ζ 0.45, 0.005 at ζ 0.65.
   - This matches what we saw: Kd 1.0 and Kd 2.5 help, and the final Kd 1.0 at Kp 60 is still underdamped.
   - Testable prediction: if stiffness sets the mode, its period should fall toward 0.20 s as Kp → 60.
4. **Entry momentum.** An entry yaw rate r0 = 0.5 rad/s into ω = 18 gives a peak excursion ≈ r0/ω =
   0.028 rad (1.6°) and an initial velocity amplitude near r0. The ±0.36 rad/s swing fits a free response to
   the entry state.
5. **Energy injected by the torque-matched ramp.** Near q0, τ = τ0 − Kp(t)·δ with τ0 = Kp0(T0 − q0)
   constant. With storage V = −τ0·δ + ½Kp·δ², the explicit time derivative is ∂V/∂t = ½K˙p·δ² ≥ 0.
   - If δ = 0.03 rad is held through the ramp (assumed), the injection is ½·40·0.03² = 0.018 J per joint.
   - For scale, yaw kinetic energy at 0.5 rad/s with an assumed I_zz ≈ 0.15 kg·m² (torso 0.070 from the
     URDF, plus legs) is 0.019 J, i.e. the same order.
6. **Explicit PD integration bound.** For semi-implicit Euler with a = h·Kd/I and b = h²·Kp/I, the Jury test
   gives stability iff a < 2 and 2a + b < 4, i.e. Kd < 2I/h − h·Kp/2. Keeping Kd < I/h also avoids velocity
   sign flips from one step to the next.
   Unloaded knee (I 0.004): Kd < 1.45 at Kp 60, sign flips above 0.8, so **Kd 2.5 exceeds the bound**.
   HipY: Kd < 4.25. Loaded stance joints (I ≫ 0.01): not binding. PhysX may differ from this model;
   check the step2p5 runs for a 100 Hz alternation in knee velocity.
7. **Damping for Kp 60**, using Kd = 2ζ√(60·I): knee (I 0.004) Kd 0.98 at ζ = 1; HipY (I 0.011) Kd 1.62
   at ζ = 1; yaw mode (I 0.06–0.12) Kd 2.7–3.8 at ζ = 0.7, or 3.9–5.4 at ζ = 1. The targets conflict. Resolving that needs per-group Kd or modelled armature, as in the
   Isaac Lab docs and BeyondMimic.
8. **Dwell.** μ ≈ 60/20 = 3 (same equilibrium) and λ ≈ 2ζωn = 7.9 s⁻¹ (ζ 0.22) give τ* ≈ ln 3/7.9 ≈ 0.14 s.
   That is below the 0.5 s ramp, the 0.25 s rejoin and the 0.5 s lockout. The estimate is rough: the RL
   loop is not LTI, and the two equilibria differ.
9. **Sampled-data passivity.** KT/2 = 60·0.005/2 = 0.15 N·m·s/rad (0.03 at 1 ms). This is well below Kd, so
   it does not bind.

## Implications for the entry design (lead proposals; not validated)

- **Entry target:** keep the torque-matched seed. It is the textbook realizable reference, and SeC also
  seeds from the current state.
- **Ramp:** raise Kd first (or at the entry step). Then ramp Kp with Kd(t) = 2ζ√(Kp(t)·I_eq), using a
  per-joint-group I_eq and ζ ≈ 0.7–1. The smoothstep rate already passes the Kronander test.
- **Damping:** check the knee Kd against item 6, or add armature, before adopting Kd 2.5. The hips can take
  more damping than the knees.
- **Entry gating:** replace |yaw rate| ≤ 0.5 rad/s with an energy-like set, such as body-rate kinetic
  energy plus joint kinetic energy below a threshold (SeC). A 0.5 rad/s entry alone explains ±0.36 rad/s.
- **Acceptance:** use the post-entry L2 of yaw rate and joint velocity (Zaccarian–Teel spirit), not torque
  continuity alone.
- **Dwell:** size the minimum hold from the measured decay rate (SeC Eq. 22). The current timers already
  exceed τ*.

## Searched, nothing relevant

- The ros2_control controller_manager docs cover only `strictness` and activate-asap; nothing on
  continuity or gain blending.
- No primary rule was found for stiffness ramps in legged RL-to-PD stand transitions. unitree_rl_gym ramps
  the target at fixed gains; the Lite3 vendor stack goes RL → damping → stand (local survey).
- Blocked: PubMed (Insperger 2013, cookies); EPFL Infoscience (Kronander, HTTP 429); LAAS preprint
  (Zaccarian, bot check); ScienceDirect and Wiley (HTTP 403).
- Not relevant: the Frontiers 2026 single-delay stability paper (Cuesta-García & Márquez-Martínez) is
  generic, and arXiv 2511.12184 and 2503.04414 do not restate the Kronander condition.
