# Separate physical floor presence from traversal selection

Stage: planning. Planned version v56 from v55; no implementation exists yet.
Parent: ../10-02-newton-corner-continuity.

## Goal and background

Saved PCT products contain a floor at the guard neighbors but cost 50 excludes it from the <=20 selected evidence. Supply a separate qualified physical geometry role for drop/neighbor presence while keeping central traversal, costs and LiDAR classification unchanged.

## Requirements

Own parent R3; all R4–R6 safety/version/storage constraints remain mandatory.
Preserve final goal/yaw, PVA/dynamics, full safety, controller and stop protocol.
No v49 timeout/cancellation, unchecked connector or inherited-source edits.

## Dependency

Requires qualified frozen v55; verify source/install hashes and component gates before task.py start. Parent links do not imply readiness.

## Acceptance criteria

- [ ] Recorded front-footprint support succeeds through full native entry with qualified physical-presence evidence.
- [ ] True drop, missing/ambiguous/unrelated floor, tall step and cost-rejected central query still reject.
- [ ] Low box, static/unknown obstacle and historical nonterrain remain blocked; physical evidence never waives raw hits.
- [ ] Missing/stale/mismatched added source creates no grant; absent input preserves legacy behavior; configured readiness is explicit.
- [ ] Callback/identity/cache tests plus manager final-PVA/dynamic/whole-curve suites pass.

The parent scores combined corner progression, >=100 ms tails, strict 30 Hz and
physical/arrival outcomes. Component success alone cannot close those gates.

## Out of scope

Other children, changes to safety thresholds/physics/stop behavior, long runs,
training or real-robot actuation. No unresolved user-owned scope decision remains.


## Version allocation update 2026-10-02

Renumbered after reproduced frozen-v53 clock defect: v56 from v55. Original approved behavior scope unchanged. See parent version-allocation record.
