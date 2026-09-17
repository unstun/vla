# Isaac runner stance hold for V12 stops

Stage: planning (draft). Parent: `09-16-emos-harnessvln-reimplementation`.

## Goal

When the robot is told to stop, the Isaac runner should hand control from the V12 RL policy to a PD stance hold,
and hand it back when a new motion command arrives. Both transitions must be smooth. The runner should hold the
robot still without the policy's standing jitter, and resume walking without a fall, jump or contact.

## Background

- Dr Sun, 2026-09-17: "It's an issue with the inference in the robot's deployment program. The robot dog was
  supposed to use the V12 149999 weights. [...] it's almost impossible for the robot to stay perfectly still. It
  requires transitioning to a PD controller to hold the stance, but making that transition smooth is very
  difficult."
- Evidence: SCAN fix series episode 3 (`two_goal_20260917T090126Z_scanfix_e03`) failed the goal-B stillness check.
  One yaw-rate sample of 0.1595 rad/s (limit 0.15) came from the V12 policy running on a zero command.
  Sources: `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/isaac_series/e03_failure_analysis.md`
  and `RESULT.md`.
- The runs loaded the intended `model_149999.pt` (sha256 `a9d31dce…d5450`). The runner writes every command into
  `base_velocity` and steps the policy; it has no stance-hold mode.

## Decisions

- D1 (Dr Sun, 2026-09-17) Scope is the VLA Isaac runner only. The real-robot deployment program in `machine-dog`
  is not changed and stays read-only. A deployment fix would be a separate task opened by Dr Sun in that
  repository.

## Constraints

- Keep the V12 checkpoint, observation, action scale and training config unchanged; the change is only in how the
  runner applies actions around stops.
- Stillness thresholds, the 41 review checks and the SCAN/PCT stack (`scan_04`) stay unchanged. No threshold is
  relaxed to make the hold pass.
- The runner source used in Isaac is a VLA-owned copy (bridge exported from `machine-dog-nav` at a pinned commit, plus
  the recorded runner patch). Every change is a recorded, hash-checked local modification with its own run IDs;
  existing run packages stay immutable.
- No Isaac run before Dr Sun approves the run budget.
- The stance-hold mode must be switchable (on/off) so an A/B comparison with the current behaviour is possible.

## Requirements (draft; to be completed after the code survey)

- R1 A runner mode that enters a PD stance hold after the command has been zero for a defined time, and leaves it
  when a non-zero command arrives.
- R2 Smooth transitions in both directions: joint targets and gains blended over a defined time, with no command
  or torque step beyond defined limits.
- R3 The hold uses the robot's own recorded stance (or V12 default joint positions, to be decided). Kp/Kd and torque
  limits must respect the simulated actuator limits.
- R4 The policy's observation history (last actions and so on) stays consistent across the hold, so that resuming
  RL does not produce an action spike.
- R5 Records: mode, blend factor, joint targets, gains and torques are logged per step, and the walk review shows the
  mode.

## Acceptance Criteria (draft)

- [ ] AC1 Standing A/B on the flat platform (hold off vs on): body speed and yaw rate while stopped. Limits are to be
      set before any run.
- [ ] AC2 Stop-resume transitions: no contact-guard failure, no fall, and joint and body rate spikes within limits
      set before the run.
- [ ] AC3 The two-goal cancel/resume episode with `scan_04` passes the unchanged 41 checks over a repeated series
      (count and stop rule to be approved).
- [ ] AC4 The report states the claim boundary: simulation only, and not a real-robot deployment fix.

## Open questions for Dr Sun

- Q1 Hold target: the joint pose at the moment the hold starts, or V12's default standing pose (the latter needs a
  pose blend while standing)?
- Q2 Entry trigger: command zero for N seconds, the backend's stop request, or both?
- Q3 Blend time and gains: copy them from the real deployment program (read-only reference, if it has a stand mode)
  or tune them in simulation?

## Out of scope

- `machine-dog` deployment code, retraining V12, backend stop-evidence polling, and placed-obstacle scenes.
