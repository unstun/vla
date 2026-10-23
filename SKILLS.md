# Project Skills

The active set contains only the 12 Trellis core skills.
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
