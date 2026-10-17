---
origin: ai+web
reviewed: false
date: 2026-09-18
status: surveyed
stage: planning
family: B (learned local planners and learned navigation policies with stair capability)
---

# Survey B: learned local planners and navigation policies that handle stairs

**Question (Dr Sun, 2026-09-18).** Apart from SCAN, which open-source local planners handle stairs, so that we
reuse rather than invent? This note covers the learned family: learned local planners, learned-cost planners, and
hierarchical RL navigation policies.

**Our chain, for the fit column.** PCT global route (known tomogram; SLAM relocalization on the robot, truth pose in
simulation) -> local planner (SCAN today: live LiDAR occupancy, B-spline, tracking controller, `cmd_vel`) -> V12,
a **blind** proprioceptive RL policy. Simulation: Isaac Lab 2.3.x / Isaac Sim 5.x, 16-channel LiDAR, optional
cameras. Real Lite3: Livox MID-360, head camera, RealSense D435i. Inference GPU: RTX 5070 Ti (16 GB). SCAN runs on
ROS 2 Foxy.

**Status: `surveyed` only.** Nothing was cloned into the project, imported, installed, built or run. No weights or
datasets were downloaded. Source was read through `gh api` at the commits listed below, into the session scratchpad.
Papers were read as arXiv HTML. Anything not read directly is marked **UNVERIFIED**. Licenses come from the LICENSE
file text unless noted; GitHub's detector returns `NOASSERTION` for several ETH repositories.

**Prior surveys this extends (not redone).** `2026-09-17_scan_stairs_upstream_survey.md` (SCAN/PCT forks),
`2026-09-14_body_clearance_margin_sources/C_learned_legged_notes.md` (ViPlanner, iPlanner, NavDP, X-NavDP,
legged-loco read for body clearance), `2026-09-17_collision_handling_sources/A_legged_sim_notes.md` (contact
classification; legged-loco stairs commented out; VLN-PE removes stair episodes).

---

## 0. Summary table

| Method | Repo @ commit | License | Inputs -> outputs | Stair evidence | Weights public? | Needs perceptive locomotion? | Fit to our chain |
|---|---|---|---|---|---|---|---|
| **SanD-Planner** (RSS 2026) | WangJinCheng1998/sandplanner @ `415589e` | Apache-2.0 | 4 depth frames + 3-D relative goal + previous heading -> 8 (or 12) B-spline control points, ESDF critic picks 1 of K | Real Go2 with D435: stair-climbing "trials" shown, **no numbers**. Sim benchmark (NavDP, wheeled, flat): 90.1% / 72.0% SR. Trained with **PCT as the expert** | Yes: 3 checkpoints on GitHub release v1.0; dataset only partly released | Not stated; Go2 driven through an MPC tracker (locomotion mode UNVERIFIED) | Same output form as SCAN (B-spline), 3-D goal fits a PCT carrot, D435 matches our D435i. **But the released default pipeline is planar** (see §1) |
| **ViPlanner** (ICRA 2024) | leggedrobotics/viplanner @ `6fcf3c6` | BSD-3-Clause file; README says "All right reserved" (conflict) | Depth + RGB (Mask2Former semantics) + goal point -> 51-point 3-D path, fear score | Real ANYmal: one qualitative stair experiment (Fig. 5), **no stair numbers**. Sim goal-reached 71.6% (Matterport), not stair-specific | Yes: Google Drive (not fetched) | Evidence uses perceptive policies (Isaac demo: ANYmal-C HeightScan) | Path + goal point interface fits a PCT carrot. Camera-specific model (author: very sensitive to camera placement); Isaac Lab 1.2, ROS Noetic |
| **iPlanner** (RSS 2023) | leggedrobotics/iPlanner @ `4a8d823` | MIT | Depth + goal -> path, fear score | Own paper: real ANYmal "ascend and descend stairs" (qualitative). ViPlanner paper: iPlanner **halts** at stairs (fear > threshold) | Yes: Google Drive; README: not adapted to real data | Not stated | Geometric only; conflicting stair evidence. Screened |
| **Perceptive FDM + MPPI** (RSS 2025) | leggedrobotics/fdm @ `06f5d80` | BSD-3-Clause (SPDX in LICENCE) | Height scan + proprioceptive history + candidate velocity sequences -> predicted SE2 states + failure probability; MPPI -> velocity command | Sim ANYmal, 3-D env with stairs and ramps: **73.75% SR vs 33.13%** (height-scan heuristic) and 48.75% (Kim et al.). Real ANYmal deployment (stairs not quantified) | Yes (Google Drive), but trained with the non-public Miki et al. perceptive policy | Paper: yes (Miki policy). **Design is platform-aware**: it learns whatever policy it is trained with | Best conceptual fit for a blind V12: retrain the FDM on Lite3 + V12 in Isaac Lab so it learns where V12 can and cannot climb. Replaces SCAN + tracking controller. Needs a height map (MID-360). ROS Noetic; Isaac Lab 2.1.1-2.2 with a "sinking" warning |
| **SRU navigation stack** (IJRR 2025) | leggedrobotics/sru-navigation-sim @ `80f6c01`; sru-navigation-learning @ `df600e8`; sru-robot-deployment @ `568a96c` | MIT (sim, deployment); BSD-3-Clause (learning, rsl_rl-derived) | Stereo/forward depth (VAE features) + proprioception + goal -> (vx, vy, wz) at 5 Hz to a frozen low-level policy | Sim stairs environment: **82.8% SR** (LSTM 33.1%). Real B2W (wheel-legged): stairs mentioned qualitatively | Yes: B2W `nav_policy.onnx` + VAE encoder; locomotion policies in sim repo | **No in the public sim default: AoW-D *blind* low-level policy** | Closest published pattern to "learned navigation over a blind walker". Retrain for Lite3 + V12 needed. Isaac Lab 2.1.1; ROS 2 Jazzy deployment. Replaces SCAN + controller |
| **ArtPlanner** (Field Robotics 2023) | leggedrobotics/art_planner @ `2f3fde6` | BSD-3-Clause | 2.5-D height map + goal -> PRM path with learned motion cost (time, risk) | Real ANYmal, DARPA SubT: the deployed cost weights rated stairs risky and the planner **avoided** the subway stairs | Yes: motion-cost `.pt` for **blind and perceptive** ANYmal in repo | Ships blind weights; retraining environment not provided | Learned-cost sampling planner, not a learned policy. ROS Noetic, 2023, stale. Would replace SCAN |
| NavDP / LoGoPlanner / X-NavDP | InternRobotics/NavDP @ `bff5eb8` | CC BY-NC-SA 4.0 (README); X-NavDP subdir MIT | RGB-D + goal -> planar waypoints | **None**: zero stair mentions in NavDP, X-NavDP, LoGoPlanner papers; benchmark is wheeled Dingo | NavDP gated form; LoGoPlanner, X-NavDP on HF | n/a | Screened (planar, no stairs, non-commercial) |
| legged-loco (NaVILA low level) | yang-zj1026/legged-loco @ `87b0d3d` | MIT | LiDAR height map + velocity command -> joint actions | NaVILA paper: real Go2 stairs qualitative. Public Go2 vision config has stairs commented out | No (issue #18) | It *is* the perceptive policy | Replaces V12, not SCAN. Screened |
| REASAN | ASIG-X/REASAN @ `655bf4f` | GPL-3.0 (README) | LiDAR -> RL nav + shield + locomotion | None (zero stair mentions) | ONNX models in repo | Own LiDAR locomotion | Screened |
| VAMOS | vamos-vla/vamos @ `bfe078b` | **No license** | RGB + language -> image-space paths re-ranked by an affordance model | Spot stairs claimed (abstract) | Planner only; affordance model not found | Spot stock controller | Screened (no license) |

---

## 1. SanD-Planner (arXiv 2602.00923; RSS 2026)

- **Repository:** https://github.com/WangJinCheng1998/sandplanner, branch `main`, pinned
  `415589ef81970d0ec055c6eaeef5edcdf1cf6c46` (2026-07-21). Created 2026-06-05, 23 stars, no issues.
  Project page repo: WangJinCheng1998/SanD-planner `86e604f` (includes `real-world-stair-01.mp4`, not viewed).
- **License:** Apache-2.0 (LICENSE file; README §License). The NavDP benchmark assets it evaluates on are
  CC BY-NC-SA 4.0 and are not bundled.
- **Authors:** Jincheng Wang, …, Jianhao Jiao (corresponding), Dimitrios Kanoulas; UCL. Jiao is a PCT co-author.
- **Method (paper §III-IV):** mapless local planning; inputs are four depth frames, a 3-D relative goal
  `[x, y, z]` and the previous plan's heading; a DDPM predicts N×3 B-spline control points; an ESDF critic built
  from the current depth frame ranks K candidates.
- **Training data (paper §V):** 500 episodes in 2 Matterport3D scenes and 8 Gazebo worlds, "explicitly"
  including stairs and low-clearance obstacles, with **PCT-planner as the expert**. About 5 h on one RTX 4080.
- **Stair evidence:** real Unitree Go2 with a D435, planner on a tethered laptop (RTX 4090) at about 10 Hz,
  tracked by NavDP's MPC. The paper says it demonstrates 3-D navigation "through stair-climbing trials". **No
  success count, step height or descent result is given.** The quantitative results (Table I: ClutteredEnv 90.1% SR,
  InternScenes 72.0% SR) are from the NavDP benchmark, which uses a wheeled robot on flat floors.
- **What the released code does (read, not run):**
  - The ESDF critic is configured as a "2D planar query variant (suited for ground robots)": every trajectory
    point's z is overwritten by `clearance_height = 0.36` before the ESDF lookup.
    [config.py L69-L80](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/sand_planner/config.py#L69-L80),
    [trajectory_evaluator.py L116-L120](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/sand_planner/core/trajectory_evaluator.py#L116-L120),
    [L232-L236](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/sand_planner/core/trajectory_evaluator.py#L232-L236)
  - The default normaliser is `trajectory_stats_mg2_mg50_2d.json` with percentile scaling and `clamp=True`. Its z
    axis spans p1..p99 ≈ −0.00044..0.00047 m, so denormalised control-point z is clamped to about ±0.5 mm.
    [model_manager.py L120-L126](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/sand_planner/core/model_manager.py#L120-L126),
    [normalize.py L105-L118](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/sand_planner/utils/normalize.py#L105-L118),
    [stats z L42-L54](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/data/outputs/trajectory_stats_mg2_mg50_2d.json#L42-L54)
  - **Inference from reading, not run:** the released default pipeline produces planar trajectories. Whether the
    released checkpoints ever saw stair data is **UNVERIFIED**; the released dataset is only the Gazebo
    `dataset_avoid` subset (README L245-L249).
  - Goal clipping: x in [−3, 10], y in [−10, 10] m; z passes through.
    [sand_planner_agent.py L309-L324](https://github.com/WangJinCheng1998/sandplanner/blob/415589ef81970d0ec055c6eaeef5edcdf1cf6c46/sand_planner/agent/sand_planner_agent.py#L309-L324)
  - Interface: Python API or a Flask HTTP server (`/pointgoal_step`); no ROS package. Evaluation needs Isaac Sim
    4.2 + Isaac Lab 1.2 through the NavDP benchmark (README L62-L119).
- **Weights:** GitHub release `v1.0` lists `NoMax.pth` (169 MB), `NoMax_12.pth` and `Max_2.1m.pth` (187 MB each)
  (release metadata read through the API; not downloaded).
- **Fit (lead proposal):** closest in form to SCAN (B-spline, 3-D goal, trained on PCT routes) and to our D435i.
  To use it on stairs we would have to retrain with stair data and a 3-D (non-planar) critic, both of which the
  paper describes but the release does not ship. Depth-only, so it sees only the forward field of view.

## 2. ViPlanner (arXiv 2310.00982; ICRA 2024)

- **Pin:** leggedrobotics/viplanner `main` `6fcf3c60f6fa3b28b3a11af054d6033825923789` (2025-02-12). Other branches:
  `feature/beat_the_planner`, `fix/warehouse`, `outdated/main` (not read).
- **License:** LICENSE is BSD-3-Clause ("Copyright (c) 2023 Pascal Roth, RSL ETH"); source headers carry SPDX
  BSD-3-Clause; README §License still says "All right reserved". Unresolved conflict (already flagged 2026-09-14).
- **Inputs -> outputs:** depth + semantic image (Mask2Former) + goal `PointStamped` on `/mp_waypoint` (world frame;
  cropped when farther than `max_goal_distance`) -> `nav_msgs/Path` of 3-D waypoints and a fear score; a CMU
  `pathFollower` turns the path into a twist.
  [viplanner_node.py L139](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/ros/planner/src/viplanner_node.py#L139),
  [L165](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/ros/planner/src/viplanner_node.py#L165),
  [L285-L297](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/ros/planner/src/viplanner_node.py#L285-L297)
- **How stairs enter:**
  - `stairs` is a ground class with loss `TRAVERSABLE_INTENDED_LOSS = 0`.
    [viplanner_sem_meta.py L8, L36-L40](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/config/viplanner_sem_meta.py#L36-L40)
  - A height loss keeps the path at robot base height above the height map (paper Eq. 5), so paths can climb.
  - Lead, not verified at runtime: the public Isaac Lab data collector samples start/goal graphs with a Matterport
    mapping that sets `stairs: OBSTACLE_COST`.
    [matterport_class_cost.py L32](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/omniverse/extension/omni.viplanner/omni/viplanner/config/matterport_class_cost.py#L32),
    [terrain_analysis_cfg.py L74-L78](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/omniverse/extension/omni.viplanner/omni/viplanner/collectors/terrain_analysis_cfg.py#L74-L78)
- **Stair evidence:** real ANYmal, one experiment shown in Fig. 5, where ViPlanner navigates stairs and iPlanner's
  fear estimate stops the robot. **No stair success rate.** Simulation Table II reports goal-reached 71.60%
  (Matterport), 87.75% (CARLA), 85.58% (warehouse), not broken out by stairs. Planner at 10 Hz and semantics at
  about 3 Hz on a Jetson Orin AGX.
- **Locomotion:** Isaac demo uses the ANYmal-C `HeightScan` policy (perceptive).
  [base_cfg.py L39](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/omniverse/extension/omni.viplanner/omni/viplanner/config/base_cfg.py#L39).
  The real-robot locomotion controller is not named in the paper (UNVERIFIED).
- **Weights:** checkpoint and config on Google Drive (README L107-L108); not fetched.
- **Versions:** Isaac Sim 4.2 + Isaac Lab 1.2 (omniverse README L32); open issues #104/#106 on newer Isaac Lab.
  ROS Noetic only.
- **Camera sensitivity:** in issue #79 the author says the model is very sensitive to camera intrinsics and
  placement. A Lite3 camera mount would likely need retraining (inference, not tested).
- **Fit (lead proposal):** the most direct "stairs are traversable" learned local planner with a goal-point
  interface that a PCT carrot can drive. Costs: Noetic-only, old Isaac Lab, semantic segmentation on the GPU,
  camera-specific retraining, a license conflict, and no quantitative stair evidence.

## 3. iPlanner (arXiv 2302.11434; RSS 2023)

- **Pin:** leggedrobotics/iPlanner `master` `4a8d823ff9d09c3f626b727e7e00484b38f80d49`. MIT. ROS Noetic (README L18).
- **Evidence conflict:** its own paper shows ANYmal ascending and descending stairs between human-set waypoints
  (Fig. 10, qualitative). The later ViPlanner paper (same lab) shows iPlanner's fear estimate stopping it at stairs.
  The README warns the released network "has not been adapted to real-world data" (L53).
- **Verdict:** geometric depth-only; screened as a stair solution.

## 4. Perceptive Forward Dynamics Model + MPPI (arXiv 2504.19322; RSS 2025)

- **Pin:** leggedrobotics/fdm `main` `06f5d8033bafed4f6838662af99ba31cbd4f5ce0` (2025-08-11). 351 stars.
- **License:** LICENCE carries SPDX BSD-3-Clause; README badge BSD-3. GitHub reports `NOASSERTION`.
- **Method:** a recurrent model predicts 10 future SE2 states (0.5 s steps, 5 s horizon) and failure probability
  from a height scan, past states and proprioception, given a candidate velocity sequence. MPPI samples 2048
  sequences and optimises a goal reward plus a failure reward, with no hand-tuned traversability cost.
- **Stair evidence (paper Table III, simulation, ANYmal):** in the 3-D environment (stairs, ramps) MPPI with the
  FDM reaches **73.75%** success, against 48.75% (Kim et al. FDM) and 33.13% (height-scan traversability
  heuristic). 2-D: 88.33 / 78.33 / 82.50%. Onboard: Jetson Orin AGX, planner at 7 Hz, 40.6 ms per model call.
  The paper names spiral staircases as a likely failure, limited by the locomotion policy.
- **Locomotion dependence:** paper results use the non-public Miki et al. perceptive policy. The repository default
  is a standard Isaac Lab ANYmal policy "with reduced stability".
  [README L66-L69](https://github.com/leggedrobotics/fdm/blob/06f5d8033bafed4f6838662af99ba31cbd4f5ce0/README.md#L66-L69),
  [L156-L164](https://github.com/leggedrobotics/fdm/blob/06f5d8033bafed4f6838662af99ba31cbd4f5ce0/README.md#L156-L164),
  [env_cfg_base.py L170](https://github.com/leggedrobotics/fdm/blob/06f5d8033bafed4f6838662af99ba31cbd4f5ce0/exts/fdm/fdm/env_cfg/env_cfg_base.py#L170).
  The low-level policy is loaded from a file through `PerceptiveNavigationSE2ActionCfg`
  ([robot_cfg.py L89-L103](https://github.com/leggedrobotics/fdm/blob/06f5d8033bafed4f6838662af99ba31cbd4f5ce0/exts/fdm/fdm/env_cfg/robot_cfg.py#L89-L103)),
  so a TorchScript V12 could in principle be substituted (UNVERIFIED; observation layout would have to match).
- **Versions and risks:** Isaac Sim 4.5 / Isaac Lab 2.1.1-2.2.0 (README L21-L22, L66); README warns of the robot
  "sinking into the ground" on the latest Isaac Lab (L63). Also requires an Isaac Lab PR (#2183). Real deployment
  ROS Noetic, code under `ros/` (the README's separate `forward_dynamics_model` repo returns 404).
- **Weights:** simulation and real fine-tuned models on Google Drive, trained with the Miki policy (not fetched;
  not transferable to Lite3).
- **Fit (lead proposal):** the only candidate whose learned quantity is "what *this* locomotion policy can
  traverse". Retrained on Lite3 + V12, it would encode V12's blind stair ability instead of assuming perception in
  the walker. It consumes a height scan, which matches a MID-360 elevation map, and takes a goal pose that a PCT
  carrot can supply. It replaces SCAN and the tracking controller. Retraining cost is unmeasured.

## 5. SRU long-range mapless navigation (arXiv 2506.05997; IJRR 2025)

- **Repositories (ETH RSL, released 2026-01):**
  - `sru-pytorch-spatial-learning` `d537910` (MIT): recurrent unit only; README says the navigation system is not
    included (L18-L23).
  - `sru-navigation-sim` `80f6c01c2d9f171374c9f9dba289abd38bcf0c6c` (MIT): Isaac Lab 2.1.1 / Isaac Sim 4.5 task
    extension; high-level policy outputs SE2 velocity at 5 Hz, low-level policy at 50 Hz (docs/README L10, L19-L20).
  - `sru-navigation-learning` `df600e8fd0d60447da4cab9aa5f961da0111d9a9` (BSD-3-Clause, rsl_rl-derived): SRU actor-critic,
    PPO/MDPO.
  - `sru-robot-deployment` `568a96c6c704d9dede4d7293fa09b98d9cbff4e0` (MIT): ROS 2 Jazzy, ONNX `nav_policy.onnx` +
    VAE encoder for the B2W; goals on `/goal_pose`, `Twist` out, waypoint recording.
    [rl_nav_controller.py L321-L357](https://github.com/leggedrobotics/sru-robot-deployment/blob/568a96c6c704d9dede4d7293fa09b98d9cbff4e0/rl_nav_controller/rl_nav_controller/rl_nav_controller.py#L321-L357)
  - `sru-depth-pretraining` `2d153dc` (MIT): depth VAE pretraining.
- **The public sim default drives a blind walker:** the navigation action loads AoW-D `policy_blind_3_1.pt`.
  [navigation_env_cfg.py L150-L166](https://github.com/leggedrobotics/sru-navigation-sim/blob/80f6c01c2d9f171374c9f9dba289abd38bcf0c6c/isaaclab_nav_task/navigation/navigation_env_cfg.py#L150-L166).
  Stairs are 5 steps of 0.20 m in 3×3 platform structures, 30% of terrains.
  [terrain_constants.py L187-L200](https://github.com/leggedrobotics/sru-navigation-sim/blob/80f6c01c2d9f171374c9f9dba289abd38bcf0c6c/isaaclab_nav_task/terrains/terrain_constants.py#L187-L200)
  AoW-D is ANYmal on wheels, so a wheeled-legged robot; how its blind policy climbs 0.20 m steps is UNVERIFIED.
- **Stair evidence (paper Table 1, simulation):** stairs environment SR **82.8%** for SRU vs 33.1% LSTM and 35.7%
  GRU. Which robot model and locomotion policy produced Table 1 is not stated beyond "differs from" the wheeled
  ANYmal used in Table 2 (UNVERIFIED). Real: Unitree B2W with an RIVR locomotion policy and a ZED X; the text lists
  stairs among handled obstacles, qualitatively.
- **Fit (lead proposal):** the clearest open example of an RL navigation policy trained over a frozen blind
  low-level policy with stairs in the curriculum, in Isaac Lab. For Lite3 it means training a new navigation policy
  over V12 (policy file swap plus a new robot asset), with forward depth only. It outputs velocity, so it replaces
  SCAN and the controller. Following PCT would mean feeding successive carrots to `/goal_pose` (deployment is Jazzy,
  not Foxy).

## 6. ArtPlanner (arXiv 2303.01420; Field Robotics 2023)

- **Pin:** leggedrobotics/art_planner `main` `2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f` (2023-08-09). BSD-3-Clause.
- **Method:** PRM on a 2.5-D height map with reachability checks, learned foothold scores and a learned motion
  cost (time, risk). The motion-cost weights are "trained for blind and perceptive policies" of ANYmal; the
  retraining environment is not provided (README L108-L112). Uses `elevation_mapping_cupy` (L118). ROS Noetic (L72).
- **Stair evidence:** in the DARPA SubT Finals the team used older cost weights that rated stairs as high risk, so
  the planner did not follow the path at the subway stairs; the paper says newer weights "perform well on stairs"
  but gives no numbers.
- **Fit:** a learned-cost classical planner that would replace SCAN. Blind-policy weights exist, but for ANYmal.
  Stale since 2023.

## 7. Infrastructure worth knowing

- **leggedrobotics/nav-suite** `648ba3b28dac61aec48e150a507c2a8507646ea2` (Apache-2.0): Isaac Lab 2.1.1 navigation
  suite used by FDM and ViPlanner work. It has stair/ramp terrains, goal commands (including consecutive goals),
  and an example depth-image PPO navigation task over the ANYmal-C HeightScan policy on `ROUGH_TERRAINS_CFG`
  ([env_cfg_base.py L57-L61, L133](https://github.com/leggedrobotics/nav-suite/blob/648ba3b28dac61aec48e150a507c2a8507646ea2/exts/nav_tasks/nav_tasks/configs/env_cfg_base.py#L133)).
  The README asks for a PR from a private `IsaacLab-Internal` repository (L100-L101), a reproducibility risk.

## 8. Screened out

- **NavDP, LoGoPlanner, X-NavDP** (NavDP `bff5eb8`): no occurrence of "stair" in any of the three papers; the
  benchmark is a wheeled Dingo; trajectories are planar. NavDP is CC BY-NC-SA 4.0 with gated weights.
- **InternNav / InternVLA-N1:** VLN-PE removes stair episodes (prior survey A).
- **legged-loco / NaVILA low level** (`87b0d3d`): a perceptive locomotion policy, not a planner; stair sub-terrains
  are commented out in the Go2 vision config
  ([go2_low_vision_cfg.py L67-L92](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/config/go2/go2_low_vision_cfg.py#L67-L92));
  no checkpoints. NaVILA's real Go2 stair clips are qualitative.
- **REASAN** (`655bf4f`, GPL-3.0): LiDAR RL navigation on Go2; no stairs in the paper.
- **VAMOS** (`bfe078b`): no license; relies on Spot's controller; affordance model not found in the repo.
- **Rudin et al. 2022, "Advanced Skills…"** (arXiv 2209.12827): end-to-end locomotion + local navigation with
  obstacles and stairs; **no official code found** (UNVERIFIED absence).
- **MulDP** (arXiv 2609.03984, IROS 2026), **firefighting stair RL** (arXiv 2602.03087), **Predictive Training with
  Latent Imagination** (arXiv 2607.17574), **AgniNav** (2606.10903), **CeRLP** (2603.19602): no code link found in the
  abstract pages; MulDP and 2602.03087 are end-to-end walkers or velocity generators; the others make no stair claim.
- **GaussGym** (arXiv 2510.15352): trains RGB locomotion that climbs 17 cm stairs; a locomotion replacement.
- **StairMaster** (arXiv 2606.25765): perceptive stair locomotion; a locomotion replacement.

## 9. Cross-family lead (for the classical-planner surveyor)

- **TravExplorer** (arXiv 2605.19958; wuyi2121/TravExplorer `eab0765`, Apache-2.0): from the SCAN authors' account
  (SJTU). Cross-floor planning with foothold-guided 3-D search and a "vertically constrained" local trajectory,
  which is the stair extension SCAN lacks. The README says code will be released upon acceptance; the repo has
  only a README and images today. Not learned, so outside this family, but directly relevant to SCAN.

## 10. What a blind V12 changes

- Most stair evidence here rests on perceptive locomotion: ViPlanner (ANYmal HeightScan in simulation), FDM (Miki
  et al.), NaVILA (LiDAR height map). A planner that routes onto stairs does not make a blind walker climb them.
- Three designs do not assume a perceptive walker:
  - the FDM, if retrained on V12;
  - the SRU stack, whose public sim default uses a blind low-level policy;
  - ArtPlanner, which ships blind-policy cost weights, but only for ANYmal.
- Depth-only planners (SanD, ViPlanner, iPlanner, SRU) see only the forward field of view. On a stair descent the
  camera pitch and height matter, and none reports descent numbers.

## 11. UNVERIFIED / open

- SanD: whether the released checkpoints were trained with stair data; its Go2 locomotion mode; any stair
  success count.
- ViPlanner: the real-robot locomotion controller; whether the data collector's stair filtering affects the released
  model; the license conflict.
- FDM: behaviour on Isaac Lab 2.3.x ("sinking" warning); training compute; whether V12 can be loaded through
  `PerceptiveNavigationSE2ActionCfg` unchanged.
- SRU: the robot and locomotion behind the 82.8% stair SR; how a blind wheeled-legged policy climbs 0.20 m steps;
  whether the Jazzy deployment runs on Foxy.
- ArtPlanner: which in-repo weight file is the "newer" stair-capable one.
- All: Google Drive and GitHub release weights were not downloaded or checked for integrity or content.
- Absence claims (no code for Rudin 2022, MulDP, 2602.03087) come from abstract pages and GitHub search only.

## Claim boundary

`surveyed` only. No candidate was built, run, imported or integrated. Every stair result above is the authors' own,
mostly qualitative, and on robots other than Lite3. Commit pins are branch heads read on 2026-09-18.
