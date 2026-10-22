# Codex VLA Project Entry

Read `AGENTS.md`, the relevant Trellis task and its specs. Load project history
only when the question needs it; `SKILLS.md` lists the active capabilities.

Project hooks and hook scripts are removed. Use Trellis skills to load context.
The three `trellis-*` agents remain available only when Dr Sun requests them;
they read task artifacts and manifests directly through their existing fallback.

Use native session identity or a stable per-session `TRELLIS_CONTEXT_ID` with
Trellis task commands. The inline task-start patch prevents empty subagent
manifests from blocking main-session execution. `session_auto_commit` remains
false. At completion, review task-owned changes and follow `AGENTS.md` plus
`docs/agents/git-workflow.md` for the authorized commit and publishing route.

Project configuration does not declare MCP servers. Global MCP and plugin
settings remain user-owned. Remote execution copies must return final source
changes and verified evidence to this local VLA repository.
