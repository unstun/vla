---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
question: "Dr Sun: what end-point (goal) tolerance do other planners use; would raising the SCAN acceleration limit to 2 m/s^2 be an option?"
---

# Goal tolerances and acceleration limits: defaults in other planners

Defaults were read from each project's source on 2026-09-17. These are package defaults, not recommendations for
Lite3.

| Stack | Goal XY tolerance | Goal yaw tolerance | Accel limit default | Source |
|---|---|---|---|---|
| Nav2 `SimpleGoalChecker` (ROS 2) | 0.25 m | 0.25 rad | n/a (controller-specific) | `nav2_controller/plugins/simple_goal_checker.cpp` initializer list, <https://raw.githubusercontent.com/ros-navigation/navigation2/main/nav2_controller/plugins/simple_goal_checker.cpp> |
| ROS 1 `base_local_planner` limits (used by DWA) | 0.10 m | 0.10 rad | `acc_lim_x` 2.5 m/s^2 | <https://raw.githubusercontent.com/ros-planning/navigation/noetic-devel/base_local_planner/src/local_planner_limits/__init__.py> |
| ROS 1 `teb_local_planner` | 0.20 m | 0.10 rad | `acc_lim_x` 0.5 m/s^2 | <https://raw.githubusercontent.com/rst-tu-dortmund/teb_local_planner/noetic-devel/cfg/TebLocalPlannerReconfigure.cfg> |
| Our pilot (arrival check) | 0.25 m (+ Z 0.20 m) | not checked | n/a | `p2b_execution/inputs/pilot.json:36`; `review_two_goal.py` |
| Our SCAN build | no explicit goal tolerance | n/a | `manager.max_acc` 0.5 + `optimization.acc_tolerance` 1.0 (default) = 1.5 m/s^2 gate | `builds/scan_04/src/plan_manage/config/planner.yaml:54`; `src/planner_manager.cpp:58,61,462` |

SCAN's own finish logic (`builds/scan_04/src/plan_manage/src/scan_replan_fsm.cpp`):
- a local trajectory is finished when its time runs out (`t_cur > duration - 1e-2`, line 844);
- no replanning happens within `fsm.thresh_no_replan` = 0.1 m of the end point (line 888; `planner.yaml:7`);
- in waypoint mode, the next waypoint is taken within 0.5 m (line 830).

Lineage: PCT-SCAN-ROS2 derives its planner packages from SCAN-Planner (Zheng et al., arXiv 2606.19555), a local
planner for quadrupeds (`source/pct_scan_base/NOTICE`).

## Reading for AC3

These tolerances apply to the robot's final position. None of the stacks sets a separate tolerance for where the
planned path ends, because the path is replanned and the goal checker judges the robot. The task's 0.05 m
single-plan limit is therefore stricter than all three defaults. The report-only follow-up endpoints (at most about
0.08 m in both builds) are within the 0.10-0.25 m goal tolerances and within SCAN's own 0.1 m no-replan zone.
The system-level check remains the Isaac arrival check (0.25 m, the Nav2 default).

## Reading for a 2 m/s^2 gate

- The gate is a feasibility check with tolerance on top of the design acceleration: 0.5 m/s^2 design + 1.0 = 1.5.
- With the fix, sampled path maxima are about 0.59 m/s^2, close to the design value. With the original line, path
  ends reached 1.26-1.57 m/s^2 in the native sweep (`native_suite_20260917T083723Z`), because a non-zero terminal
  acceleration is imposed where the path should come to rest.
- Raising the gate to 2.0 would accept those paths and move the failure boundary, not remove it. The wrong value
  depends on sample spacing versus polynomial duration, and no bound below 2.0 is established. It would also relax
  the check for every trajectory.
- The ROS 1 defaults (2.5 for DWA, 0.5 for TEB) show that limits depend on the robot. Lite3's real acceleration
  capability under the V12 policy has not been measured here, so any gate change needs its own evidence.
