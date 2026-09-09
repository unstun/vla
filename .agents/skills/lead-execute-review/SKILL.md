---
name: lead-execute-review
description: Coordinate model-led work through evidence-backed execution packages, bounded executor ownership, and lead acceptance. Use when Dr Sun requests an Opus execution package or asks a lead model to plan and review another model's work. Keep simple tasks direct.
---

# Lead, Execute, Review

A capable lead model owns the problem, decisions, execution package, and final acceptance. Executors perform bounded implementation or analysis with enough context to act without rediscovering the project. Model names are selectable roles, not a claim that any particular model is always strongest.

## VLA project scope

The authoritative repository is `/Users/sun/tongbu/study/phdproject/vla`.
Sibling repositories are read-only references; remote GPU and simulator roots
are execution copies. Follow this project's `AGENTS.md`, preserve the current
research stage, and do not import another project's experiment approvals.

Use `.pipeline/external_tasks/YYYY-MM-DD_<topic>/EXECUTION_PACKAGE.md` for a
standalone handoff, or keep the package inside the existing VLA experiment or
task directory when it already owns the work. Record checkpoint/source pins,
precision, observation/action interfaces, and inference-versus-training scope
when they affect the task. Keep `surveyed`, `imported`, `reproduced`,
`integrated`, and `validated` distinct in both the package and acceptance.

This skill was adapted from the user-selected local `machine-dog` skill;
[source provenance](references/source-provenance.json) records its actual
working-tree file hashes. Historical source packages are not VLA results.

## Roles and permission boundary

| Role | Owns |
|---|---|
| Lead | Inspect primary evidence, resolve scope, define interfaces and checks, assign work, review actual outputs, and accept or reject the result. |
| Executor | Edit assigned files, run the authorized checks or workloads, diagnose ordinary implementation failures, and return inspectable artifacts. |
| Independent reviewer, when requested or justified | Examine the goal and raw artifacts in a separate context; report supported findings without inheriting the desired verdict. The lead still owns acceptance. |

Use the user's requested models when available; otherwise report the unavailable executor and offer a manual package or another model before dispatch. Do not silently substitute models or relabel the current model. A role analogy does not ask you to locate or install a model or CLI. Preparing an Opus package does not itself invoke Opus.

Follow the active session's delegation permissions. A package does not authorize an external action, new user-owned task, training launch, or wider edit scope. If delegation is disabled, prepare the package and report that it was not dispatched. Do not use another CLI to bypass that restriction. A local workflow configuration change applies only when the session actually receives the revised instructions.

## 1. Lead: ground and bound the work

Before writing a package, inspect one or two relevant local packages when available, plus the current source/artifacts they concern. If no matching precedent exists, use the template rather than importing unrelated experiment history. Prefer the closest task type over the longest example. Separate:

- facts verified by the lead, with exact source locations;
- mutable observations, with verification time and a cheap refresh instruction;
- completed work the executor should reuse;
- unresolved choices that affect correctness, scope, or research interpretation.

Resolve consequential choices with the user when existing authorization does not settle them. Routine implementation details stay with the executor. Do not shift an unresolved research decision into a hidden default.

Define one concrete outcome and its minimum evidence. Identify the existing code path and interface before naming edits; reuse working launchers and native interfaces. Prefer one executor for one coherent change. Split only independent work with disjoint write ownership. Keep the lead's parallel work distinct from the executor's work.

## 2. Lead: write an executable package

Use [the English package template](assets/execution-package.md), scaled to the task, under the VLA package paths above. Follow an explicit request for a Chinese artifact. Do not create a Trellis task merely to hold the package when the user has declined one.

A package must let a fresh executor determine:

1. The user's goal, authorization, allowed files, and frozen boundaries.
2. Exact inputs and existing implementation paths; source identities when relevant.
3. The ordered remaining work, including what is already done and must not be repeated.
4. Commands or command templates, expected outputs, and artifact destinations.
5. Observable acceptance conditions, failure handling, and any actual approval gate.
6. The return report and the evidence the lead will inspect.

Use **Source of Truth** and **Sync Gate** explicitly for remote work: the local repository is authoritative; remote code is a runtime copy; final diagnostic edits return to the same local paths and are reviewable locally. Remote-only edits or unresolved source identity block further experiments and reproducibility claims, not delivery of available media. Follow current project transfer rules rather than copying obsolete checksum gates from an old package.

Specify a narrow change at the actual interface, with file/function pointers and examples where they reduce ambiguity. Do not prescribe every line or create extra tests, documentation, or approval stages without a task reason. State real failure conditions; do not turn every recoverable import error into a new user approval.

## 3. Dispatch and execution

Choose the permitted delivery route:

- **Manual:** provide the package path and a short instruction to paste its execution section into a fresh executor window. Status remains `prepared_not_dispatched` until dispatch is evidenced.
- **Tool or CLI:** send the complete bounded package through an available, authorized route and retain the returned task/agent id or process record. Distinguish `dispatched` from `running` and `completed`.

Do not claim another model received or executed a package because the file exists. Do not create a separate user-owned task unless the user requested one.

Inspect the exact text being sent: it must include the repository root, user authorization, and remaining approval gates. Do not leave these only in an omitted package preamble or inherited chat history.

The executor must preserve other contributors' edits, write only its assigned scope, and record commands, exit outcomes, and result paths. For a failed implementation check, repair the local cause and rerun the relevant check. If the fix would change the approved experiment, interface, acceptance criteria, or ownership, return the failure evidence and proposed delta to the lead. Never silently replace the experiment with an easier one.

When work takes time, the lead should answer new user input and advance independent work. Use bounded status checks; inspect large logs only when a failure or evidence gap requires them. Deliver requested playable media as soon as it is locally available and verified, before bookkeeping blocks the user from seeing it.

## 4. Lead: review and accept

Treat the executor's report as an index to evidence, not the evidence itself. Inspect the actual diff and the raw outputs supporting the goal. Check source/input identity, scope, numerical or behavioral acceptance, and any omitted failure. Reuse passed checks unless a changed file, failure, or unresolved concern justifies rerunning them.

When an independent review is requested and permitted, provide the reviewer the user's goal, package, raw artifacts, and write boundary in a fresh context. Do not supply a preferred verdict. Request findings with severity, exact source location, effect, and a verification method. A self-check must never be described as independent review.

If changes are needed, issue a small correction package referencing the original package, exact findings, owned paths, and checks to rerun. Preserve the earlier result and review. Prefer a bounded correction over restarting the task.

Return one of: **accepted**, **corrections required**, or **blocked**, with the concrete evidence or blocker. Distinguish work completion, media delivery, local archival, and Git commit status. Commit only verified owned changes under the current project rules; an existing Git lock is not permission to delete it or use another index. Keep user-facing conclusions within the verified evidence level.

## Related delivery routes

This skill governs the lead/executor/acceptance cycle. An Opus package can be
handed to the user's Opus session manually. Use an automated executor only when
the active session authorizes it and the actual requested model is available.
[delegate-offline](../delegate-offline/SKILL.md) covers a manual Codex delivery
route; [remote-experiment](../remote-experiment/SKILL.md) covers this project's
remote execution workflow when needed. None requires extra agents for a small
direct task.
