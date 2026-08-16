# Harness Specifications

Project-level contracts for AI instructions, Trellis, platform adapters,
research skills, pipeline state, and memory.

## Pre-Development Checklist

Before changing the harness:

1. Read `AGENTS.md`.
2. Read the active Trellis task.
3. Read [Project Harness Contract](project-harness-contract.md).
4. Inspect the target platform files and search for mirrored behavior.
5. Preserve unrelated dirty-worktree paths.

## Quality Check

Run the validation commands in
[Project Harness Contract](project-harness-contract.md#6-tests-required), then
review the staged path list and confirm `docs/research/` or upstream source
clones were not included accidentally.
