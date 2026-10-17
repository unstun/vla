---
origin: ai+web
reviewed: false
date: 2026-09-17
stage: planning
status: surveyed
scope: stair/terrain improvements to SCAN in its GitHub lineage (forks, issues/PRs, downstream repos, upstream history)
---

# SCAN stair lineage survey (A)

Label: **surveyed** only. Everything below was read through `gh api` at the
commit SHAs given. Nothing was cloned, built or run. No claim here is
reproduced, integrated or validated. "Evidence of testing" means what the
authors committed, such as unit tests, READMEs or commit messages. None of it
was checked by us.

Query window: GitHub state on 2026-09-17 (Asia/Shanghai evening).

## 0. Reference points

| Item | Value |
|---|---|
| Upstream | `wuyi2121/SCAN-Planner`, Apache-2.0, default `main` @ `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` (last push 2026-07-29). Other branches: `ros2-community` @ `d0b921c9b05a6d291d144d60882b2e0e88d2c0e0` (2026-07-13) and `gh_pages` |
| Orphaned upstream commit | `529f0ba43b7e79e6fff85a5777c786237f0f8f33`, "fix: his_path + mode3 replan", by hanzheng, 2026-07-16. It was replaced on `main` by `b654557`, but several forks still carry it. We treat it as upstream work, not fork work |
| Our executed copy | `yagami-light7/PCT-SCAN-ROS2` @ `1cf45a1c12ca785ce533293302be09d51daf0ccb`. It is built on `xiaoqi371317/SCAN-Planner-Ros2` main @ `103bce48bd` plus four commits dated 2026-08-08 |
| Local vendored path | `references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base/src` |

## 1. Fork census

### 1a. `wuyi2121/SCAN-Planner`

- `forks_count` is 58. That is 57 direct forks, which we enumerated by
  paginating `repos/wuyi2121/SCAN-Planner/forks`, plus one fork of a fork:
  `lifliu/SCAN-Planner`, forked from `YanYaoyuan/Scan_Planner`.
- **Pushed after creation** (`pushed_at > created_at`): **17** (16 direct plus lifliu).
- **Ahead of upstream**, meaning at least one branch has commits that are in
  neither `main` nor `ros2-community`: **11 repositories, 20 branches**.
  - We compared every branch with
    `compare/main...owner:branch`. Where the two had no common ancestor, we
    used `compare/ros2-community...owner:branch` instead.
  - Six forks were pushed but hold only upstream SHAs: VisionTrekker,
    Longxiaoze, caoli-CHN, chengwei920412, ctangaf and OxygenLost. ctangaf and
    OxygenLost sit on the orphaned upstream commit `529f0ba`.
- The other 40 forks were never pushed and are only counted here.

The forks that are ahead, with our classification:

| Fork : branch (head) | Base | Ahead | What it changes | Stair/terrain? |
|---|---|---|---|---|
| **Pumpkin003 : main** (`11aa945f7f`) | main | 1 | Go2/XT16 real-robot adaptation: TF frame alignment, extrinsics as parameters, **`fsm/planning_z_offset` (+0.10 m) justified as a stair heuristic** | **Yes (parameter heuristic)**. See §2.1 |
| **Eas1L : 3d_real_dog** (`e2b49a208f`) | main | 27 | Stale and transient obstacle decay; footprint clearing and self-filter in the body frame; near-ground filter for a LiDAR artefact; NavigateToPose action; **3D manual goal height, allowing goals below the robot** | **Partial**. See §2.2 |
| Eas1L : real_dog (`3d1e0b3c8f`) | main | 10 | 2D subset of the above | Partial (footprint clear only) |
| Eas1L : travexplorer-real (`31745ff851`) | main | 1 | Imported "TravExplorer real-robot planner state": B-spline time scaling, Go2 cmd_vel nodes, resolution 0.1, `z_down` 0.4 | No |
| greenjim301-ux : main (`14a9ccd433`) | main | 44 | Tools, far_planner bridge, reboundReplan result codes, fix for a single-segment global trajectory bulge, waypoint skipping | **Workaround only**. See §2.3 |
| YanYaoyuan : main / feature/bgy-planner-safety-foundation / feat/omni-tf-contract / codex/integrate-dog3 | ros2-community | 52 / 51 / 35 / 21 | ZsiBot deployment, route-progress tracker, trajectory acceptance validator, planning deadlines, CI; **docs contain a stair/traversability TODO** | **Docs only**. See §2.4 |
| lifliu : ros2-community / feat/follow-route-action / fix/follow-route-ci / codex/integrate-dog3 | ros2-community | 22–26 | Same lineage as YanYaoyuan plus a FollowRoute action server | No |
| hengzhiyou666 : heng_ros2 (`acca120aa5`) | ros2-community | 1 | Large refactor: virtual corridor, diagonal corner check in the 2.5D A* (z still interpolated), **ground clipping at a fixed `ground_height`** | No. The fixed-ground assumption works against stairs |
| johyunyoung : feat/ftr-robot-adaptation (`b1f963c8a2`) | ros2-community | 1 | Flipper-tracked robot with Mid360; start and goal z offset by `body_height_` because diff-drive odometry reports z=0 | No (planar adaptation) |
| johyunyoung : port-mode3-collision-fix (`83f35f6ac7`) | ros2-community | 2 | Ports upstream `b654557` to ROS 2 and adds a Jazzy build. This is open PR #11 | No new work; ports upstream (§4) |
| wangyp501 : g1-main (`02e900f6fa`) | main (diverged) | 3 | Stale-obstacle expiry for a G1 humanoid, plus the orphaned `529f0ba` | No |
| Lurvelly : nav (`fa951987d6`) | ros2-community | 1 | Bilingual comments and waypoint progress | No |
| luo-cong-jjy : ros2-community (`7c2c7cf433`) | ros2-community | 2 | Foxy compatibility | No |
| GeeniTiming : codex/pct-scan-integration (`26df52dd54`) | ros2-community | 1 | Adds COLCON_IGNORE only | No |

### 1b. `yagami-light7/PCT-SCAN-ROS2`

- 2 forks. **1** was pushed after creation. **1** is ahead of upstream.
- `JINGHANW/PCT-SCAN-ROS2` was never pushed and is counted only.
- `GeeniTiming/PCT-SCAN-ROS2` has two branches ahead of upstream:
  - `codex/foxy-rk3588` (`a0080a1023`), 9 commits ahead.
  - `migration/m20-field-20260910` (`5cb062d250`), 10 commits ahead.
- What these branches change:
  - Ports to Foxy/ARM64, adds a CPU tomography backend, adds an odometry-driven
    PCT start, and adds a planner config for the M20 robot with the Lightning
    LIO.
  - The SCAN-side edits are Foxy API changes and topic parameters.
    `grid_map.cpp` and `scan_replan_fsm.cpp` show about 1000 changed lines, but
    this is mostly line-ending churn.
- On stairs, the only changes are documentation:
  - The docs tell the reader to calibrate PCT `step_max` and `slope_max` for
    their robot and stairs.
  - The README says `odom_start_z_offset` defaults to 0.0 and relies on
    tomogram snapping, and that it must be measured before real stair tests.
- **No SCAN stair change.**

## 2. Stair- or terrain-relevant changes inside SCAN forks

### 2.1 Pumpkin003: planning z offset (stair heuristic)

- **Code.** The `fsm/planning_z_offset` parameter is read at
  <https://github.com/Pumpkin003/SCAN-Planner/blob/11aa945f7f9e89c1ce61b5e6fe44d6e430782808/src/planner/plan_manage/src/scan_replan_fsm.cpp#L56>.
  It is added to the odometry z at
  [#L531](https://github.com/Pumpkin003/SCAN-Planner/blob/11aa945f7f9e89c1ce61b5e6fe44d6e430782808/src/planner/plan_manage/src/scan_replan_fsm.cpp#L531).
- **Config.** The Go2 launch sets the offset to 0.10 and feeds the same value
  into `body_height`:
  <https://github.com/Pumpkin003/SCAN-Planner/blob/11aa945f7f9e89c1ce61b5e6fe44d6e430782808/src/planner/plan_manage/launch/run_Go2.launch#L58-L61>
  and [#L107-L108](https://github.com/Pumpkin003/SCAN-Planner/blob/11aa945f7f9e89c1ce61b5e6fe44d6e430782808/src/planner/plan_manage/launch/run_Go2.launch#L107-L108).
- **Rationale given in the launch comment.** The heuristic is copied from a
  "3d-navi/EGO-Planner" setup. It raises the planning state by 0.1 m on stairs
  so that step risers and the reference point do not fall into the same
  occupancy layer.
- **Evidence.** The commit message is "some commit". There are no tests and no
  logs.
- **Reuse value.** Low. It is the same knob the maintainer recommends in #5,
  raising the body or path z, applied through odometry.

### 2.2 Eas1L 3d_real_dog: body-frame footprint clearing and 3D goal heights

- **Footprint clearing.** Stale occupancy inside the robot's own
  double-cylinder footprint is cleared, using a z interval taken in the live
  body frame. A code comment says this lets stairs and kerbs follow odometry z
  instead of a fixed ground height:
  <https://github.com/Eas1L/SCAN-Planner/blob/e2b49a208feed007baa9cd67bdf54bc8668d7342/src/planner/plan_env/src/grid_map.cpp#L570-L637>.
- **Near-ground filter.** Removes a near-field sheet produced by the Odin
  LiDAR. It is a sensor artefact filter, not terrain analysis:
  [#L1303-L1324](https://github.com/Eas1L/SCAN-Planner/blob/e2b49a208feed007baa9cd67bdf54bc8668d7342/src/planner/plan_env/src/grid_map.cpp#L1303-L1324).
- **3D goal heights.** `fsm/manual_goal_use_requested_height` (default off)
  uses the requested goal z. It removes the sentinel that dropped goals below
  -0.1 m, so goals on a lower floor are accepted:
  <https://github.com/Eas1L/SCAN-Planner/blob/e2b49a208feed007baa9cd67bdf54bc8668d7342/src/planner/plan_manage/src/scan_replan_fsm.cpp#L67>
  and [#L388-L399](https://github.com/Eas1L/SCAN-Planner/blob/e2b49a208feed007baa9cd67bdf54bc8668d7342/src/planner/plan_manage/src/scan_replan_fsm.cpp#L388-L399).
- **Evidence.**
  - `PLAN.md` says a full Orin rebuild passed.
  - A node with motion control disconnected accepted goals ±0.30 m from the
    body and produced 65-point trajectories.
  - It also says collision and control logic are otherwise unchanged.
  - There is no stair traversal run.
- **Reuse value.** Only the footprint-clearing idea, and the goal-drop fix for
  mode 1.

### 2.3 greenjim301-ux: documents the downstairs goal-drop bug (workaround)

- **What it documents.** `tools/far_planner_bridge.py` notes that mode 1 drops
  goals with z < -0.1. far_planner waypoints turn negative when descending
  below the origin plane, so those goals are silently discarded.
- **Workaround.** The bridge always sends a fixed `goal_z` (0.0):
  <https://github.com/greenjim301-ux/SCAN-Planner/blob/14a9ccd433beb2ccbca356e3a05d91140c1dbdce/tools/far_planner_bridge.py#L20-L24>
  and [#L115-L116](https://github.com/greenjim301-ux/SCAN-Planner/blob/14a9ccd433beb2ccbca356e3a05d91140c1dbdce/tools/far_planner_bridge.py#L115-L116).
- **Where the sentinel lives upstream.**
  <https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp#L168>.
- **Our copy.** The sentinel is still present at line 156 of
  `references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base/src/plan_manage/src/scan_replan_fsm.cpp`,
  inside `waypointCallback`. It affects mode 1 only, not mode 3 `/initial_path`.

### 2.4 YanYaoyuan: stair/traversability is a TODO, not code

- **Roadmap document.** `doc/Omni_SCAN-Planner_BGY算法升级TODO.md` at
  `26d021c6112c858f43bd60ef31bb9940d289670f` plans the following. All of it is
  unimplemented:
  - a traversability layer with slope, step height and support surface (L884-L898);
  - adding traversability to the A* cost;
  - checking stairs along the B-spline;
  - stair and slope test scenes (L898).
- **Analysis document.** `doc/SCAN-Planner算法与ROS2代码解析.md` makes three
  points, which agree with our own reading:
  - SCAN does not check foothold feasibility.
  - SCAN relies on the locomotion controller to climb stairs.
  - roll and pitch are outside the collision model.
- **Code.** A search of the fork's no-patch planner files found no terrain code
  (§6).

## 3. Downstream (non-fork) repos with stair or terrain work on SCAN

### Search method

- Repository search terms: `gh search repos` for "SCAN-Planner",
  "scan_planner", "SCAN planner", "PCT SCAN", "scan-planner ros2" and
  "TravExplorer".
- Code search terms: `gh search code` for `double_cylinder_radius`,
  `scan_replan_fsm`, `SCANReplanFSM`, `SCANPlannerManager`, "SCAN-Planner"
  and "2606.19555".
- This produced 35 candidate repos.
- **Files checked in each repo.** At the default-branch head we fetched these
  files (under each repo's own paths):
  - `grid_map.cpp`
  - `scan_replan_fsm.cpp`
  - `planner_manager.cpp`
  - `dyn_a_star.cpp`
  - `bspline_optimizer.cpp`
  - the planner yaml or `advanced_param.xml`
- **Keyword pass.** We searched those files, the repo file paths, and commit
  messages on all branches for stair/terrain keywords in English and Chinese.
- **Forks of downstream repos.** We also checked forks of the main downstream
  repos. Among those that were pushed:
  - `YiFanWei1/SCAN-Planner-Ros2` has relevant commits (item 3.2).
  - `lorenzo0720/legbot_3D_Nav` has relevant commits (item 3.4).
  - `bigblack024/MapPilot` was pushed but not inspected (UNVERIFIED).

### 3.1 robwawa/motion_planner: terrain-aware SCAN with PCT traversability (strongest match)

- **Repo.** <https://github.com/robwawa/motion_planner>, head
  `dfeae40eb6c42b5110f736950cd6f6854a8cab38`, ROS 1 Noetic, 0 stars, 0 forks.
- **License.**
  - GitHub reports no license, and there is no root LICENSE file.
  - `src/scan_planner/LICENSE` is the Apache-2.0 text inherited from SCAN.
  - The author's new files carry no license header.
  - So **the reuse terms for the new code are UNVERIFIED** and need the
    author's clarification.
- **Key commits.**
  - `256a9c3c63`, 2026-08-13: mode 3 seeds the B-spline z from the trajectory
    instead of a linear ramp.
  - `3126b02728` and `fecf08b2c9`, 2026-08-21: adds a PctTerrainMap message and
    folds PCT traversability into SCAN collision checks.
  - `3071cf18b7`, 2026-08-25: samples reference z in route order and adds
    projection and diagnostics.
- **What it adds, in SCAN `plan_env/src/grid_map.cpp` @ `dfeae40`.**
  - **PCT traversability in the collision query.** `getPlanningOccupancy`
    returns an obstacle when PCT reports that no layer at that x,y is below the
    cost threshold within `max_height_error` of the expected ground height,
    which is body z minus `body_height`.
    - Code: [#L448-L584](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_env/src/grid_map.cpp#L448-L584).
    - Layer selection: `PctTerrainMap::queryTraversableLayer`,
      [pct_terrain_map.cpp#L65-L107](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_env/src/pct_terrain_map.cpp#L65-L107).
    - Missing or unknown PCT data falls back to plain SCAN occupancy.
    - The check is used by the B-spline optimizer and by the FSM collision checks.
  - **SCAN-side support-surface check (optional, default off).**
    - For each footprint sample, the code finds the highest raw occupied voxel
      within `[expected_ground - max_drop, expected_ground + tol_up]`.
    - It rejects the pose when a sample has no support.
    - It also rejects the pose when the spread between the highest and lowest
      support heights exceeds `support_max_height_difference`.
    - Code: [#L324-L446](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_env/src/grid_map.cpp#L324-L446).
  - **Reference-path z profile in mode 3.**
    - The initial control points take z from the PCT route by XY progress,
      instead of a straight start-to-target z ramp.
    - The A* inside rebound still uses the linear z plane (`dyn_a_star.cpp` L168/L235).
    - Profile code: [reference_path_z.h](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_manage/include/plan_manage/reference_path_z.h)
      and [planner_manager.cpp#L73-L90](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_manage/src/planner_manager.cpp#L73-L90).
    - Applied at [#L307-L311](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_manage/src/planner_manager.cpp#L307-L311).
    - Called from [scan_replan_fsm.cpp#L1321-L1342](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_manage/src/scan_replan_fsm.cpp#L1321-L1342).
  - **Defaults.** Set in
    [advanced_param.xml#L20-L23 and #L86-L104](https://github.com/robwawa/motion_planner/blob/dfeae40eb6c42b5110f736950cd6f6854a8cab38/src/scan_planner/planner/plan_manage/launch/advanced_param.xml#L86-L104):
    - `use_pct_traversability=true` and `use_scan_support=false`;
    - `obstacles_inflation_z_up/down = 0.0`;
    - `cost_threshold 60` and `max_height_error 0.40`;
    - support thresholds of 0.15, 0.15 and 0.35.
  - **A design consequence.** Terrain feasibility comes from the **prebuilt PCT
    tomogram**, not live sensing. With vertical inflation at zero, SCAN's live
    point cloud only blocks at the body-centre slice.
- **Evidence of testing.**
  - gtest suites exist: `pct_terrain_map_test.cpp` (3 tests) and
    `reference_path_z_test.cpp` (11 tests, covering overlapping floors and
    self-intersections).
  - There is a Gazebo A1 setup with `stairs.xacro` and a stair RL policy
    (`policy_act_inference_stair.pt`).
  - The README warns that the kinematic closed-loop simulator does not update z
    from terrain. It says that path must not be used to validate stairs
    (README L141-L143).
  - **No logged stair runs or metrics.**
- **Similarity to our stack.** This is the closest to our PCT→SCAN stack,
  since it uses PCT tomogram layers in SCAN mode 3. It is ROS 1, and its
  licence status is unclear.

### 3.2 YiFanWei1/SCAN-Planner-Ros2 `dev`: vertical-band A* and terrain segmentation of the route

- **Repo.** <https://github.com/YiFanWei1/SCAN-Planner-Ros2>, a fork of
  xiaoqi371317/SCAN-Planner-Ros2, which is the same base as PCT-SCAN-ROS2.
- **License.** Apache-2.0.
- **Head.** `dev` @ `ed97b9337726cb6efcdf7fe7a5c7cff591e995d8`, pushed
  2026-08-14, real Go2 with Livox.
- **Vertical-band A\*** (`db3cddd0ff`).
  - Each A* expansion may use z within ±3 voxels of the interpolated reference
    plane, with at most one voxel of z change per edge.
  - The comment says stair surfaces are not the straight start-to-end z plane.
  - Code: [dyn_a_star.cpp#L292-L318](https://github.com/YiFanWei1/SCAN-Planner-Ros2/blob/ed97b9337726cb6efcdf7fe7a5c7cff591e995d8/src/planner/path_searching/src/dyn_a_star.cpp#L292-L318).
  - This is a **direct, small change to SCAN's linear-z A\*.**
- **`terrain_path_segmenter` package.**
  - `segment_path` splits the reference path into overlapping segments whose z
    is near-linear (`max_linear_z_error` 0.04 m), so each SCAN local problem
    matches its linear-z assumption.
  - `project_onto_path` uses a z weight to tell overlapping floors apart.
  - Code: [segmentation.py#L70, #L214](https://github.com/YiFanWei1/SCAN-Planner-Ros2/blob/ed97b9337726cb6efcdf7fe7a5c7cff591e995d8/src/terrain_path_segmenter/terrain_path_segmenter/segmentation.py#L214).
  - Supporting commits: `2b93258d39` fixes rolling terrain path progress, and
    `f9183a9285` projects the planning start onto the raised path.
- **Evidence of testing.**
  - Python and C++ unit tests exist (`test_segmentation.py`,
    `test_progress.py`, `test_reference_path_utils.cpp`).
  - `gazebo_stairs_slopes_demo.launch.py` builds two staircases and ramps.
  - Commit history shows real Go2 tuning.
  - **No committed stair results.** A commit named "test 0.4 meter reference
    path height" is not a results artefact.

### 3.3 wangxx771/SCAN-Planner-ROS2-Humble: mode 3 changes for stairs

- **Repo.** <https://github.com/wangxx771/SCAN-Planner-ROS2-Humble>, head
  `43237df8c3979922b8f9905f219f3641f99ab587`, 2026-07-25, one commit on top of
  upstream `ros2-community`.
- **License.** Apache-2.0. The bundled OctoMap has its own licence.
- **Commit.** "Integrate OctoPlanner3D and improve mode 3 stair navigation".
- **Full 3D A\*.** Expansion over dz ∈ {-1, 0, 1} with a supercover check on
  diagonals:
  [dyn_a_star.cpp#L280-L318](https://github.com/wangxx771/SCAN-Planner-ROS2-Humble/blob/43237df8c3979922b8f9905f219f3641f99ab587/src/planner/path_searching/src/dyn_a_star.cpp#L280-L318).
  Endpoints are no longer pushed along the chord, per the stair/landing
  comment at
  [#L157-L165](https://github.com/wangxx771/SCAN-Planner-ROS2-Humble/blob/43237df8c3979922b8f9905f219f3641f99ab587/src/planner/path_searching/src/dyn_a_star.cpp#L157-L165).
- **Local initialisation that keeps the reference.** It samples the global
  reference instead of fitting one polynomial. The comment says a single
  polynomial would turn a stepped height profile into a straight z ramp:
  [planner_manager.cpp#L136-L143](https://github.com/wangxx771/SCAN-Planner-ROS2-Humble/blob/43237df8c3979922b8f9905f219f3641f99ab587/src/planner/plan_manage/src/planner_manager.cpp#L136-L143).
- **Piecewise-linear global reference** instead of a single minimum-snap fit:
  [#L536-L542](https://github.com/wangxx771/SCAN-Planner-ROS2-Humble/blob/43237df8c3979922b8f9905f219f3641f99ab587/src/planner/plan_manage/src/planner_manager.cpp#L536-L542).
- **Path handling.**
  - Collinear thinning keeps every 3D direction change:
    [scan_replan_fsm.cpp#L404-L411](https://github.com/wangxx771/SCAN-Planner-ROS2-Humble/blob/43237df8c3979922b8f9905f219f3641f99ab587/src/planner/plan_manage/src/scan_replan_fsm.cpp#L404-L411).
  - Mode 3 does not regenerate the global trajectory from odometry:
    [#L938-L944](https://github.com/wangxx771/SCAN-Planner-ROS2-Humble/blob/43237df8c3979922b8f9905f219f3641f99ab587/src/planner/plan_manage/src/scan_replan_fsm.cpp#L938-L944).
- **New parameters** `fsm.reference_path_z_offset`, `reference_path_min_spacing`
  and `reference_path_horizon`, in `planner.yaml` L14-L20.
- **Other changes listed in the README** (L40-L77): forward-window projection,
  so the robot does not jump to another floor with an overlapping XY
  projection, and a fallback to a short safe segment.
- **Evidence of testing.**
  - gtest (`test_dyn_a_star.cpp`, `test_uniform_bspline.cpp`).
  - A Gazebo Fortress Go2 setup.
  - The README's stair checklist (L706+) includes checking whether SCAN
    classifies stair treads as obstacles.
  - **No results committed.**
- **Overlap with our copy.** Parts of this overlap with what PCT-SCAN-ROS2
  already has: piecewise-linear reference and RDP simplification. The full 3D
  A* is new.

### 3.4 Robot-Nav/legbot_3D_Nav: reference z alignment and replanning from odometry (+ fork fix)

- **Repo.** <https://github.com/Robot-Nav/legbot_3D_Nav>, head
  `f60606a4903bad58fca813f76072f9940a284d1d`, 56 stars. The stack is ROS 1,
  Gazebo, a Unitree A1, PCT with EGO or SCAN, and an RL controller.
- **License.** Apache-2.0.
- **Copies.** `atom-1024/legbot-3d-navi` (Apache-2.0) and
  `LiiiiPeggy/3DNav` (GPL-3.0) contain the same SCAN files.
- **Reference z aligned to odometry.** The constant offset between PCT
  tomogram z and odometry z is calibrated once at the route start (limit
  0.8 m). The comment says the uncorrected offset pushed the local target
  behind the robot on stairs:
  [scan_replan_fsm.cpp#L411-L431](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/src/SCAN-Planner/src/planner/plan_manage/src/scan_replan_fsm.cpp#L411-L431).
  Parameters are at L57-L58.
- **Corner-preserving thinning** at 20°:
  [#L440-L457](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/src/SCAN-Planner/src/planner/plan_manage/src/scan_replan_fsm.cpp#L440-L457).
- **Mode 3 replans from measured odometry.** The comment says replanning from
  the old planned state let the trajectory detach from the robot on stairs:
  [#L875-L880](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/src/SCAN-Planner/src/planner/plan_manage/src/scan_replan_fsm.cpp#L875-L880).
- **Piecewise-linear reference.** A comment says it keeps PCT corners and stair
  turns:
  [planner_manager.cpp#L360](https://github.com/Robot-Nav/legbot_3D_Nav/blob/f60606a4903bad58fca813f76072f9940a284d1d/src/SCAN-Planner/src/planner/plan_manage/src/planner_manager.cpp#L360).
- **Evidence of testing.** README L37-L53 reports one Gazebo "Building" route
  in which both EGO and SCAN succeeded: SCAN took 187 s over 79.3 m with a
  final Z error of 0.379 m. This is a **single self-reported run**, and no logs
  are committed.
- **Fork `lorenzo0720/legbot_3D_Nav`**, commit `df2eb4de4acafd2ecdc6d7903e1141d86a6079db`
  ("Prevent SCAN stair replanning stalls", 2026-08-24):
  - Guards resampling of the previous trajectory against an empty or
    degenerate arc, falling back to a polynomial initialisation.
  - Lowers `z_projection_weight` from 8.0 to 1.0. The launch comment says a
    transient stair-height odometry error pinned progress at the stair entry.
  - Apache-2.0. No tests.

### 3.5 TheChanYe/SCAN_Planner_dmq `compy_work`: stair-up mode with support clearance

- **Repo.** <https://github.com/TheChanYe/SCAN_Planner_dmq>, branch
  `compy_work` @ `58c4c39dba4708f28b732296fbf2f689d1ac1d6d`.
- **License.** Apache-2.0.
- **Key commits.**
  - `c428f6e10f` (2026-08-10), message: basically climbs stairs.
  - `58dbd2f874` (2026-08-10), message: stair obstacle avoidance works, still
    buggy.
  - `f25cefb993` (2026-08-20), message: debug stair detection from waypoints.
- **Stair detection from the route.** `RouteManager::assessElevation` looks
  ahead along the route arc (2.2 m) and reports "ascending" when the rise is at
  least `trigger_rise_m`, which is 0.30 m at head:
  [route_manager.cpp#L143](https://github.com/TheChanYe/SCAN_Planner_dmq/blob/58c4c39dba4708f28b732296fbf2f689d1ac1d6d/src/navdog/navdog_core/src/route_manager.cpp#L143).
  Configuration is at
  [robot_real.yaml#L200](https://github.com/TheChanYe/SCAN_Planner_dmq/blob/58c4c39dba4708f28b732296fbf2f689d1ac1d6d/src/dmq_dog/config/robot_real.yaml#L200).
- **Stair-support clearance in collision checks.**
  - While stair mode is latched, an occupied result is checked again at
    `z + z_up + stair_support_clearance_m`, which is 0.25 m.
  - The effect is that treads and risers near the interpolated route are
    ignored, while taller walls still block.
  - Code: [grid_map.h#L440-L458](https://github.com/TheChanYe/SCAN_Planner_dmq/blob/58c4c39dba4708f28b732296fbf2f689d1ac1d6d/src/planner/plan_env/include/plan_env/grid_map.h#L440-L458).
  - Configuration: [robot_real.yaml#L159](https://github.com/TheChanYe/SCAN_Planner_dmq/blob/58c4c39dba4708f28b732296fbf2f689d1ac1d6d/src/dmq_dog/config/robot_real.yaml#L159).
- **Other stair-mode changes.** Random lateral initialisation is turned off
  (`planner_manager.cpp` L154-L165), and a separate stair speed limit is used.
- **Evidence of testing.**
  - Unit tests exist for the navdog core. None cover the planner-side clearance.
  - Commit messages report real-robot stair attempts ("dmq" dog) with bugs.
    **Anecdotal only.**
  - On branch `stayvar` (`6288ac06f2`, 2026-08-18) the grid_map
    stair-clearance code was **removed** again. So the author kept two
    variants.

### 3.6 xcg124110023416/SCAN_PLANNER: Patchwork++ ground removal and slope-following z (M20)

- **Repo.** <https://github.com/xcg124110023416/SCAN_PLANNER>, branch
  `work/scan-control-resource-api` @ `f22306ea916a27d8d66ecacc4656a0eafba24c74`.
- **License.** Apache-2.0. The vendored Patchwork++ is BSD-2-Clause (KAIST).
- **Key commits.** `bf7b6989b9` and `a0603c6845`, both 2026-08-19: terrain-aware
  planning for "mode4".
- **Ground removal.**
  - Patchwork++ labels the scan into ground and non-ground points. Only
    non-ground endpoints are written as occupied, and ground rays still clear
    free space.
  - Code: [grid_map.cpp#L1547-L1592](https://github.com/xcg124110023416/SCAN_PLANNER/blob/f22306ea916a27d8d66ecacc4656a0eafba24c74/src/planner/plan_env/src/grid_map.cpp#L1547-L1592).
  - Parameters: [m20_scan_planner.yaml#L48-L69](https://github.com/xcg124110023416/SCAN_PLANNER/blob/f22306ea916a27d8d66ecacc4656a0eafba24c74/src/m20_scan_bringup/config/m20_scan_planner.yaml#L48-L69).
- **Slope-following z.**
  - The terrain z is `start.z + slope_x*dx + slope_y*dy`, taken from **one
    plane fitted** to the ground points (up to 30°).
  - It sets the local target z and projects control points onto that plane in
    mode 4.
  - Plane code: [grid_map.cpp#L1321-L1337](https://github.com/xcg124110023416/SCAN_PLANNER/blob/f22306ea916a27d8d66ecacc4656a0eafba24c74/src/planner/plan_env/src/grid_map.cpp#L1321-L1337).
  - Uses: [planner_manager.cpp#L201-L218, #L465-L495](https://github.com/xcg124110023416/SCAN_PLANNER/blob/f22306ea916a27d8d66ecacc4656a0eafba24c74/src/planner/plan_manage/src/planner_manager.cpp#L201-L218).
- **Relevance.** This handles ramps. It does not model steps. Whether
  Patchwork++ labels stair risers as non-ground is UNVERIFIED.
- **Evidence of testing.** pytest wiring and config tests only. No stair runs.

### 3.7 JINGHANW/nav_quadruped-robot: A* ground-support requirement

- **Repo.** <https://github.com/JINGHANW/nav_quadruped-robot> @
  `2bce8b91921fb94f1d9b779371a33cb938b2fb74`.
- **License.** None declared, so reuse terms are UNVERIFIED.
- **Change.** Every A* node, including start and end, must lie `body_height`
  ± tolerance (0.10 m) above a raw occupied voxel below it. The z plane is
  still linearly interpolated.
- **Code.** [dyn_a_star.cpp#L148-L180, #L201, #L306](https://github.com/JINGHANW/nav_quadruped-robot/blob/2bce8b91921fb94f1d9b779371a33cb938b2fb74/src/SCAN-Planner-Ros2/src/planner/path_searching/src/dyn_a_star.cpp#L148-L180).
  Configuration in `planner.yaml` L13-L15.
- **Evidence of testing.** One gtest, `test_astar_support.cpp`, on a flat floor
  patch only.

### 3.8 qiyu-lu/nav-benchmark: evaluation of a SCAN "terrain layer" (implementation not public)

- **Repo.** <https://github.com/qiyu-lu/nav-benchmark> @
  `ac4711e260e7664433d2d4360480fc8fcdffbc17`. License Apache-2.0.
- **What was evaluated** (README L196-L243).
  - A SCAN change adding a 2.5D elevation and traversability layer. The A*
    takes z from the elevation map and decides feasibility by step height and
    slope.
  - The implementation is linked to `qiyu-lu/HG-Planner`, which returns
    **HTTP 404**. **The code is UNVERIFIED.**
- **Reported stair result.** 0% → 100% on a stair scene.
  - Without the layer, the robot stops at the first step and the A* errors
    22,530 times.
  - The README frames this as one demo. **No stair trial data is committed.**
- **Reported flat-ground results.** 80-trial comparisons whose summaries and
  CSVs are committed:

  | Metric | Before the layer | With the layer |
  |---|---|---|
  | Dense-field success rate | 67.5% | 55.0% |
  | Command jerk | baseline | about 4.7× higher |
  | p99 planning time | baseline | about 4× higher |

- **The documented v1 bug.** Unknown ground was allowed as a step, so the A*
  could step onto the top of a 2 m box. The fix compared the z values of
  adjacent nodes instead.
- **Author's conclusion.** The terrain layer should stay off by default.
- **Sensor note** (commit `4800374a0f`). With the LiDAR pitched at 45°, stair
  treads never entered the occupancy map because of the grazing angle. 60°
  worked. This is relevant to our Lite3 sensor geometry.

### 3.9 Other downstream repos (checked; no stair improvement to SCAN)

- **`atom-1024/SCAN-Planner-FOXY`** (Apache-2.0, `911e6bb309`): only a
  `stair_keypoints.yaml` for mode 2 with dense waypoints up a stair.
- **`Luckyt1/3D_nav`** (no license): a fixed-world-height ground filter
  (`ground_height + ground_filter_height`). It suits a flat floor and works
  against stairs.
- **`l0-0-0l/scan-planner-lk`**: an adaptive map window that follows robot z.
  A comment mentions stairs. Minor.
- **`liweimingkk/Go2_dddmr`**: its stair and ramp work (`78e33efbaf`,
  "fail-closed ramp and stair navigation") lives in the separate DDDMR global
  planner. The vendored SCAN is unchanged.
- **`Kitjesen/MapPilot`** (150 stars): a ROS-free port pinned to upstream
  `348e8a5`. Its README says the SCAN core has no custom slope logic.
- **`wuyi2121/TravExplorer`** (same authors as SCAN, 196 stars): a
  traversability-aware cross-floor explorer that uses SCAN as its local
  planner. Its README says code will be released upon acceptance, and the repo
  holds only a README and images at `eab0765a22`.
- **Checked with no stair or terrain hits in SCAN files or commits:**
  - xiaoqi371317/SCAN-Planner-Ros2 (its `a5fa4ea340` ramp demo adds only a
    reference-path publisher)
  - JackJu-HIT/SCAN-Planner-Pure-ROS2
  - nanjia24/SCAN-Planner-Ros2
  - luo-cong-jjy/SCAN-Planner-ros2-community-read (comments only)
  - luo-cong-jjy/RoboDogNav-System
  - wangtao-bit/scan_planner
  - 601978297a-cmd/scan-planner
  - MiYiRobot/go2w_nav_ws_Qin (a parameter comment only)
  - tangweixing/G1-XIAOZHI-NAVI (a comment only)
  - Zxbxdxd/gogo-planner
  - robwawa excluded, since it is covered in §3.1
  - zqdbb/go2-slam
  - hu43/Unitree_GO2
  - kunkunwei/slamibot_agent
  - August-snoopy/VlnRFT
  - machinekind/w01-tek (its "terrain" commits concern RL height scans)
  - kinjo-tohoku/scan-planner (unrelated)
  - JackJu-HIT/bspline_conversion
  - xuqiang656/Note_4683

## 4. Upstream issues and PRs

`wuyi2121/SCAN-Planner` has 17 items (16 issues and PR #11). `PCT-SCAN-ROS2`
has none. `xiaoqi371317/SCAN-Planner-Ros2` has one issue, a mode 3 adaptation
question.

### #5, stairs treated as obstacles in mode 3 (closed, 10 comments)

<https://github.com/wuyi2121/SCAN-Planner/issues/5>

- **Maintainer's answer.** wuyi2121, OWNER, 2026-07-14 said to increase
  `body_height_` if mode 3 cannot climb stairs:
  [comment](https://github.com/wuyi2121/SCAN-Planner/issues/5#issuecomment-4969429334).
- **Same-day commit.** Upstream `e3f28a2` ("fix: body height") fixed
  `body_height_`, which had been read from the `double_cylinder_offset`
  parameter.
  - The commit also added a README note: raise the body, keypoint or path z if
    the robot cannot climb stairs.
  - README note: [README.md#L98](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/README.md#L98).
  - A similar note is in `tools/README.md` L24.
- **Follow-up reports.** Users reported that on a two-flight stair with a
  landing, local planning "shortcuts across z". Reducing `planning_horizon`
  then produced A* errors, and one user asked whether arc length should ignore
  z (comment 4998430202).
- **Second maintainer answer.** On 2026-07-29 the owner said only that the code
  had been updated (comment 5112382749).
- **Matching commit.** That update is upstream `b654557` ("fix: mode3
  collision", 2026-07-28). It includes:
  - arc-length progress from the projected point;
  - 0.5 m waypoint thinning;
  - replanning from the current trajectory point;
  - `planning_horizon` changed from 7.5 to 3.5;
  - `obstacles_inflation_z_down` changed from 0.4 to 0.1.
- Our inference is that this answers the landing complaint. The maintainer did
  not say so explicitly.
- **Our copy already has both fixes**, in the vendored `scan_replan_fsm.cpp`:
  - `body_height` loaded at L49;
  - arc-length `getLocalTarget` at L986-L1026.

### #16, stairs versus obstacle point clouds (open, 5 comments)

<https://github.com/wuyi2121/SCAN-Planner/issues/16>

- **No semantic distinction.** The owner (2026-09-02) said SCAN does not tell
  stairs from people. It only checks whether the initial path collides with the
  obstacle cloud. A person standing on the stair becomes an obstacle and is
  avoided.
- **Waypoint advice.** For flat ground, then stairs, then flat ground, **three
  waypoints are required**: the stair start, the stair end and the goal. This
  was confirmed on 2026-09-15.
- **Future global planner.** The owner said open 3D global planners are scarce,
  and that the team is building one "better than PCT" to be open-sourced later
  (UNVERIFIED future release).

### #9, choosing z inflation (open)

- The owner agreed that a larger `z_up` avoids low obstacles, provided a margin
  is kept to the configured body height above ground.
- A follow-up about stale obstacles outside the update range is unanswered.

### #17, B-spline lifted after adding z interpolation (closed)

- The z interpolation lifted the whole optimised curve. The maintainer did not
  answer. The reporter said the optimised path "may be weird".

### #10, random control points should not get a vertical random value (closed)

- The body is empty and there is no reply.

### #12, humanoids (G1/H1)

- The owner said the planner applies in principle to ground robots that can
  cross terrain, and that SCAN has not been deployed on G1.

### Other issues

- #14 (early stop on U-shaped mode 3 paths, open) and #7 (mode 3 hits walls)
  concern mode 3 progress.
- #6, #8, #13 and #15 concern sensing, LIO and GPS. None is stair-related.

### PR #11 (open, johyunyoung)

- Ports `b654557` to `ros2-community` and adds a Jazzy build.
- It was tested only in the bundled mockamap simulation. The PR states that
  keypoint multi-floor mode was not tested.

## 5. Upstream history after the pinned copy

- **No commits since our pin.** Upstream `main` has had no commits since
  `348e8a5` (2026-07-29, README sensor layout), and `ros2-community` none since
  2026-07-13.
- **All stair-relevant upstream changes** are `e3f28a2` and `b654557`. Both are
  already in PCT-SCAN-ROS2 and in our vendored copy.
- **Upstream README guidance on stairs:**
  - raise the z of the body, keypoints or path;
  - mode 2 multi-floor keypoints;
  - an Elevator-LIO link for localisation.
- **Still missing upstream:** ground removal, step detection and terrain
  analysis.

## 6. Method notes and UNVERIFIED items

- **The census was regenerated after a scratch-file collision.**
  - The first census used a shared scratch file `compare.tsv`. Another
    surveyor truncated that file at about 22:55, and the first rows were lost.
  - The whole fork census was rebuilt from fresh `gh api` calls into an
    isolated scratch subfolder (`scratchpad/A_scan/`). The rebuild covered the
    fork lists, `pushed_at` versus `created_at`, and the comparison of every
    non-upstream branch against `main` and `ros2-community`.
  - The rebuilt counts match the figures in §1: 58 forks, 17 pushed, and 11
    repositories with 20 branches ahead.

- **Stair search is keyword-based.** Fork diffs came from the compare API,
  which returns at most 300 files per compare.
  - Where a patch was omitted (large files in YanYaoyuan and hengzhiyou666), we
    fetched the file at the head SHA and searched it.
  - Classification rests on keyword hits (`stair|楼梯|台阶|slope|terrain|traversab|elevation|ground|floor…`)
    followed by reading the matching hunks. A stair-motivated change with no
    such words could be missed.
- **Downstream repos: only the default branch was file-scanned.** For other
  branches we searched commit messages only, which led to the TheChanYe
  `compy_work`/`stayvar` and Go2_dddmr findings.
- **Not read:** forks of downstream repos beyond those listed, and GitHub
  results beyond the first 50–100 per query. `bigblack024/MapPilot`, which was
  pushed, was not inspected.
- **UNVERIFIED:**
  - the `qiyu-lu/HG-Planner` implementation (404);
  - the TravExplorer code (unreleased);
  - the maintainers' future 3D global planner;
  - licence terms for robwawa's own additions and for JINGHANW and Luckyt1
    (no licence);
  - whether Patchwork++ keeps stair risers as non-ground;
  - every "works on stairs" claim in commit messages (TheChanYe) or single-run
    README tables (legbot_3D_Nav).
- **Our copy's remaining quirk.** Mode 1's goal-drop sentinel (`z < -0.1`) is
  still at vendored `scan_replan_fsm.cpp` L156.
