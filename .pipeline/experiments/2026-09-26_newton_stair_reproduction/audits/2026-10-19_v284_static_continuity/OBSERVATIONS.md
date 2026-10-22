# Confirmed findings and unresolved boundary

The v284 protocol is complete; the requested physical repair is not accepted.
Goal/PD: 3/10. Goal/PD plus sampled physical geometry: 1/10 (CM07).

1. Every actual global route stream retains one epoch and original geometry or
   its suffix. Endpoint rejection and shared no-route log counts are both zero.
   The largest post-motion measured low-speed interval is 31.183 s; the former
   approximately 80 s intervals are absent in these ten attempts. Seven missions
   still abort earlier, so this is not evidence of fluid completed navigation.
2. All seven failed recorded prefixes are sampled support/source/raw-clear.
   Every failed controller terminates with `Native SCAN has no executable
   trajectory before timeout`. Refinement/line-search failures are also logged;
   their full causal chain has not been established by a replay ablation.
3. S04 and CS03 arrive and hold PD but violate source solids, independently
   confirmed by original raw points. Their selected published-curve samples have
   positive source margins at the recorded excursion witnesses.

| Route/event | Native time s | Body source margin m | Applied command | Stance | Measured XY speed m/s | Selected curve source min m | Nominal endpoint discrepancy m |
|---|---:|---:|---|---|---:|---:|---:|
| S04 / first negative | 36.311672 | -0.004394 | [0.0, 0.0, 0.0] | STAND_SETTLING | 0.309540 | 0.150000 | 0.220232 |
| S04 / worst negative | 36.611507 | -0.051553 | [0.09373290091753006, -0.1299285888671875, 0.02017357386648655] | RL | 0.103560 | 0.150000 | 0.282786 |
| CS03 / first negative | 31.514309 | -0.012763 | [0.0, 0.0, 0.0] | STAND_SETTLING | 0.274828 | 0.097871 | 0.125095 |
| CS03 / worst negative | 31.814144 | -0.034650 | [0.0, 0.0, 0.0] | STAND_SETTLING | 0.038742 | 0.097871 | 0.155317 |

Both first sampled solid excursions occur with zero applied commands in
STAND_SETTLING while the body still moves at approximately 0.310 and 0.275 m/s.
S04 reaches its deepest excursion after RL resumes; CS03's deepest excursion
remains in STAND_SETTLING. At these witnesses the latest published curve is
past its nominal end. The execution/stance-drift gap therefore remains despite
removing v283's explicit local source veto and measured warm reset.

This is a recorded temporal chain, not exact internal phase reconstruction or
a counterfactual causal ablation. Nominal endpoint discrepancies measure body
displacement relative to that old endpoint, not a claim that the controller is
still executing an expired curve. Degenerate endpoint headings can fall back
to measured yaw and carry no zero-heading-error claim.

Applied near-zero-translation yaw transients remain (maximum 0.220 s under the
<=0.01 m/s, >0.1 rad/s definition). Final capture-region alignment is excluded.
Ordinary low-speed navigation counts include allowed final heading alignment
and must not all be called mid-route deadlocks.

The unresolved boundary is executable-curve availability and actual command to
stance/motion handoff, plus local infeasibility on the safe failed prefixes.
No successful repair for that boundary is claimed. No new native revision,
extra physical trial, wider hard boundary, relaxed scan deadline, scenario rule
or baseline promotion was performed. See RESULTS.md, the seven terminal bills,
per-route recorded_curve_diagnosis.json and command_continuity.json. Full query
inputs and raw recordings remain remote with hashes and regeneration code.
