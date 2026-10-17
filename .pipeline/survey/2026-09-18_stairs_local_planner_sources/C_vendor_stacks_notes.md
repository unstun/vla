---
origin: ai+web
reviewed: false
date: 2026-09-18
stage: planning
status: surveyed
scope: stair handling in vendor and robot-specific open-source quadruped navigation stacks (stair detection, route annotation, mode switching, gait hand-off, local-map filtering, speed and heading limits)
---

# Vendor and robot-specific quadruped stacks: how they handle stairs in local planning (C)

Label: **surveyed** only. Code was read through `gh api` at the commit SHAs given below; one vendor manual
was read as a PDF. Nothing was cloned into the project, built, installed or run, and no robot or remote
machine was touched. "Evidence" means what the authors committed or published; none of it was checked by us.
Anything not read directly is marked UNVERIFIED. Quotes are short fragments; Chinese text is paraphrased.

Query window: GitHub state on 2026-09-18.

Already covered elsewhere and not repeated: `AugetyVolta/M20-loc-nav` `981579e`, `robwawa/motion_planner`
`dfeae40`, `tianchaowen/PCT_planner` `8c56322`, the Dimensional copy of CMU `terrain_analysis`
(`fukexue/ros-navigation` `5a39a29`, stairs profile) and `Robot-Nav/legbot_3D_Nav`
(see `../2026-09-17_scan_stairs_sources/B_pct_lineage_notes.md`).

## 0. Summary table

| # | Stack | Repo @ commit | License | Robot / sensors / ROS | Stair mechanism | Stair evidence | Assumes vendor stair gait? | Fit to our chain |
|---|---|---|---|---|---|---|---|---|
| 1 | DEEP Robotics Lite3 official navigation | `DeepRoboticsLab/Lite3_Navigation` @ `b091cee` | none (no LICENSE) | Lite3, RoboSense LiDAR, ROS 1 Noetic | **None.** 2D `move_base` + TEB + STVL; obstacles are points 0.15-2.0 m high | none (one commit, 14-byte README) | n/a | none |
| 2 | DEEP Robotics X30 navigation SDK (client of closed RobotServer) | `DeepRoboticsLab/robotserver_sdk` @ `f70df5e` | MIT | X30 Pro, closed navigation host | **Route annotation:** each navigation point carries `Gait`, `Speed`, `ObsMode`, `NavMode`, `Terrain`, `Posture` | product; no data | yes (gait per waypoint) | design reference only; value meanings UNVERIFIED |
| 3 | DEEP Robotics Lite3 stock gaits (manual + motion-host protocol) | Lite3 LiDAR User Manual V1.0.6 (PDF); protocol doc V1.0.7 via third-party transcription `Mplus0/Dog-Machine-2026` @ `6581380` | vendor documents | Lite3 motion host, UDP | Manual gait selection: RUG "General" (steps up to 12 cm), "Grip" (slopes), "H-Step" (steps up to 15 cm); UDP codes `0x21010401/402/407` | vendor spec only | yes (it *is* the vendor gait) | we run blind V12 instead; hand-off to the stock controller mid-route is untested |
| 4 | DEEP Robotics perception host software "lite_cog" VOA (user-redistributed) | `zhshui/slam_navx86` @ `dc0bc3e` and `DedSecer/lite_cog` @ `64887ee` (copies) | package.xml says BSD; redistribution status unclear | Mini/X20/Lite, depth cameras (+ LiDAR), ROS 1 | Local elevation map with an accessibility layer (steppable / empty / passable-not-steppable / blocked), "industrial stairs" mode, run-time `step_z_max`, stair-edge slope inflation, automatic stair-gait switching (changelog) | changelog only; **source not in the copies** | yes | closest vendor design for local filtering; code not reusable |
| 5 | Community Lite3 / Jueying / M20 / X30 nav repos (10 read) | see section 3 | mostly none | Lite3, M20, X30 | **None** (flat Nav2 / move_base, safety stop) | none | n/a | none |
| 6 | Jueying X20 gait switcher (community) | `YinghaoJia98/gait_switcher` @ `3e30a4c` | none | X20, elevation map, ROS 1 | Look-ahead corridor along `cmd_vel` on `elevation_mapping` + `traversability_estimation` layers; enough "bad" cells switches the X20 into its vision stair mode (front or back) | none (README "TODO"); has a mode-2 bug | yes | pattern only (no license) |
| 7 | Xiaomi CyberDog2 | `MiRoboticsLab/cyberdog_nav2` @ `77c6578`, `MiRoboticsLab/motion` @ `4d241d1` | Apache-2.0 | CyberDog2, head ToF, depth, ROS 2 | `elevation_mapping/stair_detected` (+1 up, -1 down) pauses tracking, runs a step-alignment state machine (ToF left/right point balance), then a scripted jump, then resumes | product feature; no data | yes (scripted jump) | hand-off state machine reusable (Apache-2.0); the detector is not public |
| 8 | Boston Dynamics Spot SDK and ROS drivers | `boston-dynamics/spot-sdk` @ `04537dd`; `rai-opensource/spot_ros2` @ `fc0eb24`; `heuristicus/spot_ros` @ `1364052` | BD SDK License (proprietary); MIT; BSD-3 | Spot | `StairsMode` OFF/ON/AUTO/PROHIBITED; GraphNav edges carry staircase geometry, descent preference, lateral alignment offset, direction constraint, per-edge mobility override; drivers only expose a service | product; no public numbers | yes (on-robot StairTracker) | best **specification** for stair-segment annotation; protos not copyable |
| 9 | Unitree official | `unitreerobotics/unitree_sdk2` @ `c753829`; `unitreerobotics/unitree_slam` @ `1e49bfa` | BSD-3; none | Go2/B2/A2, closed SLAM/nav | Go2 SDK exposes no stair API; A2 has a "climb mode" id; unitree_slam graph edges have `dog_stats` / `dog_speed`, "not open" | none | stock controller | none |
| 10 | CMU autonomy stack (original) | `jizhang-cmu/autonomy_stack_go2` @ `43d5f54` | none (no LICENSE) | Go2, L1 LiDAR, ROS 2 | Height above local ground; `obstacleHeightThre` 0.3 by default; no stair mode | none | stock Go2 gait | pattern 4 in the 2026-09-17 survey |
| 11 | Go2 Gazebo auto gait manager (community) | `asoming/ros-slam-demo` @ `2b9ac80` | Apache-2.0 | Go2 sim (CHAMP), VLP-16, ROS 2 Humble | LiDAR ground-slope fit in a forward box + IMU pitch check + hysteresis, plus fixed map "stair zones" | Gazebo only | yes (CHAMP gait profiles) | hysteresis design reusable |
| 12 | ANYbotics / ETH open pieces | `ANYbotics/elevation_mapping`, `ethz-asl/traversability_estimation` @ `14d24c0`, `leggedrobotics/art_planner` @ `2f3fde6` | BSD-3; BSD (file); BSD-3 | ANYmal, 2.5D height maps | Step filter (critical 0.12 m) in a traversability map; learned motion cost for blind and perceptive ANYmal policies | papers (not re-read here) | no mode switch | local-map filter reusable; art_planner cost is ANYmal-specific |
| 13 | Dimensional dimos (extends B lead) | `dimensionalOS/dimos` @ `26665a9` | Apache-2.0 (LICENSE file; GitHub API says NOASSERTION) | Go2, MID-360 | Multi-level-surface **global** planner with a step threshold and step penalty; stairs evaluation cases on recorded Go2/MID-360 stair datasets | eval harness; results not read | no | global, not local; its stair eval cases are a test-design lead |
| 14 | AgileX, Agibot, LimX official orgs | (listing only) | — | — | No legged navigation or stair code found | — | — | none |

## 1. DEEP Robotics official (github.com/DeepRoboticsLab)

The organisation has 27 public repositories (listing on 2026-09-18). Relevant ones:

| Repo | Default branch @ SHA | License (GitHub) | Contents relevant to stairs |
|---|---|---|---|
| `Lite3_Navigation` | `ros1-ubuntu20` @ `b091cee10a11ea8b43459f906a91ff07f5dbb417` (2024-09-13, one commit "first commit") | none | none, see 1.1 |
| `Lite3_ROS` | `ros2-foxy` @ `e4ab5dc1c7f3ff46274162a1ef302253936578aa`; `ubuntu20` @ `794198042edd3273b8951d3693c74bfc4ba5dcf6` | MIT | UDP bridge only; a placeholder state field, see 1.2 |
| `robotserver_sdk` | `main` @ `f70df5efc57c7855f61d7ad98c93cf524ce4dfa0` | MIT | X30 navigation client with per-waypoint gait/terrain fields, see 1.3 |
| `deep-robotics-msg` | `main` @ `aa646c1782aa982f384b7e46469723f31696f778` | BSD-3 | ROS 2 `Gait.msg` = a single `uint32 gait`; `NavCmdValue.msg` = vx, vy, yaw rate |
| `deep-robotics-sdk2` | `main` @ `79dd1267ca9cac6c5f148445ad0675610cf0ed17` | BSD-3 | DR02 humanoid only |
| `sdk_deploy` | `main` @ `7d738b3f034196ba688db213bc1d04691b650de6` | BSD-3 | RL deployment; MuJoCo `Lite3_stair.xml` / `M20_stair.xml` test scenes (locomotion, not planning) |
| `Lite3_SLAM`, `lightning-lm-deep-robotics`, `fast-livo2-deep-robotics` | various | none / BSD-3 / GPL-2.0 | mapping and localization; no stair logic found by path search |
| `Lite3_VMC` | `master` @ `724aa54` | none | model-based locomotion controller (`terrain.yaml`), not planning |

**Finding: no official DEEP Robotics repository contains a stair-aware local planner, stair detector or
automatic stair-mode switch.** The stair-related logic in the vendor products lives in closed hosts (X30
RobotServer; Lite3/X20 perception image), visible only through the SDK fields and user copies below.

### 1.1 Lite3_Navigation: flat 2D, no stairs

- `navigation/launch/navigation.launch` L1-20: `move_base` with global planner and TEB.
- `navigation/config/local_costmap_params.yaml` L5-7: Spatio-Temporal Voxel Layer plus a `sob_layer`.
- `navigation/config/common_costmap_params.yaml` L45-56: source `/rslidar_points`; `min_obstacle_height` 0.15,
  `max_obstacle_height` 2.0, `min_z` 0.2. A 15-18 cm stair riser would sit right at this threshold.
- README is 14 bytes; there is no license file. Localization is `hdl_localization`.

### 1.2 Lite3 stock gaits and the motion-host protocol

- **Manual (vendor primary).** *Jueying Lite3 LiDAR User Manual V1.0.6-0, 2024/03/25*,
  <https://static.generation-robots.com/media/deep-robotics-lite-3-lidar-user-manual.pdf>, SHA-256
  `87256e2bb3414857c39302c197b614a3c92e399a6211b71882c27dfbb658d6a2` (kept in the scratchpad only, not stored
  in the project). Section 2.3.4 "RUG Gait" (PDF page 15, printed page 13): three rough-terrain gaits,
  General (stairs and slopes, steps up to 12 cm, slope up to 30 deg), Grip (slopes up to 40 deg) and H-Step
  ("higher stairs", steps up to 15 cm). Spec table (PDF page 8): step height 15 cm. Operation section (PDF
  page 21): the **user** chooses General for low steps and stairs and H-Step for higher steps. The manual describes no automatic stair
  detection and no stair behaviour for autonomous navigation.
- **Protocol (secondary, third-party transcription of the vendor document).** *Lite3 motion host UDP interface
  (beta) V1.0.7*, transcribed in `Mplus0/Dog-Machine-2026` @ `65813801724597f6a6a47dfbdf7ed505c9f6b226`
  `src/message_transformer/docs/lite3_motion_host_udp_interface_beta_v1_0_7.md` L240-252: gait switch codes,
  including general obstacle gait `0x21010401`, grip gait `0x21010402` and high-step gait `0x21010407`; state
  values L431-441 (general 2, grip 6, high-step 13). Provenance was classified in
  `../2026-09-10_lite3_cameras_web_sources/README.md` (row 4: two independent transcriptions agree).
- `Lite3_ROS` `src/transfer/include/protocol.hpp` L39 (`e4ab5dc`): state field `touch_down_and_stair_trot`, marked in
  the vendor comment as not activated.
- **Fit:** these gaits belong to the stock motion-host controller. Our chain runs the blind V12 RL policy
  through our own deployment, so a "stair gait" hand-off would mean switching controllers mid-route. That
  switch is untested and the vendor gives step limits (12-15 cm) at or below typical stair risers.

### 1.3 X30 RobotServer SDK: the vendor annotates the route, not the local map

- `include/types.h` L107-122 (`f70df5e`): `NavigationPoint` has position, yaw and integer fields `gait`,
  `speed`, `manner`, `obsMode`, `navMode`, `terrain`, `posture`. `examples/basic/default_navigation_points.json`
  sets them per point (all zero except `NavMode` and `Speed` in the example).
- Failure codes show which on-robot modules exist: terrain module state (L38), switch walking mode (L42),
  switch gait (L45), set terrain-map parameter (L50), plus stop-avoidance modules.
- README: mapping and waypoint setup follow the *Jueying X30 Pro Application Manual* (not read).
- **Value meanings of `Gait` / `Terrain` / `ObsMode` are not documented in the SDK: UNVERIFIED.**
- **Design takeaway:** DEEP Robotics' own navigation product puts stair handling into **per-waypoint route
  attributes** (gait, speed, obstacle mode, terrain), which the robot applies as it passes each point. This is
  the same pattern as M20-loc-nav's route labels, Spot's edge annotations and Unitree's edge `dog_stats`.

## 2. DEEP Robotics perception software as redistributed by users ("lite_cog" VOA)

Several user repositories carry a `lite_cog` tree that looks like the vendor's Lite3 perception-host software
(SLAM, `move_base`, `voa`, tracking, drivers). **Provenance is inferred, not confirmed: UNVERIFIED.** Copies read:
`zhshui/slam_navx86` @ `dc0bc3e18dd397d1a1ef909123499c16a3ba2bfd` (no license) and `DedSecer/lite_cog` @
`64887eeb3e72d9d4db5d5f8b98efdfdc67553fc2` (no license). The `voa` package `deeprobotics_local_height_map`
ships configs, launch files and a CMakeLists that compiles `src/ElevationMapping.cpp`, `src/safety.cpp` and
others, but **no `src/` directory is present in either copy**, so the mechanism cannot be read.

What the configs and docs show (paths under `lite_cog/voa/src/` in `zhshui/slam_navx86`):

- `README.md` L27-28: output `/deeprobotics_local_height_map/height_map` (grid_map) with layers elevation,
  slope and **accessibility**. Accessibility values: steppable 0.0, empty 0.01, passable but not steppable 0.1,
  impassable 1.0.
- `README.md` L82-94: `addPointMethod` 1 normal / **2 industrial stairs**; `height_filter` (erode-dilate) is
  said to smooth the map and remove the robot's own feet when descending stairs, at the cost of thin obstacles;
  `step_z_max` 0.2 m, set larger than real steps because of mapping error and **adjustable at run time on
  `/step_z_max` because different gaits have different limits**; `slope_inflation` inflates stair edges.
- `deeprobotics_local_height_map/config/analyze_l_h_hei.yaml` L6 `step_z_max: 0.2` versus
  `analyze_l_h_safe.yaml` L6 `step_z_max: 0.07`: two profiles, stepping versus safety stop.
- `version` (changelog) L14-15: industrial-stair algorithm (2021-11-04) and gait switching added (2021-11-15);
  L13: fix for pose drift up or down **wrongly triggering the stair gait**, and for residual blocked cells
  triggering it during a stop (2021-11-22); L3: X20 rear-camera gait switching (2022-02-09).
- `deeprobotics_local_height_map/launch/height_map_lite.launch` L16-43: on Lite the safety node is on, plane
  segmentation (`plane_seg_ros`, from ANYmal work) is off, and the commented-out `vel_control` node is unused.
- ROS 2 copy `DedSecer/lite_cog_ros2` @ `4ec65bd359322daad9116b3b21c0b766f55c075f` `src/voa/src/voa/config/voa.yaml`
  L21-30: a simpler safety controller with `kObstatleHeight` 0.10 m; no stair logic; `package.xml` license TODO.
- **Fit:** the vendor's own local-map design is a height map with a per-gait step threshold, an explicit
  stair mode and a drift guard for gait switching. It confirms three ideas for us: make the local map's step
  threshold a run-time input tied to locomotion capability, treat stair edges specially, and guard mode
  switches against localization drift. The code itself is not available. **Lead (not executed):** the same
  package may already exist on our Lite3's perception host; check only in a separately authorised task.

## 3. Community Lite3 / Jueying / X30 / M20 projects

Search: `gh search repos` for "lite3 navigation", "lite3 nav2", "lite3 stairs", "jueying", "deeprobotics",
"绝影", "云深处", "x30 navigation", "m20 navigation", plus code search for the Lite3 gait codes. Head SHAs read on
2026-09-18; path and README search for stair terms.

| Repo @ SHA | License | What it is | Stairs |
|---|---|---|---|
| `DedSecer/coffee_nav` @ `df324b1` | none | Lite3 `move_base` + TEB waypoint navigator | none |
| `QuangTrungK22/Jueying-Lite3-Autonomous-Nav` @ `3754445` | none | vendor RL-deploy copy (MuJoCo stair scene) + manual | none in planning |
| `ChuheLin/m20pro-ros2-slam-nav` @ `37ccbcb` | other | M20 Pro SLAM/nav toolkit, 7 files | none |
| `AI-DA-STC/M20-autonomy-sim` @ `ec30acf` | none | M20 Gazebo + CMU autonomy stack | no stairs profile |
| `automatika-robotics/emos-plugin-lite3` @ `8aa389a` | none | Lite3 plugin, MID-360 + RealSense; slow/medium/fast gaits only | none |
| `syswonder/robot-deep_robotics-lite3` @ `6ee45d7` | none | Lite3 + MID-360 + Nav2 deployment | none |
| `lic33571-art/lite3_contest_2026` @ `224e1e5` | MIT (README) | contest code: line following, inspection | none |
| `YulunGuo/X30NavMsgsConvert` @ `9a98962` | none | X30 `move_base` goal conversion | none |
| `xyz2555/Lite3_ws` @ `1c13d81` | none | Lite3 stair **locomotion** (posture IK, contact equilibrium) in Gazebo | controller-level, not planning |
| `DedSecer/lite_cog_ros2` `src/nav/dr_nav2/config/lite_nav2.yaml` L140-162 | none | Lite3 Nav2 (DWB + STVL, obstacle height 0.15-1.2 m) | none |

**Finding: no community Lite3 navigation project handles stairs.** The only Jueying-family stair switcher found
is for the X20:

### 3.1 YinghaoJia98/gait_switcher (Jueying X20)

- `master` @ `3e30a4cf1c72c438615925452aa01518f9d486e4` (2023-07-06), **no license**, README says only "TODO".
- Inputs (`config/gait_switcher_settings.yaml` L3-21): `/elevation_mapping/elevation_map_raw`, `/cmd_vel`;
  layers `step` and `traversability` (from `traversability_estimation`); look-ahead 3 s; corridor width 0.6 m;
  checked at 3 Hz.
- Mechanism (`src/gait_switcher.cpp` L392-522): cast parallel lines across a corridor of robot width, from the
  robot along the commanded direction to `vx * LookAheadTime`. Count cells whose step score is at least 0.8
  (the step itself is fine) but whose overall traversability lies in (0.2, 0.8). If the count exceeds 150,
  request "vision mode".
- Hand-off (L148-226, L227-390): service `basic_command` with `a = 8` and `b = 1` (stair front), `b = 2` (stair
  back), `b = 0` then `a = 6` (normal). Direction follows the sign of `vx`.
- Defect: L205-210, in back mode with a forward command, it logs "front" but calls the back-mode setter.
- Evidence: none. **Fit:** a compact example of live stair detection from a local traversability map
  driving a mode switch. We would use the same trigger for velocity or filter profiles, not a gait.

## 4. Xiaomi CyberDog2 (MiRoboticsLab)

- `cyberdog_nav2` `rolling` @ `77c65782bd2e09e93a03fc5d36c4b68f62395c38`, `motion` `rolling` @
  `4d241d1cfca1610f3658bac31acea01277b7a47c`, both Apache-2.0. The workspace manifest
  (`cyberdog_ws` @ `b101edd` `cyberdog.repos`) lists 9 repos; none contains the `elevation_mapping` package
  that publishes the stair signal. **The detector is not public: UNVERIFIED.**
- Detection input: `behavior_manager/include/behavior_manager/mode_detector.hpp` L74-78 subscribes
  `elevation_mapping/stair_detected` (Int8: +1 up, -1 down, L49-53); L132-143 triggers the stair routine.
- Hand-off state machine: `executor_stair_jumping.hpp` L38-46 (Idle, Aligning, Jumping, Jumped, Abnorm), L61-80
  (align start/stop services, `elevation_mapping/stair_jump_detected` condition check, motion jump client),
  plus an align timeout thread. `behavior_manager.hpp` L44-60 and L114-122: stair jumping **suspends person
  tracking**, runs, then tracking resumes.
- Alignment: `motion/motion_utils/test/stair_perception.cpp` L98-156 (compiled into the `stair_align`
  executable, `motion_utils/CMakeLists.txt` L52): states BLIND_FORWARD, TURN_LEFT/RIGHT, APPROACH, FINISH.
  It balances left and right ToF points to square up to the edge, then approaches until the point count passes
  a threshold that depends on step height (`config/stair_align.toml` L17-27: 100 / 80 / 60 points for 0-0.10,
  0.10-0.13, 0.13-0.5 m). Speeds `vel_x` 0.1 m/s, `vel_omega` 0.25 rad/s (L2-3).
- `motion_bridge/src/elevation_bridge.cpp` L26-41: the elevation map is also sent to the locomotion controller
  over LCM (perceptive locomotion input).
- Scope: single steps/kerbs for a small robot, in following mode, not multi-step flights.
- Evidence: shipped product; no public success data. **Fit:** the pattern "detect, suspend the normal local
  planner, square up to the edge at low speed, run a dedicated behaviour with a timeout, resume" is directly
  reusable (Apache-2.0). The jump motion itself is irrelevant to V12.

## 5. Boston Dynamics Spot

- `boston-dynamics/spot-sdk` `master` @ `04537ddafe0641d1751af3eb9e76cb785fc18594`. License: *Boston Dynamics
  Software Development Kit License (20191101-BDSDK-SL)*, proprietary terms (GitHub reports NOASSERTION).
- `protos/bosdyn/api/spot/robot_command.proto` L80-93: `StairsMode` OFF / ON / AUTO (robot switches itself) /
  PROHIBITED (stairs detected and avoided); stairs only in trot gaits; L107-121: flags to disable the
  StairTracker, the automatic descent on error, and near-map cliff avoidance on stairs.
- `protos/bosdyn/api/graph_nav/map.proto` L287-327: GraphNav **edge annotations** hold `StairData`: state,
  staircase geometry (`StaircaseWithLandings`), `descent_preference` (default: always descend in reverse),
  and `traversal_y_offset`, which puts all navigation goals on one lateral line in the staircase frame so the
  robot climbs straight. L329-346: `direction_constraint` (e.g. NO_TURN, FORWARD, REVERSE) and
  `require_alignment` in yaw before the edge. L354-361: per-edge override of mobility parameters, including
  `stairs_mode`.
- `protos/bosdyn/api/stairs.proto` L16-147: staircase frame (origin at the bottom-centre of the first riser,
  x up the stairs), width with bounded or unbounded sides, `average_rise`, `average_run`, per-step edge
  centres and directions, landings as oriented boxes.
- ROS drivers only pass the flag through: `rai-opensource/spot_ros2` @ `fc0eb245d47e146cf2a4c4fa47c9739f89bc79bd`
  (MIT) `spot_driver/spot_driver/spot_ros2.py` L666-668 (`stairs_mode` service) and L1872-1896 (handler);
  `heuristicus/spot_ros` @ `1364052bbd116e65b362b2371602bd596c249f46` (BSD-3) `spot_driver/src/spot_driver/spot_ros.py`
  L624-631 and L1892 (deprecated `stair_hint` boolean).
- No community Spot navigation stack with its own stair logic was found; code search for the stair-mode
  enum returned SDK mirrors and one teaching simulator (`Lightrunnerwastaken/spotlab`, no license) that
  reproduces the "climb forward, descend in reverse" rule.
- **Fit:** the most complete public **specification** for annotating stair segments on a route: geometry,
  landings, alignment line, no-turn constraint, descent direction and per-segment mode/speed overrides. Only
  the concepts can be reused.

## 6. Unitree and Go2 community

- `unitreerobotics/unitree_sdk2` `main` @ `c753829882fba461ed07ba25aaabee0a25d83663` (BSD-3):
  `include/unitree/robot/go2/sport/sport_client.hpp` L60-77 lists Go2 modes (FreeWalk, ClassicWalk,
  StaticWalk, TrotRun, EconomicGait, avoid mode); none is a stair mode. `a2/sport/sport_client.hpp` L15-26 has
  `ID_CLIMB_MODE = 5` for A2 (semantics UNVERIFIED). B2 has `SwitchGait(int)` with undocumented values.
- `unitreerobotics/unitree_slam` `main` @ `1e49bfa4dca2c992a566ee7d1d8480d4102149b8` (no license, binaries plus
  examples): topological graph navigation; `ros2_msg/graph_msg/Edge.msg` L1-13 has per-edge `dog_stats`,
  `dog_back_stats`, `dog_speed`; `unitree_slam_example/add_edge.cpp` L28 says `dog_stats` is not open and must
  be 0. Route-attribute pattern again, closed.
- CMU original `jizhang-cmu/autonomy_stack_go2` `foxy-humble` @ `43d5f54b389b251713f0097893c30fa76c870d54` (no
  LICENSE file): `src/base_autonomy/local_planner/launch/local_planner.launch` L29-30 `obstacleHeightThre` 0.3,
  `groundHeightThre` 0.1; README L204 says obstacles must be above 0.3 m because of L1 noise. No stair file;
  the stairs profile read on 2026-09-17 is a Dimensional addition.
- `asoming/ros-slam-demo` `main` @ `2b9ac8083a7e31778acf5d04d90f0f3f61c4b75d` (Apache-2.0), Gazebo Fortress Go2
  with CHAMP: `robot_expo_world/auto_gait_manager.py`
  - L26: modes flat / stairs_up / stairs_down, published on `/gait_mode` (L320).
  - L39-146: robust ground-slope fit in a forward box (x 0.55-2.70 m, half-width 0.55 m; L288-289), dropping
    one-bin returns from stair noses and kerbs; confidence from bins, span and residual.
  - L149-196: hysteresis: 5 frames to enter a stair mode, 12 frames to return to flat, 4 more between the two
    stair modes, minimum 2 s between switches.
  - L279-284: up/down threshold 4.8 deg, flat 2.2 deg, minimum confidence 0.52; IMU pitch confirmation.
  - L218-270: fixed world "stair zones" used as ground truth in this simulated world.
  - Evidence: simulation only. **Fit:** the hysteresis and confirmation design is reusable (Apache-2.0).
- Search for Go2 navigation repos with stair handling ("go2 stairs", "go2 nav2", "unitree stairs navigation")
  found only RL locomotion repos (`amanarora-ai/GO2_Stair`, `wxz-521/go2-stairs-sim2real`) and flat Nav2 stacks.

## 7. ANYbotics / ETH open-source pieces

- `ANYbotics/elevation_mapping` (BSD-3) appears to be the base of DEEP Robotics' VOA: the VOA copy carries
  `config/elevation_maps/starleth_map.yaml`, `config/sensor_processors/*.yaml` and `src/ElevationMapping.cpp`
  in its CMakeLists, which match that package's file names (names compared, contents not diffed).
- `ethz-asl/traversability_estimation` `master` @ `14d24c059e1c43466aadf328280adf6394d78039` (LICENSE: BSD-style,
  Peter Fankhauser 2015): `traversability_estimation/config/robot_filter_parameter.yaml` L15-22 step filter
  `critical_value` 0.12 m, windows 0.04 m, `critical_cell_number` 4; L29-33 traversability = mean of slope,
  step and roughness. This is the layer set the X20 gait switcher reads.
- `leggedrobotics/art_planner` `main` @ `2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f` (BSD-3): sampling planner on
  2.5D height maps; README L110-112: the motion-cost network was trained for **blind and perceptive ANYmal
  policies**, and other robots should use the geometric variant. Paper arXiv 2303.01420 (not re-read here).
- **Fit:** for us, a step/traversability filter on a local height map is the ANYmal-lineage way to stop treads
  counting as obstacles. The learned cost does not transfer to Lite3/V12.

## 8. Dimensional dimos (extends the 2026-09-17 lead)

- `dimensionalOS/dimos` `main` @ `26665a90f2d844e698eb0cf126373d9e3bd46a52`, LICENSE file Apache-2.0.
- `dimos/navigation/nav_3d/mls_planner/rust/src/adjacency.rs` L34-48 and L202-237: voxel multi-level-surface
  graph; neighbours with a height change above `step_threshold_cells` are not connected, and rises add a
  step penalty. This is a **global** 3D planner (Dijkstra), comparable to PCT, not a local planner.
- `dimos/navigation/nav_3d/evaluator/case_manifests/mid360_athens_stairs.yaml`: start/goal cases tagged
  stairs up/down on recorded MID-360 stair datasets (`data/.lfs/go2_mid360_stairs.db.tar.gz` and others,
  LFS, not downloaded). Results were not read.
- **Fit:** the offline stair case manifest is a test-design lead for a SCAN stair baseline; the planner
  overlaps with PCT.

## 9. Other vendors checked

- AgileX (`agilexrobotics`, 98 public repos): only wheeled navigation (`IC-Nav`, `Navis`); no legged or
  stair code.
- Agibot (`AgibotTech`): `agibot_D1_Edu-Ultra` @ `b5fe0a8` (BSD-3), `Agibot_D1_MaxPro` @ `7828aef`: SDK READMEs;
  no navigation or stair logic. `Agibot_D1_Max` tree read timed out: UNVERIFIED.
- LimX (`limxdynamics`, 46 public repos): RL training and deployment, simulators, descriptions; no navigation
  repository. TRON1's manual stair-mode toggle was covered in the 2026-09-17 survey (`81578823/PCT_planner`).

## 10. Design patterns and fit to our chain (lead proposal)

Our chain: PCT route on a known tomogram, SCAN local planner on live MID-360 occupancy, blind V12 policy
with no stair gait. What the vendor stacks do, grouped:

1. **Annotate stair segments on the route and switch behaviour per segment.** DEEP Robotics X30 (per-waypoint
   gait/speed/terrain/obstacle mode), Spot GraphNav (edge stair geometry, alignment line, direction
   constraint, descent preference, mobility overrides), Unitree SLAM (edge `dog_stats`, `dog_speed`), and
   M20-loc-nav (labels 3-4 m ahead). Fit: high. PCT already knows the route height, so stair segments can be
   labelled offline or at plan time. For V12 the "gait" field becomes a SCAN profile: filter mode, speed cap,
   no-turn heading constraint, lateral alignment to the stair centre line, and possibly descent direction.
2. **Local height map with a step threshold as a run-time input.** DEEP Robotics VOA (`step_z_max` topic,
   stair mode, edge inflation, own-feet filtering on descent), ETH step filter (0.12 m), CMU height above
   ground (0.3 m). Fit: medium. This is SCAN's missing ground/step semantics. It works without the map, but
   needs a height map that SCAN does not build today.
3. **Live stair detection with hysteresis for the switch.** X20 gait switcher (corridor along the command,
   cell count), `asoming` auto gait manager (slope fit, IMU confirmation, 5/12-frame hysteresis, 2 s minimum),
   and the VOA changelog's drift guard. Fit: medium, as a cross-check on the route label and for unmapped
   stairs.
4. **A dedicated stair behaviour that suspends the normal local planner.** CyberDog2 (align, execute with a
   timeout, resume), Spot (StairTracker inside the robot). Fit: medium. An "align then climb straight" mode
   in front of SCAN would avoid B-spline replanning on the treads; it needs a clear exit and timeout.
5. **Vendor stair gait hand-off.** Every product stack here assumes one (Lite3 RUG H-Step, X20 vision stair
   mode, X30 gait field, Spot stairs mode, CyberDog jump). Fit: low. V12 is blind and has no stair mode, and the
   Lite3 stock step limits are 12-15 cm. Switching to the stock controller mid-route would be a new, untested
   controller hand-off and needs Dr Sun's authorisation before any real-robot test.

## 11. UNVERIFIED and gaps

- Meanings of X30 `Gait` / `Terrain` / `ObsMode` / `NavMode` values; the X30 application manual was not read.
- That `lite_cog` is DEEP Robotics' shipped perception software; its missing `src/` (stair detection and gait
  switching could not be read); whether it is installed on our Lite3.
- The CyberDog2 `elevation_mapping` fork that publishes `stair_detected` / `stair_jump_detected`.
- Unitree A2 `ID_CLIMB_MODE` semantics, B2 `SwitchGait` values, Go2 firmware stair behaviour.
- Spot on-robot StairTracker and AUTO mode behaviour (closed); no public success rates.
- dimos stair evaluation results and datasets (LFS, not downloaded).
- `Agibot_D1_Max` tree (timeout). Videos and product claims were not checked.
- No stack in this family publishes a stair success rate from a real robot.
