---
name: archive
description: Archive durable VLA findings or synchronize project status when Dr Sun requests archival, hot-zone refresh or missing-record updates. Preserve research evidence and existing history.
---

# Project Archive And State Sync

Work in the main session. An archive request does not authorize subagents,
a second model/CLI review, data deletion or bulk history rewriting.
Use subagents only if Dr Sun explicitly requests them.

1. Read `bigmemory/格式规范.md` and the relevant hot-zone files. Inspect the
   actual changes, results and decisions to be saved; search for existing
   entries before adding another record.
2. Save only durable facts: meaningful changes, verified pitfalls, research
   findings, decisions with their rationale, and completed milestones. Use the
   existing dated categories under `bigmemory/冷区/`. Preserve prior entries
   and link raw evidence, including failed attempts.
3. Update only the affected hot-zone files. Keep their existing capacity
   budgets (status 1500 characters/30 lines, open decisions 1200/25, recent
   changes 1000/25). Move necessary detail into linked durable records before
   shortening summaries; do not drop unresolved decisions to meet a budget.
4. When relevant, reconcile the existing `.pipeline/literature/`, `survey/`,
   `experiments/` or `terminology/` indexes using their local formats. Record
   source URLs, pinned commits and test evidence. Preserve `origin` metadata
   and reset `reviewed: true` to `reviewed: false` on edited reviewed documents.
5. Check links, evidence labels and capacity. Report the files changed and any
   missing evidence. If nothing durable changed, say no archival was needed.

Do not age-delete, merge or relocate old research records automatically.
Do not export the whole conversation. Follow the task-completion commit and
push rule in `AGENTS.md`, reviewing only task-owned changes and file sizes.
A request that excludes research/state edits overrides this workflow.
