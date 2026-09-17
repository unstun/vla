# Isaac runner stance hold for V12 stops

Stage: planning. Parent: `09-16-emos-harnessvln-reimplementation`.

## Goal

When the robot comes to a stop, the Isaac runner should hand control from the V12 RL policy to a PD stance hold,
and hand it back when a new motion command arrives. Both transitions must be smooth. The runner should hold the
robot still without the policy's standing jitter, and resume walking without a fall, jump or contact.

## Background

- Dr Sun, 2026-09-17: "It's an issue with the inference in the robot's deployment program. The robot dog was
  supposed to use the V12 149999 weights. [...] it's almost impossible for the robot to stay perfectly still. It
  requires transitioning to a PD controller to hold the stance, but making that transition smooth is very
  difficult."
- Evidence: SCAN fix series episode 3 (`two_goal_20260917T090126Z_scanfix_e03`) failed the goal-B stillness check.
  One yaw-rate sample was 0.1595 rad/s against a 0.15 limit, while V12 ran on a zero command.
  - Sources: `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/isaac_series/e03_failure_analysis.md`
    and `RESULT.md`.
  - V12's own zero-command stand in Isaac: yaw rate −0.101 to +0.126 rad/s, and 3.2 cm drift in 10 s
    (`machine-dog/artifacts/2026-07-18_v12_model149999_flat_standstill_diagnosis/README.md`).
- Code survey: `research/stance_hold_code_survey.md`.
  - Neither the Isaac runner nor the real Zig deployment has a PD hold after RL.
  - `machine-dog`'s MuJoCo preview has a qualified walk-to-stand state machine (V17). Its dynamic gate passed
    9/9 move-stand-rejoin runs, and a 73 s hold drifted 1.1 mm.

## Decisions

- D1 (Dr Sun, 2026-09-17) Scope is the VLA Isaac runner only. The real-robot deployment program in `machine-dog`
  is not changed and stays read-only. A deployment fix would be a separate task opened by Dr Sun in that
  repository.
- D2 (lead proposal, 2026-09-17) Dr Sun declined the design questions and said "continue". The recommended defaults
  below are used and he may override any of them.
  - **Base design:** port the MuJoCo state machine (RL → STAND_SETTLING → STAND_TRANSITION → FIXED_STAND → REJOIN).
    The hold target is torque-matched, and the policy keeps running in the background with the applied action
    fed back to it. The file is read and copied only; `machine-dog` is not edited.
  - **Gains:** the hold uses Kp 60 / Kd 1, the MuJoCo-qualified values, written to the V12 `Lite3Actuator` at run
    time. REJOIN blends back to Kp 20 / Kd 0.5 over 0.25 s.
  - **Trigger:** automatic. The command must be exactly zero, and the body must be quiet with four loaded, balanced
    feet. Any non-zero command cancels the settle or starts REJOIN.
- D3 (Dr Sun, 2026-09-17) Run budget approved: "approved, run the stand test after the check". C1 (stand A/B,
  2 × 60 s) runs after the A6 check pass; C2 (8 two-goal episodes) follows only if AC3 passes. About 30-35 min and
  7 GB GPU in total on the 5070 Ti host.
- D4 (Dr Sun, 2026-09-17) "yes, fix the entry and rerun the stand test". Run C1 (`stand_20260917T125239Z`)
  passed AC3, but the hold entry hopped: vertical speed +0.21 m/s and |yaw rate| 0.30 rad/s. The cause is the
  immediate Kp 20 → 60 step against position targets the V12 actuator applies 3 substeps late. Fix: ramp Kp
  (and Kd) to the hold values over 0.5 s at the start of STAND_TRANSITION. Each step moves the target so that
  `Kp(t) * (target(t) - q0) = Kp0 * (T0 - q0)`, which ends at the same torque-matched seed. This departs from
  the MuJoCo design, which had no actuator delay. AC7 is added before the rerun. Then one hold-on stand run
  repeats C1; the hold-off baseline is reused. C2 follows only if AC3, AC5 and AC7 pass.

## Constraints

- The V12 checkpoint, observation, action scale and training config stay unchanged. The change is only in which
  action and which gains the runner applies around a stop.
- Stillness thresholds, the 41 review checks and `scan_04` stay unchanged. No threshold is relaxed to make the hold
  pass.
- The runner used in Isaac is the frozen reference plus the recorded, hash-checked patch (`materialize_runner_patch.py`).
  The hold is added the same way, and existing run packages stay immutable.
- `--stance-hold off` is the default and must leave today's control path unchanged.
- No Isaac run before Dr Sun approves the run budget (implement.md step C).

## Requirements

- R1 A pure state-machine module (no Isaac import). It takes the command, joint state, policy target, body motion,
  tilt, foot forces, and the applied target and gains. It returns the joint target, Kp, Kd and whether the policy
  owns the joints.
- R2 Entry, hold, exit and rejoin behave as in the MuJoCo design (design.md section 2), with V12's gains, joint
  limits and 20 ms control period.
- R3 Runner integration:
  - the applied target goes to `wrapped.step` as an action, `(q_target − q_default) / 0.25`, so the policy's
    last-action observation is the applied action;
  - Kp/Kd are written to both actuator groups before each step;
  - the policy is still evaluated every step.
- R4 Per-step records in `metrics.jsonl` (additive fields): mode, transition reason, progress, applied Kp/Kd, applied
  target, and max applied torque ratio. The summary lists entries and exits. The walk review video shows the mode.
- R5 The launchers (`qualify_stand_runner.py`, `run_two_goal_pilot.py`) pass `--stance-hold {off,auto}`. The value
  is recorded in the run request and checked against the package.

## Acceptance Criteria (fixed before any Isaac run)

- [ ] AC1 Unit tests of the state machine:
      - entry gates (zero command, speed ≤ 0.15 m/s, |yaw rate| ≤ 0.5 rad/s, tilt ≤ 10°, all four feet ≥ 10 N,
        dwell-mean support shares in [0.35, 0.65] over 0.25 s);
      - a torque-matched seed, so the commanded PD torque is continuous at entry (difference ≤ 1e-6 Nm);
      - STAND_TRANSITION 2 s, then FIXED_STAND;
      - a non-zero command cancels settling or starts REJOIN (0.25 s smoothstep on target and gains);
      - disturbance exit after 0.25 s persistence, then a 0.5 s re-entry lockout;
      - non-finite input fails closed (the hold refuses and the runner stops the case);
      - `off` mode returns the policy target and V12 gains unchanged.
- [ ] AC2 Patch: `materialize_runner_patch.py --check` passes; with `--stance-hold off` the patched control step
      equals today's (test on the materialized text plus a mock-step test); the existing isaac_runner tests pass.
- [ ] AC3 Isaac stand A/B (`stand_probe`, 60 s, one run each with the hold off and on). Over the FIXED_STAND part of
      the hold-on run:
      - every sample has four feet above 1 N;
      - planar drift ≤ 0.02 m, max horizontal speed ≤ 0.02 m/s, max |yaw rate| ≤ 0.05 rad/s;
      - |roll| and |pitch| ≤ 5°;
      - no torque-clip step and no non-finite value;
      - FIXED_STAND is reached within 10 s of the zero command.
      The hold-off numbers are reported as the baseline, with no threshold.
- [ ] AC4 Two-goal series with `scan_04` and the hold on, 8 episodes (6 cancel at 0.40 m, 1 at 0.45 m, 1 at 0.50 m):
      - every episode passes the unchanged 41 checks;
      - stop rule as the SCAN series (PRD D11 there);
      - the report gives the pass count with its exact bound, the hold entries and exits, the time to hold, the max
        |yaw rate| inside each review still window, and the rejoin transitions.
- [ ] AC5 Transitions in every run: no non-foot contact above the 5 N guard, |roll| and |pitch| ≤ 10° during
      REJOIN, and no torque-clip step at an entry or rejoin step.
- [ ] AC7 Entry smoothness (added 2026-09-17 before the rerun, D4). In every hold-on run, over each entry window
      (from the first STAND_TRANSITION row to 1.0 s after it): max |yaw rate| ≤ 0.15 rad/s and max |vertical body
      speed| ≤ 0.05 m/s.
- [ ] AC6 The report states the claim boundary: simulation only, V12 in Isaac, one flat route, not a real-robot or
      deployment fix.

## Out of scope

- `machine-dog` deployment code, retraining V12, backend stop-evidence polling, placed-obstacle scenes, and a
  damping or passive mode.
