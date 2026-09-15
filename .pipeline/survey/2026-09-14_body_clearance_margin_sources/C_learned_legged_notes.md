# Survey C: Learned, Legged-Specific, and VLA-Deployment Collision Safety

Date: 2026-09-14. Stage: planning (survey). Label: `surveyed` only. Nothing was
imported, reproduced, integrated, or validated. No code was run, built, or
installed. No weights were downloaded.

Question: where does robot body size or footprint enter each candidate's
clearance mechanism, and can that mechanism wrap our InternVLA-N1 (DualVLN)
System 1 trajectory or the MPC's (v, w) output without retraining?

Method: repository metadata and HEAD SHAs came from `gh api`. Source was read
through raw.githubusercontent.com at the pinned SHA. InternNav was read from the
local snapshot at `7a5c62400ac45b313d9b709c740b64191556a242` (clean worktree).
Papers were read as arXiv HTML text. The GitHub license detector returns
`NOASSERTION` for iPlanner and ViPlanner, but their LICENSE files contain
standard MIT and BSD-3-Clause text. The SPDX labels below come from the file
text.

---

## 0. Context finding: our own baseline has no runtime clearance term

These findings come from the InternNav snapshot, MIT license (LICENSE:
"Copyright (c) 2025 Intern Robotics").

- **The upstream MPC has no obstacle or footprint term.** Its only constraints
  are the dynamics and bounds on v and w. The cost is Q = diag(10, 10, 0) and
  R = diag(0.05, 0.2).
  [controllers.py L14-L71](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/scripts/realworld/controllers.py#L14-L71)
- **DualVLN System 1 (`nextdit_async`) is RGB-only.** In `generate_traj`, the
  nextdit branch uses `images_dp` through `rgb_model` and never reads
  `depths_dp`. Only the `navdp` branch passes depth.
  [internvla_n1.py L349-L441](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/model/basemodel/internvla_n1/internvla_n1.py#L349-L441)
- **InternVLA-N1-w-NavDP System 1 takes RGB-D but does not use its critic.**
  `predict_pointgoal_action_async` returns the denoised samples with no critic
  ranking. The module is constructed with `use_critic=False`, although a
  `critic_head` layer exists. Whether the released w-NavDP checkpoint has
  trained critic weights is UNVERIFIED.
  [navdp.py L197-L253](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/model/basemodel/internvla_n1/navdp.py#L197-L253),
  [navdp.py L30-L92](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/model/basemodel/internvla_n1/navdp.py#L30-L92)
- **Both variants average all sampled trajectories.** `generate_traj` defaults
  to 32 samples. `traj_to_actions` computes
  `trajectory = np.mean(all_trajectory, axis=0)`. The real-world agent uses
  this with `use_discrate_action=False`. A mean of multimodal samples (for
  example, left of a box and right of a box) can run between the modes.
  [vln_utils.py L128-L131](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/model/utils/vln_utils.py#L128-L131),
  [internvla_n1_agent_realworld.py L160-L162](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/agent/internvla_n1_agent_realworld.py#L160-L162)
- **The real-world client adds no depth or LiDAR safety layer.** Depth only
  feeds the model. The client publishes a Twist to `/cmd_vel_bridge`
  (scripts/realworld/http_internvla_client.py L213). What the downstream bridge
  does is outside the repository and UNVERIFIED.

Hypothesis only, not tested: mean-averaging could contribute to corner-cutting
paths. It should be ablated before a safety layer is credited with any fix.

---

## 1. OCR safety filter ("One Filter to Deploy Them All")

- **Repository:** https://github.com/albertklin/observation-conditioned-reachability
- **License:** MIT (LICENSE: "Copyright (c) 2026 Albert Lin, Shuang Peng,
  Somil Bansal"). The vendored `libraries/walk-these-ways` and BreezySLAM carry
  their own licenses.
- **Pin:** branch `main`, SHA `92d14861fcb0bf9ca663738e93a7c156afa62b0a`, last
  commit 2026-02-09 ("hardware").
- **Paper:** arXiv 2412.09989. The README cites IEEE T-RO 2026, vol. 42,
  pp. 545-560, doi 10.1109/TRO.2025.3644957.
- **Mechanism:** a learned Hamilton-Jacobi reachability value
  V(state, LiDAR, disturbance bounds) for Dubins3D dynamics, followed by a
  least-restrictive QP over (v_x, v_yaw). If V > threshold (0.35), the nominal
  command passes through. Otherwise the QP enforces
  ∇V·f ≥ −slack + disturbance margin. When the QP fails, the fallback is
  bang-bang control.
  [safety_filter.py L162-L215](https://github.com/albertklin/observation-conditioned-reachability/blob/92d14861fcb0bf9ca663738e93a7c156afa62b0a/utils/safety_filter.py#L162-L215),
  [value and gradient L101-L160](https://github.com/albertklin/observation-conditioned-reachability/blob/92d14861fcb0bf9ca663738e93a7c156afa62b0a/utils/safety_filter.py#L101-L160).
  The calibration offset (−0.5) comes from conformal prediction in
  `scripts/calibrate_value_network.py`.
- **Where robot size enters:**
  - **Not explicitly.** The failure set is `distance_grid <= 0`, where distance
    is |state_xy − obstacle_center| − obstacle_radius. The robot is a point at
    the state position.
    [obstacle.py L70-L77](https://github.com/albertklin/observation-conditioned-reachability/blob/92d14861fcb0bf9ca663738e93a7c156afa62b0a/utils/hj_reachability_utils/obstacle.py#L70-L77),
    [environment.py L80-L85](https://github.com/albertklin/observation-conditioned-reachability/blob/92d14861fcb0bf9ca663738e93a7c156afa62b0a/utils/hj_reachability_utils/environment.py#L80-L85)
  - **Data generation.** Obstacles are circles of radius 0.1-1 m. The state box
    is ±5 m. The controls are v in [0, 2] and w in [−2, 2].
    [generate_value_network_data.py L40-L80](https://github.com/albertklin/observation-conditioned-reachability/blob/92d14861fcb0bf9ca663738e93a7c156afa62b0a/scripts/generate_value_network_data.py#L40-L80)
  - **Implicit buffer.** Body size is covered only by `filter.threshold: 0.35`
    and the calibration adjustment
    ([default.yaml L24-L25](https://github.com/albertklin/observation-conditioned-reachability/blob/92d14861fcb0bf9ca663738e93a7c156afa62b0a/hardware/configs/default.yaml#L24-L25)).
    The LiDAR offset from the robot center is 0.2 m (L39). The paper's
    "radius" mentions refer to obstacle radii only. The paper does not state a
    robot footprint (UNVERIFIED beyond a text search).
- **Wraps our output without retraining:** yes for (v, w), with a caveat. The
  interface is LCM `NOMINAL_COMMAND` (v_x, v_yaw) → `SAFE_COMMAND` (README
  "Deploying on Your Hardware"). A Lite3-specific footprint needs either a
  retuned threshold (no retraining) or regenerated HJ data with inflated
  obstacle radii (retraining; the README says about 8 hours on a recent GPU).
- **Inputs, outputs, runtime:**
  - Inputs: 2D 360° LiDAR scan (RPLidar A2 on hardware), SLAM pose (x, y, θ),
    and estimated disturbance bounds.
  - Output: filtered (v_x, v_yaw).
  - Runtime: Python, PyTorch, cvxpy, and LCM. No ROS. Simulation uses Isaac Gym
    and walk-these-ways.
  - Weights: "Get access" to the Hugging Face dataset
    albertkuilin/observation-conditioned-reachability (access terms
    UNVERIFIED).
- **Legged evidence:** Unitree Go1 EDU hardware with walk-these-ways locomotion.
  The paper also runs simulated Go1 with payload and friction variation.
- **Maintenance:** 23 stars, 0 open issues, code released 2026-02.
- **Limitations for our stack:**
  1. Unicycle model with v_x ≥ 0. There is no v_y, although our bridge accepts
     (vx, vy, wz).
  2. It needs a 360° planar scan. The simulation has only a 79° head RGB-D
     camera. The MID-360 would need projection to 2D.
  3. The paper admits conservatism in clutter. For corridors the authors
     discarded readings outside a π/2 front cone and used the uncalibrated
     value (§VII-B5). It reports non-zero collisions (§VIII).
  4. Training environments had sparse circles and no walls.

## 2. CARE (Collision Avoidance via Repulsive Estimation)

- **Repository:** https://github.com/airlab-sogang/CARE (canonical; linked from
  the project page https://airlab-sogang.github.io/CARE/).
- **License:** MIT. The LICENSE copyright line names the visualnav-transformer
  authors (Shah, Sridhar, et al., 2023); CARE authors are not named. CARE
  additions are assumed to be under the same MIT file (flag).
- **Pin:** branch `main`, SHA `fc916451651353b13e03ded213c40819ff32d953`, last
  commit 2025-08-18.
- **Paper:** arXiv 2506.03834 (CoRL 2025).
- **Mechanism:**
  1. UniDepth metric depth from RGB.
  2. Points within `proximity_threshold` (1.0-1.2 m) form a top-down map. The
     closest point per column is kept.
  3. APF repulsion Σ (1/d³)·unit vector, with influence range 1.0 m.
  4. For each trajectory, take the waypoint with the maximum force. Rotate the
     whole trajectory by atan2(F) clipped to ±π/4.
  5. "Safe-FOV" gate: v = 0 when |desired yaw| > 30°.
  - [navigate_care.py L316-L392](https://github.com/airlab-sogang/CARE/blob/fc916451651353b13e03ded213c40819ff32d953/deployment/src/navigate_care.py#L316-L392),
    [applied after diffusion sampling L495-L507](https://github.com/airlab-sogang/CARE/blob/fc916451651353b13e03ded213c40819ff32d953/deployment/src/navigate_care.py#L495-L507),
    [pd_controller.py L127-L130](https://github.com/airlab-sogang/CARE/blob/fc916451651353b13e03ded213c40819ff32d953/deployment/src/pd_controller.py#L127-L130)
- **Where robot size enters:** a per-robot `safety_margin` is subtracted from
  forward depth Z only: `Z = max(Z0 - safety_margin, 1e-3)`. The values are
  locobot 0.05, robomaster −0.1, and turtlebot4 0.2.
  [L94-L104](https://github.com/airlab-sogang/CARE/blob/fc916451651353b13e03ded213c40819ff32d953/deployment/src/navigate_care.py#L94-L104),
  [L319-L320](https://github.com/airlab-sogang/CARE/blob/fc916451651353b13e03ded213c40819ff32d953/deployment/src/navigate_care.py#L319-L320).
  Paper Table 5 calls this "Depth Offset" and says it compensates body radius
  and camera mounting, "further tuned empirically". There is no lateral width
  term.
- **Wraps our output without retraining:** yes. It post-processes any
  waypoint trajectory. It is designed for NoMaD, ViNT, and GNM.
- **Inputs, outputs, runtime:** RGB plus intrinsics (monocular depth; true depth
  could replace it) → rotated waypoints → PD (v, w). ROS 2, PyTorch, GPU for
  UniDepth. No CARE-specific weights; UniDepth weights are upstream.
- **Legged evidence:** none. The platforms are LoCoBot, TurtleBot4, and
  RoboMaster S1, all wheeled.
- **Maintenance:** 25 stars, 0 open issues, no commits since 2025-08.
- **Limitations for our stack:**
  1. The rotation-only correction cannot shift a path sideways past a corner.
  2. The margin acts on the camera Z axis, not on the body's lateral extent,
     which is our failure mode.
  3. Reactive only, within the field of view and a 1-1.2 m range. The paper's
     §6 states it cannot correct a base path aimed directly at an obstacle.

## 3. NavDP critic (InternRobotics/NavDP), with training code in InternNav

- **Repository:** https://github.com/InternRobotics/NavDP
- **License:** no LICENSE file at the root. The README §License states
  CC BY-NC-SA 4.0 (non-commercial, share-alike). The InternNav copy of the
  NavDP training code is under InternNav's MIT license.
- **Pin:** branch `master`, SHA `bff5eb8857f50e082243fb455d312409daabc3aa`,
  last commit 2026-09-07.
- **Paper:** arXiv 2505.08712 (v3).
- **Mechanism:**
  - **Critic at inference.** The critic scores sampled trajectories from RGB-D
    tokens with the goal masked out (`cond_critic_mask[:, 0:4] = -inf`). This
    makes it goal-independent. The top-2 are selected.
    [policy_network.py L58-L61, L83-L91, L109-L127](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/navdp/policy_network.py#L83-L127)
  - **Stop fallback.** If max critic < `stop_threshold` (eval default −3.0),
    the agent zeroes x and rotates.
    [policy_agent.py L174-L177](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/navdp/policy_agent.py#L174-L177)
  - **Selection matters.** The paper's ablation "w/o Selection" drops Sim-Home
    SR from 60.3 to 53.1 (Table V).
- **Where robot size enters:**
  - **Data engine (paper §III).** A cylindrical robot with "navigation safe
    radius r_b = 0.25 m". ESDF voxels with distance < r_b are truncated before
    A*. Waypoints are pushed away from obstacles by greedy ESDF search.
    Camera height is randomized over 0.25-1.25 m. The data-generation code is
    not in NavDP or InternNav (UNVERIFIED elsewhere).
  - **Critic label (paper Eq. 4).** V = γ·Σ(d_{m+1} − d_m) + λ·mean 𝕀(d_m < d_safe).
    Table II gives d_safe = 0.5.
  - **Released training code is different.** It uses an **L1 (Manhattan) BEV
    distance** from trajectory points to obstacle points with threshold
    **0.1**: `-5.0 * (pred_distance < 0.1).mean() + 0.5 * Σ Δd`.
    [navdp_dataset.py L372-L382](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/dataset/navdp_dataset.py#L372-L382),
    [navdp_lerobot_dataset.py L471-L495](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/dataset/navdp_lerobot_dataset.py#L471-L495).
    This paper-versus-code discrepancy is unresolved.
- **Wraps our output without retraining:** partial.
  - In principle the goal-independent critic can score an external trajectory
    given 8 RGB frames plus one depth frame at 224 px. The trajectory must be
    converted to its delta ×4 xyθ format with 24 waypoints.
  - Obstacles: the standalone checkpoint is behind a Google Form, and our
    trajectories are out of distribution.
  - A checkpoint trained for a 0.25 m disc does not encode Lite3.
- **Legged evidence:** real Unitree Go2 and G1 (Table III point-goal: Go2 7/10,
  G1 7/10). The authors also report iPlanner Go2 5/10 and ViPlanner Go2 4/10.
- **Maintenance:** 791 stars, active.
  - Issue #94: wall collisions traced by the maintainer to depth units.
  - Issue #43: critic values very low until `stop_threshold` was tuned.
  - Issue #10: collisions do not terminate point-goal evaluation.
- **Limitations for our stack:**
  1. Learned scoring, not certification.
  2. Non-commercial license.
  3. Disc model with r_b = 0.25 m.
  4. Critic unused in the w-NavDP System 1.

## 4. X-NavDP (NavDP/baselines/x-navdp)

- **License:** MIT (subdirectory LICENSE). The parent README states
  CC BY-NC-SA 4.0.
- **Pin:** same NavDP SHA as §3. **Paper:** arXiv 2607.28560.
- **Where robot size enters:** RL collision reward from a physical contact
  sensor. Impact is declared when force > 8 N or the force jump > 10 N, and
  repeats within 1 m are suppressed.
  [reward_utils.py L234-L276](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/x-navdp/src/environment/tasks/reward_utils.py#L234-L276).
  The Go2 contact sensor covers the base and hip, thigh, and calf links, with
  the feet excluded (robots/go2_config.py L71-L85). At inference, the twin Q
  critic is conditioned on goal and embodiment, and the mean is used for top-2
  selection.
  [policy_network_embodiment.py L436-L458](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/x-navdp/eval/src/policy_network_embodiment.py#L436-L458)
- **Wraps our output without retraining:** no. Its own planner could, with
  effort, score our trajectory with the endpoint as goal (UNVERIFIED). A Lite3
  embodiment would need post-training.
- **Legged evidence:** Go2 and G1 in simulation, per the prior survey on
  2026-09-10.
- **Limitations:** already recorded in the 2026-09-10 survey (random candidate
  when stuck, 1.5 s sleep).

## 5. ViPlanner (leggedrobotics/viplanner)

- **License:** BSD-3-Clause (LICENSE, "Copyright (c) 2023 Pascal Roth"). The
  README §License still says "belongs to Robotic Systems Lab, ETH Zurich. All
  right reserved". This conflict should be resolved with the authors before
  reuse.
- **Pin:** branch `main`, SHA `6fcf3c60f6fa3b28b3a11af054d6033825923789`, last
  commit 2025-02-12.
- **Paper:** arXiv 2310.00982 (ICRA 2024).
- **Where robot size enters:**
  - **Training loss.** `TrajCost(robot_width=0.6)` samples the cost map at the
    centerline and at ±width/2 along the path normal, giving a square footprint
    approximation. The fear label is the max cost ahead > threshold.
    [traj_cost.py L224-L259](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/traj_cost_opt/traj_cost.py#L224-L259),
    [L30-L61](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/traj_cost_opt/traj_cost.py#L30-L61),
    [fear label L144-L155](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/traj_cost_opt/traj_cost.py#L144-L155).
    The trainer does not override `robot_width`
    ([trainer.py L244-L251](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/utils/trainer.py#L244-L251)).
  - **Cost maps.** Dilation is `sigma_expand` in cells, with no metric robot
    radius (costmap_cfg.py `TsdfCostMapConfig`).
  - **Runtime.** fear > 0.7 marks planning as failed and publishes only the
    first pose.
    [viplanner_node.py L284-L297](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/ros/planner/src/viplanner_node.py#L284-L297)
  - **Offline scorer.** `obs_cost_eval(odom, waypoints)` can score arbitrary
    waypoints, but only against a prebuilt offline cost map, not live
    perception
    ([L190-L209](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/traj_cost_opt/traj_cost.py#L190-L209)).
- **Wraps our output without retraining:** no. The fear head evaluates only its
  own predicted path. The offline cost-map scorer is useful for simulation
  evaluation.
- **Runtime:** ROS Noetic, depth plus semantics (Mask2Former), checkpoint on
  Google Drive.
- **Legged evidence:** ANYmal C and D, real and in Isaac.
- **Maintenance:** 673 stars, 23 open issues, mostly Isaac Lab version breakage
  (#104, #106).

## 6. iPlanner (leggedrobotics/iPlanner)

- **License:** MIT (LICENSE, "Copyright (c) 2023 Fan Yang"; README says MIT).
- **Pin:** branch `master`, SHA `4a8d823ff9d09c3f626b727e7e00484b38f80d49`,
  last commit 2025-02-23.
- **Paper:** arXiv 2302.11434 (RSS 2023).
- **Where robot size enters:**
  - `robot_size = 0.3` ("the inflated robot radius")
    ([data_generation.py L40](https://github.com/leggedrobotics/iPlanner/blob/4a8d823ff9d09c3f626b727e7e00484b38f80d49/iplanner/data_generation.py#L40)).
  - This is the Gaussian blur sigma for obstacle occupancy (robot_size /
    voxel_size), thresholded at > 0.3, then EDT and log to form the cost.
    [esdf_mapping.py L222-L286](https://github.com/leggedrobotics/iPlanner/blob/4a8d823ff9d09c3f626b727e7e00484b38f80d49/iplanner/esdf_mapping.py#L222-L286)
  - Centerline-only cost sampling and fear label:
    [traj_cost.py L37-L74](https://github.com/leggedrobotics/iPlanner/blob/4a8d823ff9d09c3f626b727e7e00484b38f80d49/iplanner/traj_cost.py#L37-L74).
  - Runtime fear buffer truncates the path to its first pose:
    [iplanner_node.py L118-L166](https://github.com/leggedrobotics/iPlanner/blob/4a8d823ff9d09c3f626b727e7e00484b38f80d49/src/iplanner_node.py#L118-L166).
- **Wraps our output without retraining:** no.
- **Runtime:** ROS1, depth only. The README says the pretrained network "has
  not been adapted to real-world data".
- **Legged evidence:** ANYmal (configuration offsets). The authors list real
  experiments in the paper (not re-read here). NavDP's own comparison reports
  Go2 5/10.
- **Maintenance:** issue #17 (open) says code for success and collision
  metrics is missing.

## 7. ABS: Agile But Safe (LeCAR-Lab/ABS)

- **License: no repository-level license (`gh api .../license` returns 404).
  The ABS-authored code is not reusable.** Subdirectory LICENSE files cover
  only third-party parts: legged_gym and rsl_rl (BSD-3, ETH/NVIDIA) and the
  Unitree SDK (BSD-3, Unitree).
- **Pin:** branch `main`, SHA `9b95329ffb823c15dead02be620ff96938e4d0a3`, last
  commit 2024-07-11.
- **Paper:** arXiv 2401.17583 (RSS 2024).
- **Mechanism:**
  - **RA value network.** An MLP with 19 inputs (base linear and angular
    velocity, goal xy, 11 rays), Tanh output.
    [testbed.py L205](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L205)
  - **Shield.** If V > −0.05, it runs 10 gradient steps on the twist
    (vx, vy, wz) to lower V near the goal, then executes the **recovery
    policy**.
    [testbed.py L318-L357](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L318-L357);
    hardware version (3 steps) at
    [depth_obstacle_depth_goal_ros.py L477-L525](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/deployment/src/abs_src/depth_obstacle_depth_goal_ros.py#L477-L525)
- **Where robot size enters:**
  - **Implicitly, through physical contact.** g = +1 on collision, where
    collision means contact on the termination bodies or horizontal foot force
    > 2 × vertical + 10.
    [testbed.py L362-L371, L498-L503](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L498-L503)
  - Contact penalties on thigh and calf; termination on base contact
    ([go1_pos_config.py L85-L86](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/go1/go1_pos_config.py#L85-L86)).
  - Rays start from the base (x0 = −0.05) over ±45° in 9° steps, range
    0.1-6 m, against simulated cylinders only
    ([L137-L150](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/go1/go1_pos_config.py#L137-L150)).
- **Wraps our output without retraining:** no. The RA value is tied to the ABS
  agile and recovery policy dynamics on Go1, and the rays require a trained
  ray-prediction network. The twist-search shield pattern is architecturally
  analogous to wrapping (v, w).
- **Runtime:** Isaac Gym, ROS Noetic, ZED Mini, Orin NX. No released weights.
  The README says the code is only for their hardware.
- **Legged evidence:** Unitree Go1 EDU, real.
- **Maintenance:** stale since 2024. Open issues #7 (collected depth all max
  values), #8, #10, #11.

## 8. legged-loco (yang-zj1026/legged-loco), NaVILA's low-level controller

- **License:** MIT (LICENSE, Cheng et al. 2024).
- **Pin:** branch `main`, SHA `87b0d3d18404e784abc0a62227bc41c940f29ecc`, last
  commit 2024-12-15.
- **Paper:** NaVILA, arXiv 2412.04453.
- **Mechanism:** avoidance happens inside the velocity-tracking RL policy.
  - **Observation.** A LiDAR-derived height map (32 channels, 0-90° vertical,
    360°, 4° resolution; voxel 0.06 m, window x in [−0.8, 0.2], y in
    [−0.8, 0.8] in the LiDAR frame).
    [go2_low_vision_cfg.py L171-L189, L315-L320](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/config/go2/go2_low_vision_cfg.py#L171-L189),
    [observations.py L282-L330](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/leggedloco/mdp/observations.py#L282-L330)
  - **Where robot size enters.** Contact penalty (−5, threshold 0.1) on
    Head, hip, thigh, and calf. Terminations on base, hip, head, and calf
    contact above 1 N.
    [L255-L285](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/config/go2/go2_low_vision_cfg.py#L255-L285).
    Obstacles come from `HfDiscreteObstaclesTerrainCfg` (width 0.4-1.0 m).
- **Wraps our output without retraining:** no. It replaces our proprioceptive
  Lite3 policy.
- **Runtime:** Isaac Sim 4.1, a modified Isaac Lab 1.1. No checkpoints in the
  repository (tree checked). Issue #18 (open) asks for pretrained models.
  Issue #27: mid-level environments are not released.
- **Legged evidence:** Go2 and H1 in simulation. NaVILA reports Go2 real SR
  50.2% versus 36.2% blind (prior survey).
- **Maintenance:** issue #9 (maintainer) says obstacles must be added to the
  terrain config, and 10% of envs use standing commands. Issue #29 (open)
  reports tests without obstacles.

## 9. NVIDIA COMPASS and X-Mobility

- **COMPASS:** https://github.com/NVlabs/COMPASS, Apache-2.0 (LICENSE). Branch
  `main`, SHA `8060f7ccb126b364707d52db3bab016f01547890`, last commit
  2026-06-26. Paper arXiv 2502.16372.
  - **Where robot size enters:** base-contact termination with reward −1000
    (illegal_contact).
    [env_cfg.py L242-L247, L266-L271](https://github.com/NVlabs/COMPASS/blob/8060f7ccb126b364707d52db3bab016f01547890/compass/rl_env/exts/mobility_es/mobility_es/config/env_cfg.py#L242-L271).
    Spot uses body and leg contact (spot_env_cfg.py L56-L78).
  - **Deployment:** publishes `/cmd_vel` directly from model output with no
    safety layer
    ([compass_inference.py L329-L332](https://github.com/NVlabs/COMPASS/blob/8060f7ccb126b364707d52db3bab016f01547890/ros2_deployment/compass_navigator/compass_navigator/compass_inference.py#L329-L332)).
  - **Wraps our output:** no.
- **X-Mobility:** https://github.com/NVlabs/X-MOBILITY, Apache-2.0. Branch
  `main`, SHA `5837aead8902a2f4afdeb372548c45a6b0f8d69b`, last commit
  2026-02-10. Paper arXiv 2410.17491.
  - Trained by imitation of a Nav2 teacher dataset
    (`x_mobility_isaac_sim_nav2_100k`). The Nav2 costmap and footprint settings
    that encode clearance are not in the repository (UNVERIFIED).
  - The Hugging Face model nvidia/X-Mobility is gated=auto, license
    `nvidia-open-model-license`.
  - **Wraps our output:** no.

## 10. Leads screened, not inspected as code

- **Safe-VLN** (arXiv 2311.02817, RA-L 2024): waypoint filtering with a
  simulated 2D LiDAR occupancy mask. No official code found. Unofficial repos
  with similar names (pppjjj274/SafeVLN, xxR627/VLN-CE-SAFETY) were not
  inspected.
- **Unified Autonomy Stack** (arXiv 2605.12735): CBF last-resort filter plus
  depth. This is model-based and belongs to the classical-safety surveyor's
  family.
- **Dynamic CBF regulation with VLMs** (arXiv 2603.21142) and **TTC-based
  filtering** (arXiv 2607.07885): code not checked.

## Ranking against our need (wrap trajectory or (v, w), body-size aware, no retraining)

1. **OCR filter.** Yes for (v, w). Principled QP shield, pure Python, quadruped
   hardware evidence. Point-robot HJ, so the footprint goes into the threshold
   or regenerated data. Needs a 360° planar scan and uses a unicycle model.
2. **CARE.** Yes for trajectory. Trivial to wrap, MIT. Forward-only depth offset
   with no lateral width, rotation-only correction, wheeled evidence only.
3. **NavDP critic.** Partial. Goal-independent learned scorer on RGB-D
   (matches our sensor). Trained for a 0.25 m disc. Non-commercial license.
   Gated weights. The paper's d_safe differs from the code.
4. **ViPlanner.** No at runtime. The 0.6 m-width footprint cost is the best
   explicit width model here, but it is only a training loss and an offline
   scorer.
5. **X-NavDP.** No. Contact-grounded Q critic, requires an embodiment.
6. **iPlanner.** No. 0.3 m inflation, centerline cost.
7. **ABS.** No. Unlicensed, and the RA is tied to its own policies. The shield
   pattern is a useful reference.
8. **legged-loco.** No. Replaces the locomotion policy; no weights.
9. **COMPASS / X-Mobility.** No. Contact-only RL; no deployment safety layer.
