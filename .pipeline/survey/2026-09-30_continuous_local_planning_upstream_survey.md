---
origin: ai_only
reviewed: false
status: surveyed
---

# Continuous Local Planning And The v34 Handoff Gap

Scope: source inspection for Dr Sun's question about pauses during local
planning. No new implementation, upstream reproduction, or physics run was
performed. Frozen v34 remains unchanged.

## Inspected Sources

| Source | Revision and license | Inspected entry points |
| --- | --- | --- |
| [Nav2](https://github.com/ros-navigation/navigation2) | `3c3db59d6969d8ecee8e68468693d006397f4a0c`; root license delegates to each package | `nav2_mppi_controller/src/optimizer.cpp`: `evalControl`, `prepare`, `shiftControlSequence`, `getControlFromSequenceAsTwist`; existing local RPP source: `computeVelocityCommands`, `applyConstraints`, `setPlan` |
| [SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner) | `348e8a590a50a5a6bbab8d8c6dcfd171f009be26`; root Apache-2.0 | `src/planner/plan_manage/src/scan_replan_fsm.cpp`: `EXEC_TRAJ`, `planFromCurrentTraj`, `getLocalTarget`, `checkCollisionCallback` |
| [EGO-Planner](https://github.com/ZJU-FAST-Lab/ego-planner) | `bfda51284c8c1b476043255a8145ef925a3778a5`; root GPL-3.0 | `src/planner/plan_manage/src/ego_replan_fsm.cpp`: the same trajectory-state handoff and distance-trigger pattern |

The additional FSM and MPPI optimizer files were read at their exact pinned
raw GitHub URLs. Previously acquired local source and license files remain
under the experiment's `references/2026-09-26_trajectory_diagnosis/` and
`references/2026-09-27_min_cruise/`. No new source snapshot was imported.

## Observed Upstream Behavior

1. **Path planning and tracking can overlap.** The Nav2 Jazzy default
   `NavigateWithReplanning` behavior tree recomputes the global path while
   `FollowPath` is running. Its documented global replanning rate is 1 Hz.
   The controller server's documented default is 20 Hz; the MPPI example
   configures 30 Hz. These are defaults/examples, not universal robotics
   requirements. Sources: [behavior tree walkthrough](https://docs.nav2.org/jazzy/getting_started/nav2_behavior_trees/detailed_behavior_tree_walkthrough/detailed_behavior_tree_walkthrough/),
   [controller server](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/).
2. **MPPI updates a rolling control horizon.** At the inspected Nav2 pin,
   `evalControl` loads current robot pose/speed and the reference path,
   optimizes the control sequence, returns one near-term velocity command,
   and optionally shifts the sequence for reuse. It does not wait for the
   complete prediction horizon to finish. The selected sequence index is
   zero or one depending on `shift_control_sequence`; describing this as
   executing the entire optimized trajectory would be incorrect. Source:
   [pinned optimizer](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_mppi_controller/src/optimizer.cpp#L123).
3. **Spline planners carry state across replans.** EGO and SCAN use the old
   trajectory's evaluated position, velocity and acceleration as the next
   planning start state. Both inspected FSMs also suppress nominal replanning
   while displacement from the local trajectory start is below a configured
   threshold. EGO uses global-reference velocity at intermediate local
   targets and zero terminal velocity near the global endpoint's braking
   distance. Sources: [EGO FSM](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_manage/src/ego_replan_fsm.cpp#L319),
   [SCAN FSM](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp#L698).
4. **Continuous tracking retains slowing and stopping conditions.** Nav2 RPP
   regulates speed for path curvature and nearby obstacles, slows toward the
   path end, and stops on projected footprint collision. EGO's safety
   callback tries replanning and enters emergency stop when a failed replan
   leaves an imminent collision. Smooth operation is not a guarantee that
   every static corner, unknown area, or moving obstacle can be traversed
   without stopping. Source: [RPP documentation](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/configuring_regulated_pp/).

## Mapping To Frozen v34

Local source:
`../experiments/2026-09-26_newton_stair_reproduction/runtime/scan65_evidence_floor_v34/src/plan_manage/src/scan_replan_fsm.cpp`.
Configuration:
`../experiments/2026-09-26_newton_stair_reproduction/versions/v34/building_planner.yaml`.

- The v34 configuration sets `fsm.thresh_replan` to 1.0 m. `EXEC_TRAJ`
  retains the upstream near-start suppression at line 967.
- The local shortened-prefix fallback explicitly assigns zero terminal
  velocity at line 1197. In reference mode, expiration requests the next
  local window at lines 929-935 instead of dropping the global target.
- `planFromCurrentTraj` already carries old-trajectory PVA at lines 1037-1039.
  This useful upstream mechanism should be retained and its actual switching
  time/latency verified; sampling PVA alone does not prove seamless runtime
  continuity.

**Inference from these sources and the preceding v34 telemetry diagnosis:**
a short stopping trajectory that never travels 1 m can suppress nominal
replanning until expiration. The next solve then occurs after the robot has
already reached the stopping tail. The observed short gaps and the long
corner failure are different issues; early handoff does not establish a
solution to the corner's geometric/search failures.

## Narrow Recommendation, Not An Implemented Change

Prioritize a v35 design for triggering replenishment before the current
trajectory's braking/expiration deadline, accounting for measured solve and
delivery latency, and carrying PVA at the intended switch time. Retain a
collision-checked stopping tail when no safe successor is accepted. A
zero-speed tail can coexist with continuous motion if replaced sufficiently
early; removing all stop endpoints is not justified by this survey.

Acceptance should distinguish: successor arrival before braking; measured
PVA/command continuity; intentional stops with recorded reasons; and a safe
stop when replenishment fails. Inspect the static corner failure separately.
Nav2's wheeled-robot motion models and 2D costmaps are useful architectural
references, not an immediately validated replacement for Lite3's 3D stair
trajectory and locomotion interface. Dynamic-obstacle performance remains
unvalidated. No new installation or original upstream demo was executed.
