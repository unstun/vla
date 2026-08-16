# Backend Quality Guidelines

> Pre-baseline contracts for VLA backend work. No implementation-specific
> runtime contract is active until a clean baseline is imported and inspected.

## 1. Current Scope

This repository has no imported VLA or navigation implementation. These rules
govern source selection, interface definition, evidence, and the first code
changes without assuming a simulator, ROS version, model family, observation
shape, action dimension, checkpoint, or evaluation course.

## 2. Evidence Labels

Keep the labels from `AGENTS.md` separate:

- `surveyed`: primary material or canonical source was inspected;
- `imported`: a pinned committed snapshot exists in this repository;
- `reproduced`: an original upstream command ran with recorded evidence;
- `integrated`: the behavior works through this repository's interface;
- `validated`: the declared acceptance test passed.

Never infer a later label from an earlier one.

## 3. Baseline Import Gate

Before importing code from `machine-dog-nav` or another upstream:

1. Record the canonical source, branch, clean commit, license, dependencies,
   original commands, and selected import method.
2. Reject an uncommitted working tree as a reproducible baseline.
3. Keep upstream task history, experiment state, mutable memory, generated
   artifacts, and unrelated Harness files out of the import.
4. Record every imported path and local modification.
5. Review name collisions with `AGENTS.md`, `.trellis/`, `.pipeline/`,
   `bigmemory/`, `.agents/`, `.claude/`, `.codex/`, and `.cursor/` before merge.

## 4. Interface Contract Gate

Before behavior-changing implementation, define and review:

- visual and language inputs, timestamps, units, shapes, and validity rules;
- action representation and its consumer;
- VLA-to-navigation and navigation-to-locomotion ownership boundaries;
- stale-input, timeout, reset, and stop behavior;
- deterministic fixtures and the smallest acceptance scenario;
- expected, failure, and stop signals;
- local artifact paths and sync-back requirements for external execution.

Do not hard-code a waypoint, velocity, trajectory, token, observation, or action
contract merely because one candidate upstream uses it.

## 5. Implementation Quality

- Read the active task and relevant package specs before editing.
- Keep changes limited to one reviewable contract or behavior group.
- Validate external inputs at the boundary and preserve raw evidence needed for
  diagnosis.
- Make configuration and run identity explicit in logs and artifacts.
- Add tests for new parsing, validation, state transitions, and failure paths.
- Use primary upstream behavior as a reference; do not copy unidentified code,
  weights, datasets, or policies.
- Treat remote and simulator workspaces as execution copies. Sync final source,
  configuration, logs, and declared artifacts back locally before claims.

## 6. Forbidden Patterns

- Importing implementation-specific SCAN, Go2, V12, forest, ROS, sensor, model,
  or checkpoint assumptions before the corresponding baseline is selected.
- Presenting a repository clone, model download, successful import, or process
  exit code as integration or validation evidence.
- Starting formal training, long remote runs, destructive data operations, or
  real-robot actuation without Dr Sun's explicit authorization.
- Broad refactors mixed into a baseline import or first interface slice.
- Remote-only fixes or artifacts with no local source-of-truth copy.

## 7. Quality Check

For every backend change, report:

- exact files and contract changed;
- tests, builds, simulator runs, or other direct checks actually executed;
- artifact and source commit identity;
- the strongest justified evidence label;
- untested paths, unresolved decisions, and the next gate.

Replace or extend this document only after real imported code establishes a
stable convention. Record implementation-specific contracts in a reviewed task
or a focused spec instead of silently turning one experiment into a project
default.
