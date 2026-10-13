---
date: 2026-10-08
stage: implementation_and_component_analysis
status: full_nav2_implemented_physical_validation_in_progress
reviewed: false
---

# Foxy navigation integration

Target: Ubuntu 20.04, ROS 2 Foxy, ARM64 on the existing Jetson. Dr Sun approved
full Nav2 integration after the earlier controller-plugin increment. The
[historical BT-only proposal](bt_only_design_superseded.md) remains superseded.

## Implemented chain

1. Public `NavigateToPose`, optionally fed by the existing HTTP goal adapter,
   enters a mission gateway preserving caller identity and the applied-stop gate.
2. The actual BT Navigator in `/nav2_internal` runs ComputePath, BindScanRoute,
   FollowPath, and measured-stop recovery before retries.
3. The `nav2_core::GlobalPlanner` plugin invokes the pinned native PCT worker.
   Its service correlates replies with the current mission and rejects late data.
4. The SCAN Controller/GoalChecker plugins run inside the patched Foxy 0.4.7
   ControllerServer. An exact P2B binding acknowledgment precedes FollowPath;
   only native FSM admission authorizes the existing command gate.
5. SCAN owns its native 3D mapper and solver. A Nav2 TerrainLayer consumes a
   source-stamped body-height projection of the completed immutable snapshot.
   Native full-curve collision/support checks remain authoritative on stairs.
6. Controller output retains command identity. Both task termination and retries
   wait for controller hold plus causal measured stillness from applied evidence.
   A failed stop keeps ownership latched; no new goal may bypass it.

No second 3D mapper, alternative local planner, or standalone SCAN command timer
is introduced. Original XYZ/yaw, PCT layer/map identity and target-height semantics
are preserved. The optional HTTP adapter makes no planning/arrival decisions.

## Mapping admission

The v87 temporal buffer keeps a 0.5 s observation window and a bounded queue.
The v91 profile changes worker scheduling from 5 to 20 Hz; scan input remains
10 Hz. Normal replay of the same 188 observations keeps every scan and the same
final full-map/occupancy bytes. Sampled map age falls from 400 to 100 ms. FIFO is
also 100 ms on this ARM64 normal-load control. These measurements do not prove
30 Hz physical navigation and do not attribute every prior delay to FIFO.

Injected 650 ms stalls are separate fault tests. They still produce stale maps;
the 250 ms observation gate, 100 ms body limit and 100 ms native safety lease
remain unchanged. Evidence loss under faults must be reported independently.

## Evidence boundary

Actual ARM64/Foxy builds, native PCT planning, 21 GTest cases, stock Nav2 goal/cancel,
full mission protocol and native 40-scan packaged launch have direct evidence.
Protocol fixtures explicitly synthesize SCAN curves/map/safety and use a
kinematic plant. They do not qualify physical stairs or the robot.

The original Newton integration now uses the same Nav2 graph. Its failures and
versioned compatibility repairs are retained in the
[full implementation report](../../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-08_nav2_full/REPORT.zh.md).
The selected reference remains v48 until complete navigation acceptance.
Jetson inventory, receive-only sensing/TF validation, applied-evidence integration
and explicitly authorized walking remain separate gates. Dr Sun will provide
Jetson access later; no connection or robot actuation has occurred.
