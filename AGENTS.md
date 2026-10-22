# Lite3 VLA Research Project

> Scope: this repository. `AGENTS.md` is the instruction source of truth;
> `CLAUDE.md` remains the single-line `@AGENTS.md` wrapper.

## Collaboration

- Start replies with `Dr Sun,`. Use English by default; follow the requested
  language for discussion or deliverables. Explain decisions in plain language.
- Work in the main session. Use subagents only when Dr Sun explicitly asks.
- For non-trivial work, state the scope and checkable outcome, then carry out
  authorized work. Ask when a consequential choice remains unresolved.
- Preserve unrelated working-tree changes. No automatic session-start or
  pre-edit commits; review task-owned paths and checks before any commit.
- After completing an authorized development task and passing its checks,
  automatically commit that task's changes and push the current branch to its
  configured remote without asking again. Review the exact staged diff, file
  list and sizes; exclude unrelated edits, model weights, videos, full logs and
  large generated data. Report the commit and verified push result.

## Research And Execution

- VLA owns visual/language understanding, planning and navigation integration.
  `machine-dog` owns locomotion; sibling repositories are read-only references
  unless Dr Sun explicitly authorizes work there.
- This local repository is the source of truth. Pin upstream commits and the
  locomotion interface; record source URL, license, dependencies and changes.
  Do not silently import another repository's uncommitted working tree.
- Read relevant local evidence first. Verify professional claims against
  primary sources, code or raw results. Identify the research stage when it
  matters: planning, experiment and analysis, or writing.
- Keep evidence labels distinct: `surveyed`, `imported`, `reproduced`,
  `integrated`, `validated`. A success claim needs the corresponding direct test.
- Remote workspaces are execution copies. Return final changes, exact commands,
  compact results and provenance locally; state what an incomplete run proves.
- Formal training, long remote runs, destructive data operations and real-robot
  actuation require Dr Sun's explicit authorization.
- Keep heavy data on gpu5070ti and compact source/configuration, reports,
  provenance and review videos locally. Preserve research records and failed
  trials. Local-only bytes need scoped ignores, hashes, storage and recovery
  information; no repository-wide extension ignores for research evidence.
- Follow `.trellis/spec/backend/newton-versioning.md` for Newton changes:
  preserve frozen sources and assign each logical change its own integer version
  after the designated v3 baseline; bind tests/videos to that version.
- Use `.pipeline/terminology/terminology.md` for project terms. Reset
  `reviewed: true` to `reviewed: false` when editing reviewed research documents.

## Where To Read

- Current state: `bigmemory/热区/`; verify against the relevant original records.
- Research and experiments: `.pipeline/`, `docs/research/`, `references/upstream/`.
- Development: `.trellis/workflow.md`, `.trellis/spec/`, and the relevant task.
- Active skills and synchronization: `SKILLS.md` and `sync-skills.sh`.
- Tracker and domain conventions: `docs/agents/`; never fall through to a sibling
  repository's issue tracker.

Load Trellis context through skills as needed for the current task.
Routine prompt/session hooks are disabled. Agent-context hooks only support
explicitly requested delegation; Cursor retains its task-session bridge.

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
