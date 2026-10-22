# Lite3 VLA Research Project

> Scope: `/Users/sun/tongbu/study/phdproject/vla/**`. Source of truth: this file (`AGENTS.md`). `CLAUDE.md` references it through `@AGENTS.md`.

## Hard Rules

### Core Behavior

1. MUST: Every reply to Dr Sun starts with `Dr Sun,`.
2. MUST: Default to English for this repository.
3. Please keep VLA maintainable for the long term, historically traceable (record every experiment as thoroughly as possible, since that is critical for future experiments), and efficient. If you find anything in the repository that looks unreasonable or needs updating, please remind Dr Sun.
4. After completing a clearly defined development task and passing the relevant checks, automatically commit the changes for that task and push the current branch without asking for confirmation again. Before committing, review the file list and file sizes; do not commit model weights, videos, full logs, or large generated data.
5. Generally work in the main session. Use subagents only when Dr Sun brings up using them; no additional confirmation is needed.

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
