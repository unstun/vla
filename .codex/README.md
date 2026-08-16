# Codex VLA Project Entry

`AGENTS.md` is the cross-CLI behavior source of truth. Project-level Codex
configuration is loaded only after this repository is trusted.

## Startup order

1. Read `AGENTS.md`.
2. Read the active Trellis task and its planning artifacts.
3. Read the three `bigmemory/热区/` files when current status matters.
4. Read `.pipeline/terminology/terminology.md` before research or design prose.

## Hooks

- `UserPromptSubmit`: injects git state and memory freshness only when relevant,
  then injects the Trellis workflow state.
- `PostToolUse`: resets `reviewed: true` after AI edits to trusted pipeline or
  cold-memory Markdown.
- No hook stages or commits changes automatically.

## Agents

- `conductor`: project status and one-task routing.
- `memory_retriever`: compact read-only memory lookup.
- `literature_scout`: primary literature and upstream repository survey.
- `reviewer`: code, evidence, license, source-sync, and claim review.
- `harness_explorer` / `harness_reviewer`: settings inspection and review.
- `trellis-*`: Trellis-managed implementation, research, and checking roles.

## Source boundary

The local `/Users/sun/vla` checkout is the VLA source of truth. The local
`machine-dog-nav` checkout, upstream clones, and remote workspaces are references
or execution copies until their pinned source and local sync-back evidence are
recorded here.
