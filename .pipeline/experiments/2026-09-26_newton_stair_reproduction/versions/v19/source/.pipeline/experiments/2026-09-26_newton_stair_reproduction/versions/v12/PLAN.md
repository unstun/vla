# v12: consistent heading for a planned continuation

Parent: v11. Stage: experiment + analysis. Repair authorized by Dr Sun.

One behavior change in the native FSM: reference-mode local target and shorter
prefix occupancy checks derive heading from the actual planned start state,
using the existing `collisionSegmentYaw` helper, as the native search/segment
checks do. The previous reference curve endpoint and measured odometry differ
by about 4.7 cm in the captured stop; aiming from odometry rotates the cylinder
query even when the planned motion is straight. This causes contradictory
target and segment decisions. First planning still starts from measured body
state, and near-zero translation uses the existing fresh measured-yaw fallback.

Keep non-reference mode unchanged. Only `scan_replan_fsm.cpp` changes in
`scan50_heading_v12`. Do not change collision buffers, dimensions, obstacle
classification, speed limits or the actual robot heading. Full-curve collision,
PVA and dynamics remain mandatory. No body position is injected.

Validation: actual v10 original-input replay is the failing baseline; the same
66 scans, body state, last spline and route must produce an accepted native
continuation with full-curve and PVA checks. Add no-motion/unknown/stale and
same-segment heading controls. Preserve the previously verified generic
obstacle suite. Bounded physical stair execution is a separate required gate.
