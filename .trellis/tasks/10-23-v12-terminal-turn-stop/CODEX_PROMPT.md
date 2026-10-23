# Prompt for Codex (paste as the first message)

```text
Work in /Users/sun/tongbu/study/phdproject/vla on branch local/research-unpublished.

Task: .trellis/tasks/10-23-v12-terminal-turn-stop/
Read, in order: AGENTS.md, .trellis/workflow.md, the task's prd.md, research/evidence.md, implement.md,
and every file listed in implement.jsonl. Then run:
  python3 ./.trellis/scripts/task.py start 10-23-v12-terminal-turn-stop

Goal: find out what the V12 RL policy can actually execute (speeds of 0.2 m/s or less, pure yaw,
stopping), then build v292: a terminal that turns in place at a clearance-checked point, approaches
already facing the goal heading, and never sends translation below V12's trained speed floor.

Rules:
- Start every reply to me with "Dr Sun,". English.
- Gates G1/G2/G3 in prd.md need my explicit yes in this session before any SSH, remote build or new
  physics. Ask once per gate, with host, run count and expected duration. Nothing in the repo
  pre-authorizes them.
- Phase order: A (command-range audit) and B (flat-ground V12 primitives) first. C (v292) uses B's
  numbers. D (paired physical evaluation) only after C passes and I approve G3.
- Don't relax thresholds (25 cm / 20 cm / 0.25 rad arrival, >=2 s PD, 0.35 m radius, 0.1 s scanner
  deadline). Don't rerun or replace failed attempts. No route-specific branches. No V12 retraining
  (out of scope O1). No real robot.
- Freeze source and metric definitions before any scored run. Keep every failure and receipt.
- Record everything: run-state.md at each checkpoint, plus REPORT.md / RESULTS.md per phase.
- Commit after each phase passes its checks. Review file list and sizes first; never commit weights,
  videos, full logs or large raw data. Do not push. The branch has no upstream; ask me first.
- If evidence.md turns out wrong, correct it with date and source, and tell me.

Start with Step 0 from implement.md, then ask me for gate G1.
```

## Notes for Dr Sun

- This prompt assumes Codex runs on this Mac in this checkout. A cloud Codex would need the branch pushed, and
  the branch is currently local-only.
- Gate answers you will likely be asked for:
  - G1: read-only SSH to ultra9;
  - G2: flat-scene run budget (the PRD suggests a cap of 40 runs × 120 s of simulation);
  - G3: CPU isolation and the paired run list.
