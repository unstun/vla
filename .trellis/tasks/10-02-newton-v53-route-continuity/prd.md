# Preserve safe continuation across compatible reference refreshes

Stage: planning. Planned version v53 from v52; no implementation exists yet.
Parent: ../10-02-newton-corner-continuity.

## Goal and background

Requested goal/yaw and owner stay exact; snap-point jitter may change the reference but must not unnecessarily destroy a freshly valid continuation. Real changed goals/owners/maps and invalid curves still disable reuse.

## Requirements

Own parent R1; all R4–R6 safety/version/storage constraints remain mandatory.
Preserve final goal/yaw, PVA/dynamics, full safety, controller and stop protocol.
No v49 timeout/cancellation, unchecked connector or inherited-source edits.

## Dependency

First implementation target; requires frozen v52.

## Acceptance criteria

- [ ] Real same-owner captured refresh permits a newly admitted curve with original final PVA/dynamics/full-curve checks.
- [ ] Sequential replay extends actual curve reserve and target progression before expiry; repeated same-endpoint trimming does not pass.
- [ ] Changed requested XYZ/yaw, identity/map, expired/malformed curve, unsafe connector and failed final check retain rejection/fallback.
- [ ] Failed refresh restores old reference/window/binding without publishing/restamping the old curve.
- [ ] Inherited cold/native/cache/warm/goal/backend checks and predecessor hashes pass.

The parent scores combined corner progression, >=100 ms tails, strict 30 Hz and
physical/arrival outcomes. Component success alone cannot close those gates.

## Out of scope

Other children, changes to safety thresholds/physics/stop behavior, long runs,
training or real-robot actuation. No unresolved user-owned scope decision remains.
