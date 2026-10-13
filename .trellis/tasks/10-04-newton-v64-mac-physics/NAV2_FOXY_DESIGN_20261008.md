# Foxy design continuation

Stage: planning. On 2026-10-08 Dr Sun fixed the target to the existing Jetson,
Ubuntu 20.04 and ROS 2 Foxy; upgrading the robot to Ubuntu 22.04 is not a
prerequisite. This is a design continuation of the mapping/continuity work.

Reviewable deliverables:

- [Chinese overview](../../../.pipeline/design/2026-10-08_nav2_foxy/README.zh.md)
- [Technical design and acceptance](../../../.pipeline/design/2026-10-08_nav2_foxy/design.md)
- [Pinned source audit](../../../.pipeline/design/2026-10-08_nav2_foxy/source_audit.json)

First migration slice uses official Foxy Nav2 task/BT/lifecycle components with
a thin adapter to the existing PCT/SCAN backend. It preserves native 3D/stair,
identity, command-owner and physically verified stop contracts. Foxy cancellation
does not prove stop; new ownership waits for controller hold and measured
stillness. No default planar recovery or latest-only frame dropping is adopted.

The design records build, mock, command-free, Newton and Jetson receive-only
gates. Real-robot motion requires separate explicit authorization. No Nav2
runtime was imported, built or integrated in this design step; no new runtime
version, current-version promotion, training or remote execution. Current v48
and frozen failed v82 remain as recorded. Main task status stays in_progress.
