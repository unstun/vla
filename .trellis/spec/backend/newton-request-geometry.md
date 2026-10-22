# Request endpoints, local geometry, and measured continuation

## 1. Scope / trigger

Applies to the frozen v283 Newton candidate when changing global feedback,
local collision queries, warm continuation, legal-start admission, or execution
attempt accounting. Component/offline evidence does not establish physical
acceptance. Preserve the original 0.35 m two-cylinder profile and 0.1 s scanner
period/deadline. Frozen parents and candidate source remain immutable.

## 2. Signatures

- `PCTRoutePlanner::setRequestEndpoints(start, goal)` supplies finite world XYZ
  before feedback refresh and native solving.
- `feedbackExemptAt(point)` covers the existing endpoint 3x3 lattice attachment
  region, derived from `1.5 * resolution` and the existing critical height.
- `rejectedAt(point, yaw, feedback_only)` distinguishes route-selection hints
  from authoritative support/solid and shared-check repair constraints.
- `GridMap::getInflateOccupancy(pos, yaw)` is the common local optimizer,
  publication and active-controller collision query.
- `scan_planner::measuredSeedAgrees(planned, planned_yaw, measured,
  measured_yaw, resolution, offset)` compares both cylinder centers.
- `SharedTraversability::query(header, start, poses, mode)` retains its original
  total 1500 ms request budget.

## 3. Contracts

Set request endpoints before adopting feedback. Hints within endpoint attachment
regions cannot reject those poses/connections. Interior hints and actual static
support/solid refusals remain effective. Moving-start graph expansion retains
safe neighboring headings and swept turns; measured yaw is not discarded.

Cached-route retention validates the measured start connector and remaining
reference after removing obsolete prefix poses, retaining at least two poses.
Retaining a route never substitutes a timestamp refresh for geometry checks.

In `STATIC_ONLY`, exactly `static_evidence_unavailable` may be polled within the
original total budget. Do not renew the budget. Ready malformed responses,
other unavailable evidence, cancellation and hard invalidity retain refusal.

When a static solid field is configured, the common local collision query must
first require `staticTraversability(pos, yaw) == Free`, then perform the existing
live two-cylinder query. Global and local field descriptors/hashes must match.
An absent live return cannot waive a known source wall or support gap.

Warm continuation requires each predicted cylinder center to agree with its
measured counterpart within half the existing map resolution. Match the
half-turn symmetry of the envelope. On disagreement, use the existing measured
position/velocity initializer and invalidate the warm cache. This is a seed
ownership check; it does not certify subsequent physical tracking.

All stored legal starts, including inherited ones, require both physical support
and source-solid extra margins >=0.10 m. Keep qualifying starts. Select nearest
connected replacements deterministically using geometry before planner scoring;
retain goals/headings, exactly 50 distinct spatial pairs, and three unchanged
illegal controls. Start margin is not a proven maximum factory-PD drift.

## 4. Validation and error matrix

| Condition | Required behavior |
|---|---|
| Live hint at a legal endpoint/attachment | Ignore hint exclusion there; retain physical checks |
| Actual endpoint support/solid invalidity | Refuse; include role/XYZ/yaw/support/solid diagnostics |
| Initial static evidence becomes ready within original budget | Resume request |
| Static evidence remains missing | Timeout at original deadline |
| Local live buffer free but source wall collides | Reject local pose/curve |
| Predicted body differs from measured envelope | Existing measured initializer; no teleport or state reset |
| Inherited legal start has either margin below0.10 m | Geometry-only replacement and frozen certificate |
| Frozen result fails | Retain failure; no score-seeking retry or frozen-source edit |
| Launch ledger exists but exact traceback precedes simulator initialization | Inspect direct runtime evidence; retain and classify zero-physics rejection separately |

## 5. Good / base / bad cases

Good: translated and rotated endpoint witnesses pass on v283 and fail on parent
v280; the same recorded static wall is rejected despite a live-free query.
Base: full updated53-case offline matrix passes49/50 legal plus3/3 controls.
This does not prove the ten physical routes satisfy measured geometry.
Bad: infer SupportGap from the generic endpoint exception, suppress a real
support refusal, or count an early launch ledger as evidence of physics.

## 6. Required tests and evidence

Retain parent/candidate endpoint and blind-wall contrasts, interior-hint and
invalid-endpoint controls, measured-seed translation/rotation/yaw controls,
bounded readiness/timeout tests, inherited native tests, and all53 once-only
requests with independent support/source/raw audits. Bind starts, fixtures,
source/install and execution snapshots before physics.

For physical results, report arrival/PD and measured support/solid independently
for every fixed route. Ten-hertz body samples do not prove continuous-time or
foot-contact clearance. Return ten real full-prefix MP4s with hash/decode/state
coverage and visual checks; failed prefixes remain evidence.

Keep direct launch-failure traces, original dispatcher status and a correction
receipt if an inherited ledger was written before episode validation. A verified
lossless relocation may free storage without changing a frozen gate: hash both
copies before freeing redundant source bytes and preserve the old path.

## 7. Wrong vs correct

Wrong: certify the planned spline, then conclude a displaced measured body is
safe; or waive a wall because the current LiDAR did not see it.

Correct: apply the same exact source geometry to every local hard query, bind
continuation to measured state, and independently audit the actual body poses.

Evidence: `versions/v283/{changes.patch,native_manifest.json,manifest.json,
OFFLINE_RESULTS.md,results/component_review.json}` and
`audits/2026-10-19_v283_navigation_geometry/results/recovery/` in the Newton
experiment. Physical acceptance is determined only by the eventual full report.

## Observed v283 gap: actual commands and frozen phase

The frozen controller's `TrackingNode::cmdCallback` may emit pure yaw through
`publishStop(yaw_rate)` and return from goal-position-latched or in-place-turn
branches before advancing spline phase. `sampleCommand(pose, velocity, true)`
calls that tracker; `LocalMotion::command` checks finite output and ownership,
but has no per-command measured-body swept-rotation geometry query. Curve
publication/remaining-curve checking is not a proof for those commands.

At the v283 D07 source-solid witness, the applied command is `[0,0,+1]`; at the
worst S04 witness it is `[0,0,-1]`. At S04's first witness the applied command
is zero while horizontal body velocity remains nonzero during STAND_SETTLING.
The published-curve reconstruction is clear at inspected samples, while the
measured envelopes are not. These are failed physical acceptance results.

Any later repair must exercise the actual command owner, measured yaw, zero-
command drift and in-place/terminal rotation against the same source field.
Do not waive the0.35m boundary or use a new coordinate exception. Keep component
curve validation separate from closed-loop command and body acceptance.

Elapsed time since the published start gives a nominal phase only: the tracker
freezes its internal phase during yaw branches. Never call this reconstruction
an exact tracker replay or infer that its internal phase expired from wall time
alone. Evidence is bound in the audit's `results/candidate_recording/` queries,
margins, control witnesses and native source hashes.
