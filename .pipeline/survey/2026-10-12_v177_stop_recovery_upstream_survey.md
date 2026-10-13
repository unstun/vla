# Stop and recovery design: thirteen upstream repositories

Stage: experiment + analysis. Status: **surveyed**, not upstream reproduced or
integrated. Scope: explain v177 stopping behavior, not rank general navigation
quality from demonstrations. No upstream source was imported into execution.

The actual stop audit is in
`../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-12_v177_stop_causes/`.
Its `upstream_verification.json` records 27 inspected source/license files from
ten repositories, including two Nav2 revisions. All 27 local file hashes matched
fresh downloads from the canonical commit-pinned URLs during this audit.
Existing reference snapshots are reused rather than cloning duplicate trees.

## Findings that matter to this failure

1. Stop output, retry computation, and abandon a route are different actions.
   Current Nav2 MPPI retries internally; current ControllerServer has typed
   failure patience; move_base has controller patience. These mechanisms still
   stop unsafe output. They do not require every temporary invalid command to
   tear down and reacquire the whole navigation owner.
2. A failed replacement trajectory need not invalidate an independently safe
   executing trajectory. SCAN/EGO explicitly try another plan and distinguish
   imminent collision from more distant collision. FASTER commits a trajectory
   only after constructing a safe continuation. Neither design licenses driving
   on an expired map or through an invalid near-term path.
3. Repeated failure should change the search problem. TEB shortens the local
   horizon and retains a preferred turning direction during oscillation recovery.
   The CMU Go2 stack reduces path scale/range before declaring no path. Repeating
   the same infeasible start/seed until a ten-second progress timeout is a weak
   recovery strategy, even if a later attempt eventually completes the route.
4. Failure categories must remain visible. ART exposes invalid start, invalid
   goal, missing map and no solution separately. Our controller currently labels
   `!proof->clear` as `scan_safety_evidence_stale`, conflating geometry with age.
   A source-age violation, unknown cell, support gap, search failure and lack of
   measured progress need distinct diagnoses and recovery policies.

## Source comparison

| Repository / pin | Inspected implementation | Relevant behavior | Applicability and limits |
|---|---|---|---|
| [Nav2](https://github.com/ros-navigation/navigation2/tree/bcc9c48cf468588559d01942b72d511a6b990891), `bcc9c48` | `nav2_mppi_controller/src/optimizer.cpp:285–350`; `nav2_controller/src/controller_server.cpp:680–695,759–793` | MPPI distinguishes soft reset and hard failure, resets/retries with a bounded counter; ControllerServer handles `NoValidControl` with zero output and optional patience. Costmap waiting has a separate timeout. | ROS 2 current snapshot; **not Foxy functionality by default**. Port semantics deliberately; do not assume interfaces or exception types exist in 0.4.7. No comparable runtime rate established here. |
| [Nav2 Foxy 0.4.7](https://github.com/ros-navigation/navigation2/tree/a947ab5656e46ae3aa1afdf95e1706a16e478974), `a947ab5` | `nav2_controller/src/nav2_controller.cpp:265–318`; `plugins/simple_progress_checker.cpp:32–90`; `nav2_costmap_2d/src/observation_buffer.cpp:203,245–259` | Controller catches `PlannerException`, publishes zero and terminates FollowPath. Simple progress uses measured displacement and time. Observation buffer freshness uses time since update; retention separately uses cloud timestamps. | Exact Foxy API reference. Our custom SCAN source-age gate is stricter/different than upstream buffer liveness; copying receipt-time semantics would not prove sensor freshness. Our physical stopped-evidence contract must remain intact. |
| [move_base/navigation](https://github.com/ros-planning/navigation/tree/f44bb1fc2810399165115cc98b530fe4b9397c18), `f44bb1f` | `move_base/src/move_base.cpp:829–834,912–944` | Stale costmap causes zero output and another cycle. A failed local command returns to planning until controller patience expires, then enters recovery. | ROS 1 Noetic, archived repository. Useful state-machine reference, not a drop-in ROS 2 plugin. Wheel-oriented stopping assumptions need separate Lite3 qualification. |
| [TEB](https://github.com/rst-tu-dortmund/teb_local_planner/tree/9e55af4724310c34bcfa8cbb3b2783478c1a246a), `9e55af4` | `src/teb_local_planner_ros.cpp:358–418,935–1022` | Optimization failure, divergence and infeasible trajectory have explicit handling; clears optimizer state; can reduce horizon and retain a turn direction after oscillation. Warns about inconsistent optimization and costmap footprints. | ROS 1, ground robots. Its initial feasibility horizon is configurable and shorter than our whole remaining spline check. Do not copy weaker collision coverage without a separately proven stopping envelope. |
| [SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner/tree/348e8a590a50a5a6bbab8d8c6dcfd171f009be26), `348e8a5` | `src/planner/plan_manage/src/scan_replan_fsm.cpp:713–753,757–789,850–896` | Tries replanning on collision, enters emergency stop when collision is near and replanning fails; accumulated failures can require a new target. Checks first two thirds of a trajectory while its phase is in that region. | ROS 1 legged planner and our algorithmic ancestor. Our independent full-remaining-curve safety gate can revoke before its internal fallback completes. Original demo smoothness is not evidence that this integration should never stop. |
| [EGO-Planner](https://github.com/ZJU-FAST-Lab/ego-planner/tree/bfda51284c8c1b476043255a8145ef925a3778a5), `bfda512` | `src/planner/plan_manage/src/ego_replan_fsm.cpp:323–415` | Three initialization choices, emergency stop, then regeneration after measured speed falls below its threshold; near/far collision distinction. | ROS 1 aerial system, related SCAN lineage. Count as an implementation comparison, not an independent experimental vote. Hover stability and quadrotor dynamics do not transfer to a quadruped. |
| [Fast-Planner](https://github.com/HKUST-Aerial-Robotics/Fast-Planner/tree/41be219fe4ecc43bf0e0c2b42a523f8755ccc0bd), `41be219` | `fast_planner/plan_manage/src/kino_replan_fsm.cpp:255–305` | Searches for a safer local goal near an obstructed goal; otherwise retries. Current trajectory collision requests replanning. | ROS 1 aerial system. Local-goal adjustment requires preserving our final requested goal and route contract; do not silently change mission acceptance. |
| [FASTER](https://github.com/mit-acl/faster/tree/f431c97115b96ea08b85ef7796a53183e08441dc), `f431c97` | `faster/src/faster.cpp:467–550` | Constructs safe and whole trajectories; returns without committing a new plan if safe optimization or append fails. | ROS 1 aerial system, Gurobi-based optimization. Relevant as a safe-continuation architecture, not a quick replacement for the present planner. |
| [CMU autonomy_stack_go2](https://github.com/jizhang-cmu/autonomy_stack_go2/tree/43d5f54b389b251713f0097893c30fa76c870d54), `43d5f54` | `src/base_autonomy/local_planner/src/localPlanner.cpp:950–975`; `pathFollower.cpp:344–407` | Tries reduced path scale/range; no path publishes a one-point stop path. Follower separates heading alignment, goal slowdown, acceleration limits and directional safety stops; forward/reverse switching has hysteresis. | ROS 2 Foxy/Humble branch, Go2. Most directly relevant legged velocity interface. Different path library, footprint and traversability assumptions; no evidence here of equivalence to our Building map. |
| [ART planner](https://github.com/leggedrobotics/art_planner/tree/2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f), `2f3fde6` | `art_planner_ros/src/planner_ros.cpp:44–63,95–144,324–336` | Periodic planning, queued map updates, explicit invalid start/goal/no-map/no-solution feedback; publishes only solved paths. | ROS 1 legged traversability planner, geometric path output. Strong diagnostic taxonomy; does not itself establish our downstream controller stop behavior. |
| [field_local_planner](https://github.com/ori-drs/field_local_planner/tree/f1f8f0fd5fcb38527026747eea469ff19cdd853e), `f1f8f0f` | `field_local_planner_base/.../base_plugin.cpp:183–211,297–330` | Publishes a status independently from valid output; action loop retains EXECUTING/NOT_READY states and distinguishes finished, aborted and preempted. | ROS 1 local planner. Wrapper structure is useful; the inspected wrapper alone cannot prove how long every invalid output retains or zeros a command. |

## License and environment boundary

Exact pins and source SHA-256 are in the machine-readable verification file.
Nav2 is multi-license (Apache-2.0/BSD/LGPL per package); the inspected controller
and MPPI files carry Apache notices. SCAN is Apache-2.0; TEB, FASTER and ART have
BSD-3-Clause metadata; EGO, Fast-Planner and field_local_planner have GPL-3.0
metadata. The navigation and CMU Go2 API metadata do not supply one reliable
repository-wide SPDX identifier: preserve their per-file notices and perform a
package-level license check before any future copying. No licensing assumption
is used to authorize code incorporation in this audit.

Maintenance/default-branch values are those recorded with the 2026-10-09 pinned
inventory, not claims about today's newest release. Fresh remote hash checks
establish the inspected source identity. All repositories were inspected as
source; none was installed, benchmarked, or run against our route this turn.

## Recommended implementation order after diagnosis

0. Qualify physical stopped-pose retention first. v177 attempt01 moves about
   0.957 m during the measured zero-command portion of a 15.86 s recovery span,
   while remaining in STAND_SETTLING. A successfully completed route cannot
   substitute for this independent contract.
1. Separate rejection reasons and measure source receipt, map application,
   snapshot publication and controller consumption times. Investigate map
   publication mutex hold time; current logs do not attribute all delay to it.
2. Keep immediate safe zero output, but introduce a bounded transient-data
   waiting state instead of cancelling the route for every short freshness gap.
   Qualification must retain the original sensor-age limit and measured stop
   proof when an owner actually changes.
3. For stalled geometry, prove the recovery's commanded heading and swept
   footprint are feasible at the measured pose; choose a different safe local
   start/turn/short path instead of repeatedly regenerating the same blocked seed.
4. Only then consider near-term safe continuation with a certified stopping
   envelope. SCAN/EGO's shorter collision horizon is a design reference, not
   permission to drop the current full-curve safety check.

Acceptance must count intermediate stops, stall duration, actual progress,
source-age violations and recovery outcomes in addition to final arrival.
Ten inspected repositories cannot by themselves establish a comparable success
rate or a claim that other projects do not experience these failures.

## Additional legged control references after the drift finding

Three more repositories were fetched as selected, commit-pinned text files under
`references/upstream/2026-10-12_stop_hold/source/`. Each has repository metadata,
a source tree listing, URLs and SHA-256 in `files.json`. None was executed.

| Reference | Inspected behavior | What it does and does not establish |
|---|---|---|
| [DeepRoboticsLab/sdk_deploy](https://github.com/DeepRoboticsLab/sdk_deploy/tree/9ea6ee94bfe90c9a36f5799d39f8dc1d821128db), `9ea6ee9`, BSD-3-Clause | Lite3 `standup_state.hpp` sends interpolated joint targets with explicit gains; `rl_control_state.hpp` runs a separate policy thread; `lite3_policy_runner.hpp:201–237` puts velocity commands into the network observation and computes joint targets. | The official Lite3 implementation distinguishes posture control and RL control. Its RL state does **not** automatically switch to standup merely because velocity is zero. This is evidence for separating those contracts, not an already-qualified stair-stop algorithm. |
| [unitreerobotics/unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym/tree/276801e46c5d433564f24658bac64f254b7d2d4b), `276801e`, BSD-3-Clause | `deploy/deploy_real/deploy_real.py:132–151` holds default joint positions; `153–210` separately evaluates the policy on joystick velocity commands. | The inspected real deployment example targets G1/H1/H1_2, not Lite3. A distinct startup posture state is not evidence of automatic recovery from arbitrary stair poses; do not transplant these joint gains or targets. |
| [leggedrobotics/legged_gym](https://github.com/leggedrobotics/legged_gym/tree/8fa29acc6fd1910c3d9659eef6310bdd301cde0a), `8fa29ac`, preserve file/LICENSE notices | `legged_gym/envs/base/legged_robot.py:872–902` implements velocity-tracking rewards and an optional zero-command posture penalty; air-time reward is suppressed for small commands. | These are training objectives rather than a hard spatial stop guarantee. Their existence does not prove our policy used the same reward settings or can retain position on this stair. No training was run. |

The combined survey therefore covers **13 repositories**, with Nav2 examined
at both the exact Foxy release and a newer pinned revision. Navigation and
locomotion evidence remain separate. The immediate recommendation is an
explicitly qualified physical hold transition plus clearer failure/retry
semantics, not wholesale adoption of another robot's policy or a weaker safety
threshold.

Follow-up correction after Dr Sun's locomotion concern: see
[the seven-repository zero-command training audit](2026-10-12_rl_zero_command_upstream_survey.md).
The observed missed hold transition does not establish that forced or per-leg
holding will fix stair drift. Isolate the current policy's stopping capability,
contact state and inference contract before selecting a handoff repair. No
controller change is justified solely by the earlier state-machine observation.
