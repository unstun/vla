# Lite3 VLA Research Project

> Scope: `/Users/sun/tongbu/study/phdproject/vla/**`.
> Source of truth: this file (`AGENTS.md`). `CLAUDE.md` imports it through
> `@AGENTS.md`.

## Project Purpose

This repository develops a vision-language-action layer for Lite3 autonomous
navigation. It will start from a deliberately selected, pinned snapshot of the
local `machine-dog-nav` project and may reuse its navigation-to-locomotion loop.
The intended scope includes visual and language understanding, action
representation, planning, simulation, evaluation, and eventual real-robot
integration. The exact VLA architecture and action interface remain research
decisions until evidence and acceptance criteria are recorded.

These repositories have different responsibilities:

- `machine-dog`: locomotion training, evaluation, and deployment.
- `machine-dog-nav`: read-only navigation baseline and interface reference
  until a clean source commit is selected and imported.
- `vla`: VLA research, source acquisition, implementation, integration,
  evaluation, and VLA-to-navigation interface work.

## Identity And Protocol

This is a long-horizon PhD research project.

1. Every reply to Dr Sun starts with `Dr Sun,`.
2. Use Chinese for interaction with Dr Sun unless he requests another language.
   Use clear professional English for code, configuration, and repository-facing
   technical documentation unless the requested artifact is Chinese.
   Project override: use English by default.
3. At the start of a session, identify the current stage:
   **planning -> experiment + analysis -> writing**. Do not silently mix stages.
4. Human review comes before speed. If requirements have several materially
   different interpretations, explain the difference and ask before choosing.

## Research Discipline

1. AI output is untrusted until verified. Search results and prior AI summaries
   are leads, not evidence.
2. Read local sources first. For professional claims, verify primary papers,
   official documentation, or the upstream repository itself and cite a short
   file reference or URL.
3. Separate these labels:
   - `surveyed`: papers or repositories were inspected.
   - `imported`: a pinned source snapshot was brought into this repository.
   - `reproduced`: an upstream run was executed with recorded evidence.
   - `integrated`: upstream behavior works inside this repository.
   - `validated`: the declared acceptance test passed.
   Never promote one label into another.
4. Prefer an existing open-source implementation over writing a new framework
   from scratch, but record its URL, license, pinned commit, dependencies,
   original run instructions, and local modifications.
5. Keep third-party source inside this project under a dated, purpose-named
   directory. Do not use `/tmp` as durable storage.
6. `.pipeline/terminology/terminology.md` is the terminology source of truth.
   Check it before introducing project terms in research or design documents.

## Source Of Truth And Sync Gate

The local `/Users/sun/tongbu/study/phdproject/vla` repository is the only
source of truth for VLA code and project state.

- `/Users/sun/tongbu/study/phdproject/machine-dog-nav` and other upstream
  repositories are read-only references until deliberately imported.
- Before importing from `machine-dog-nav`, record the selected branch and clean
  commit. Do not silently copy its uncommitted working-tree changes.
- Do not edit `machine-dog-nav` from a VLA task unless Dr Sun explicitly opens a
  separate task in that repository.
- Remote code and simulator workspaces are execution copies only.
- Temporary remote diagnostic edits are allowed, but final changes must return
  to the same local paths and be visible in local `git diff`.
- A remote-only success claim without locally returned provenance and verified
  results is not reproducible evidence.
- VLA-to-navigation integration must pin the imported `machine-dog-nav`
  baseline, and navigation-to-locomotion integration must pin the sibling
  `machine-dog` interface version or commit instead of copying unidentified
  code or policies.

## Engineering Rules

1. Think before editing. Convert requests into checkable goals and state a short
   plan for non-trivial work.
2. Keep scope small. Do not refactor or reformat unrelated files.
3. Preserve user changes in a dirty worktree. Stage only paths owned by the
   current task.
4. Automatic pre-edit or session commits are forbidden. Commit only after a
   meaningful change is verified and the staged diff is reviewed.
5. Do not claim `fixed`, `working`, `reproduced`, or `complete` without a direct
   test, build, simulator run, or equivalent runtime check.
6. Formal training, long remote runs, destructive data operations, and
   real-robot actuation require explicit authorization from Dr Sun.
7. For external execution packages, state:
   - local source of truth;
   - exact sync gate;
   - expected artifacts;
   - claim boundary if the run is incomplete.
8. Keep heavy files and data on gpu5070ti, retaining only source/configuration,
   compact reports and provenance, and review videos in the local repository.
9. Do not hide research evidence with repository-wide extension ignores. Large
   local-only bytes require a reviewed path-specific ignore entry plus tracked
   provenance, SHA-256, storage location, and regeneration instructions.
10. Local Newton navigation versions start from the user-designated `v3`
    baseline (2026-09-27). Give each subsequent logical code/configuration
    change its own integer version. Preserve the preceding source snapshot,
    record the difference and bind tests/videos to the version. Never overwrite
    a frozen version or treat a version increment as acceptance. The index is
    `.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/README.md`.

## Project State Layout

- `.trellis/`: tasks, workflow, specifications, and session journals.
- `.agents/skills/`: canonical real directories for project-owned Skills.
- `vendor-skills.lock` + `sync-skills.sh`: exact Vendor Skill source and
  cross-host discovery-link restoration.
- `.pipeline/`: reviewed research indexes, terminology, surveys, experiment
  records, templates, and external task packages.
- `bigmemory/热区/`: current status, recent changes, and open decisions.
- `bigmemory/冷区/`: durable change, pitfall, research, rationale, and milestone
  records.
- `docs/research/`: human-readable research documents and paper sources.

Existing repository conventions remain active:

- `CLAUDE.md` remains exactly the single-line `@AGENTS.md` wrapper. Setup or
  Vendor Skills must not edit it.
- A GitHub issue tracker is not configured until this repository has an
  approved remote. See `docs/agents/issue-tracker.md`; never fall through to
  the `machine-dog-nav` tracker.
- Default triage labels are `needs-triage`, `needs-info`, `ready-for-agent`,
  `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.
- Multi-context domain documentation follows `docs/agents/domain.md`.

## Current Boundary

As of 2026-08-16, the repository contains a fresh Git/Trellis workspace and the
migrated cross-agent harness. No `machine-dog-nav` code has been imported or
pinned, and there is no VLA implementation, simulator task, checkpoint,
training run, or runtime result. Agent configuration readiness is not VLA
implementation evidence. The first implementation task must select a clean
baseline and define a reviewable VLA contract before code import or execution.

<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
