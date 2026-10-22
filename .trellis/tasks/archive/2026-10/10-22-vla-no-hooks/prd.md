# Finish the hook-free harness

Dr Sun requested completing VLA cleanup to match machine-dog after confirming
that VLA still retained hooks. Keep Trellis core and necessary project skills.
The previously reviewed framework update is finalized with its startup repair
so the same runtime is available in the published checkout.

Acceptance:
- No project hook registrations or hook script directories for Claude, Cursor
  or Codex. Preserve the existing 21 skills and three Trellis agents per host.
- Keep exact deleted hook sources recoverable, including their prior dirty bytes.
- Inline task startup works even with Claude/Cursor directories and empty
  subagent manifests. Auto/subagent mode still rejects missing curated context.
- Tasks and context remain available through the main session and explicit
  TRELLIS_CONTEXT_ID; explicitly requested agents can read task files directly.
- Preserve the five research/retention modifications, existing untracked
  research tasks/files, raw data, global MCP and all 24 unpublished commits.
- Commit only harness maintenance and this task, then publish on origin/main
  ancestry without the held research history.
