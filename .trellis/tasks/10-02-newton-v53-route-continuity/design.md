# v53 design

Authoritative design: parent design.md section D1, plus rollout/rollback
and verification sections. This file binds that reviewed design to this child.

## Behavior boundary

Requested goal/yaw and owner stay exact; snap-point jitter may change the reference but must not unnecessarily destroy a freshly valid continuation. Real changed goals/owners/maps and invalid curves still disable reuse.

## Owned files/responsibility

Native FSM header/cpp and minimal manager context/header/cpp; version-owned actual-route/native-manager and sequential-replay regressions.

Use parent-described existing APIs and typed input roles; do not duplicate safety
logic. New behavior must preserve every parent R4 constraint and fail closed on
unqualified inputs. Version data/input/source identity is part of the interface.

## Compatibility and rollback

First implementation target; requires frozen v52.
Materialize a new source tree and version from this frozen predecessor. Inactive
feature follows original semantics; actual new candidates retain full native
admission. Rollback selects a frozen predecessor, never overwrites its source.
