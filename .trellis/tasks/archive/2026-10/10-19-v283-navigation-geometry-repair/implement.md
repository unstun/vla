# v283 execution plan

## Current gate

Planning artifacts were presented and Dr Sun explicitly approved the final plan
on 2026-10-19, directing implementation and execution. The planning gate is
satisfied. Work inline; do not dispatch implementation/check sub-agents.

## 1. Establish parents and capture regressions

- [x] Preserve unrelated dirty-worktree changes and verify frozen v280/v281/v282.
- [x] Resolve inherited source against the full v280 source inventory.
- [x] Load `trellis-before-dev` and relevant shared-environment, support,
  trajectory, Nav2/SCAN, PD startup, deadline, Linux execution, versioning,
  rendering and retention specs before coding.
- [x] Check gpu5070ti resources, container and original captures read-only.
- [x] Create v283-owned source/diagnostic paths with explicit parent bindings.
- [x] Reproduce static-free endpoints affected by feedback, including post-solve
  refresh, safe connecting edges, actual obstacles and translated/rotated cases.
- [x] Attribute A04/CU06/CM02/CE03 from request/witness evidence; label any
  reconstructed replay separately from an exact original asynchronous snapshot.
- [ ] Test initial evidence readiness, retained safe/unsafe routes, cancellation,
  mission replacement, deadlines and safe departures under differing yaw.
- [x] Reproduce missing source-wall checking in actual local and final-curve
  calls, with absent live-cloud wall evidence.
- [x] Replay CD12's four support witnesses against curves, tracking yaw, actual
  pose, floor association and epoch before selecting the correction owner.

## 2. Implement and check the shared mechanisms

- [x] Separate feedback hints from endpoint physical validity consistently.
- [x] Add bounded typed diagnostics and reuse existing mission/route retention.
- [x] Connect source-solid checking to common local/controller query paths;
  provide exact geometry repair gradients where necessary.
- [x] Repair the demonstrated CD12 support/heading/tracking discrepancy without
  an all-heading expansion, coordinate exception or support waiver.
- [x] Run targeted parent/candidate tests and inherited native/controller tests.
- [x] Verify all original hard/profile/time contracts and inspect the diff for
  route, scene or coordinate-specific production branches.

## 3. Construct and freeze the cohort

- [x] Certify all 50 legal starts and deterministically replace only failures
  of either 0.10 m margin, including G05 and inherited historical starts.
- [x] Re-certify exact connections to unchanged goals; retain three controls
  and 50 distinct spatial pairs.
- [x] Return old/new poses, exact margins, fixture hashes and selection evidence
  locally before scoring. Freeze the original ten physical case identities.
- [x] Freeze native/configuration/install/evaluator identities, inherited
  snapshot locations, and the parent changes.patch. No frozen-parent edits.

## 4. Finish all 50+3 offline cases

- [x] Execute exactly 53 scored calls under the CPU2 timing protocol; retain
  every refusal and cold initialization measurement.
- [x] Run independent source-solid/support audits after timed native calls.
- [x] Report >=48/50 full-chain legal passes, 3/3 illegal refusals, nonnegative
  admitted/published hard margins, median global <=1.5 s, p95/max, initialization,
  and both first-GPMP denominators. Retain >=90% first-GPMP/admitted.
- [x] Verify each original physical case, including replacement G05, is admitted.
  Return the frozen gate and full ledger locally before launching physics.
- [x] If the frozen gate fails, retain and report failure. Do not overwrite
  v283 or launch physics against a failed offline gate.

## 5. Ten physical attempts and delivery

- [x] Complete generated-config, source, process and scanner preflights.
- [x] Run A04, G05 replacement, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03
  once each. Resume only cases with no formal attempt started.
- [x] Preserve actual profiles, source/install/policy identities, request/map
  diagnostics, resource observations, raw captures and immutable attempt ledger.
- [x] Score endpoint abort causes, solid/support excursions (including CD12),
  arrival, PD, pauses, local planning success and scanner timing separately.
- [x] Render each complete recording, including failed prefixes. Verify decode,
  state coverage and identity; do not regenerate physics.
- [x] Return compact reports/tables/provenance and ten real local MP4s, verify
  hashes, and inspect representative and terminal frames for every route.
- [x] Write RESULTS.md and the video index with unmet acceptance criteria stated.
- [ ] Apply `trellis-check`; review task-owned changes before any commit. Finish
  only when required work is complete; preserve baseline adoption as separate.

## Activation and runbook

After final planning approval:

```sh
python3 .trellis/scripts/task.py start .trellis/tasks/10-19-v283-navigation-geometry-repair
python3 .trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex
```

Record exact v283 build, benchmark, preflight and launch commands in its runbook
before use. Adapt the verified v280 build/v282 launcher with explicit bindings;
inspect generated commands and inherited paths before executing any wrapper.
Planning verification checks documents/references only, not runtime acceptance.

## Evidence boundary at recovery

AC3/AC4/AC5 component/offline evidence is complete; see v283/OFFLINE_RESULTS.md
and audit/results/local_review01.json. The CD12 mechanism is implemented and
passes recorded-input/component checks, while physical correction remains
unvalidated. No exact original asynchronous replay is claimed. The combined
initial-readiness/retention/cancellation/departure test item remains open for
final coverage review; do not infer all its assertions from a total test count.

Five pre-simulator disk-gate rejections are preserved with direct runtime proof
and excluded from the ten-physical-attempt denominator. No native or execution
freeze was modified for recovery. The new coordinator owns automatic resource
waiting and resumes the still-unattempted frozen list.

## Final evaluation and delivery

All53offline calls and all ten single actual physical attempts are complete.
Ten regular local MP4s,465primary compact files, final media/source hash checks,
complete decode/source-frame coverage and local visual checks are complete.
CM07 display revisions preserve all2951source indices/times and all physical
inputs. All program/checker outputs are returned and source-bound.

Offline AC3/AC4/AC5 pass. AC7 delivery passes. AC6 FAILS:5/10goal/PD and2/10with
clear sampled geometry, including a new S04 solid regression. All14881sensor
jobs meet the original0.1s deadline. No true SupportGap appears in navigation
samples;14WrongHeight samples and negative solid margins in D07/S04/CE03 remain.
The complete task is not marked achieved or archived. No automatic commit or
baseline advancement; any further logical navigation repair needs a new integer
version while preserving frozenv283.
