---
name: lead-execute-review
description: Prepare an Opus execution package and review its results. Use for lead/executor delegation; handle simple edits directly.
---

# Lead, Execute, Review

The lead defines the task and accepts the result; the executor performs the bounded work.

## Prepare

- Inspect relevant local code and artifacts. Reuse completed work; identify unresolved decisions.
- Use [the template](assets/execution-package.md). Include only details needed to execute and verify the task.
- Save in the existing task/experiment directory or `.pipeline/external_tasks/YYYY-MM-DD_<topic>/EXECUTION_PACKAGE.md`.
- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`. Remote roots are execution copies; final edits and evidence return locally through the stated Sync Gate.
- For VLA experiments, specify source/checkpoint revision, precision, observation/action interface, workload, and measurable acceptance conditions.

## Execute

- Use the requested model through an authorized route. If unavailable, provide a manual package; do not silently substitute models.
- Deliver the complete package, including scope and authorization. Record the actual dispatch/task identity; a written package is only `prepared_not_dispatched`.
- The executor owns the assigned paths, preserves concurrent edits, and returns commands, raw outputs, and artifact paths.
- Fix ordinary implementation errors within scope. Return consequential changes to the lead; keep the approved experiment and acceptance criteria intact.

## Review

- Inspect the actual diff and raw evidence, not just the executor's summary. Deliver requested media once verified.
- Return `accepted`, `corrections required`, or `blocked`, with evidence. Corrections should reference specific findings and checks.
- Keep execution, lead acceptance, archival, and commit status separate. Apply the project's research evidence labels.

[Source provenance](references/source-provenance.json).
