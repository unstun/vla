# Project Skills

The active set contains 12 Trellis core skills and nine project skills.
Canonical project skills are real directories under `.agents/skills/`.
Claude Code and Cursor discover them through generated links, except where
an installed Trellis directory already owns the name.

## Trellis Core

`trellis-start`, `trellis-continue`, `trellis-before-dev`, `trellis-brainstorm`,
`trellis-check`, `trellis-finish-work`, `trellis-break-loop`,
`trellis-update-spec`, `trellis-meta`, `trellis-session-insight`,
`trellis-spec-bootstrap`, `trellis-channel`.

Keep the Trellis core skills and runtime, with the hook removals and local
task-start patch documented in the harness specification. Project rules in
`AGENTS.md` take precedence over generic templates. In particular, subagents
require an explicit user request and `session_auto_commit` remains false.

## Project Capabilities

| Skill | Purpose |
|---|---|
| `project-status` | Read current evidence and explain progress and next steps. |
| `memory-retrieval` | Retrieve relevant past decisions and evidence, read-only. |
| `archive` | Save durable findings or synchronize project state when requested. |
| `research-pipeline-planner` | Plan research stages, dependencies and acceptance criteria. |
| `literature-survey` | Find and compare primary papers with traceable sources. |
| `inno-code-survey` | Inspect and acquire pinned upstream implementations. |
| `paper-analyzer` | Analyze one paper against its actual methods and results. |
| `fetch-arxiv-md` | Convert arXiv source into local Markdown with existing scripts. |
| `remote-experiment` | Execute authorized remote work and return reproducible evidence. |

Status questions do not trigger archival. Literature discovery does not require
extra generic research skills. Dataset discovery uses the same primary-source
approach; source-code selection belongs to `inno-code-survey`.

## Synchronization

Run `./sync-skills.sh` from a checkout to restore project discovery links.
It runs offline, preserves real platform directories and custom links, and
removes obsolete generated vendor links and dangling generated project links.
It does not fetch, check out, or activate a vendor repository.

`vendor-skills.lock` and the existing ignored `.skills-upstream/` checkout are
retained as provenance for earlier adaptations, not as an active skill catalog.
Retired skills can be recovered selectively from Git history. Do not restore
all vendor links as part of ordinary synchronization.

Project hooks and their script directories are removed, matching machine-dog.
Use Trellis skills and direct task-context reads; no automatic injection or
shell session bridge is required. Native session identity or `TRELLIS_CONTEXT_ID`
selects the task session. After a Trellis update, remove any reintroduced project
hooks and check the documented local task-start patch. Validate with
`python3 -m unittest discover -s tools/harness -p 'test_*.py'` and check discovery
in a new host session. An already-open session may retain its old skill catalog.
