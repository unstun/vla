# V12 low-speed/turn characterization and rotate-then-approach terminal

Created 2026-10-23 from Dr Sun's hypothesis: the current bottleneck is not global or local planning. It is that
the RL policy (V12) stops badly and that in-place turning is missing. Evidence checked before writing this task:
[research/evidence.md](research/evidence.md). Read it first.

## Goal

1. Measure what V12 can actually execute on flat ground: low linear speeds, pure yaw and stopping.
2. Use those numbers to build **v292**, a terminal behaviour that:
   - never sends V12 a translation command below its trained floor;
   - turns in place at a point that has full-rotation clearance, not at the goal pose;
   - then approaches already facing the goal heading.
3. Evaluate v292 against v290 under the existing frozen protocol.

## Background (short)

- In v290 and v291, every physical failure that was not a scanner timeout happened at the goal: while turning,
  standing or handing over to PD. Planning passes offline (49/50).
- Stop drift (about 20 cm) happens while V12 owns the joints, before PD takes over.
- Corrected 2026-10-23: the saved V12 config selects dynamic sampling, which bypasses the fixed 0.2 m/s
  zeroing branch. The terminal sends 0.05–0.15 m/s and has recorded tracking weakness; Phase B must establish
  the usable floor. See the dated source/config correction in `research/evidence.md`.
- In-place turning existed in v206 and was replaced in v285 by turning while moving.
- At the CD12, CS03 and CE03 goals, half or more of the 32 checked headings collide. So the turn cannot simply be
  done at the goal.

## Phases and gates

Each gate needs Dr Sun's explicit "yes" in the working session. A gate is not inherited from this file, from an
earlier session or from another agent.

| Phase | Physics | Gate |
|---|---|---|
| A. Command-range audit of retained recordings | none (read-only) | **G1**: read-only SSH to ultra9 |
| B. Flat-ground V12 primitive characterization | new, flat scene only | **G2**: host, run count and budget |
| C. v292 implementation plus component/offline checks | none | **G1** for remote native build/offline checks |
| D. Paired physical evaluation | new, Building routes | **G3**: host, CPU isolation, run list |

Order: A and B first. C uses B's numbers. D only after C passes. If B shows V12 cannot turn in place with bounded
drift, stop and report to Dr Sun before C. That would make retraining (O1) the next decision.

## Requirements

### Phase A — command-range audit (zero physics)

- A1. Use the retained raw recordings of v290's ten routes and v291's paired-24 runs on ultra9. Read them
  read-only, under `nice -n 19`, and never rerun a physics launcher to repair an analysis.
- A2. For each run's terminal window (from the first entry into the 25 cm goal circle, or 10 s before the first
  zero command if it never enters, to the end of the recording), report:
  - the share of applied-command time with 0 < ‖(vx, vy)‖ ≤ 0.2 m/s, and the share at 0.2 m/s or above;
  - total and longest pure-yaw intervals, with the applied yaw rate;
  - measured body speed against commanded speed in each band;
  - XY drift during each pure-yaw interval.
- A3. Return compact tables and plots locally. Large CSVs stay on the host with hashes.

### Phase B — flat-ground V12 primitives (new physics, gate G2)

- B1. Harness: `E/scripts/flat_scene.py` `FlatSceneRobot` driven by scripted commands, following
  `E/scripts/qualify_stance_switch.py`. Locomotion as in the paired-24 **parent** arm: the V12 checkpoint, the
  hash-pinned v216 stance hold in `auto` mode, and the same factory/PD startup. Freeze the probe source and hashes
  before the first run. (`E` = `.pipeline/experiments/2026-09-26_newton_stair_reproduction`.)
- B2. Cells, each from a fresh start:
  - **Low-speed linear**, entered from a 0.4 m/s walk and held for 6 s:
    - forward vx ∈ {0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40} m/s;
    - backward vx ∈ {−0.10, −0.20};
    - lateral vy ∈ {±0.10, ±0.20}.
  - **Pure yaw** wz ∈ {±0.3, ±0.6, ±1.0} rad/s, each from standing and from walking, through at least 180°.
  - **Stop**: zero command after 0.4 m/s, after 0.2 m/s, after 0.1 m/s and after pure yaw at 1.0 rad/s.
  - **Rotate-then-approach**: stop, pure yaw by 90° and by 180°, walk 0.3 m at the lowest tracked speed, stop.
- B3. Three repeats per cell. Suggested cap: 40 runs and 120 s of simulation each; Dr Sun sets the real budget at G2.
- B4. Optional second arm, stop cells only: the v291 settling-assistance adapter. This separates its effect from
  unified terminal control, as the paired-24 report recommended.
- B5. Metrics:
  - **Tracking**: the steady-state ratio of measured to commanded speed over the last 4 s of each hold, plus
    lateral and yaw drift.
  - **Pure yaw**: yaw-rate tracking ratio, the maximum XY displacement of the body centre, and the swept-disc
    radius actually used.
  - **Stop**:
    - the maximum XY displacement from the first effective zero command to `FIXED_STAND`;
    - the time to four-foot contact and the time to PD entry;
    - PD aborts with their reasons;
    - the yaw change after the zero command.
- B6. Derived outputs for v292, each with the evidence row it comes from:
  - `v_floor`: the lowest |v| with a tracking ratio of at least 0.8 in all three repeats;
  - `wz_turn`: the pure-yaw rate with the lowest XY drift;
  - `turn_drift_margin`: the worst-case drift at `wz_turn` plus a stated safety term;
  - `stop_distance(v)`: the braking distance at each tested speed.
  Treat 0.2 m/s as an initial test point, not an established training floor (2026-10-23 source correction).
  Measure `v_floor`; do not assume it. The command-floor requirement remains unchanged.

### Phase C — v292 terminal (zero physics; lead proposals, confirm in design.md)

- C0. Version: v292, frozen per `.trellis/spec/backend/newton-versioning.md`. Parent: v291's unified
  `TrackingNode` terminal ownership with v291 settling assistance **off** (v216 stance). If Phase B shows the assist
  helps, record that and ask before adding it back.
- C1. **Command floor.** The tracker never emits translation with 0 < ‖(vx, vy)‖ < `v_floor`.
  - Outside the unchanged 25 cm / 20 cm / 0.25 rad acceptance: approach at `v_floor` or faster.
  - Brake when the predicted stop distance (B6) reaches the goal.
  - Inside acceptance: stop. No creep toward the old 5 cm deadzone.
- C2. **Planned terminal heading.** Before the final approach, compute the turn the goal heading needs.
  - If it exceeds a threshold, select a turn point: search backward along the published route for the nearest
    pose whose full-rotation sweep is clear by at least `turn_drift_margin`.
  - Use the same geometry as the v290 32-heading goal audit: source solid, raw points, support gap and the same
    body envelope.
  - At that point, rotate in place: translation exactly 0, yaw at `wz_turn`.
  - Then approach along the goal heading, forward, lateral or backward as the envelope allows, at `v_floor` or
    faster.
  - If no turn point exists, end with an explicit `terminal_heading_infeasible`. Never spin at a goal whose sweep
    is illegal (CD12, CS03, CE03).
- C3. **Swept-rotation guard.** Check every pure-yaw command against the measured pose with the swept disc. A
  failure stops and reports; it does not continue. This closes the gap found in v283.
- C4. **En-route in-place turning** behind a flag, default on, so it can be ablated. Reinstate v206's hysteresis
  (enter at 1.0 rad, exit at 0.6) only where C3 passes at the measured pose. Elsewhere keep v291's turn-while-moving.
- C5. **Unchanged:**
  - the emergency stop;
  - arrival acceptance and the measured PD gate of at least 2 s;
  - PD gains, crossfade and disturbance exit;
  - the 0.35 m hard radius and the 0.1 s scanner period and deadline;
  - the global planner, the route cohort and factory startup.
  No route-, coordinate- or scene-specific branches.

### Phase D — paired physical evaluation (gate G3)

- D1. Fix CPU contention first. Request pinned or exclusive CPUs for physics and the scanner, and record the
  admission for every run. If isolation is not available, report that and ask; do not spend runs on scanner
  timeouts again.
- D2. v292 against v290: frozen routes D07, CD12, S04 and A04 × 3 fresh starts, plus frozen holdouts CU04, CD09,
  CM04 and CE04, following `E/audits/2026-10-22_v291_paired24/PLAN.md`.
- D3. Report:
  - complete success and whole-route geometry, separately;
  - the first and the worst stop displacement;
  - time spent with 0 < |v| < `v_floor` (target: zero);
  - the turn-point sweep margin and `terminal_heading_infeasible` counts;
  - PD aborts and elapsed time.
  Keep every failure; never rerun to replace one.

## Acceptance criteria

- [x] A: terminal command-band and pure-yaw tables for all 34 retained runs (10 + 24), with source hashes and
      missing runs listed. Passed 2026-10-23: 102 matched source files; no missing runs; 28 circle / 6 fallback
      windows; report at `E/audits/2026-10-23_v12_command_range/REPORT.md`.
- [ ] B: every cell × repeat reported, failures kept, with `v_floor`, `wz_turn`, `turn_drift_margin` and
      `stop_distance(v)` each traced to rows. A clear yes or no on "V12 can turn in place with drift below X cm".
- [ ] C: component tests for C1–C4:
  - [ ] a sub-floor command is never emitted;
  - [ ] the turn point is chosen at a clear pose;
  - [ ] an illegal goal sweep gives `terminal_heading_infeasible`;
  - [ ] the guard stops a blocked spin;
  - [ ] the flag-off path equals the parent.
- [ ] C: recorded-input replays of D07 and CD12 through the real Controller, LocalMotion and TrackingNode.
- [ ] C: a native swept-rotation probe reproduces v290's 32-heading goal table.
- [ ] C: strict53 offline passes at the unchanged thresholds (≥48/50 legal, 3/3 illegal, median ≤1.5 s, first
      solve ≥90%).
- [ ] D: only after G3. Results reported as in D3. No baseline promotion without Dr Sun's decision.

## Out of scope (record, don't do)

- O1. **Retraining or fine-tuning V12** with:
  - a used `stand_still` / `feet_contact_without_cmd` reward;
  - exact all-zero stand commands;
  - low-speed commands below 0.2 m/s;
  - PD-hold segments.
  This fixes the root cause but needs Dr Sun's scope decision and a training host.
- O2. Real-robot runs. Changes to the global planner. Relaxing any threshold, radius or deadline. Rerunning or
  reclassifying old attempts. Promoting v291 or v292 to baseline. The accepted baseline stays v232/v233.

## Records (AGENTS.md rule 3)

- Phase A and B reports go in `E/audits/2026-10-2x_<name>/REPORT.md`, together with frozen source, `results/`
  JSON and hashes.
- v292 goes in `E/versions/v292/` (`RESULTS.md`, `manifest.json`, `changes.patch`).
- Keep `run-state.md` in this task current at every checkpoint.
- Never commit weights, videos, full logs or large raw data. Review the file list and sizes before each commit.
- Branch `local/research-unpublished` has no upstream, and earlier closeouts record "no push". Commit locally and
  ask Dr Sun before any push.
