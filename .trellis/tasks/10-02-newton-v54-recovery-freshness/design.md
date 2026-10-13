# v55 design

Authoritative design: parent design.md section D2, plus rollout/rollback
and verification sections. This file binds that reviewed design to this child.

## Behavior boundary

Long graph work may age the last applied cloud beyond 250 ms while newer messages wait. Apply valid queued inputs at recovery target boundaries, preserving the existing limit and original start PVA.

## Owned files/responsibility

Native FSM cpp; minimal existing GridMap drain interface only if required. Queued-message native regression and full-round profiler are version-owned.

Use parent-described existing APIs and typed input roles; do not duplicate safety
logic. New behavior must preserve every parent R4 constraint and fail closed on
unqualified inputs. Version data/input/source identity is part of the interface.

## Compatibility and rollback

Requires qualified frozen v54; verify source/install hashes and component gates before task.py start. Parent links do not imply readiness.
Materialize a new source tree and version from this frozen predecessor. Inactive
feature follows original semantics; actual new candidates retain full native
admission. Rollback selects a frozen predecessor, never overwrites its source.


## Version allocation update 2026-10-02

Renumbered after reproduced frozen-v53 clock defect: v55 from v54. Original approved behavior scope unchanged. See parent version-allocation record.
