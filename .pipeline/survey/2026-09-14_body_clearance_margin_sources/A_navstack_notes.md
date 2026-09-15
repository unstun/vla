# Survey A: Classical navigation-stack footprint and clearance layers

Surveyor family: A (classical nav-stack footprint/clearance layers).
Date of survey: 2026-09-14. Label: `surveyed` only. Nothing was cloned, built,
run, installed, imported, reproduced, or integrated.

Method: repository metadata and HEAD SHAs from `gh api repos/OWNER/REPO` and
`gh api repos/OWNER/REPO/commits/BRANCH --jq .sha`; source read at the pinned
SHA through `gh api -H "Accept: application/vnd.github.raw"
repos/OWNER/REPO/contents/PATH?ref=SHA`. Licenses were confirmed by reading
LICENSE/COPYING text and package.xml, not only the GitHub API field. Local copies
of every file read are under `scratchpad/survey_clearance/src/` (scratch only).

Stack context assumed (from the task brief, not re-verified here): System 1
trajectory (x, y) at ~2.5 Hz -> CasADi MPC (point robot) at 10 Hz -> (v, w) ->
bridge clamp 0.75 m/s, 1.0 rad/s, 250 ms watchdog -> locomotion policy
(vx, vy, wz). Incident: planned path 0.13 m outside a box corner; front-right hip
hit at 514 N. Lite3 body ~0.61 x 0.39 m (approximate); hips at +-0.1745 m x,
+-0.062 m y. Sim sensors: head RGB-D 640x480, HFOV 79 deg, optional ray-cast
depth. Real robot: D435i, Livox MID-360 (leads). Sim loop is pure Python, no
ROS; real-robot baseline is ROS 2 Foxy.

---

## Pin table

| # | Repo (component) | License (SPDX, how confirmed) | Branch | Pinned SHA | Last commit (branch) | ROS |
|---|---|---|---|---|---|---|
| 1 | https://github.com/ros-navigation/navigation2 (`nav2_collision_monitor`) | Apache-2.0 (package.xml L9; repo LICENSE says per-package) | main | f31c7f49bf7afb9e32f4651ef91fb46f5636c88c | 2026-09-13 | ROS 2 Rolling on main; branches humble 3c3db59d6969d8ecee8e68468693d006397f4a0c (2026-06-03), jazzy f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501 (2026-08-21), kilted, lyrical. **Not present on foxy-devel** 0c9917ffc3cd53175a066b87659ea3920e3a4f20. `VelocityPolygon` absent on humble. |
| 2 | https://github.com/at-wat/neonavigation (`safety_limiter`) | BSD-3-Clause (LICENSE text, 3 clauses; package.xml says `BSD`; API returns NOASSERTION because LICENSE concatenates several notices) | master | 5fe952229b181e989faa6c119380631c97510105 | 2026-04-23 (touches safety_limiter) | ROS 1 (catkin; README: released to Alpine ROS after ROS 1 EOL). ROS 2 only as WIP branch `humble` cd7027a8abe46ffc1993f765f2cdd734fd4b7592 (2024-06-25, "[WIP] Testing of migration to ROS2 Humble", 38 commits behind master). |
| 3 | https://github.com/ros-navigation/navigation2 (`nav2_costmap_2d` footprint + inflation; `nav2_mppi_controller` CostCritic/ObstaclesCritic; `dwb_critics` ObstacleFootprintCritic) | costmap_2d: BSD-3-Clause and Apache-2.0 (both in package.xml L16-L17); mppi: MIT (package.xml L9); dwb_critics: BSD-3-Clause (package.xml) | main | f31c7f49bf7afb9e32f4651ef91fb46f5636c88c | 2026-09-13 | Same as row 1. MPPI absent on foxy-devel; DWB + costmap present on foxy-devel. |
| 4 | https://github.com/MRPT/mrpt (`modules/mrpt_nav`, PTG robot shapes, reactive nav) | BSD-3-Clause (COPYING and modules/mrpt_nav/LICENSE text) | develop (MRPT 3.x) | d6d0e4ad47b0df2d9ccc2c1799b89948271846ca | 2026-09-11 | No ROS needed. ROS 2 wrappers: https://github.com/mrpt-ros-pkg/mrpt_navigation branch ros2 3b8c564c6441c7aa030546b04ada77d13751cab7 (2026-08-10), BSD-3-Clause (LICENSE.txt), README lists Humble/Jazzy/Kilted/Rolling. Stable 2.x branch 51286ccf6fc5969d2ffc47ba2bb844813eef5cc7 (2026-08-20). |
| 5 | https://github.com/rst-tu-dortmund/teb_local_planner | BSD-3-Clause (LICENSE text 3 clauses; package.xml `BSD`); README notes g2o csparse_extension is LGPL-3.0-or-later | noetic-devel (default) | 8f429538601d7c4102aa345e8b5ba8dfae989c00 | 2026-01-09 | ROS 1 Noetic/ROS-O default. ros2-master e4562a62bac75f6004b74661ba1538be9cd07608 (2024-11-10, jazzy compile fixes); foxy-devel d6865b419ba70bf637f5125317c380e00f7944c3 (2021-01-04); humble-devel 630a22e88dc9fd45be726a762edbb5b776bef231 (2022-09-12). |
| 6 | https://github.com/4am-robotics/cob_control (`cob_collision_velocity_filter`) | Apache-2.0 (repo LICENSE text; package.xml `Apache 2.0`) | noetic-devel (default) | e1e1018911448e1e07e8e32cb2d0220f0d768164 | 2026-08-20 (repo); package last touched 2024-08-05 | ROS 1 only (catkin, costmap_2d). |
| 7 | https://github.com/rst-tu-dortmund/mpc_local_planner | GPL-3.0-or-later (README L38-L53 "version 3 ... or any later"; COPYING.md GPLv3; package.xml `GPLv3`); depends on control_box_rst (GPLv3) and Ipopt (EPL-1.0) per README | master (default) | 5b4e465fec718245484e8668e6dd45539ca37983 | 2021-01-04 | ROS 1 only upstream (catkin on master, noetic-devel, and even `ros2-master` 8a5980a7aedfc6385a2329a3f2baba8318091857 has a catkin package.xml). ROS 2 ports only as unmerged PRs #35 and #49 (fork stephenadhi/mpc_local_planner foxy-devel). |

---

## 1. Nav2 `nav2_collision_monitor` (best documented velocity filter with footprint)

Base URL for permalinks: `https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/`

### What the margin is
- Zones are arbitrary polygons in the base frame, circles, or the robot footprint
  (subscribed from `local_costmap/published_footprint`, i.e. the costmap's padded
  footprint). No padding parameter inside the monitor itself; the margin is
  whatever polygon you draw, or the costmap `footprint_padding`.
  - Footprint subscription and polygon update: `nav2_collision_monitor/src/polygon.cpp#L246-L291`; default topic `#L498-L501`.
  - Point-in-polygon counting: `nav2_collision_monitor/src/polygon.cpp#L293-L319`, using ray crossing in `nav2_util/include/nav2_util/geometry_utils.hpp#L200-L233`.
  - Circle: `nav2_collision_monitor/src/circle.cpp#L53-L60` (squared radius test).
- Action models (`collision_monitor_node.cpp`):
  - STOP / SLOWDOWN (scale by `slowdown_ratio`) / LIMIT (cap linear/angular, same ratio to keep curvature): `nav2_collision_monitor/src/collision_monitor_node.cpp#L544-L606`.
  - APPROACH: forward-simulate the current command as a constant twist and scale speed by `collision_time / time_before_collision`: `#L608-L638`; simulation in `nav2_collision_monitor/src/polygon.cpp#L339-L388`; motion model `nav2_collision_monitor/src/kinematics.cpp#L44-L68` (integrates x, y and theta, so `vy` is handled); point transform `#L22-L42`.
  - Parameters and defaults: `min_points` default 4 `polygon.cpp#L439`; `slowdown_ratio` 0.5, `linear_limit`/`angular_limit` 0.5 `#L467-L472`; `time_before_collision` 2.0 s, `simulation_time_step` 0.1 s `#L476-L479`.
  - Debounce `trigger_consecutive_points` / `release_consecutive_points`: `polygon.cpp#L170-L194`.
- `VelocityPolygon` (switch polygon by commanded velocity; optional `holonomic` mode uses |v| and direction atan2(vy, vx)): `nav2_collision_monitor/src/velocity_polygon.cpp#L37-L112`, `#L114-L178`.
- Clearance is binary per polygon (count of points inside >= `min_points`), or a
  time-to-collision for APPROACH. No metric distance-to-footprint is computed.

### Inputs / outputs / stale data
- Inputs: `cmd_vel_in` (Twist or TwistStamped), sources LaserScan, PointCloud2,
  Range, `nav2_msgs/Costmap`, plus polygon sources; TF from source frame to
  `base_frame_id` (with optional `base_shift_correction` through odom frame).
  - PointCloud filter: range from sensor `min_range`, height band `min_height`
    (default 0.05) / `max_height` (default 0.5), then flattened to 2D:
    `nav2_collision_monitor/src/pointcloud.cpp#L107-L179`, defaults `#L190-L194`.
- Output: `cmd_vel` scaled or zero; action-state notifications; markers.
- Processing is event-driven: `process()` runs only inside the `cmd_vel_in`
  callback (`collision_monitor_node.cpp#L211-L229`, `#L429-L542`). If the upstream
  controller stops publishing, the monitor publishes nothing (no watchdog of its
  own); after a stop it keeps publishing zero for `stop_pub_timeout` then goes
  silent (`#L231-L253`).
- Stale sensor data: if any enabled source is older than `source_timeout`
  (default 2.0 s, `#L262-L283`) or its TF fails, the result is STOP with
  polygon name "invalid source" (`#L449-L465`; `source.cpp#L179-L196`,
  `#L325-L349`). `source_timeout: 0.0` disables the block.

### Standalone?
- No. Every class takes an `rclcpp_lifecycle` node for parameters and
  subscriptions; built with ament; lifecycle-managed.
- Glue option A (run upstream): a ROS 2 (Humble or newer) sidecar node; the
  Python sim publishes `PointCloud2` (ray-cast depth or RGB-D back-projection),
  TF base->sensor (and odom->base if `base_shift_correction`), and MPC
  `(v, 0, w)` to `cmd_vel_in`; the bridge reads `cmd_vel`. This reintroduces
  ROS 2 into the sim loop that was deliberately made ROS-free, and adds DDS
  latency to a 10 Hz loop with a 250 ms watchdog.
- Glue option B (port): the decision logic is small (point-in-polygon,
  constant-twist projection, min/scale rules; roughly the line ranges above).
  A Python port under Apache-2.0 with attribution is feasible, and upstream
  unit tests exist to build parity cases from:
  `nav2_collision_monitor/test/polygons_test.cpp`, `kinematics_test.cpp`,
  `velocity_polygons_test.cpp`, `collision_monitor_node_test.cpp`. A port is
  local code and would need its own parity evidence; it is not "using upstream".
- Real robot: the Foxy baseline has no collision monitor (absent on
  `foxy-devel`). Humble is the oldest branch that has it, and Humble lacks
  `VelocityPolygon`. Backport effort UNVERIFIED.

### Legged-robot evidence
- Nav2 issue #1676 "Legged robot demo" is still open (created 2020-05-04). In
  2025 comments the maintainer agrees a quadruped with a vendor gait controller
  can take Nav2 Twist commands, but says he has not done it himself
  (https://github.com/ros-navigation/navigation2/issues/1676).
- Nav2 docs "robots using" page shows Unitree Go2 and G1 logos
  (docs.nav2.org repo, rolling 3a991e6319c63c18a7de2fc30f4c2d5bf0b0a0fb,
  `docs/robots_using/index.md` L43-L46). Marketing-level only; no collision
  monitor configuration or evaluation shown.
- Community Go2 SDK (https://github.com/abizovnuralem/go2_ros2_sdk, license per GitHub API field
  BSD-2-Clause, LICENSE file not read: UNVERIFIED;
  b440609591a249e7bdd4bbc88e056a3660575447) `go2_robot_sdk/config/nav2_params.yaml`
  uses DWB + rectangular costmap footprint (L201, L244) and does not configure the
  collision monitor. Configuration only; no reported evaluation.
- No paper or issue found that evaluates `nav2_collision_monitor` on a legged robot.

### Maintenance
- Active: package commits 2026-07-30/31 (exclusion zones, #6233, #6304).
- Relevant open issues: #6346 (2026-08-12) approach polygon brakes constantly
  near walls the robot intends to pass close to, meaning a long
  `time_before_collision` conflicts with close maneuvering, which matches our
  corner-passing case. Closed-but-relevant: #5740 (holonomic resultant-speed
  bands, closed 2026-02-17); #4863 (source timestamp mismatch -> ignored source).

### Quadruped-relevant limitations (from source)
- 2D only: points in a height band are flattened; body is a 2D polygon. Leg swing
  envelope and the hip, which sits lower than the torso top, are not modelled
  separately.
- APPROACH assumes the current twist stays constant for `time_before_collision`.
  The MPC changes the command every 100 ms, so a curving path that clips a corner
  is only caught when the constant-twist arc of that instant intersects it.
- Returned collision time is the loop variable at the start of the step in which
  collision is found (first projected step returns 0.0), so the model is one step
  conservative. Read from source, not tested.
- No obstacle memory: each cycle uses only the latest message per source. A
  corner that has left a forward camera's FOV is forgotten unless a
  `nav2_msgs/Costmap` source (with its own memory) is used.
- `min_points` default 4 can miss a thin corner seen by few rays.
- `VelocityPolygon` keeps the previous polygon, with a throttled warning, when
  the command matches no sub-polygon (`velocity_polygon.cpp#L134-L139`).
- Holonomic direction bands exist, but the APPROACH model and the zone
  shapes are not tied to the actual stopping distance of the robot; braking
  capability must be encoded by hand through `time_before_collision` or zone size.

---

## 2. neonavigation `safety_limiter` (closest match to "predict footprint collision for this cmd_vel and limit")

Base: `https://github.com/at-wat/neonavigation/blob/5fe952229b181e989faa6c119380631c97510105/safety_limiter/`

### What the margin is
- Footprint: required polygon param (>= 3 vertices), closed internally;
  `footprint_radius_` = max vertex distance used as a KD-tree search radius:
  `src/safety_limiter.cpp#L219-L251`. Point-in-polygon: `#L675-L692`.
- Prediction: for t in [0, tmax) with step `dt`, move the robot by the *current*
  twist (x, y, and yaw, so `linear.y` is supported) and test downsampled cloud
  points inside the footprint: `#L425-L508`. `tmax` = 1.5 x max(v/a) + max(d_margin/v, yaw_margin/w): `#L343-L351`.
- Margin is along the motion: travel distance to first contact minus `d_margin`
  (default 0.2 m), yaw to contact minus `yaw_margin` (default 0.2 rad), with delay
  compensation (delay = 1/freq + dt), then the allowed speed is sqrt(2 a d) and the
  output is scaled by ratio = min(d_r, yaw_r): `#L525-L554`; applied uniformly to
  vx, vy, wz: `#L557-L577`. Defaults: `cfg/SafetyLimiter.cfg` L8-L26
  (freq 6 Hz, cloud_timeout 0.8 s, lin_acc 1.0, ang_acc 1.6, z_range 0.0-0.5 m,
  dt 0.1, d_escape 0.05, yaw_escape 0.05, hold 0, allow_empty_cloud false).
- Escape: if already in collision at t = 0, small motions under `d_escape` /
  `yaw_escape` are allowed; otherwise stop: `#L484-L507`.
- No lateral clearance margin: `d_margin` is a distance before contact along the
  predicted motion, not an inflation of the polygon. A lateral buffer needs a
  padded footprint polygon.

### Inputs / outputs / stale data
- Inputs: `cmd_vel_in` (Twist), one or more `cloud`/`cloudN` PointCloud2, TF to
  `fixed_frame` (odom) and `base_frame`, `disable_safety` (Bool), `watchdog_reset`.
  Clouds are accumulated in the fixed frame between prediction ticks and cleared
  after each tick (`#L736-L772`); z-band filter then flattened (`#L402-L410`).
- Output: limited `cmd_vel`, `collision` PointCloud, status and diagnostics.
- Stale data: cloud older than `cloud_timeout` -> publish zero and require new
  cloud (`#L293-L305`); empty cloud -> ratio 0 unless `allow_empty_cloud`
  (`#L356-L364`, `#L412-L420`); TF failure -> ratio 0 (`#L372-L382`); optional
  `watchdog_interval` -> publish zero until reset (`#L271-L285`). No cloud yet ->
  zero output (`#L721-L725`).
- Output is published only when a `cmd_vel_in` arrives (`#L710-L734`); the
  prediction runs on its own timer.

### Standalone?
- No: single-file roscpp node (catkin, dynamic_reconfigure, PCL, tf2). ROS 1 only
  upstream. The algorithm is compact (predict at `#L354-L555`) and portable to
  Python (BSD-3-Clause with notice), but that is a port with its own validation.
- Glue: port `predict()` + `limit()` into the bridge path between MPC (v, w) and
  the bridge clamp; feed it a base-frame point set from the sim depth/ray-cast.

### Legged-robot evidence
- None found in repo docs or issues. UNVERIFIED for any legged use.

### Maintenance
- Active through 2026 (release 0.18.3 2026-01-16; empty-cloud fix 2026-04-23).
  A centrifugal acceleration limit was added and reverted after real-robot trials
  (PR #774 -> #784, 2025-07-16; revert reason: abrupt deceleration at curve entry).
- Open issues relevant to correctness:
  - #314 (open since 2019): output only published on input arrival; prediction
    keeps the current curvature and cannot stop a collision if angular velocity
    changes while running close and parallel to a wall. This is the corner-grazing
    failure mode.
  - #426 (open since 2020): cloud may be transformed with latest TF (time 0),
    introducing delay; extrapolation suggested.

### Quadruped-relevant limitations
- Constant-twist extrapolation (issue #314); MPC updates every 100 ms.
- Braking model uses constant decelerations (`lin_acc`, `ang_acc`); a learned
  locomotion policy's real stopping behaviour must be measured to set them.
- 2D footprint and a z band; no obstacle memory beyond one prediction tick.
- Uniform scaling of (vx, vy, wz) keeps the curvature of a path that may itself
  be the problem.

---

## 3. Nav2 costmap footprint + inflation, MPPI `consider_footprint`, DWB footprint critic

Base: `https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/`

### What the margin is
- Footprint polygon or `robot_radius`; `footprint_padding` (default 0.01 m)
  pushes each vertex outward by sign(x)*pad, sign(y)*pad:
  `nav2_costmap_2d/src/costmap_2d_ros.cpp#L387` and `#L496`;
  `nav2_costmap_2d/src/footprint.cpp#L147-L155`.
- Inflation layer: cost 254 at distance 0, 253 inside `inscribed_radius`, then
  exponential decay by `cost_scaling_factor` up to `inflation_radius`
  (defaults 0.55 m and 10.0): `nav2_costmap_2d/include/nav2_costmap_2d/inflation_layer.hpp#L121-L135`,
  params `nav2_costmap_2d/plugins/inflation_layer.cpp#L95-L102`.
- Footprint collision check rasterizes only the polygon *edges*:
  `nav2_costmap_2d/src/footprint_collision_checker.cpp#L47-L107`.
- MPPI CostCritic: centre-point cost first; full SE2 footprint check only if
  cost >= circumscribed cost (`consider_footprint`); collision is a large soft
  cost (`collision_cost` 1e6), near-collision adds `critical_cost`:
  `nav2_mppi_controller/src/critics/cost_critic.cpp#L24-L83`, `#L131-L231`;
  `include/nav2_mppi_controller/critics/cost_critic.hpp#L59-L81`.
- MPPI ObstaclesCritic: distance recovered from inflation cost;
  `collision_margin_distance` (default 0.10 m) as a virtual footprint inflation:
  `nav2_mppi_controller/src/critics/obstacles_critic.cpp#L24-L35`, `#L105-L185`.
- DWB ObstacleFootprintCritic: edge rasterization; lethal or unknown cell ->
  trajectory illegal: `nav2_dwb_controller/dwb_critics/src/obstacle_footprint.cpp#L88-L164`.

### Inputs / outputs
- Input: layered costmap (static, obstacle/voxel from LaserScan/PointCloud2,
  inflation), footprint, odometry, a path. Output: a controller `cmd_vel` or
  critic cost. This is a controller-level margin, not a filter on an external
  (v, w). Using it means replacing or re-hosting the CasADi MPC (for example MPPI
  with `mppi::OmniMotionModel` following the System 1 path), not wrapping it.
- Stale data: costmap observation buffers have `expected_update_rate` and
  `observation_persistence` (not read in detail here: UNVERIFIED specifics);
  open issue #6494 (2026-09-10) reports late subscribers receiving stale costmaps.

### Standalone?
- No (costmap is `Costmap2DROS` lifecycle node; MPPI/DWB are `nav2_core`
  plugins). `Costmap2D` and `FootprintCollisionChecker` are C++ classes that could
  be linked without spinning ROS, but still depend on rclcpp headers. Python
  access: none upstream.

### Legged evidence
- As in section 1: Go2 community config uses DWB + footprint costmap; no evaluation.

### Maintenance / open correctness issues
- #5329 (open, 2025-07-03): Smac collision checker checks footprint vertices/edges
  only; a single lethal cell can sit inside the footprint. Draft fix PR #5416
  "Full-area footprint check" (open).
- #6273 (open, 2026-07-16): MPPI applies a constant footprint over the whole
  horizon; proposal for velocity-dependent footprint. Draft PR #6503 (2026-09-13).
- MPPI holonomic limits churn: #6344 merged then reverted #6383 (2026-08-21);
  PR #6390 and #6460 open.

### Quadruped-relevant limitations
- Edge-only footprint rasterization plus soft costs means "footprint aware" is
  not a hard guarantee; the inflation radius must be at least the circumscribed
  radius for the fast path (warning text in `cost_critic.cpp#L51-L59`,
  `#L102-L112`).
- 2D grid resolution adds quantization at the scale of the 0.065 m
  body-overlap in our incident.

---

## 4. MRPT `mrpt_nav` (TP-Space PTGs with robot shape)

Base: `https://github.com/MRPT/mrpt/blob/d6d0e4ad47b0df2d9ccc2c1799b89948271846ca/modules/mrpt_nav/`

### What the margin is
- Robot shape is a polygon (`CPTG_RobotShape_Polygonal`) or a circle
  (`CPTG_RobotShape_Circular`): `include/mrpt/nav/tpspace/CParameterizedTrajectoryGenerator.h#L547` and `#L591`.
- Obstacles are mapped into TP-Space: for each PTG path index k, the free
  distance until the shape hits each obstacle (`updateTPObstacle`,
  `CParameterizedTrajectoryGenerator.h#L285-L295`). The reactive navigator then
  scales speed by a ramp between `secure_distance_start` and
  `secure_distance_end` (normalized [0,1] free distance):
  `src/reactive/CAbstractPTGBasedReactive.cpp#L1463-L1479`.
- Polygon clearance is approximate: inside-polygon -> 0, else hypot minus the
  max robot radius, floored at 0.1 x max radius:
  `src/tpspace/CPTG_RobotShape_Polygonal.cpp#L151-L170`. For a 0.61 x 0.39 body
  this is circumscribed-circle conservative laterally.
- Holonomic PTG `CPTG_Holo_Blend` derives from the circular shape only:
  `include/mrpt/nav/tpspace/CPTG_Holo_Blend.h#L30`; obstacle update
  `src/tpspace/CPTG_Holo_Blend.cpp#L653-L790`.
- Height band: obstacles kept if `min_obstacles_height <= z <= max_obstacles_height`:
  `src/reactive/CReactiveNavigationSystem.cpp#L208-L248`.

### Inputs / outputs / stale data
- Input: obstacle point cloud via a robot interface (`senseObstacles`), pose/vel,
  targets. Output: a velocity command chosen among PTGs (it is a navigator, not a
  filter on an external command). Sense failure -> emergency stop:
  `src/reactive/CAbstractPTGBasedReactive.cpp#L232-L262`. It also checks the
  time offset between pose and obstacle timestamps (warns if > 1.25 s):
  `#L271-L341`.

### Standalone?
- Yes as a C++ library (no ROS). Python bindings exist but at this SHA expose only
  PTG factory, `inverseMap_WS2TP`, `PTG_IsIntoDomain`, config loading:
  `python_bindings/mrpt_nav_py.cpp#L87-L125`. `updateTPObstacle` and
  `setRobotShape` are not bound here. On the 2.x branch, the generated binding
  `python/src/mrpt/nav/tpspace/CParameterizedTrajectoryGenerator.cpp` contains
  `setRobotShape`, `isPointInsideRobotShape`, `evalClearanceToRobotShape`, but a
  string search found no `updateTPObstacle` binding. Partial.
- Glue: either C++/pybind shim exposing `updateTPObstacle` for the PTG that matches
  the current (v, w) arc, or adopt the whole reactive navigator (replaces MPC).

### Legged evidence
- None found. UNVERIFIED.

### Maintenance / correctness signals
- Very active. Commit 0aaa3b5fdd (2026-09-08) "fix 7 TP-Space bugs" includes:
  clearance modes swapped relative to docs; clearance diagram keyed by metres
  instead of normalized distance; `CPTG_Holo_Blend` using `V_MAX` in
  `updateTPObstacleSingle` while path poses use direction-dependent speed. Results
  from older MRPT versions (including 2.x) may carry these bugs; whether 2.x has
  the fixes is UNVERIFIED.

### Quadruped-relevant limitations
- Holonomic PTG is circle-only (a 0.61 x 0.39 body becomes r ~0.36 m).
- Navigator architecture does not fit "filter the MPC output" without glue.
- API churn at develop HEAD (MRPT 3) versus stable 2.x.

---

## 5. `teb_local_planner` footprint models

Base (ROS 1 default): `https://github.com/rst-tu-dortmund/teb_local_planner/blob/8f429538601d7c4102aa345e8b5ba8dfae989c00/`

### What the margin is
- Footprint models point, circular, two-circles, line, polygon:
  `include/teb_local_planner/robot_footprint_model.h#L51-L110` (base),
  circular distance `#L263-L266`, two circles `#L351-L357`, polygon `#L664-L669`,
  polygon inscribed radius `#L728-L748`. Param parsing
  `src/teb_local_planner_ros.cpp#L1049-L1161`.
  ROS 2 copy: `https://github.com/rst-tu-dortmund/teb_local_planner/blob/e4562a62bac75f6004b74661ba1538be9cd07608/teb_local_planner/include/teb_local_planner/robot_footprint_model.h#L541-L575`.
- `min_obstacle_dist` (default 0.5 m) and `inflation_dist` (0.6 m):
  `include/teb_local_planner/teb_config.h#L129-L131`, `#L302-L304`. Enforced as a
  soft penalty `max(0, min_obstacle_dist + penalty_epsilon - dist)`:
  `include/teb_local_planner/g2o_types/edge_obstacle.h#L85-L103`,
  `include/teb_local_planner/g2o_types/penalties.h#L107-L117`.
- Polygon-to-point distance is unsigned edge distance with no inside test:
  `include/teb_local_planner/distance_calculations.h#L165-L190`, used by
  `PointObstacle::getMinimumDistance(polygon)` `include/teb_local_planner/obstacles.h#L370-L373`.
  A point fully inside the footprint therefore reports a positive distance to the
  nearest edge (read from source, not tested).
- Hard check: `isTrajectoryFeasible` uses costmap footprint cost for the first
  `feasibility_check_no_poses` poses with interpolation:
  `src/optimal_planner.cpp#L1250-L1300`.
- Class comment says the footprint model is used in optimization only
  (`robot_footprint_model.h#L51-L57`).

### Inputs / outputs / standalone
- Inputs: costmap obstacles (optionally via costmap_converter), global plan, odom.
  Output: `cmd_vel` from an optimized trajectory. Replaces the MPC.
- Standalone: the footprint header is header-only math, but it includes ROS
  message types (`visualization_msgs`). The planner is a move_base / nav2_core
  plugin. Not a filter.

### Legged evidence / maintenance
- None found (GitHub issue search returned nothing for "legged"/"quadruped";
  search API unreliable, so UNVERIFIED).
- Low activity: ros2-master last 2024-11-10; noetic-devel 2026-01-09 build-flag
  change; footprint header last changed 2022-05-31. 153 open issues; for example
  #317 (open) planned path passing through obstacles.

### Quadruped-relevant limitations
- Soft constraint; supports `max_vel_y` (holonomic) but footprint and obstacle
  association heuristics were built for wheeled bases.

---

## 6. `cob_collision_velocity_filter` (Care-O-bot, holonomic)

Base: `https://github.com/4am-robotics/cob_control/blob/e1e1018911448e1e07e8e32cb2d0220f0d768164/cob_collision_velocity_filter/`

- Margin: rectangular footprint only (warns if > 4 points)
  `src/cob_collision_velocity_filter.cpp#L113-L118`; `influence_radius` (1.5 m),
  `stop_threshold` (0.10 m), `obstacle_damping_dist` (5.0 m) `#L69-L86`.
  Obstacles from a costmap; a "tube" swept along the commanded (vx, vy) direction
  plus a circumscribed circle when rotating; distance to rectangle border
  per side: `#L356-L575`. Speed limited by a potential-field/damping law and stop
  below `stop_threshold`: `#L234-L350`.
- Input: Twist `command_in`, own costmap_2d. Output: filtered `command`.
  Processing on each incoming command (`#L156-L172`). Stale-costmap handling not
  found in the read ranges: UNVERIFIED.
- Standalone: no (roscpp + costmap_2d, ROS 1 only).
- Legged evidence: none found.
- Maintenance: package last changed 2024-08-05 (release 0.9.25).
- Fit: illustrates a holonomic direction-aware tube, but ROS 1, rectangle-only,
  costmap-bound.

---

## 7. `mpc_local_planner` (rst-tu-dortmund)

Base: `https://github.com/rst-tu-dortmund/mpc_local_planner/blob/5b4e465fec718245484e8668e6dd45539ca37983/mpc_local_planner/`

- Margin: hard inequality `min_obstacle_dist - dist(robot_model, obstacle) <= 0`
  per stage, reusing TEB footprint models:
  `src/optimal_control/stage_inequality_se2.cpp#L164-L175`. Only the nearest
  left and nearest right obstacle per stage are kept, plus force-included
  obstacles: `#L50-L162`. Issue #1 (open since 2020): no inflation, only hard
  constraints, so it passes obstacles very close.
- Models: unicycle, simple car, kinematic bicycle (`include/mpc_local_planner/systems/`);
  no holonomic model found in the tree.
- Standalone: no (ROS 1 plugin; control_box_rst). License GPL-3.0-or-later.
- Maintenance: default branch last commit 2021-01-04; ROS 2 only as unmerged PRs.
- Fit: lowest (license, no vy, stale, replaces the MPC). Useful only as a
  reference that CasADi-style hard footprint constraints exist upstream.

---

## Considered but not surveyed in depth
- Autoware obstacle stop/cruise and collision checker packages (vehicle footprint
  + margin, ROS 2 heavy): not read.
- `spatio_temporal_voxel_layer`, `robot_body_filter`: address obstacle memory and
  self-filtering respectively, not the footprint margin itself. Not read.

## Cross-cutting observations relevant to the Lite3 incident
- Geometry: the centre path passed 0.13 m from the corner while the body half
  width is about 0.195 m, so a padded rectangle of the brief's size would flag the
  pose, provided the corner is present in the obstacle input at that moment.
- Every candidate reduces the body to a 2D shape plus a z band; none models leg
  swing or hip protrusion separately.
- The filters (1, 2, 6) keep no obstacle memory beyond one cycle. A corner beside
  the hip is likely outside a forward head camera's 79 deg HFOV at contact time
  (camera mount pose UNVERIFIED); a sensor-frame-only filter would then see
  nothing. A memory source (costmap/voxel layer or world-frame accumulation) is a
  separate requirement.
- Filters that act on the instantaneous twist (1, 2, 6) use constant-twist
  extrapolation; safety_limiter issue #314 documents the failure when curvature
  changes near a wall. The System 1 trajectory itself is not checked by any of
  them unless a separate footprint-along-path check is added.
- None exposes a Python API for the relevant operation without ROS or a port,
  except MRPT with missing bindings for obstacle mapping.
