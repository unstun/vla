---
name: memory-retrieval
description: Retrieve VLA project history, prior decisions or experiment evidence from bigmemory, .pipeline and Trellis records. Read-only and targeted to the current question.
---

# Project Memory Retrieval

Start from the question, not a full repository scan. For current progress,
read the relevant files under `bigmemory/热区/`. For an older decision, extract
2-6 keywords and search `bigmemory/冷区/`, `.pipeline/` and `.trellis/tasks/`
with `rg`; open the most relevant records and their cited original evidence.
Use `trellis-session-insight` if the requested answer requires raw past dialogue.

A connected semantic search tool may help locate records, but is optional.
Do not install or change MCP configuration for retrieval. Work in the main
session unless Dr Sun explicitly requests a subagent.

Return a short answer with source paths, the decision or observation found,
and any concrete unresolved issue. Treat old summaries as leads; verify
changeable facts against source/configuration/logs before calling them current.
Missing records should be reported plainly. Do not edit files or trigger archive.
