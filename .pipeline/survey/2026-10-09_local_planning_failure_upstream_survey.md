# Local-planning failures in upstream projects

Date: 2026-10-09. Stage: experiment + analysis. Status: **surveyed**.

Question: do comparable projects also fail to produce a usable local trajectory,
and what does their code do next?

Yes. The inspected implementations explicitly handle failed planning, and
public issue reports describe failures during use. Those reports are not
independently reproduced here and do not establish matching causes or failure
rates for our Newton run. No production code, safety threshold, or dependency
was changed. No upstream smoke run or full repository import was performed.

## Source inspection

| Project / inspected revision | Failure handling verified in source | Applicability |
|---|---|---|
| [SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner), main snapshot `348e8a590a50a5a6bbab8d8c6dcfd171f009be26`; Apache-2.0 declared by project | Reference-path replanning tries three initialization choices. Failed rounds increment a counter; reaching its configured limit requests emergency stop and then a new target. Collision checking can also request emergency stop when replanning fails and the predicted collision is near. | Closest quadruped/B-spline implementation. Shows that the original planner anticipates failure; does not prove a particular failure rate. |
| [EGO-Planner](https://github.com/ZJU-FAST-Lab/ego-planner), master `bfda51284c8c1b476043255a8145ef925a3778a5`; GPL-3.0 | `planFromCurrentTraj` tries previous-trajectory initialization, polynomial initialization, and randomized polynomial initialization; returns false if all fail. Safety handling retries or enters emergency stop depending on time to collision. | ROS 1 aerial B-spline planner; relevant recovery structure, different robot dynamics. |
| [TEB](https://github.com/rst-tu-dortmund/teb_local_planner), noetic-devel `9e55af4724310c34bcfa8cbb3b2783478c1a246a`; BSD-3-Clause source notice | Infeasible trajectory: zero command, clear planner, count failure, return `NO_VALID_CMD`. Optional reduced-horizon backup changes the next planning request after failures. | ROS 1 ground-robot local planner. Optimization output can exist but fail its subsequent feasibility check. This is different from failing to find an initial graph path. |
| [Nav2](https://github.com/ros-navigation/navigation2), Foxy release 0.4.7 `a947ab5656e46ae3aa1afdf95e1706a16e478974`; Apache-2.0 / per-file notices | Controller catches `PlannerException`, publishes zero velocity, and terminates the current FollowPath action. | ROS 2 Foxy server behavior; plugin-specific algorithms still determine whether a usable local command exists. Do not assume newer-release failure-tolerance behavior exists in this pin. |

Direct source locations:

- [SCAN FSM, lines 687–723](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp#L687): failure counter and three reference-path attempts; safety fallback around line 802.
- [EGO FSM, lines 320–387](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_manage/src/ego_replan_fsm.cpp#L320): retries and collision response. [License](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/LICENSE).
- [TEB feasibility handling, around line 368](https://github.com/rst-tu-dortmund/teb_local_planner/blob/9e55af4724310c34bcfa8cbb3b2783478c1a246a/src/teb_local_planner_ros.cpp#L368); [optional shorter horizon, around line 878](https://github.com/rst-tu-dortmund/teb_local_planner/blob/9e55af4724310c34bcfa8cbb3b2783478c1a246a/src/teb_local_planner_ros.cpp#L878). The source file carries its BSD license notice.
- [Foxy controller exception handling, around line 287](https://github.com/ros-navigation/navigation2/blob/a947ab5656e46ae3aa1afdf95e1706a16e478974/nav2_controller/src/nav2_controller.cpp#L287).

EGO and TEB branch-head commits were resolved through the public GitHub API
and the pinned files were opened independently. SCAN and Nav2 use the project's
previously selected pins, opened again upstream. This is a failure-path survey,
not a current maintenance, deployment, dependency, dataset or performance audit.

## Reported cases, separate from verified code behavior

- [TEB issue #7](https://github.com/rst-tu-dortmund/teb_local_planner/issues/7),
  opened 2016-05-26: the reporter describes infeasible trajectories, planner
  reset and eventual navigation abort in Stage. This is historical user evidence.
- [EGO-Planner-v2 issue #56](https://github.com/ZJU-FAST-Lab/EGO-Planner-v2/issues/56),
  opened 2026-05-31: the reporter describes repeated replanning/emergency recovery
  in crowded multi-drone tests, citing commit
  `5c99a95880401e2599638d567abc0e240396cb42`. Its proposed root cause and fixes are
  the reporter's claims, not verified repairs. This is v2, distinct from the
  original EGO source inspected above.
- [linorobot2 issue #139](https://github.com/linorobot/linorobot2/issues/139),
  opened 2025-01-24: a user specifying Ubuntu 20.04 / ROS 2 Foxy reports DWB
  finding no valid trajectory among 419 candidates and controller action abort.
  The same report includes global-plan/local-costmap errors and missed loop
  rates; it does not establish our A* or mapper root cause.

## Interpretation for our run

"No usable new curve" can mean the initial graph search failed, an optimizer
failed, or a generated curve was rejected by a later collision/dynamics check.
The two slow failed rounds in the current recording failed before optimization:
one during seed search and one during target-neighborhood search. Calling both
an optimizer numerical failure would be inaccurate. See the
[measured local diagnosis](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-09_over60ms_diagnosis/REPORT.md).

The existence of upstream failures does not qualify our latency, recovery,
freshness or whole-navigation reliability. Conversely, an individual failed
candidate is not itself proof that a planner is defective: the system must
reject candidates that violate its checks. The unresolved question is whether
our failed searches reflect real blocked/unknown space, inconsistent inputs,
or avoidable search/recovery work, and whether recovery remains timely.

The most informative first comparison would replay the same failed inputs
through the pinned SCAN search/initialization and our version, recording query
rejections and map/clock state. TEB/EGO provide recovery references but cannot
be treated as drop-in, measured improvements. No new reproduction is claimed.
