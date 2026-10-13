# v56 design

Authoritative design: parent design.md section D3, plus rollout/rollback
and verification sections. This file binds that reviewed design to this child.

## Behavior boundary

Saved PCT products contain a floor at the guard neighbors but cost 50 excludes it from the <=20 selected evidence. Supply a separate qualified physical geometry role for drop/neighbor presence while keeping central traversal, costs and LiDAR classification unchanged.

## Owned files/responsibility

Native GridMap header/cpp, reactive methods, floor-fill and minimal ETH neighbor plumbing; version-owned physical-floor generator/publisher/wiring/config and native role/obstacle/drop tests.

Use parent-described existing APIs and typed input roles; do not duplicate safety
logic. New behavior must preserve every parent R4 constraint and fail closed on
unqualified inputs. Version data/input/source identity is part of the interface.

## Compatibility and rollback

Requires qualified frozen v55; verify source/install hashes and component gates before task.py start. Parent links do not imply readiness.
Materialize a new source tree and version from this frozen predecessor. Inactive
feature follows original semantics; actual new candidates retain full native
admission. Rollback selects a frozen predecessor, never overwrites its source.


## Version allocation update 2026-10-02

Renumbered after reproduced frozen-v53 clock defect: v56 from v55. Original approved behavior scope unchanged. See parent version-allocation record.
