---
origin: ai+web
reviewed: false
date: 2026-09-17
status: surveyed
---

# PCT lineage and PCT-based integrations: how local planning treats stairs

Scope: the PCT side of the PCT -> SCAN -> blind RL stack. This file covers byangw/PCT_planner
forks, issues, and PRs, and other GitHub repositories that pair PCT with a local planner or local
map. SCAN-Planner forks and PCT-SCAN-ROS2 forks and issues belong to the other surveyor and are not
repeated here. Stage: planning. Label: `surveyed` only. Nothing was cloned, installed, or run.
All code was read through `gh api` at the commit SHAs given below. Anything not read directly is
marked UNVERIFIED.

Upstream baseline: byangw/PCT_planner `main` @ `35cd73fd82bcd51bc538429294af7646b2a09815`
(2025-02-17), GPL-2.0, 508 stars, API `forks_count` = 68. It has only three commits: an initial
commit, `init commit`, and `update readme`.

## 1. Fork census

Method: I paginated `repos/byangw/PCT_planner/forks` and then walked forks of forks to depth 3.
For every branch of every fork, I ran `compare/main...<owner>:<repo>:<branch>`. That covered 94
branches.

| Count | Meaning |
| ---: | --- |
| 70 | fork repositories in the network: 54 direct, 15 second-level, 1 third-level |
| 31 | have at least one branch ahead of upstream `main` (list below) |
| 36 | identical to or only behind upstream (no own commits) |
| 1 | `overloadsc/PCT_planner`: history rewritten ("no common ancestor"). I read its one own commit directly |
| 2 | `1y7rzc35/PCT_planner`, `1y7rzc35/PCT_planner_ros2`: HTTP 404 (deleted or private). UNVERIFIED |

Some of the 31 forks that are ahead only carry commits from their parent fork. These are
AdairShelby, huyasann, lichao951787328, ruiqichao, XeonHis, and DaYeon-416 (from `2473o`),
`dimensionalOS/PCT_planner` (from VectorRobotics), `qza36/PCT_planner_ros2` (from Kuriharamio), and
`AlexWUrobot`, which is a prefix of `OpenMind`. About 23 forks have commits of their own.

### Classification of forks with commits ahead

| Class | Forks (head SHA) | Notes |
| --- | --- | --- |
| **Local planner + stair terrain handling** | `tianchaowen/PCT_planner` `8c56322fa3fc` | **The only fork with this.** It bridges PCT to EGO-Planner and filters the live cloud by height above the PCT surface. See section 2 |
| Local planner or online map (not stair-specific) | `SC0K/PCT_planner` `b766a4f43e7f` | Coverage and next-best-view planner. Live voxels missing from the prior map are written back into the tomogram as obstacles |
| Path follower only | `81578823/PCT_planner` `44b236928523` | Pure pursuit on `/pct_path` for LimX TRON1. "Stair mode" is a manual WebSocket toggle. No obstacle avoidance |
| ROS 2 ports | `2473o` `2a8dbe3954` (+6 derivatives), `hengzhiyou666@heng` `a01fe4df65`, `zichnw` (3D/layer), `VectorRobotics` `0cf4827eb0e3` (+dimensionalOS), `Kuriharamio@RC2026_Map_Planner` `be820e1d61b5` (+qza36), `AlexWUrobot`/`OpenMind` `b5ee5284f349` (+mozluk), `jalenzz` `a52ba35958` | Global planner only. VectorRobotics feeds the CMU autonomy stack (section 3.3) |
| Global-planner fixes relevant to stairs | `zhongrenjiexing@jetson` `0a5cb4dd5fe2`, `hengzhiyou666`, `NeuroNexa`, `VectorRobotics` (z to slice), `OpenMind` (float16 indexing) | See section 2.4 |
| Other | `greenjim301-ux`, `lyb020513` (CPU tomogram backends), `EnderMandS` (conda build), `Spercent521` and `NeuroNexa` (comments and docs), `CoolCode4` and `XinZhaoDC` (scenes), `kotarokanazawa` and `binbin2002` (ROS wrappers), `lljj123` (A* refactor), `overloadsc` (UE4 dataset pipeline, multi-route planner) | Not relevant to stairs in local planning |

## 2. Relevant fork changes (with permalinks)

### 2.1 tianchaowen/PCT_planner: PCT to EGO bridge with PCT-surface-relative filtering

- Commit `8c56322fa3fcc6e8a5316bd0dd23000dc30f1200` (2026-09-07, one commit, 31 files). GPL-2.0.
  The local planner is the author's fork of ZJU-FAST-Lab/ego-planner-swarm (`ros2_version`,
  GPL-3.0) with one commit, `12bb97b708fc327b07dbb8ebf4c1cbef5594adfc`. That commit adds
  `fsm/replan_from_odometry`, so every replan for a ground robot starts from measured odometry
  ([ego_replan_fsm.cpp diff](https://github.com/tianchaowen/ego-planner-swarm/commit/12bb97b708fc327b07dbb8ebf4c1cbef5594adfc)).
- **Mechanism** ([plan.py L514-L627](https://github.com/tianchaowen/PCT_planner/blob/8c56322fa3fcc6e8a5316bd0dd23000dc30f1200/planner/scripts/plan.py#L514-L627)):
  1. The live LiDAR cloud is transformed into `odom`.
  2. For each point, `terrain_heights_at()` looks up the PCT ground-elevation layer closest to the
     robot's expected floor, which is the robot z minus the sensor clearance (0.28 m)
     ([planner_wrapper.py L141-L174](https://github.com/tianchaowen/PCT_planner/blob/8c56322fa3fcc6e8a5316bd0dd23000dc30f1200/planner/scripts/planner_wrapper.py#L141-L174)).
  3. A point is kept as an obstacle only if it is at least `ego_traversable_height` (default
     0.23 m) above the PCT surface. Off-map points fall back to a robot-relative z window of
     [-0.18, 0.65] m (L569-L592).
  4. Cells with PCT cost at or above 50 on the current layer are added as synthetic static
     obstacles ([forbidden_xy_at_layer L176-L196](https://github.com/tianchaowen/PCT_planner/blob/8c56322fa3fcc6e8a5316bd0dd23000dc30f1200/planner/scripts/planner_wrapper.py#L176-L196); plan.py L596-L612).
  5. All retained points are **flattened onto one z plane** (L616). EGO runs as a 2.5D planner with
     `map_size_z: 0.32` ([ego_sim.yaml L21-L28](https://github.com/tianchaowen/PCT_planner/blob/8c56322fa3fcc6e8a5316bd0dd23000dc30f1200/planner/ego/ego_sim.yaml#L21-L28)).
  6. The EGO goal is a rolling target on the PCT path within a 3 m radius.
- In short, slopes and steps no higher than 0.23 m above the PCT surface are not obstacles. Taller
  objects and dynamic obstacles are. The README says this in Chinese; the sentence was paraphrased,
  not quoted.
- **Testing evidence:** MuJoCo Go2 simulation for the RC2026 competition. The README says the plain
  chain only publishes paths and not `/cmd_vel`. A separate script adds control. A real MID-360
  launch script exists, but there are no logs, metrics, or videos. UNVERIFIED on hardware.
- **Caveats for us:**
  - It depends on accurate localization against the PCT map.
  - The flattening throws away SCAN-style 3D body-window semantics.
  - The 0.23 m threshold is below a typical stair riser (about 0.15-0.18 m) plus noise, so it has
    little margin.
  - The nearest-layer lookup can pick the wrong floor near landings. UNVERIFIED.
  - GPL-2.0 plus GPL-3.0.

### 2.2 SC0K/PCT_planner: prior-map differencing into the tomogram

- Head `b766a4f43e7f5c6dbfb88c2dcfae2fc12986c5b7`, 78 commits, GPL-2.0. This is a coverage planner.
- New voxels are live LiDAR voxels that are absent from a dilated prior-map voxel grid
  ([lidar_mapping.py L106-L125](https://github.com/SC0K/PCT_planner/blob/b766a4f43e7f5c6dbfb88c2dcfae2fc12986c5b7/planner/scripts/lidar_mapping.py#L106-L125)).
  They are written back as cost barriers on tomogram layers whose ground lies within 0.5 m
  ([planner_wrapper_coveragev2.py L293-L316](https://github.com/SC0K/PCT_planner/blob/b766a4f43e7f5c6dbfb88c2dcfae2fc12986c5b7/planner/scripts/planner_wrapper_coveragev2.py#L293-L316)).
- Stairs that are already in the prior map therefore never become obstacles.
- Commit `1c89604f4b` ("optimised trajectory on stairts") only turns off quintic smoothing and
  lowers `step_max` from 0.6 to 0.4.
- Evidence: README and CSV profiles for the Gazebo building. No robot data.

### 2.3 81578823/PCT_planner (and non-fork 81578823/3D_navigation_PCTplanner, 71 stars)

- Real LimX TRON1 (bipedal wheeled robot) demo with a stair video (README, UNVERIFIED content).
  `local_planner*.py` is a pure-pursuit follower. `local_planner_new.py` sends a manual
  `request_stair_mode` to the base. `scene_stairs.py` sets `step_max = 0.17`. There is no live
  obstacle handling.

### 2.4 Global-planner stair fixes worth knowing

- **Height smoother flattens stairs.** Upstream `HeightSmoother` uses a fixed lower bound of -1.0
  and weighs smoothness 30 to reference 1
  ([height_smoother.cc L21-L33 @35cd73f](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/planner/lib/src/trajectory_optimization/height_smoother/height_smoother.cc#L21-L33)).
  zhongrenjiexing measured an optimized trajectory that stayed horizontal on a descending flight,
  with up to 3 m height error (`轨迹平滑问题分析.md` @`0a5cb4dd5fe2`). Their fix changes the lower
  bound to the coarse height minus 0.8 m in commit `ba89d0cbd6`. The same fork also fixes A* using
  invalid ground (`elev_g` NaN, set to -100) on some layers in `DecideLayer`.
  **This affects anything that uses PCT's path z as a body-height reference on stairs.**
- `hengzhiyou666@heng` `ce904a8e3b`: fits the ground plane and levels a tilted PCD before slicing.
  This fixes "flying" paths.
- `OpenMind` `35c3272d38`: upstream CUDA `getIndexLine` takes `float16` coordinates
  ([kernels.py L8-L14 @35cd73f](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/kernels.py#L8-L14)).
  The fork changes them to `float32`. The precision impact at large map coordinates has not been
  tested (UNVERIFIED).
- VectorRobotics `ca9dca31ed` ("parameter tuning to get it to work with stairs"): parameter changes
  only. `step_max` goes from 0.4 to 0.5, `resolution` to 0.1, the A* cost threshold to 25, and
  z now maps to a slice.

## 3. PCT-based integrations outside the fork network

Repositories found through `gh search repos "PCT planner"` and `gh search code` for
`TomogramPlanner`, `OfflineElePlanner`, `pct_path`, `PctTerrainMap`, `tomogram_surface`, and
`use_pct_planner`. Licenses come from the GitHub API unless stated otherwise.

### 3.1 AugetyVolta/M20-loc-nav: the most complete stair handling found (DEEP Robotics M20)

- Branch `feature/3d-body-plane-nav` @ `981579eeee3a56b705fe975cbd0aeeb150ab7461`, 47 commits
  (2026-05-21 to 2026-08-12). **No license file (all rights reserved).** Runs on a real M20 with an
  Orin and MID-360.
- **Pipeline:** Fast-LIO and Open3D localization, then a PCT 3D path, then pure pursuit to a
  subgoal, then an RL "PRIEST" local path, then Nav2 DWB, then `/NAV_CMD`
  ([README L1-L40](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/README.md)).
- **Stair mechanism 1, mode switching from the mapped route.** `terrain_state_estimator` labels
  stair-up and stair-down zones on the *static* PCT reference path using slope and dz thresholds
  (0.14/0.28 up, 0.18/0.35 down)
  ([terrain_state_estimator.py L149-L176](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/src/m20_fastlio_nav/m20_fastlio_nav/terrain_state_estimator.py#L149-L176)).
  `navigation_mode_manager` then switches the following
  ([navigation_mode_manager.py L107-L159](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/src/m20_fastlio_nav/m20_fastlio_nav/navigation_mode_manager.py#L107-L159)):
  - the costmap profile and the RL scan to their filtered versions 4 m before a stair;
  - the heading guard and the stair gait (sent over UDP) 3 m before;
  - PCT dynamic perception off within 5 m.
- **Stair mechanism 2, tomogram-surface scan filter** (`tomogram_filter_layer`).
  - An offline `.surface.pcd` is exported from the tomogram.
  - Live points within 0.20 m in XY and between -0.20 and +0.22 m in z of a surface sample with
    cost at most 45 are deleted.
  - Points in unmapped areas are kept.
  ([tomogram_filter_layer.cpp L442-L475](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/src/tomogram_filter_layer/src/tomogram_filter_layer.cpp#L442-L475);
  [README](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/src/tomogram_filter_layer/README.md)).
- **Stair mechanism 3, live 3D traversability layer.** This is the current default.
  - Ray-traced ground extraction per cell.
  - A cell is lethal only if the obstacle height above ground exceeds `step_height_threshold` AND
    the obstacle ratio passes its threshold
    ([traversability_layer.cpp L1478-L1495](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/src/traversability_layer/src/traversability_layer.cpp#L1478-L1495)).
  - M20 values: `step_height_threshold: 0.40`, `obstacle_ratio_threshold: 0.75`
    ([nav2_dwb_body_plane.yaml L93-L137](https://github.com/AugetyVolta/M20-loc-nav/blob/981579eeee3a56b705fe975cbd0aeeb150ab7461/src/m20_fastlio_nav/config/nav2_dwb_body_plane.yaml#L93-L137)).
- **Testing evidence:**
  - Commit messages and README notes from real runs, for example a rosbag named `stair1`.
  - Downstairs localization drift was fixed by using finer Fast-LIO filter sizes (0.2 and 0.3).
  - One unit test, `test_terrain_mode_logic.py`.
  - No success-rate table. Runs themselves are UNVERIFIED.
- **Reusable for us:** as a design reference only (no license). It is the closest match to our
  problem: same vendor family, a PCT route, mapped-stair mode switching, and a stair gait.

### 3.2 robwawa/motion_planner: PCT terrain map fed into SCAN (not a SCAN fork)

- `master` @ `dfeae40eb6c42b5110f736950cd6f6854a8cab38`, 15 commits (2026-08-11 to 2026-09-16),
  ROS Noetic.
- License: no repository license. `src/scan_planner/LICENSE` (upstream Apache-2.0) and GPL-2.0 PCT
  are vendored.
- Overlap note: it vendors SCAN, so the SCAN surveyor may also list it.
- **Mechanism 1.** PCT publishes a `PctTerrainMap` (traversability plus ground elevation per layer).
  In SCAN, `getPlanningOccupancy()` becomes: the inflated SCAN occupancy check, **AND** the PCT cell
  near the expected ground (body z minus `body_height`) is free with cost below the threshold, AND
  an optional footprint-support check
  ([grid_map.cpp L481-L584](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_env/src/grid_map.cpp#L481-L584);
  commit `fecf08b2c92420399d817859c6248926c512cdfd`).
  - Note: this *adds* rejections. It does **not** remove stair points from SCAN's live occupancy.
- **Mechanism 2.** The Z initial value of the local B-spline is sampled from the PCT path by XY
  progress (`reference_path_z.cpp`, commit `3071cf18b7`). This keeps SCAN's double-cylinder body
  window above the treads. `obstacles_inflation_z_up/down = 0`
  ([advanced_param.xml L86-L104](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_manage/launch/advanced_param.xml#L86-L104)).
- **Mechanism 3.** `dynamic_perception_3d` differences the live cloud against the static PCD with a
  KD-tree. This output feeds PCT global replanning only. SCAN still consumes raw
  `/livox/Pointcloud2`.
- **Testing evidence:**
  - Unit tests `pct_terrain_map_test.cpp` and `reference_path_z_test.cpp`.
  - A Gazebo A1 world with an RL stair policy.
  - The README warns that the kinematic simulator does not update z, so closed-loop runs there are
    not stair-dynamics evidence.
  - No run logs.

### 3.3 VectorRobotics / Dimensional stack: PCT plus CMU terrain_analysis and localPlanner

- **PCT fork.** `VectorRobotics/PCT_planner` @ `0cf4827eb0e3374345b836b74ad6ea7d913b0edf`, ROS 2
  Jazzy. It publishes `/way_point` from `/state_estimation` and reads `/explored_areas`, which are
  CMU autonomy-stack topics.
  - The fork **deleted `LICENSE` and `NOTICE`**, although its README still says GPLv2.
  - Upstream PR #13 from this fork was closed without merge.
- **Companion stack.** `VectorRobotics/vector_navigation_stack` returns **HTTP 451, DMCA-blocked
  since 2026-05-22**. UNVERIFIED.
- **Readable copy.** `fukexue/ros-navigation` @ `5a39a297039819201aa7a02ec66b2cc2e9ac5b48`, branch
  `fastlio2`. It has no license and its history includes `alexlin2` commits such as "updated
  pct_planner tested multistory nav". Its README header reads "Dimensional Ground Autonomy Stack".
  Also `jeff-hykin/ros-navigation-autonomy-stack` (no license).
- **Mechanism (CMU base autonomy).**
  - `terrainAnalysis` estimates local ground per planar voxel from a low z quantile (0.25). It
    stores each point's height above that ground in `intensity`
    ([terrainAnalysis.cpp L581-L606](https://github.com/fukexue/ros-navigation/blob/5a39a297039819201aa7a02ec66b2cc2e9ac5b48/src/base_autonomy/terrain_analysis/src/terrainAnalysis.cpp#L581-L606)).
  - `localPlanner` treats only `intensity > obstacleHeightThre` as an obstacle
    ([localPlanner.cpp L227](https://github.com/fukexue/ros-navigation/blob/5a39a297039819201aa7a02ec66b2cc2e9ac5b48/src/base_autonomy/local_planner/src/localPlanner.cpp#L227)).
  - The stairs profile `unitree_go2_stairs.yaml` raises `obstacleHeightThre` from 0.1 to 0.3 and
    changes path-scale and range settings
    ([L33](https://github.com/fukexue/ros-navigation/blob/5a39a297039819201aa7a02ec66b2cc2e9ac5b48/src/base_autonomy/local_planner/config/unitree/unitree_go2_stairs.yaml#L33)).
- **Testing evidence:** commit messages only ("tested multistory nav"). The README's real-robot
  command uses the stairs profile. There is no data.
- **License:** CMU `terrain_analysis/package.xml` declares BSD, but there is no repository LICENSE
  file (`jizhang-cmu/autonomy_stack_go2`). The Dimensional copies have no license, plus the DMCA
  history. Reuse ideas, not this code.
- **Maintainer recommendation.** PCT maintainer gogojjh pointed to CMU's `pathFollower.cpp` in issue
  #17 (section 4).

### 3.4 Robot-Nav/legbot_3D_Nav: PCT plus selectable EGO or SCAN on Gazebo stairs

- `main` @ `f60606a4903bad58fca813f76072f9940a284d1d`, Apache-2.0 (vendored PCT stays GPL-2.0),
  56 stars, ROS Noetic, Unitree A1 with an RL policy.
- Copies: `atom-1024/legbot-3d-navi` @ `c68b8a1a` (one commit, same tree) and `LiiiiPeggy/3DNav`
  @ `7e975339` (aggregates this plus SCAN-Planner-Ros2).
- **Mechanism:**
  - **No ground or step removal.**
  - SCAN uses its double cylinder (radius 0.15 m, z inflation 0.03 m) on the raw
    `/livox/Pointcloud2`. The trajectory z follows the PCT reference, with
    `z_projection_weight 8.0` and alignment to odometry
    ([scan.launch L30-L67](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/src/legbot_bringup/launch/scan.launch#L30-L67)).
  - The modified EGO only clears an ellipsoid around the body (0.25/0.25/0.15 m) to remove
    self-returns
    ([grid_map.cpp L885-L912](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/src/planner/plan_env/src/grid_map.cpp#L885-L912)).
- **Testing evidence:** a self-reported Gazebo table in which both planners succeed on the
  `Building.world` route, with final z error of about 0.38 m
  ([README L37-L52](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/README.md#L37-L52)).
  There are videos but no raw logs. The GitHub repository description says real-robot validation
  is in progress.

### 3.5 jhr419/3d-nav: EGO local planner with ground removal against the path z

- `master` @ `97935334862ea8796843d4650030a506509a69d8`, no license, ROS 2 Humble, Go2.
- `ego_local_planner` drops points less than `ground_z_threshold` (0.18 m) above a reference z. The
  reference is interpolated from the global path at the point's XY
  ([ego_local_planner_node.cpp L1632-L1639](https://github.com/jhr419/3d-nav/blob/97935334862ea8796843d4650030a506509a69d8/src/local_planning/ego_local_planner/src/ego_local_planner_node.cpp#L1632-L1639);
  [ego_local_planner.yaml L42-L45](https://github.com/jhr419/3d-nav/blob/97935334862ea8796843d4650030a506509a69d8/src/local_planning/ego_local_planner/config/ego_local_planner.yaml#L42-L45)).
- Whether that z means the ground or the base height is **UNVERIFIED**; the fallback is base z.
- No stair test evidence. One commit says real-robot testing is being prepared.

### 3.6 Others checked (global-only, or no stair logic in local planning)

| Repo @ SHA | License | What it is |
| --- | --- | --- |
| ypat999/3d_dog_navi_ros2 @ `415f7481` | MIT | `pct_path_adapter` splits the PCT path at step edges (>0.15 m), scales speed to 0.3 in step zones, and projects to 2D for Nav2 MPPI. No terrain-aware costmap found. Gazebo |
| laohao78/StrataPlanner @ `1e7366f2` | none | PCT plus SCAN mode 3 bridge (`plan_bringup`). No stair filtering. Open-loop controller |
| sibeanly/pct_planner @ `90ce0336` | GPL-2.0 | ROS 2 Jazzy PCT that remaps `/pct_path` to SCAN `initial_path` |
| lovelyyoshino/3D-Nav-ROS2, LiHao-Creater/3d-nav, lxs5127/3d-navi | AFL-3.0 | PCT plus EGO plus unitree_guide Gazebo templates. EGO grid map unchanged (not read in depth) |
| enffft/3d-nav @ `0337ace4` | Apache-2.0 | PCT as a `move_base` global plugin plus 2D DWA. README says DWA is not 3D. Plans for legged_perceptive (UNVERIFIED) |
| HEU-ROBOCON/HEU-Robocon @ `0fe083b2`, Cats-eat-peppercorns/HEU_ROBOCON_2026_CV | none | PCT plus ego-planner-swarm plus terrain_analysis in a RoboMaster/Robocon tree. Their `plan.py` copies lack tianchaowen's EGO bridge |
| Kitjesen/MapPilot @ `61a518f8` | none | Large stack with a ROS-free SCAN port pinned to `348e8a59`. Its README says the SCAN core adds no custom slope logic. PCT is only a legacy backend |
| Forrest-Z/pct_nav_stack @ `d99e10dc` | none | PCT, a pure tracker, and a forward safety stop. Indoor, no stairs |
| 1392559136a-jpg/tron2-navigation-pct-gpl @ `3b029e5a` | GPL-2.0 | LimX TRON2 PCT derivative (from RC2026_Map_Planner), global only. Companion `limxdynamics/tron2-navigation-ros2` returns 404 (UNVERIFIED) |
| x2333iaohei/cmu-tare-far-pct-planners, AugetyVolta/pct_planner_ros2, rvxfahim, xiaoqi371317, Empty0909, qza36/pct_planner_ros2_cpu, sjtumrgx, jie0110, heyi30, CuteCar384 | mixed | Archives or ROS 2 or CPU ports of the global planner only |
| dimensionalOS/dimos @ `26665a90` | Apache-2.0 | `nav_3d/mls_planner` (Rust MLS planner) with stair evaluation bags. **Not PCT**, noted as a lead only |

## 4. Upstream issues and PRs (19 total: 17 issues, 2 PRs, all read)

- **#17 (closed 2026-03-09): which local planner did the stair and obstacle demo use?**
  Collaborator gogojjh (a PCT co-author) answered in Chinese. Paraphrase:
  - The demo probably used no local planner. With LiDAR localization, the nearest global waypoint
    served as the local target.
  - For tracking, see CMU `autonomy_stack_go2` `pathFollower.cpp`.
  - PCT is global only. Local avoidance needs an added local planner; see their SanD-Planner,
    arXiv 2602.00923.
  - I checked arXiv metadata: SanD-Planner is a depth-image diffusion local planner, not
    stair-specific. Its code repo `WangJinCheng1998/sandplanner` (Apache-2.0) was not read.
- **#15 (open): stairs are not connected in tomograms built from FAST-LIO maps.** The maintainer says
  the map must be dense and accurate and suggests changing the resolution. Point-cloud noise is
  removed manually in CloudCompare. A later user (2026-05-31) reports the same with FAST-LIO in
  simulation. No fix.
- **#14 (open): path height stuck at -99.** Holes in the point cloud; fixed by a denser map
  (user-confirmed).
- **#11 (closed, no reply): downstairs goal lands on the wrong slice.**
- **#12 (open): "goal node is not reachable".** Maintainer: check whether the goal is inside an
  obstacle.
- **#3:** traversability parameter meanings; the owner answered only the runtime question.
  **#19:** error in the paper's pseudocode (ground and ceiling update). **#1:** forest parameters;
  the owner says the method is sensitive to noise and holes in real point clouds.
- **PR #6** (Eigen::Ref segfault fix) was closed unmerged. **PR #13** (VectorRobotics Jazzy
  integration, 5054 files) was closed unmerged. **#7** ROS 2 port request: no maintainer reply.
- **No issue or PR covers** dynamic or unmapped obstacles on stairs, pairing a local map on stairs,
  or real-robot stair results.

## 5. Step 4

Not run. Steps 1-3 found enough PCT-based material.

## 6. UNVERIFIED items and gaps

- Hardware stair success for any repo in this file. No repo publishes raw logs or a success-rate
  table from a real robot on stairs. M20-loc-nav has the strongest indirect signs.
- Contents of `VectorRobotics/vector_navigation_stack` (DMCA) and `limxdynamics/tron2-navigation-ros2`
  (404). Also `1y7rzc35` forks (404).
- Correctness of tianchaowen's nearest-layer surface lookup at landings, and the z semantics of
  jhr419's path-referenced ground filter.
- Videos in README files (legbot, 81578823, tianchaowen) were not watched.
- The effect of upstream float16 indexing in `kernels.py`.
