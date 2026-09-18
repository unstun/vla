# Isaac runner stance hold for V12 stops

Stage: done 2026-09-18 (experiment + analysis complete; RESULT in `stance_hold_qualification/RESULT.md`). Parent: `09-16-emos-harnessvln-reimplementation`.

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
- D5 (Dr Sun, 2026-09-17) Standing alone does not show whether the PD ↔ RL switch is smooth. The transitions must
  be shown by walking a distance and stopping suddenly, then starting suddenly from a standstill and stopping
  again, with a side view of the walking. New scripted-walk case (AC8) and side follow camera, both lead design:
  - Command script, forward only: 0-4 s zero; 4-7 s vx 0.6 m/s; 7-12 s zero; 12-14.5 s vx 0.6 m/s; 14.5-20 s
    zero; finish request at 20 s. About 3.3 m along the two-goal route corridor (walls ±1.3-1.45 m).
  - Camera: follows the robot position, looks from its right side at 1.25 m and 0.2 m above the base. The heading
    is fixed at the start yaw so body twist stays visible. 25 fps.
  - Runs (the D3 budget, replacing the stand-only evidence as the transition test): hold off (RL-only baseline),
    hold on with the current entry (Kd ramps with Kp), and hold on with two entry-damping variants proposed on
    2026-09-17. A: Kd steps to 1.0 at entry. B: Kd steps to 2.5 at entry and eases to 1.0 by FIXED_STAND. Kd acts
    on measured joint velocity, which is not delayed. Kp still ramps over 0.5 s in all hold-on runs.
  - Selection rule, fixed before the runs: among hold-on variants passing AC5 and AC8, pick the lowest max
    |yaw rate| over all entry windows. If none passes, report and stop. C2 then uses the selected variant.
- D6 (Dr Sun, 2026-09-17) "yes, go with option 1 and run the walk test". Context:
  - The C1d walk runs selected no variant: every entry-damping variant failed AC8 b at one or more entries.
  - Dr Sun asked for published practice before another home-made entry. The survey is
    `.pipeline/survey/2026-09-17_rl_pd_stance_hold_switch_survey.md`.
  - No surveyed source changes PD gains at an RL → PD switch. Code keeps the gains and moves the target over 1–2 s
    (rl_sar Lite3, LimX), switches at a suitable moment (Disney biped, Safe-Stop), or blends controllers.
  - The body was already quiet before every C1d entry, so a stricter body gate is not the fix.

  Option 1, lead design (details in design.md section 8):
  - **Entry step.** Only damping changes: Kd goes to 1.0 at once, as in `step1`. Kp stays at the applied value
    (V12's 20), and the target is V12's live policy target.
  - **Crossfade.** Over T_x, the applied PD command blends V12's live PD command into the hold's PD command. The
    weight is w = smoothstep(t / T_x):
    - Kp = (1 − w)·Kp0 + w·60;
    - target = ((1 − w)·Kp0·P(t) + w·60·H) / Kp, with P(t) the current policy target and H the torque-matched
      seed at entry (unchanged).
    - From T_x on, the hold target and gains are those of FIXED_STAND. Kp therefore rises smoothly as the weight
      moves, and no torque-preserving target trick is needed at the switch.
  - **Variants.** Two new values of `--stance-entry-kd`; the flag name is kept from D5. `xfade1s` uses T_x = 1.0 s,
    the lower end of the 1–2 s moves found in code. `xfade2s` uses T_x = 2.0 s, the whole STAND_TRANSITION.
  - **Landing grace.** In both new variants, automatic arming (RL → STAND_SETTLING) is allowed only from 1.0 s of
    episode sim time. The earliest entry is therefore about 1.25 s after spawn. Precedent: MuJoCo
    `FIXED_STAND_BOOT_GRACE_S` 1.0 s. This is a design choice fixed before the runs. It is not an exclusion of the
    landing entry: AC8 a still requires FIXED_STAND before 4.0 s, and AC7/AC8 b apply to every entry.
  - **Unchanged.** The old variants (`ramp`, `step1`, `step2p5`), the thresholds, the command script, the camera
    and `--stance-hold off`.

  Runs (D3 budget, 5070 Ti host):
  - Two hold-on scripted-walk runs, `xfade1s` and `xfade2s`, about 3–4 min each.
  - The hold-off baseline is reused from C1d (`walk_20260917T145650Z_hold_off`). Isaac is deterministic up to the
    first entry; the report checks this row by row, as a reported item without a threshold.
  - The D5 selection rule applies unchanged to the two new runs. If neither passes AC5 and AC8, report and stop.
  - `run_two_goal_pilot.py` gains the `--stance-entry-kd` passthrough, so C2 can use a selected variant. C2 still
    runs only after the walk verdict is reported.
- D7 (Dr Sun, 2026-09-18, **post-result change**) "Change the AC7 rule to stop the evaluation window at a restart,
  and explicitly label it as a post-result change in the report." Context:
  - The C2 series (8/8 on AC4) failed AC7 as written in episode 6, 1 of 30 entry windows. The entry at 6.66 s
    stayed at |yaw| ≤ 0.063 rad/s. The planner resumed at 6.84 s (the first REJOIN row, step 341), and the V12
    restart peaked at 0.174 rad/s at 6.92 s inside REJOIN.
  - The original rule's window (a fixed 1.0 s after entry) had no clause for a restart. It was frozen before any
    two-goal run, and no hold-on run before C2 had a restart within 1 s of an entry.

  Amended AC7 window:
  - The window ends at the first row after the entry row whose `stance_mode` is neither STAND_TRANSITION nor
    FIXED_STAND. That row is the restart, normally the first REJOIN row, or RL after a direct exit. The restart
    row and every row after it are excluded.
  - The window also ends at 1.0 s after the entry row, as before, if that comes first.
  - Limits, entry definition and window tolerance are unchanged.

  Reporting and scope:
  - Every report shows both verdicts for each run: the amended one, and the original "as frozen before results"
    one, with the full-window maxima.
  - The report labels the amended verdict as a post-result change, made after the C2 result was known.
  - The thresholds file is re-frozen with the amendment recorded in it. The previous file (`0be59927…`) is kept in
    `stance_hold_thresholds_history/`.
  - AC8 b keeps its literal window, 1.0 s from the first STAND_TRANSITION row. The amendment applies to AC7 only.
- D8 (Dr Sun, 2026-09-18) "Make --stance-hold auto the default going forward." Implementation (lead):
  - The launchers `qualify_stand_runner.py` and `run_two_goal_pilot.py` default to `--stance-hold auto` with the
    `xfade1s` entry. xfade1s is the D5/D6-selected variant, and C2 ran with it. The old default `ramp`
    failed AC7 in C1b, so auto with ramp would be an unqualified default.
  - Old prepared packages keep their recorded meaning. A package without a `stance_hold` field ran with `off`;
    without `stance_entry_kd` it ran `ramp`. The execute-time mismatch guard therefore compares against these
    legacy values.
  - The runner patch keeps its own default `--stance-hold off`, and the launchers always pass the flag explicitly.
    The qualified patched runner bytes (`0649747e…`) therefore do not change.
  - The SCAN-fix series driver (`scan_fix_qualification/run_isaac_series.py`) gets an explicit `--stance-hold off`,
    so it keeps reproducing its recorded hold-off conditions.
  - `--stance-hold off` stays available.
  - As implemented (C4), `--stance-entry-kd` has no fixed parser default. It resolves to `xfade1s` with the hold
    on and `ramp` with the hold off, because the launchers accept only `ramp` with the hold off.
    `pointcloud_display/run_probe.py`, whose protocol requires the hold off, also passes `--stance-hold off`, and
    `P2B_RESULT.md` notes the flag for reproduction.

## Constraints

- The V12 checkpoint, observation, action scale and training config stay unchanged. The change is only in which
  action and which gains the runner applies around a stop.
- Stillness thresholds, the 41 review checks and `scan_04` stay unchanged. No threshold is relaxed to make the hold
  pass.
- The runner used in Isaac is the frozen reference plus the recorded, hash-checked patch (`materialize_runner_patch.py`).
  The hold is added the same way, and existing run packages stay immutable.
- `--stance-hold off` must leave today's control path unchanged. It was the launcher default until D8 (2026-09-18) and
  stays the runner patch default.
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

- [x] AC1 Unit tests of the state machine:
      - entry gates (zero command, speed ≤ 0.15 m/s, |yaw rate| ≤ 0.5 rad/s, tilt ≤ 10°, all four feet ≥ 10 N,
        dwell-mean support shares in [0.35, 0.65] over 0.25 s);
      - a torque-matched seed, so the commanded PD torque is continuous at entry (difference ≤ 1e-6 Nm);
      - STAND_TRANSITION 2 s, then FIXED_STAND;
      - a non-zero command cancels settling or starts REJOIN (0.25 s smoothstep on target and gains);
      - disturbance exit after 0.25 s persistence, then a 0.5 s re-entry lockout;
      - non-finite input fails closed (the hold refuses and the runner stops the case);
      - `off` mode returns the policy target and V12 gains unchanged.
      **Result 2026-09-18: pass, with a note** (the crossfade entry step changes Kd, so the literal torque-continuity clause no longer describes the entry step; the torque-matched seed is still tested).
- [x] AC2 Patch: `materialize_runner_patch.py --check` passes; with `--stance-hold off` the patched control step
      equals today's (test on the materialized text plus a mock-step test); the existing isaac_runner tests pass.
      **Result: pass** (materializer check clean; runner `0649747e…`; 63 pre-entry rows identical to hold off).
- [x] AC3 Isaac stand A/B (`stand_probe`, 60 s, one run each with the hold off and on). Over the FIXED_STAND part of
      the hold-on run:
      - every sample has four feet above 1 N;
      - planar drift ≤ 0.02 m, max horizontal speed ≤ 0.02 m/s, max |yaw rate| ≤ 0.05 rad/s;
      - |roll| and |pitch| ≤ 5°;
      - no torque-clip step and no non-finite value;
      - FIXED_STAND is reached within 10 s of the zero command.
      The hold-off numbers are reported as the baseline, with no threshold.
      **Result: pass** (C1 stand; yaw ≤ 0.0038 rad/s, drift 2.5 mm; run with the step entry).
- [x] AC4 Two-goal series with `scan_04` and the hold on, 8 episodes (6 cancel at 0.40 m, 1 at 0.45 m, 1 at 0.50 m):
      - every episode passes the unchanged 41 checks;
      - stop rule as the SCAN series (PRD D11 there);
      - the report gives the pass count with its exact bound, the hold entries and exits, the time to hold, the max
        |yaw rate| inside each review still window, and the rejoin transitions.
      **Result: pass**, 8/8 (one-sided 95 % lower bound 0.688).
- [x] AC5 Transitions in every run: no non-foot contact above the 5 N guard, |roll| and |pitch| ≤ 10° during
      REJOIN, and no torque-clip step at an entry or rejoin step.
      **Result: pass** in all 15 hold-on runs.
- [x] AC7 Entry smoothness (added 2026-09-17 before the rerun, D4). In every hold-on run, over each entry window
      (from the first STAND_TRANSITION row to 1.0 s after it): max |yaw rate| ≤ 0.15 rad/s and max |vertical body
      speed| ≤ 0.05 m/s.
      **Post-result amendment (D7, 2026-09-18, after C2):** the window also ends at the restart. That is the first row
      after entry whose mode is neither STAND_TRANSITION nor FIXED_STAND, and it is excluded. Reports give both
      verdicts.
      **Result: pass under the D7 amendment (post-result); fail as frozen** (C2 episode 6, 1 of 30 windows).
- [x] AC8 Scripted walk (added 2026-09-17 before any walk run, D5). For each hold-on run:
      - a) every zero-command phase (0-4, 7-12 and 14.5-20 s) reaches FIXED_STAND before the next non-zero command,
        or before the finish request for the last phase;
      - b) every entry window meets the AC7 limits (|yaw rate| ≤ 0.15 rad/s, |vertical speed| ≤ 0.05 m/s over 1.0 s
        from the first STAND_TRANSITION row);
      - c) every start (4.0 and 12.0 s), over 1.0 s after the command step: no non-foot force ≥ 5 N, |roll| and
        |pitch| ≤ 10°, and max |pitch| at most 3° above the hold-off run in the same window;
      - d) the run ends normally (EXTERNAL_EPISODE_FINISHED or DURATION_REACHED) with no reset, pose write,
        non-finite value or contact-guard failure, and planar travel within ±20 % of the hold-off run.
      The hold-off run is reported with the same per-stop and per-start numbers, without thresholds.
      **Result: pass** (`xfade1s`, `xfade2s`; D5 selects `xfade1s`).
- [x] AC6 The report states the claim boundary: simulation only, V12 in Isaac, one flat route, not a real-robot or
      deployment fix.
      **Result: stated** (`stance_hold_qualification/RESULT.md`, Claim boundary).

## Out of scope

- `machine-dog` deployment code, retraining V12, backend stop-evidence polling, placed-obstacle scenes, and a
  damping or passive mode.
