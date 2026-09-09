---
origin: ai+local
reviewed: false
date: YYYY-MM-DD
status: prepared_not_dispatched
source_of_truth: local_repo
---

# [Concrete outcome]: execution package

Prepared by [lead role/model] for [executor role/model]. This package covers [one bounded task]. Replace all bracketed fields before dispatch; remove sections that do not apply.

For a manual handoff, paste the section from "Goal and ownership" through the end into a fresh executor window at [repository root]. For tool dispatch, send that same complete execution section and record the actual dispatch result separately.

---

## Goal and ownership

[User-facing problem, expected behavior, and what evidence will answer it.]

- Repository root: [exact authoritative checkout path].
- User authorization: [what the user approved; identify the decision or instruction].
- Remaining approval gates: [none, or the exact action that must wait and the evidence required to release it].

Read the applicable project instructions first. You are not alone in the repository: preserve concurrent edits, and do not stage or commit another contributor's work.

- Assigned files or modules: [exact paths and responsibility].
- Frozen boundaries: [specific code, models, interfaces, processes, and decisions relevant to this task].
- Consequential open questions: [none, or what must be resolved before dependent work].

## Source of Truth and Sync Gate

[For remote work: local repository path is the only code source of truth; named remote roots are runtime copies. Final temporary diagnostic edits must return to the same local paths and be reviewable locally. No further experiments or reproducibility claim while remote-only edits or unresolved source identity remain. State the existing source check and required local artifacts.]

[For local-only work: name the authoritative checkout and omit remote mechanics.]

## Facts established by the lead

| Fact or input | Primary evidence | Freshness or executor check |
|---|---|---|
| [Checkpoint, interface, data, or relevant behavior] | [Exact file/function, record, commit, or source URL] | [Already verified, or narrowly refresh mutable state] |

- Existing implementation to reuse: [script, function, launcher, configuration].
- Completed work to retain: [artifacts and checks; do not rerun without a stated reason].
- Known failure or uncertainty: [evidence and its limit].

## Deliverables

| Output | Exact destination | Acceptance evidence |
|---|---|---|
| [Code or analysis] | [Owned path] | [Observable result or relevant test] |
| [Requested media or raw data] | [Local artifact path] | [Playback, integrity, or domain check] |
| [Return report] | [Existing task/capsule convention] | [Commands, results, deviations, remaining issues] |

## Execution steps

1. **Check inputs.** [Minimal checks and expected values; distinguish mismatches from ordinary missing dependencies.]
2. **Implement or analyze.** [Exact remaining change at the relevant interface. Use existing code paths; include an example or a small case table if useful.]
3. **Validate.** [Concrete command and expected result. Run only checks that establish this task's acceptance.]
4. **Run or collect, if authorized.** [Exact command or usable launcher template, bounded workload, output locations, and process ownership.]
5. **Deliver and record.** [Copy requested outputs locally, show verified media promptly, and record source/configuration and raw logs.]
6. **Prepare the return.** [Review the owned diff and follow the authorized commit boundary. Do not push unless explicitly authorized.]

## Failure handling

[Define failures that end the current case and evidence to preserve. Permit repairs of ordinary implementation faults within scope. Escalate changes to the experiment, inputs, interface, acceptance criteria, or ownership to the lead. Do not weaken a failing check or restart completed work simply to obtain a passing result.]

[For a shared Git index lock: preserve it and report the blocked commit; never delete the lock or use an alternative index. This does not block delivery of already available results.]

## Return to the lead

1. Raw results and exact artifact paths, including failures and missing items.
2. What changed, why, and any departure from this package.
3. Commands actually executed and their outcomes; identify reused prior checks.
4. Owned diff/commit identity, source/sync status, and archival completeness.
5. A short interpretation limited to the evidence, plus unresolved questions.

The lead will inspect [specific diff, raw artifact, and acceptance check] before accepting the work. Execution completion is not lead acceptance. Do not claim independent review unless a separate reviewer actually performed it.
