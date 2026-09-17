---
origin: ai_only
reviewed: false
checked_on: 2026-09-16
---

# Existing Lite3 Stack: Reuse Map And Gaps

The source repositories were inspected read-only. No sibling file, estimator,
robot process, controller or simulator was changed or started by this audit.

## Navigation and control

Repository: /Users/sun/tongbu/study/phdproject/machine-dog-nav.
Branch: codex/scan-foxy-isaac. HEAD:
848b4aecd01237805e0564c88d3ba09146fd2353.

| Capability | Primary source | Current boundary |
|---|---|---|
| Isaac Lab Lite3 runtime | integration/lite3_sim_bridge/lite3_sim_bridge/run_pct_scan_building.py, AppLauncher and V12 environment | Persistent articulated dynamics exist; current wrapper is a frozen fixed-goal experiment |
| V12 locomotion | VLA references/upstream/2026-09-11_lite3_v12_locomotion/SOURCE.md | Existing pinned runtime/weight evidence; no new policy or V17 substitution |
| Native global route | .pipeline/experiments/2026-09-11_pct_scan_upstream_baseline/native01/result.json and REPORT.md | PCT TomogramPlanner output; freeze map, coordinate and body-height semantics |
| Local replanning | integration/pct_scan_upstream_ws/src/plan_manage/src/scan_replan_fsm.cpp, pathCallback | Accepts initial_path updates and can enter REPLAN_TRAJ; action IDs/receipts/cancel/results still need an adapter |
| Reference publication | integration/pct_scan_upstream_ws/src/plan_manage/scripts/reference_path_publisher.py | Current node publishes one configured path then cancels its timer |
| Control/feedback transport | protocol.py, body_state.py, command_state.py, transport.py and foxy_bridge_node.py in the bridge | Framed transport, command bounds/watchdog and measured-state identity are reusable |
| Contact observation | contact_guard.py and Building runner's contact policy | All-substep contact records exist; native_v12 does not terminate for every non-foot contact |
| Localization in this simulator | Building runner root_pos_w/root_quat_w | Simulator-truth pose, not executed SLAM |

The selected native PCT/SCAN port is based on
yagami-light7/PCT-SCAN-ROS2 1cf45a1c12ca785ce533293302be09d51daf0ccb.
Its 65 files match UPSTREAM_MANIFEST.json. It must not be confused with the
older project-modified integration/scan_planner_foxy_ws directory.

The native runner uses an Isaac Lab conda environment plus a Podman Foxy
container. The earlier probe for docker and /opt/ros on the default 5070 PATH
did not inspect this stack and is not proof that ROS resources are absent.

## Evidence and source freeze

The prior native_full02 summary records GOAL_REACHED_AND_STOPPED, 98.08 sim s,
74.063 m travel, 0.03768 m final XY error, zero non-foot force, zero autoresets
and zero pose injection. This is one fixed-goal navigation result, not language
navigation or general reliability proof.

The machine-readable audit is isaac_source_audit.json. All 79 committed bridge
files equal the current bridge working tree. Of 151 compared prior executed
source files, 150 equal the corresponding current files; run_pct_scan_building.py
differs. That difference needs review and a new runner test before inheriting
the old result. The full sibling tree is dirty and the native port is untracked
at this HEAD, so exporting the whole working tree is not the selected import.

Only the committed 79-file bridge was exported in this turn. Location:
references/upstream/2026-09-16_lite3_isaac_harness_backend. Acquisition and
per-file hashes are recorded there. The selected protocol, command-state,
feedback-health, contact-guard, transport and adapter-core tests gave 93 passed,
1 skipped and 15 subtests passed. The skip is
test_foxy_bridge_publishes_dual_clouds_with_same_stamp_and_frame because rclpy
is unavailable in the local test interpreter. No ROS/Isaac runtime claim.

## Real localization reuse candidate

The actual physical-perception implementation is in the sibling machine-dog:
2_experiment/deployment/lite3_fast_livo2_v1.2/README.md and PROVENANCE.md.
Its upstream source identity is DeepRoboticsLab/fast-livo2-deep-robotics
624b45c90bb76484a1612eaf243b962461c84819 plus the documented deployment patches.

The current local README distinguishes maintenance v1.2.1 from candidates
v1.2.4 and v1.2.9. It documents a 600-second receive-only maintenance run, but
also failed candidate stability and still-pending candidate hardware gates.
The newer artifacts/2026-09-08_slam_fixed_input_replay/README.md says the pose
offset/jump issue is not closed: R5 has offline replay evidence and live
R4/R5 comparison remains pending. These are records inspected now, not a fresh
hardware check. Do not silently select the numerically latest candidate.

Reuse the verified sensor/topic/calibration interfaces, then pin a selected
estimator build and test motion, frame alignment, map reset and bounded failure
under the navigation workload. Stationary display or replay success cannot
establish closed-loop localization suitability.

## Required new upper/backend interfaces

- Synchronized RGB-D and capture-time map/odom/base/camera transform snapshots.
- Grounded semantic target ID plus map epoch, frame, units and uncertainty.
- Navigation submit/accept/feedback/cancel/result with one active owner and
  idempotent requests. Publishing a path alone is not acceptance proof.
- Continuous robot/policy/map state across subgoals and model calls.
- Failure and operator-stop signals that remain effective if the model is down.
- Separate evaluator scoring and online subgoal feedback.

PCT native Z values are body references with the documented Lite3 0.35 m
reference height. The display-only +0.5 m offset is not part of execution.
The adapter must make ground points, body targets and floor/layer identity
explicit rather than add these offsets again.

Existing VLA phase_c camera/lockstep code is an additional reuse reference.
Its optional fusion combines RGB with ideal head_eval depth, so an independent
RGB-D alignment test is mandatory before using that mode for target geometry.
