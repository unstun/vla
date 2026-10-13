# Local trajectory completion and the last-centimetres crawl

Status: surveyed source only, not reproduced upstream behavior. 2026-10-13.
Exact pins, URLs and SHA-256 for downloaded files are recorded in
`references/upstream/2026-10-13_terminal_capture/{selection,files}.json`.
Original file headers and downloaded licenses are retained. No upstream source
is copied into the controller; the implementation adapts a state-machine idea.

| Source | Observed mechanism | Applicability / limitation |
|---|---|---|
| Navigation2 Foxy `a947ab5`, SimpleGoalChecker | Stateful XY tolerance: after entering the region, stop checking XY until reset and finish yaw | Use a completion latch. This is mission-goal code, not an upstream local-spline plugin. BSD header. |
| ROS navigation `f44bb1f`, LatchedStopRotateController | Optional XY latch; goal completion additionally requires stopped odometry; deceleration uses collision checks | Preserve measured stillness separately. Wheel acceleration rules do not establish quadruped stopping. BSD header. |
| CMU Go2 `43d5f54`, pathFollower | Slows with remaining distance; stop-distance threshold inhibits acceleration; rounds small speed to zero; calls vendor StopMove for exact-zero command | Explicit endpoint deadband and stop mode are useful. Vendor Go2 controller is different from this Lite3 policy; repository-wide licensing is not inferred from a package declaration. |
| TEB `9e55af4`, teb_local_planner_ros | XY/yaw goal tolerances plus stopped odometry unless free goal velocity is enabled | Distance alone does not establish physically stopped. BSD-3-Clause. |
| SCAN `348e8a5`, closed_loop_controller / scan_replan_fsm | Expired spline continues proportional position correction outside finish_dist; FSM moves to WAIT_TARGET when curve time expires | Our failure mechanism exists structurally in this ancestor. Source inspection cannot establish its real-world failure rate. Apache-2.0. |
| EGO `bfda512`, traj_server | Expired spline publishes terminal position with zero velocity and acceleration | Multirotor position hold differs from RL velocity tracking. GPL-3.0; reference only. |

Primary links:
- https://github.com/ros-navigation/navigation2/blob/a947ab5656e46ae3aa1afdf95e1706a16e478974/nav2_controller/plugins/simple_goal_checker.cpp
- https://github.com/ros-planning/navigation/blob/f44bb1fc2810399165115cc98b530fe4b9397c18/base_local_planner/src/latched_stop_rotate_controller.cpp
- https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/src/pathFollower.cpp
- https://github.com/rst-tu-dortmund/teb_local_planner/blob/9e55af4724310c34bcfa8cbb3b2783478c1a246a/src/teb_local_planner_ros.cpp
- https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/closed_loop_controller.cpp
- https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_manage/src/traj_server.cpp

Decision: trial v184 with 3 cm local capture plus a per-curve completion latch.
A new accepted curve resets completion, including one with the same endpoint,
because a new feasible recovery may intentionally revisit it. Keep the 5 cm
recovery regression, mission goal checking and actual stopped proof. Do not
raise every small command to 0.6 m/s or restore the old 15 cm deadband.

Evidence boundary: the audit measured 9.155 s of expired-curve correction at
about 2.19 cm error. It separately measured a 0.958 m excursion while all three
RL commands were exactly zero. The proposed change addresses the former; it
cannot be claimed to fix the latter without a separate physical result.

## Post-test correction of the adoption decision

v185 achieved3/5 full-route arrivals and v186 achieved2/5; both also failed
the declared endpoint-crawl criterion. Preserve both and reject adoption.
The contemporaneous unchanged v17706–10 control achieved5/5. This does not
provide exclusive causal attribution, but it does not justify replacing v177.

v187 returns to the original2cm behavior without a local completion latch.
Only prolonged tiny correction after curve expiry fails FollowPath through the
existing exact-owner revoke/zero/PlannerException path. Foxy ControllerServer
uses progress-check failure to throw, publish zero and terminate FollowPath:
https://github.com/ros-navigation/navigation2/blob/a947ab5656e46ae3aa1afdf95e1706a16e478974/nav2_controller/src/nav2_controller.cpp
The actual plugin regression verifies this protocol. Full-route acceptance
remains pending; a stopped command alone is still not physical stillness.
