# Repair the 43-second Newton planner corner stall

Stage: planning. Dr Sun requested "fix them" after the frozen v52 corner audit,
then approved task creation and planning. This integration parent owns combined
acceptance; its three ordered children own implementation.

## Goal

Restore safe continuity through the Building corridor corner, remove avoidable
failed recovery work, and measure whether local planning reaches 30 Hz on
gpu5070ti under the original physics, goal and safety contracts.

## Evidence

The original last accepted curve is at 42.338360 s; a same-owner refresh clears
continuation state and the 42.353352 s solve fails after 455.377 ms. Its curve
ends at 43.379634 s. Later recovery reaches 711.404 ms and rejects front support.
The native freshness probe changes supported targets from Free at 245 ms age
to StaleInput at 270 ms across the unchanged 250 ms limit.

Primary records: the Newton experiment's audits/2026-10-02_v52_corner_43s/REPORT.md,
result.json, corner_evidence.json and verification.json. Newly verified upstream
and PCT distinctions are recorded in this task's research directory.

## Requirements

- R1: Preserve still-owned, freshly valid remaining-curve initialization across
  compatible reference refresh. Reproject the feasible window in new geometry;
  actual target/expiry reserve must advance, not just accepted curve IDs.
- R2: Apply newest queued input before recovery target admission. Preserve the
  250 ms cloud limit and all body/terrain freshness rules.
- R3: Distinguish physical floor presence from traversal eligibility so omitted
  cost-rejected neighboring floors are not interpreted as open drops. Preserve
  central traversal, layer association, true-drop, step, occupancy, unknown-space
  and historical-nonterrain rejection rules.
- R4: Preserve requested final goal/yaw, PVA/dynamic limits/tolerances, controller,
  PD/RL, stop protocol and complete native safety admission. No v49 deadlines,
  cancellation, or upstream unchecked extension/linear-Z rewrite.
- R5: Each logical repair gets an integer version and qualified frozen parent.
  Preserve v48 reference and v49/v50/v52 evidence; a version is not acceptance.
- R6: Validate on gpu5070ti without disturbing other jobs. Keep raw/derived data,
  logs, archives and builds remote; return source, compact evidence and review MP4.

## Child map and explicit dependencies

| Child | Planned version / parent | Requirement | Prerequisite |
| --- | --- | --- | --- |
| 10-02-newton-v53-route-continuity | v53 / v52 | R1 | First target after review |
| 10-02-newton-v54-recovery-freshness | v54 / qualified frozen v53 | R2 | v53 component gates and source freeze |
| 10-02-newton-v55-floor-presence | v55 / qualified frozen v54 | R3 | v54 component gates and source freeze |

R4–R6 apply to every child. Task-tree links alone do not imply dependency order.

## Acceptance criteria

- AC1 (R1/R4): Exact same requested goal/yaw and owner with regenerated reference
  and snapped-endpoint jitter permits freshly checked warm initialization. Changed
  identity/requested goal/yaw/map, invalid/expired curve, malformed input and unsafe
  geometry still fail closed. Failed refresh restores previous state.
- AC2 (R1): Actual native first-failure replay admits a new curve through original
  PVA/dynamic/whole-curve gates. Sequential replay demonstrates target/expiry
  reserve extension before expiry; unchanged endpoint/end time is insufficient.
- AC3 (R2/R4): Supported-prefix fixture with queued fresh input passes after the
  existing callbacks apply it; without fresh input it still rejects above 250 ms.
  Timestamp/body/map identity and cache invalidations remain correct.
- AC4 (R3/R4): Qualified physical-floor input resolves recorded front support.
  True drops, absent/ambiguous/unrelated floors, too-tall steps, rejected central
  traversal, unknown obstacles, low boxes and nonterrain history remain blocked.
  Missing/stale/mismatched input creates no positive grant.
- AC5 (R4/R5): Inherited native/cache/warm/goal/backend/version/PVA/dynamic and
  complete-curve checks pass. Inactive-feature cold geometry stays exact. Verify
  all frozen predecessor source hashes unchanged.
- AC6 (R1–R6): Idle-host 90 s trials pass the corner and advance at least 2 m
  along the route beyond its frozen stand location, with no >1 s stationary pause
  there in the 39–55 s focus. Compare whole-run path/pauses to v52 and v48's
  29.794 m trial. Recording bound is not arrival/final-PD acceptance.
- AC7 (R2/R6): Report full-round median/P95/P99/max, >=100/1000 ms counts,
  complete-window attempted/successful Hz, rolling wall-second counts mapped to
  simulation time, curve reserve, controller Hz, path, pauses and RTF. Tail
  elimination requires zero >=100 ms rounds. Strict 30 Hz requires actual cadence
  and no >33.333 ms local solves. Do not hide startup, failures or paused time.
- AC8 (R5/R6): Verify source/install/input/return hashes and remote locators.
  Separate component, physical-continuity, performance and arrival claims;
  all unpassed flags stay false.

## Out of scope

New VLA architecture, training, real-robot actuation, physics/contact/locomotion
changes, final goal/yaw changes, relaxed freshness/traversal/drop thresholds,
hard solve deadlines, stop redesign, old-version overwrite, unique-evidence
deletion or unrelated repository/harness changes.

## Planning status

No unresolved user-owned scope decision remains. Runtime speed and physical
acceptance are technical gates, not assumed outcomes. Parent and children need
final planning review before implementation. No product source changed in planning.
