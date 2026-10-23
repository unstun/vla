# Implementation plan

`E` = `.pipeline/experiments/2026-09-26_newton_stair_reproduction`. Requirements and gates: [prd.md](prd.md).
Evidence: [research/evidence.md](research/evidence.md).

## Step 0 — orient (local, no gate)

1. Read `AGENTS.md`, `.trellis/workflow.md`, this task's `prd.md` and `research/evidence.md`, and every spec in
   `implement.jsonl`.
2. Read the parent material:
   - `E/versions/v291/RESULTS.md`
   - `E/audits/2026-10-22_v291_paired24/REPORT.md` and `PLAN.md`
   - `E/audits/2026-10-22_v290_stop_timeline/REPORT.md`
   - `.trellis/tasks/10-21-v290-terrain-terminal/CLOSEOUT.md`
3. Write a dated checkpoint in `run-state.md`: what you read, what you will do next, and which gate you need.

## Step 1 — Phase A command-range audit (gate G1)

- Templates:
  - `E/audits/2026-10-22_v290_stop_timeline/read_recordings.py`, a read-only remote extractor;
  - `E/audits/2026-10-22_v291_paired24/analysis/analyze_runs.py` and `source/stop_metrics.py`, the frozen stop
    metrics.
- Raw data (read-only, ultra9):
  - `/home/ubuntu/sun/vla_v291_pair24_20261022/physical_runs/`;
  - the v290 attempts under `/home/ubuntu/sun/vla_v290_20261021/` (paths in the v290 audit manifests).
- Worker Python on ultra9: `/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python`. Run it with
  `nice -n 19`.
- Output: `E/audits/2026-10-2x_v12_command_range/`, with `REPORT.md`, `results/*.json`, plots, and a test for the
  band and interval definitions.
- Write the band definitions before reading any numbers, using paired-24's `analysis/DEFINITIONS.md`
  as the reference (path clarified at Step 0, 2026-10-23).

## Step 2 — Phase B flat primitives (gate G2)

1. Probe source: new `E/audits/2026-10-2x_v12_primitives/source/`. Base it on `E/scripts/qualify_stance_switch.py`
   and `FlatSceneRobot` in `E/scripts/flat_scene.py`, which uses `robot.step([vx, vy, wz])` and
   `robot.telemetry()`.
2. Select the stance module explicitly, as paired-24 did for its parent arm: hash-pinned v216. For the optional
   B4 arm, use the v291 adapter through `E/versions/v291/activate.py`.
3. Verify by zero-step preflight which module is actually loaded.
4. Freeze before the first scored run: the cell list, the repeat count, all metric definitions and the source
   hashes, in `PLAN.md` and `frozen.json`.
5. Run each cell once per repeat. Keep every failure, and don't rerun to replace one. Telemetry is about 50 Hz.
   Record the host load for every run.
6. Report the B5 metrics and the B6 derived values, each with the rows it comes from.
7. Stop and report to Dr Sun if pure-yaw XY drift is so large that no realistic turn point would clear.

## Step 3 — Phase C v292 (zero physics, G1 for remote builds)

1. Write `design.md` in this task. Cover C1–C4 using the real numbers from Phase B, and state where each piece
   lives:
   - the tracker command floor and approach braking;
   - turn-point selection;
   - the swept-rotation guard.
   Point to the code: `tracking_node.hpp` `terminalCommand()` / `cmdCallback()`, `local_motion.cpp`
   `LocalMotion::command()` and `native_query.hpp`.
2. Create `E/versions/v292/` from v291's `scan_nav2_controller` overlay with the settling assistance off. Follow
   `newton-versioning.md`: one declared behaviour change set, the parent hash, `changes.patch` and
   `manifest.json`.
3. Tests:
   - native component tests for each acceptance item in the PRD;
   - recorded D07/CD12 controller replays, following `E/versions/v291/replay_controller.py`;
   - a swept-rotation probe that reproduces the v290 32-heading goal table, following the v290
     `terminal_geometry.py` evaluators;
   - strict53 through the v291 `offline.py` pattern.
   Scored directories are write-once.
4. Record the results in `E/versions/v292/RESULTS.md`. Commit after the checks pass (review the file list and
   sizes first). Don't push.

## Step 4 — Phase D paired evaluation (gate G3)

Only after Dr Sun approves the host, the CPU isolation and the run list. Follow the paired-24 freeze, preflight,
batch and analysis flow, and its "keep all failures, no replacement runs" rule.

## Checkpoints

After each step, update `run-state.md`, the relevant `REPORT.md` / `RESULTS.md`, and `task.json` notes. If a
fact contradicts `research/evidence.md`, correct the evidence file with the date and the source. Don't silently
work around it.
