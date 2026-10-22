# Codex VLA Project Entry

Read `AGENTS.md`, the relevant Trellis task and its specs. Load project history
only when the question needs it; `SKILLS.md` lists the active capabilities.

Routine prompt/session hooks are disabled. `SubagentStart` supplies context
only when Dr Sun explicitly requests delegation. The three `trellis-*` agents
remain installed; other work runs in the main session. Reset reviewed research
flags manually when editing those documents.

Use native session identity or a stable per-session `TRELLIS_CONTEXT_ID` with
Trellis task commands. `session_auto_commit` is false; task archival and journal
recording must not stage or commit unrelated files. At the end of an authorized
development task, review the task-owned staged diff and file sizes, commit the
verified changes, and push the current branch to its configured remote without
asking again, as required by `AGENTS.md`. Report the commit and push result.

Project configuration does not declare MCP servers. Global MCP and plugin
settings remain user-owned. Remote execution copies must return final source
changes and verified evidence to this local VLA repository.
