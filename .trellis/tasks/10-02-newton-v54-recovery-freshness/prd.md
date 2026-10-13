# Refresh newest queued input before recovery admission

Stage: planning. Planned version v55 from v54; no implementation exists yet.
Parent: ../10-02-newton-corner-continuity.

## Goal and background

Long graph work may age the last applied cloud beyond 250 ms while newer messages wait. Apply valid queued inputs at recovery target boundaries, preserving the existing limit and original start PVA.

## Requirements

Own parent R2; all R4–R6 safety/version/storage constraints remain mandatory.
Preserve final goal/yaw, PVA/dynamics, full safety, controller and stop protocol.
No v49 timeout/cancellation, unchecked connector or inherited-source edits.

## Dependency

Requires qualified frozen v54; verify source/install hashes and component gates before task.py start. Parent links do not imply readiness.

## Acceptance criteria

- [ ] Queued fresh input reaches the actual native predicate through original callbacks before prefix admission.
- [ ] No queued valid input still rejects the supported target above 250 ms; no synthetic refresh of timestamps.
- [ ] Body/map/clock provenance and cache invalidation are correct; start PVA is unchanged across retry chain.
- [ ] Full recovery profiling shows boundary drains, not redundant per-node/per-sample processing.
- [ ] Inherited v54 and native/cache/warm/goal/backend tests and parent source hashes pass.

The parent scores combined corner progression, >=100 ms tails, strict 30 Hz and
physical/arrival outcomes. Component success alone cannot close those gates.

## Out of scope

Other children, changes to safety thresholds/physics/stop behavior, long runs,
training or real-robot actuation. No unresolved user-owned scope decision remains.


## Version allocation update 2026-10-02

Renumbered after reproduced frozen-v53 clock defect: v55 from v54. Original approved behavior scope unchanged. See parent version-allocation record.
