# Quadruped navigation: maturity, generalization, and the PCT–SCAN decision

Date: 2026-10-16. Stage: planning / architecture assessment. Status: **surveyed**.

Follow-up: the [UAS source audit](2026-10-16_uas_quadruped_code_upstream_survey.md)
inspects the newer Unified Autonomy Stack and its actual selected dependency
branches. It finds substantial public mapping/planning code, but no matched
portable replacement for the ANYmal perceptive execution used in its quadruped
experiments. A complete UAS replacement of Lite3's local navigation is therefore
not recommended as a lower-effort route.

This review pauses the HTML explanation and evaluates whether replacing the
navigation foundation would improve the Lite3 project. It does not select a new
baseline or authorize an import, training run, simulation, or robot deployment.
Public README snapshots and GitHub metadata are retained in
`2026-10-16_quadruped_navigation_maturity_sources/`. They are survey evidence,
not imported implementations. No candidate was built or executed in this review.

## Decision

PCT as a global planner and SCAN as a local planner is a defensible architecture.
Both upstream projects address ground/legged navigation in three-dimensional
environments. SCAN is specifically designed for quadrupeds; its EGO-Planner
ancestry does not make it an unmodified aerial planner.

The combination is not a ready-made, generally validated Lite3 navigation
product. A valid global route, a collision-free local body trajectory, and a
trajectory that the installed locomotion policy can execute are different
requirements. They must agree about support surfaces, vertical clearance,
approach direction, speed, sensing, and stopping behavior.

Recommendation: preserve the current stack as a baseline, stop treating further
patching as the default strategy, and compare complete behavior on held-out
scenes before replacing a component. PCT need not be discarded to evaluate a
different local layer. For an engineering control, prioritize CMU's complete
Go2 stack on ordinary ground-navigation cases. For capability-aware local
planning research, prioritize ETH FDM + MPPI. Neither is established here as a
better cross-floor Lite3 solution.

For the strongest directly relevant field-tested **global/local architecture**
reference in this review, prioritize CERBERUS: GBPlanner2 supplies exploration
routes and global repositioning, while ArtPlanner refines motion for ANYmal.
The original integrated system has stronger field evidence than what this
review establishes for a portable, ready-to-run public reproduction package.

## What the current upstreams actually establish

- **PCT:** its [official project page](https://byangw.github.io/projects/tmech2024/)
  describes multi-layer point-cloud tomography, floor/ceiling representation,
  traversability evaluation using robot capability parameters, and real
  quadruped demonstrations. It plans routes; it does not supply our Lite3
  locomotion controller. Its body-height adjustments also require a capable
  downstream controller rather than becoming executable through a path message
  alone. [Repository](https://github.com/byangw/PCT_planner).
- **SCAN:** the [primary paper](https://arxiv.org/html/2606.19555v1) uses a
  yaw-aware twin-cylinder body footprint, projected A* with a prescribed height
  trend, vertical-gradient suppression, a sliding occupancy map, and recovery.
  It reports Go2 + Mid-360 + adapted FAST-LIO2 + Jetson Orin NX experiments,
  including a 149 m three-story inspection route and a 367 m campus route.
  These are authors' demonstrations, not a cross-robot reliability guarantee.
  The inspected paper does not identify PCT as its global planner.
  [Repository](https://github.com/wuyi2121/SCAN-Planner).
- **Local departures:** the historical local `scan_29` materialization expands
  A* in `dz = -1, 0, 1` and preserves the optimizer's vertical gradient. See
  `../experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/builds/scan_29/src/path_searching/src/dyn_a_star.cpp:268`
  and `.../src/bspline_opt/src/bspline_optimizer.cpp:1180`. These are examples of
  substantive local design changes, not just ROS message adaptation. They are
  not presented as an exhaustive diff of the latest composed version.
- **A demonstrated non-planner failure:** the v206 terminal recording and
  deterministic decision replay show zero commanded velocity but no transfer
  into fixed standing. The retained result has 543 replay samples, zero
  mode/reason/progress discrepancies, and a final
  `waiting_for_support_balance` reason. The audit attributes the terminal wait
  to support acquisition in the RL-to-PD handover. It does not exclude effects
  of the preceding approach trajectory. This failure cannot establish that PCT
  or SCAN is intrinsically unsuitable. See the
  [audit](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-15_v206_terminal_settle/REPORT.md)
  and [replay result](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-15_v206_terminal_settle/results/v206.json).

## Candidates and their actual boundaries

| Candidate | What is available / demonstrated | Lite3 implication |
|---|---|---|
| [CERBERUS: GBPlanner2 + ArtPlanner](https://arxiv.org/html/2207.04914) | The system paper documents graph-based exploration/global routing, a separate ANYmal navigation planner, elevation mapping, perceptive locomotion, and behavior-tree recovery. Its open-source appendix links both planners. [GBPlanner2 code](https://github.com/ntnu-arl/gbplanner_ros/tree/gbplanner2). | Strongest reference here for a field-tested integrated global/local design. GBPlanner2 itself also has local/global exploration stages; its local exploration stage must not be confused with ArtPlanner's local robot-motion planning. Public modules still require integration and robot-specific adaptation. |
| [CMU autonomy_stack_go2](https://github.com/jizhang-cmu/autonomy_stack_go2) | Complete ROS 2 Go2 stack: Point-LIO SLAM, FAR global routing, terrain analysis, obstacle avoidance, and waypoint following. Simulation and real-robot startup procedures are documented. | Best first engineering control in this review. Requires Lite3 sensor/state/command adaptation. Its stock L1-lidar configuration explicitly warns that low obstacles cannot be distinguished and asks for obstacles above 0.3 m; this is a configuration/sensor limitation, not a universal FAR threshold. A mature multi-floor stair capability was not established by this review. |
| [ETH ArtPlanner](https://github.com/leggedrobotics/art_planner) | Terrain-aware local planning with reachability and learned motion cost. The [paper](https://arxiv.org/abs/2303.01420) reports four ANYmals operating for 90 minutes in the DARPA SubT Finals without planning or locomotion failure. | Strong field evidence in its original system. Public release uses ROS Noetic and 2.5D elevation maps. ANYmal simulation is restricted, the bundled follower is unsupported, and the training environment for robot-specific motion costs is unavailable. A geometric variant is provided. Not a complete portable global/local/locomotion stack. |
| [ETH FDM + MPPI](https://github.com/leggedrobotics/fdm) | Predicts future motion and failure risk from terrain, proprioceptive history, and candidate velocity commands, then chooses commands with MPPI. Public training/data-generation code, model download links, Isaac Lab instructions, and ROS Noetic integration are documented. [Paper](https://arxiv.org/html/2504.19322v1). | Best conceptual match to learning the capabilities of Lite3 plus its actual locomotion policy. The paper trains individual dynamics models for different platforms/controllers. The paper's perceptive locomotion policy is not public; the repository defaults to a less stable Isaac Lab ANYmal policy and recommends retraining for comparable results. Model downloads were not tested here. |
| [ETH SRU navigation](https://github.com/leggedrobotics/sru-navigation-sim) and [deployment](https://github.com/leggedrobotics/sru-robot-deployment) | Learned navigation with spatial recurrent memory; Isaac Lab simulation, separate learning implementation, and ROS 2 robot deployment are published. The [v2 paper](https://arxiv.org/html/2506.05997v2) reports B2W real-world indoor/outdoor/forest navigation with a ZEDX and a RIVR locomotion policy, including trajectories over 100 m. | Strong evidence for transfer to unseen environments on the tested wheeled-legged platform. It does not demonstrate zero-shot transfer to ordinary Lite3. Inputs, policy dynamics, camera conditions, and training need adaptation. The paper itself limits its long-range claim to local mapless navigation; kilometer/hour-scale global navigation would need additional mechanisms. |
| [ETH ViPlanner](https://github.com/leggedrobotics/viplanner) | Semantic/depth local planner, public checkpoints and ROS Noetic deployment instructions for ANYmal. | Relevant when terrain semantics matters. It is not a complete global navigation and locomotion replacement. Checkpoint availability is not Lite3 transfer evidence. |
| [Spot GraphNav / Autowalk](https://dev.bostondynamics.com/docs/concepts/autonomy/graphnav_tech_summary.html) | Vendor-integrated mapping, localization, graph navigation, and recorded mission traversal used by industrial customers. Stair-related movement parameters can be stored on graph edges. | Mature complete behavior exists, but the API controls Spot's onboard service; the SDK is not the complete navigation implementation that can be ported to Lite3. Recorded-map autonomy is also different from unrestricted navigation in unseen environments. |

The [2024 ETH wheeled-legged navigation and locomotion system](https://arxiv.org/abs/2405.01792)
also reports kilometer-scale city missions in Zurich and Seville. This is useful
evidence that strong integrated systems exist. It does not establish that the
later SRU repository reproduces that exact complete system, or that either
transfers unchanged to Lite3.

The CERBERUS lessons-learned section is especially relevant: a gap rejected by
the local planner was repeatedly proposed by the global planner because the
feedback connection was insufficient. A staircase was also declined under
conservative local-planner tuning. Thus, field maturity does not eliminate
global/local disagreement; the documented remedies and integration are part of
what should be assessed. The current GBPlanner default is `gbplanner3`
(OmniPlanner). This review pins the historical `gbplanner2` branch for the
CERBERUS comparison and does not transfer its field evidence automatically to
the new release.

Two recent cross-floor directions merit tracking, but not immediate adoption:

- [TravExplorer](https://arxiv.org/html/2605.19958v1) is closely related to SCAN.
  Its pinned repository tree contains documentation, images, and a license,
  but no algorithm implementation; the README says release is planned upon
  acceptance.
- [RAEM](https://arxiv.org/html/2608.25366v1) reports multi-floor Go2 exploration
  using tomography, height-aware global routing, and staircase-center alignment.
  The paper says complete code will be released upon acceptance. The inspected
  `Shua1ge/quadruped_exploration_planner` repository contains scaffolding and an
  ATSP utility rather than a complete reproduction package. Its status as the
  authors' canonical release was not established. Do not label it an official
  complete RAEM implementation.

## Generalization and the comparison that would change the decision

Keep three questions separate: new scenes with the same robot, new terrain
types, and a different robot or locomotion policy. A method can succeed at the
first and still require substantial work for the other two. Neither neural
weights nor hand-designed geometry are intrinsically more generalizable.

A useful comparison would freeze Lite3's locomotion policy, sensing, initial
states, goals, and completion criteria, and test:

1. Flat corridors, clutter, and narrow turns.
2. Previously unused stair geometries, ascent/descent, and landing turns.
3. Multi-floor routes with changed obstacles and partial observations.

Measure complete-route success, collisions/falls, stalls/recovery, and successful
final standing. Classify each failure by perception/map, route, local planning,
tracking, or locomotion. Compare native upstream sensing first where required;
claim a matched Lite3 comparison only after adapting and freezing the interfaces.
This is a proposed evaluation, not one performed by this review.

If the research objective remains VLA, the navigation stack should have a finite
acceptance scope so that maintenance does not silently become the entire PhD
topic. Capability-aware navigation is a legitimate separate research direction,
but that scope change should be deliberate.

## Fixed repository references

These are default-branch HEADs inspected on 2026-10-16, except for the explicitly
selected historical `gbplanner2` branch. They are not the versions imported
by earlier local experiments. Last-commit age is a maintenance signal, not a
quality ranking. `Unknown` below means GitHub did not identify a standard
top-level license; it does not establish absence of package-level licenses.

| Repository | Branch | Commit | Last commit | License signal |
|---|---|---|---|---|
| wuyi2121/SCAN-Planner | main | `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` | 2026-07-29 | Apache-2.0 |
| byangw/PCT_planner | main | `35cd73fd82bcd51bc538429294af7646b2a09815` | 2025-02-17 | GPL-2.0 |
| jizhang-cmu/autonomy_stack_go2 | foxy-humble | `43d5f54b389b251713f0097893c30fa76c870d54` | 2026-02-18 | Unknown; inspect packages before reuse |
| leggedrobotics/art_planner | main | `2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f` | 2023-08-09 | BSD-3-Clause |
| ntnu-arl/gbplanner_ros | gbplanner2 (current default: gbplanner3) | `7301b5350915cf3a4055072ad559842db37b4ca9` | 2024-06-13 | BSD-3-Clause |
| leggedrobotics/fdm | main | `06f5d8033bafed4f6838662af99ba31cbd4f5ce0` | 2025-08-11 | API: NOASSERTION; inspect license before reuse |
| leggedrobotics/sru-navigation-sim | main | `80f6c01c2d9f171374c9f9dba289abd38bcf0c6c` | 2026-03-17 | MIT |
| leggedrobotics/sru-robot-deployment | main | `568a96c6c704d9dede4d7293fa09b98d9cbff4e0` | 2026-01-20 | MIT |
| leggedrobotics/viplanner | main | `6fcf3c60f6fa3b28b3a11af054d6033825923789` | 2025-02-12 | API: NOASSERTION; inspect license before reuse |
| wuyi2121/TravExplorer | main | `eab0765a22ba6cfef93c48b0e0edeaa1833887b5` | 2026-07-01 | Apache-2.0; implementation not released |
| Shua1ge/quadruped_exploration_planner | main | `adc2504687de7eb1b7e5111b61b62f12fb30874b` | 2026-09-07 | BSD-3-Clause; incomplete package |

The evidence manifest also includes DeepRoboticsLab/Lite3_Navigation and
dimensionalOS/dimos as preliminary repository checks. Neither was promoted to
the shortlist: the first inspected README is too sparse to establish a mature
rough-terrain stack, and the second's broad framework scope does not by itself
establish cross-floor quadruped reliability. No negative runtime conclusion is
claimed for either repository.
