---
origin: ai+web
reviewed: false
date: 2026-09-28
---

# Native seed simplification reference

> [未门控] Main-session archival under the current inline restriction; delegated
> Codex gate not run. Source receipt and observed component tests were checked.

OMPL1.7.0 is pinned at eabb4d0f825666e4553a2ec0ecb9c7a5a33637dd. The
[PathSimplifier source](https://github.com/ompl/ompl/blob/eabb4d0f825666e4553a2ec0ecb9c7a5a33637dd/src/ompl/geometric/src/PathSimplifier.cpp)
contains a deterministic front/back checkMotion branch in reduceVertices.
It preserves the endpoints after a valid direct connector. Pristine source,
BSD-3-Clause license and SHA256 receipts are under
`references/upstream/2026-09-27_ompl_seed_shortcut/`.

Local v27 adapts only that branch to Eigen value-owned points and the existing
SCAN segment checker, after original AStar success and all returned edge checks.
It does not import OMPL's runtime, randomized simplifier, a new planner or relaxed
collision rules. The complete native optimizer and final gates remain mandatory.
The captured stopped-state gains a1.847894m accepted prefix; blocked-direct
controls retain original multi-node seeds byte-for-byte. The subsequent actual
full-route attempt crashes. Component evidence is not physical acceptance or
reproduction of the complete OMPL library.

The inspected
[Fast-Planner state dispatch](https://github.com/HKUST-Aerial-Robotics/Fast-Planner/blob/master/fast_planner/plan_manage/src/topo_replan_fsm.cpp)
is only a survey lead. Local constant hold still generates position feedback,
so no hold-safety shortcut was adopted from it.

Continuation: [archive handoff](../handoffs/2026-09-28_newton_v27_archive/README.md).
