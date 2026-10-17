---
origin: ai_only
reviewed: false
status: surveyed
date: 2026-10-16
---

# UAS public quadruped implementation versus the Lite3 PCT–SCAN stack

**Recommendation: do not replace the complete local navigation stack with UAS
as a shortcut to reliable stair navigation.** Evaluate OmniPlanner separately
as a potential global exploration/route source if unknown-space autonomy is the
objective. The public UAS release does not supply the ANYmal perceptive
execution capability that underpins its quadruped demonstrations.

This narrows the earlier maturity survey: UAS is an actively developed,
substantial autonomous-system release, but its ground-robot experiment must not
be treated as delivery of a portable four-legged local planner and locomotion
stack.

## Inspected evidence

The [detailed code map](../../references/upstream/2026-10-16_uas_quadruped_audit/comparison.md)
and [manifest](../../references/upstream/2026-10-16_uas_quadruped_audit/repository_manifest.yaml)
bind the findings to UAS `cb78bf7`, ten fixed dependencies, four current moving
dependency branches, and two additional upstream default branches. No upstream
runtime was executed.

| Layer | Public implementation found | Remaining Lite3 work |
|---|---|---|
| Localization and mapping | MIMOSA estimator, volumetric mapping, elevation mapping dependencies and wiring. | Sensor timing/extrinsics, frames, map behavior and comparable perception validation. |
| Global and local graph planning | GBPlanner3 exploration, homing, target navigation, geometric ground projection and slope/occupancy checks. | Lite3 dimensions/capabilities, stacked-floor behavior, route/goal semantics. Graph-local planning is not a locomotion controller. |
| Path output | `pci_general` publishes a path and timed body trajectory. | Actual terrain-aware execution and status feedback. |
| Public UGV demo | `smb_arl` wheeled Gazebo model and pure-pursuit follower. | Four-legged physics, actual policy, terrain interaction, and complete stopping behavior. |
| NMPC / RL / CBF local modules | Real open implementations, but aerial dynamics/actions; vertical acceleration and MAVROS outputs. | Ground models, support/traversability constraints, retraining where necessary, and Lite3 control contract. |
| ANYmal experimental motion | Paper attributes near-term terrain-aware motion to commercial ANYmal perceptive locomotion and onboard velocity tracking. | Equivalent capability must be supplied; no matched ANYmal execution package or locomotion weights found in the audited public closure. |

## Decisive source anchors

- [UAS dependency selection](https://github.com/ntnu-arl/unified_autonomy_stack/blob/cb78bf7f57d074fc0999dd23bb1cfa1b1754d44d/repos/ws_gbplanner.repos): selects `gbplanner3_test`, not the `gbplanner3` default. The fixed planner is `7b10f8f`; current default is `f9904bb`.
- [Actual ground-demo launch](https://github.com/ntnu-arl/robot_bringup/blob/c190215f042da3ffa81ec2a8008e7b93fadc7381/launch/ros2/ugv_sim.launch.xml#L55): `/gbplanner_path` feeds `ugv_gz/path_tracker.py`.
- [Ground projection](https://github.com/ntnu-arl/gbplanner_ros/blob/f9904bb69392d2d46b2cbe939762f967a65daa14/gbplanner/src/rrg.cpp#L580): center/four footprint-offset elevation checks and slope limits, not a rollout of the locomotion policy.
- [UAS-selected path output](https://github.com/ntnu-arl/pci_general/blob/1e5f5c633476737b568dc922c9359e9e872fed0d/src/pci_general.cpp#L670): publishes body path/trajectory, not joint control.
- [NMPC model selection](https://github.com/ntnu-arl/sdf-nmpc/blob/8106cdda989375120cc4859c70af23029ec01257/sdf_nmpc/gen_model.py#L7): aerial models; [hardware command](https://github.com/ntnu-arl/sdf_nmpc_ros/blob/28c1c57ecd66bfa49c44d09622fdd9916f2adb30/scripts/sdfnmpc_node.py#L144) uses acceleration setpoints.
- [Current RL code](https://github.com/ntnu-arl/rl_nav/blob/93ce43eada8ea207b57bca68876214cc83f8e2be/scripts/lidar_nav_acc_ros2_node.py#L449): MAVROS acceleration output. The current README explicitly describes UAV training in Aerial Gym.
- [Pinned experiment explanation](https://github.com/ntnu-arl/unified_autonomy_stack/blob/cb78bf7f57d074fc0999dd23bb1cfa1b1754d44d/docs/indicative_results.md#L149): the ANYmal mine run does not use the additional UAS local safety layers. [Paper](https://arxiv.org/html/2605.12735v1), sections 3.4, 4.1.2, 4.4.2 and 5, gives the same boundary.

## Reliability and adoption judgment

The paper's legged demonstrations cover a mine shaft and a building ground
floor. They do not provide a matched Lite3 comparison, a repeated multi-floor
stair success rate, or proof that the public aerial local modules work for
four-foot support. Generalization across the demonstrated sensing/mission
conditions must not be converted into zero-shot locomotion transfer.

The current local Lite3 navigation already supplies SCAN mapping/geometry,
tracking, cancellation, body commands, and physical completion feedback. UAS
does not remove those requirements. A full replacement therefore adds work
without an established reliability gain. A global-only experiment is materially
smaller and preserves the same local execution chain for a useful comparison.

The local v208 evidence also supersedes a simplistic reading of the previous
v206 stop failure: two captured-state physical pairs passed the candidate's
standing criterion, while `new_full_route_runs` remains zero. See
[physical summary](../experiments/2026-09-26_newton_stair_reproduction/versions/v208/results/physical_summary.json).

Reproducibility limitations found in public packaging include moving default
dependency references, ROS Noetic/Humble bridging, and an unavailable optional
helicopter dependency in the all-workspaces installer. The latter can be
excluded for a scoped ground import and is not a ground-planner build verdict.
No installation/build failure is claimed because no build was attempted.

Status remains **surveyed**, with acquired read-only source references. There
is no UAS integration, model inference, simulation, hardware result, or accepted
baseline change from this review.
