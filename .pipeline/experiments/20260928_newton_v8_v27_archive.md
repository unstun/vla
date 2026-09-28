---
origin: ai_only
reviewed: false
date: 2026-09-28
---

# Newton v8–v27 repair archive

> [未门控] Codex CLI is available; the current inline instruction prohibits delegated
> implementation/checking, so the archive CLI gate was not run. Primary receipts
> and frozen source hashes were checked by the main session.

Stage: experiment + analysis. Task:09-23-scan-reactive-stair-pedestrian,
in_progress. Execution stopped at Dr Sun's archive request. No new v28 exists.

The local version sequence preserves20 frozen source snapshots with no archive
hash mismatch. v24 physically reaches the short stair goal but does not finish
PD handoff. v26 repairs explicit automatic-layer configuration through the real
loader/TCP/native chain and confirms the correct complete-floor route live.
v27's inspected OMPL seed reduction passes11 native continuations,8unmapped and
5mapped fixture comparisons; its physical full-route run then segfaults near
13.24s, without arrival or verified container-state copyback.

The captured seed269 reproduces abort in a bounds-checked diagnostic. Native
constraint-block tests yield3positive passes and10failures, including2finite
empty-container aborts. The exact live crash stack is not yet located. A prior
finite-constraint fix was lost when restoring the scan_04 optimizer; reuse it
in a separately versioned repair after red/green verification, retaining all
search/terrain/unknown/PVA/dynamic/full-curve gates.

Full details and reproducible entrypoints:
[handoff](../handoffs/2026-09-28_newton_v27_archive/README.md),
[versions](2026-09-26_newton_stair_reproduction/versions/README.md),
[v27 component tests](2026-09-26_newton_stair_reproduction/runs/v27_native_regression01/review.json),
[v27 physical failure](2026-09-26_newton_stair_reproduction/versions/v27/RESULTS.md).
The last fully accepted navigation condition remains one v3 empty12m trial.
No complete-floor, general obstacle, Isaac A4 or real-robot success is claimed.
