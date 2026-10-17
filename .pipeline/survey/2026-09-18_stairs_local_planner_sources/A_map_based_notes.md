---
origin: ai+web
reviewed: false
date: 2026-09-18
status: surveyed
stage: planning
family: A - map-based / geometric local planners with explicit step or stair handling
---

# A. Map-based and geometric local planners that handle stairs: notes

**Question (Dr Sun, 2026-09-18).** Besides SCAN, which open-source local planners handle stairs, so that we reuse
rather than invent?

**Scope of this family.** Geometric planners that work on a map (height/elevation map, voxel map, mesh or
traversability grid) and separate steps from obstacles by an explicit rule. Learned planners (ViPlanner, iPlanner,
FDM and similar) belong to family B and are only pointed to here.

**Status: `surveyed` only.** Nothing was cloned into the project, installed, built or run. No candidate is
`imported`, `reproduced`, `integrated` or `validated`.

**Method.**
- Code read through `gh api .../contents/PATH?ref=SHA` at the commits pinned below (branch heads on 2026-09-18).
  Temporary copies are in the session scratchpad (`.../scratchpad/A_geo/`), not in the project.
- Papers read through WebFetch (a model-written summary of the arXiv page), marked **(paper, via WebFetch)**. One
  paper PDF (RMP, arXiv 2201.03938) was converted with `pdftotext` in the scratchpad and grepped directly.
- Numbers I computed from code or config are marked **(derived)**. Anything I did not read is **UNVERIFIED**.
- Prior coverage not repeated: CMU terrain_analysis/local_planner basics, elevation_mapping_cupy, ETH
  traversability_estimation, ArtPlanner basics and Nav2 voxel/STVL are in
  `../2026-09-17_collision_handling_sources/B_planner_terrain_notes.md` (B4-B7). This file extends them.

---

## Summary table

| Planner | Repo @ commit | License | Inputs -> outputs | Step / stair mechanism | Stair evidence | ROS | Fit to PCT -> local -> V12 |
|---|---|---|---|---|---|---|---|
| CMU base autonomy (terrain_analysis + local_planner + pathFollower) | jizhang-cmu/autonomy_stack_go2 `43d5f54b` (branch `foxy-humble`) | No root LICENSE; `package.xml` BSD | registered LiDAR cloud + odom + `/way_point` -> `/path` -> `/cmd_vel` (TwistStamped) | height above local ground (25 % quantile over a 0.6 m window); `obstacleHeightThre` 0.3 m on Go2 | **None found** (README, code search) | ROS 2 Foxy/Humble | **High on interface**: Foxy and Humble, cmd_vel out, waypoint in. Stair behaviour unmeasured. |
| Dimensional-derived CMU + PCT stack ("unitree_go2_stairs" profile) | jeff-hykin/ros-navigation-autonomy-stack `3906f075`; fukexue/ros-navigation `5a39a297`; PCT node dimensionalOS/PCT_planner `ac7cf2ce` | **None** on all three; provenance disputed (DMCA below) | PCT route -> `/way_point` at 2.0 m lookahead -> CMU local planner -> cmd_vel | stairs profile: `obstacleHeightThre` 0.3 (flat 0.1), larger min path scale | Profile exists; a user runs it on a Go2 (README command); **no results** | ROS 2 Humble/Jazzy | **Same architecture as ours**, but do not copy code. Reuse the idea only. |
| dimos MLS planner + nav_3d evaluator | dimensionalOS/dimos `26665a90` | Apache-2.0 (Copyright Dimensional) | global/local voxel cloud + goal -> 3-D `Path` every LiDAR frame -> dannav path gate -> holonomic tracker | standable cells with robot-height clearance; `step_threshold_m` 0.16; wall clearance | Real MID-360 stair recordings (Go2, "Athens" stairs) and a stairs case manifest; **no result numbers in repo** | **No ROS** (LCM, Rust + Python) | Medium as algorithm/evaluator; low as drop-in. |
| ArtPlanner (reachability) | leggedrobotics/art_planner `2f3fde68` | BSD-3-Clause | elevation GridMap (elevation_mapping_cupy) -> `nav_msgs/Path` | torso box collision-free, foot boxes must touch terrain | SubT Finals (ANYmal): **declined** subway stairs with old cost weights (paper, via WebFetch); no stair success numbers | ROS 1 Noetic only; no ROS 2 fork found | Low-medium: principled check, but ROS 1, ANYmal-tuned, path only, 0.5 Hz. |
| field_local_planner (RMP / FALCO plugins) | ori-drs/field_local_planner `f1f8f0fd`; RSL fork `70255f53` (+24 commits) | GPL-3.0 | elevation GridMap + goal -> twist + path | slope (0.6 rad scale) + height below base (-0.3 m) -> traversability -> SDF | **None**; RMP paper tests are indoor clutter and a mine | ROS 1 only (README) | Low: SE(2) planar, ROS 1, GPL-3.0. |
| FAR planner / TARE | MichaelFYang/far_planner `29fb2158`; caochao39/tare_planner `b6760adb` (`humble-jazzy`) | None on GitHub | route / exploration waypoints -> CMU base autonomy | rely on CMU terrain analysis | None in README | ROS 2 Humble/Jazzy | Not local planners; PCT already fills this role. |
| Real_Time_Stair_Detector (Fan Yang, CMU-OSU SubT) | MichaelFYang/Real_Time_Stair_Detector `c61ebf59` | No LICENSE file; `package.xml` BSD | registered cloud + odom -> stair poses, `is_stair` Bool | 2-D correlation with a stair kernel on scan image | Video only (README); author says SubT-specific | ROS 1 | Possible stair-mode trigger; not a planner. |
| PUTN | jianzhuozhuTHU/putn `a12c900d` | GPL-3.0 | point-cloud map -> PF-RRT* + GPR -> NMPC | plane-fit flatness/slope/sparsity | None; UGV (slopes, bridges, forest) | ROS 1 Melodic | Low: UGV, no stairs. |
| traversability_mapping (Tixiao Shan) | TixiaoShan/traversability_mapping `ab9f2b37` | GPL-3.0 | VLP-16 cloud -> traversability grid -> move_base | step diff 0.10/0.15 m, slope 20 deg | None; UGV | ROS 1 | Low: stairs become obstacles. |
| TRG-planner | wasahaiah/TRG-planner `fc6f1e47` | Apache-2.0 **with Commons Clause** | prebuilt map -> risk graph -> global path | `heightThreshold` 0.15, collision/risk | Quadruped at ICRA 2023 QRC (paper, via WebFetch); stairs not stated | ROS 1 Noetic, ROS 2 Humble | Global planner (PCT alternative), not local. |
| mesh_navigation (MeshNav) | naturerobots/mesh_navigation `2fd7ada7` | BSD-3-Clause | triangle mesh map -> mesh planners -> vector-field / MPPI controllers | HeightDiff, Steepness layers | Steepness layer is documented as a way to **avoid** stairs | ROS 2 Humble/Jazzy | Low: needs a mesh map; diff-drive/bicycle MPPI models. |
| Nav2 + elevation traversability layers | SirErico/nav2_gridmap_traversability_layer `7c1d538a` (BSD-3); abulhasnat-abdullah/nav2_traversability_layer `ad8f66f1` (MIT) | as listed | GridMap / DEM features -> 2-D costmap -> any Nav2 controller (e.g. MPPI) | slope / step / roughness thresholds | None; both repos are weeks old, 0 stars | ROS 2 Jazzy | Low: 2-D costmap, no evidence. |
| Stair hand-off stacks | Xiong-z-x/go2w_navigation_stack `8b738dcf` (no license); real-lsy/That-nav `38b12d8d` (Apache-2.0); tu-darmstadt-ros-pkg/hector_stairs_planner `724a18ad` (BSD-3) | as listed | Nav2 on flats + separate stair executor or manual stair mode | mode switch at known stairs; hector uses forward-only motion primitives | Gazebo only (Go2W stack); manual mode switch (That-nav); tracked robots (hector) | ROS 2 Humble / ROS 1 | Pattern reference only. |
| RAEM (paper) | code **not released**; Shua1ge/quadruped_exploration_planner `adc25046` is a skeleton | n/a | local tomography + 4-state local 3-D grid -> EGO-based local planner | "traversable" class between tomogram slices, clearance and gradient criteria | Go2, MID-360, five-floor stairwell (paper, via WebFetch; no numbers read) | not stated | Closest **method** to "SCAN + terrain classes"; watch for code. |

---

## A1. CMU base autonomy on Go2 (terrain_analysis, local_planner, pathFollower)

- **Repo.** <https://github.com/jizhang-cmu/autonomy_stack_go2>, branch `foxy-humble`, commit
  `43d5f54b389b251713f0097893c30fa76c870d54` (pushed 2026-02-18, 544 stars). No root LICENSE; `package.xml`
  declares BSD (prior notes B4). Sibling stacks: `autonomy_stack_mecanum_wheel_platform`,
  `autonomy_stack_diablo_setup` (`jazzy`), both without stair content (code search for "stair" hits only vendored
  or-tools / gtsam files).
- **Interfaces (code facts).**
  - Local planner subscribes `/way_point` (PointStamped) and publishes `/path`
    ([localPlanner.cpp L595, L605](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/src/localPlanner.cpp#L595-L605)).
  - Path follower publishes `/cmd_vel` as TwistStamped in frame `vehicle` and honours `/stop`
    ([pathFollower.cpp L291-298](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/src/pathFollower.cpp#L291-L298)).
- **Go2 profile** ([local_planner.launch L18-30](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/launch/local_planner.launch#L18-L30)):
  vehicle 0.3 x 0.7 m (length x width as written), `obstacleHeightThre` 0.3, `groundHeightThre` 0.1,
  `useCost` false. Incline-based slow-down and stop exist but are **off** (`useInclRateToSlow`, `useInclToStop`,
  L75, L81).
- **Step versus obstacle (code facts).**
  - Each point is added to the 3 x 3 neighbourhood of 0.2 m planar voxels, so the ground estimate uses a
    **0.6 m window**
    ([terrainAnalysis.cpp L457-466](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/terrain_analysis/src/terrainAnalysis.cpp#L457-L466)).
  - Ground = 25 % height quantile (`quantileZ` 0.25,
    [terrain_analysis.launch L9](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/terrain_analysis/launch/terrain_analysis.launch#L9)).
  - Point intensity = height above that ground, kept if below `vehicleHeight` 1.5 m (terrainAnalysis.cpp
    L606-615; launch L29).
  - The local planner keeps points whose intensity exceeds `obstacleHeightThre` (localPlanner.cpp L204).
  - Input cloud is cropped to `maxRelZ + disRatioZ * dis` above the vehicle, 0.5 + 0.2 d on Go2
    (terrainAnalysis.cpp L176-178; launch L33-34).
- **Stairs (derived, not measured).**
  - With treads near 0.30 m, the 0.6 m window holds about two treads, so tread points sit about one riser
    (0.15-0.18 m) above the ground estimate, below 0.3. Stairs would then pass as terrain.
  - With shallower treads (0.25 m or less) the window can hold three treads, and the top tread can reach two risers
    (0.30-0.36 m), which would be marked as obstacle. **Check our Building stair tread and riser before relying on
    this.**
  - Overhead flights in a stairwell less than 1.5 m above the local ground count as obstacles (vehicleHeight).
  - On an ascent, the height crop drops stair points beyond about 2.2 m ahead, assuming a 0.35 m sensor and a
    0.59 slope. That leaves about 2 m of look-ahead on stairs.
- **Stair evidence.** None found. README L204 asks users to keep obstacles above 0.3 m because the L1 LiDAR cannot
  resolve low obstacles
  ([README L204](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/README.md?plain=1#L204)).
  The stack drives Go2 through Unitree's own sport controller.
- **Correction to 2026-09-17 notes.** The 0.3 m value in the upstream Go2 stack is the default Go2 profile, not a
  "stairs profile". A named stairs profile exists only in the Dimensional-derived copies (A2).
- **Fit.**
  - Foxy and Humble build (branch name; not built by us).
  - `/way_point` input takes a PCT look-ahead point (see A2).
  - TwistStamped cmd_vel matches a velocity-command policy.
  - The planner is 2-D: a pre-computed path set in the vehicle frame. It has no heading-alignment rule for stairs,
    so a straight approach depends on waypoint placement.

## A2. Dimensional-derived CMU + PCT stack with a "unitree_go2_stairs" profile

- **Copies read.**
  - jeff-hykin/ros-navigation-autonomy-stack, branch `fastlio2`, `3906f075348c18af06919aeb80bd5bc38546dade`
    (2026-03-01).
  - fukexue/ros-navigation, `5a39a297039819201aa7a02ec66b2cc2e9ac5b48` (2026-04-24; adds memory tweaks to PCT, no
    stair results).
  - Both READMEs call it the "Dimensional Ground Autonomy Stack". Neither declares a license.
- **Stairs profile**
  ([unitree_go2_stairs.yaml L29-48](https://github.com/jeff-hykin/ros-navigation-autonomy-stack/blob/3906f075348c18af06919aeb80bd5bc38546dade/src/base_autonomy/local_planner/config/unitree/unitree_go2_stairs.yaml#L29-L48)).
  - It differs from `unitree_go2.yaml` only in:
    - `obstacleHeightThre` 0.3, where the comment says flat terrain uses 0.1;
    - `minPathScale` 0.8 (flat 0.6);
    - `minPathRange` 0.6 (flat 0.8);
    - `pathRangeStep` 0.45 (flat 0.5).
  - Vehicle 0.6 x 0.5 m, speed 0.875 m/s.
  - A `diff` of the two files confirms these are the only changes.
- **PCT -> local planner hand-off.** The PCT ROS 2 node publishes `/way_point` at a 2.0 m look-ahead on the PCT
  trajectory. It uses `step_max` 0.3, like our profile
  ([pct_planner_node.py L45, L52, L112, L313-327](https://github.com/dimensionalOS/PCT_planner/blob/ac7cf2ce8ce307f44abfb6b0765f0eba87d408e7/pct_planner/scripts/pct_planner_node.py#L45-L112)).
  - The stack pulls PCT as a submodule from `VectorRobotics/PCT_planner`.
  - `dimensionalOS/PCT_planner` is a fork of that fork, which in turn forks `byangw/PCT_planner` (GPL-2.0).
  - It is enabled with `use_pct_planner:=true` (jeff-hykin README L210-214, L274-278).
- **Provenance warning (primary source).** GitHub blocks `VectorRobotics/vector_navigation_stack` (HTTP 451, DMCA
  2026-05-22). Counsel for Dimensional, Inc. says the repository holds Dimensional code taken without authorisation
  (`github/dmca` `2026/05/2026-05-22-dimensional.md`).
  - The jeff-hykin and fukexue copies are unlicensed and share this lineage.
  - **Do not copy code from them.** The reusable content is a few parameter values and a look-ahead-waypoint
    pattern, which we can re-derive in the BSD CMU stack.
- **Stair evidence.** fukexue's README starts with a real-robot command that selects the stairs profile with PCT on a
  Unitree host. No success, failure or contact data are given.

## A3. dimos nav_3d: MLS planner and stair evaluator (Dimensional, Apache-2.0)

- **Repo.** <https://github.com/dimensionalOS/dimos>, `main` `26665a90f2d844e698eb0cf126373d9e3bd46a52` (4.5k stars;
  nav_3d commits up to 2026-09-08). LICENSE: Apache-2.0, Copyright 2025 Dimensional Inc.
- **Planner.**
  - "Standable" = a voxel column cell with at least robot-height free space above
    ([surfaces.rs L27-44](https://github.com/dimensionalOS/dimos/blob/26665a90f2d844e698eb0cf126373d9e3bd46a52/dimos/navigation/nav_3d/mls_planner/rust/src/surfaces.rs#L27-L44)).
  - Graph edges exceeding `step_threshold_m` are impassable, and a soft cost is added per metre of climb
    ([mls_planner.rs L70-75](https://github.com/dimensionalOS/dimos/blob/26665a90f2d844e698eb0cf126373d9e3bd46a52/dimos/navigation/nav_3d/mls_planner/rust/src/mls_planner.rs#L70-L75)).
  - Defaults: voxel 0.08 m, robot height 0.3 m, wall clearance 0.1 m, step 0.16 m
    ([mls_planner_native.py L40-52](https://github.com/dimensionalOS/dimos/blob/26665a90f2d844e698eb0cf126373d9e3bd46a52/dimos/navigation/nav_3d/mls_planner/mls_planner_native.py#L40-L52)).
  - Inputs are `global_map`, `local_map`, `region_bounds` and `goal`; the output is a 3-D `Path`
    (`module.rs` L47-80).
  - The path-gate docstring says the planner re-emits a path on every LiDAR frame
    ([dannav local_planner/module.py L17](https://github.com/dimensionalOS/dimos/blob/26665a90f2d844e698eb0cf126373d9e3bd46a52/dimos/navigation/dannav/local_planner/module.py#L17)).
    A holonomic tracking controller follows the gated path.
- **Evaluator (useful to us regardless of planner).**
  - It checks a Go2 body box only in the band 0.25-0.45 m above ground, so legs and terrain never count. It also
    checks ground support (0.35 m radius) and climb limits (`max_slope` 1.2, `max_step_m` 0.2). A code comment
    says these limits come from the steepest Go2 climbs on stairs
    ([evaluator/config.py L30-47](https://github.com/dimensionalOS/dimos/blob/26665a90f2d844e698eb0cf126373d9e3bd46a52/dimos/navigation/nav_3d/evaluator/config.py#L30-L47)).
  - Stair cases: `case_manifests/mid360_athens_stairs.yaml` has up/down start-goal pairs across about 3 m of height.
  - Git LFS data include `go2_mid360_stairs`, `mid360_athens_stairs`, `sf_office_stairs` and `go2_dds_stairs`
    archives (not downloaded).
- **Stair evidence.** Real MID-360 stair recordings and an offline planning harness exist. **No result table was
  found**; the docs pages describe only the 2-D Go2 stack (`docs/capabilities/navigation/index.md`,
  `deep_dive.md`).
- **Fit.** No ROS: it uses LCM, Rust and Python modules. Using it would need a ROS 2 bridge or a port of the Rust
  crate. The evaluator's body-band and support checks map directly onto our SCAN failure modes.

## A4. FAR planner and TARE

- `MichaelFYang/far_planner` `humble-jazzy` `29fb215886df4b0c53c27f487c51041f808c5eba`;
  `caochao39/tare_planner` `humble-jazzy` `b6760adb4280b379567c76f4e684ce628e28ef71`. No license on GitHub.
- Neither is a local planner. Both publish waypoints to the CMU base autonomy.
- Neither README mentions stairs. The simulated environments are campus, indoor, garage, tunnel and forest; the
  garage uses ramps.
- For us PCT already fills the route role.

## A5. Real_Time_Stair_Detector (Fan Yang)

- `MichaelFYang/Real_Time_Stair_Detector` `c61ebf595a74b2b47c1d5161e0401a37f2e2d566` (2022). No LICENSE file;
  `package.xml` L6 says BSD.
- It correlates a hand-made 2-D stair kernel with the live scan image (threshold 0.85).
- It publishes a Bool `is_stair` and stair poses (`stair_detector.cpp` L62-69).
- ROS 1. The README warns that it is tied to the CMU-OSU SubT platforms.
- Possible use: trigger an "approach stairs straight and slow" mode. It is not a planner.

## A6. ArtPlanner (extension of prior B6)

- `leggedrobotics/art_planner` `2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f` (last push 2023-08-09). BSD-3-Clause.
- **ROS 1 only.** README L72 says it was tested on ROS Noetic. No ROS 2 fork exists among roughly 30 forks; the
  one recent fork only adds CI.
- **Interfaces.** Input is an elevation `GridMap` (README L128); output is `nav_msgs/Path` (L134). The bundled
  path follower is described as "hacky and unsupported" (L92).
- **Planning methods.** The default planner uses a learned motion cost trained on ANYmal. For robots with different
  traversability the README recommends the purely geometric `lazy_prm_star_min_update` (L112).
- **Stair evidence (paper, via WebFetch, arXiv 2303.01420).**
  - The only case where it did not follow the exploration path over traversable terrain was the subway-station
    stairs. The old motion-cost weights gave high risk there.
  - Local map 8 x 8 m at 4 cm; target rate 0.5 Hz; goals from GBPlanner2; pure-pursuit PID follower.
  - The IROS 2021 predecessor (geometric reachability) is not on arXiv. Its stair results are **UNVERIFIED**.
- **Fit.** The reachability test (torso box free, foot boxes in contact) is the most principled step/obstacle rule in
  this family and could be ported into SCAN's collision check. As a whole planner it needs ROS 1 and
  elevation_mapping_cupy (GPU). The upstream main branch is ROS 1; ROS 2 exists only on dev branches, not checked.

## A7. field_local_planner (Oxford DRS; RSL fork)

- `ori-drs/field_local_planner` `f1f8f0fd5fcb38527026747eea469ff19cdd853e`, GPL-3.0.
  `leggedrobotics/field_local_planner` `70255f53f8f30d55684bbc377023677b9a64974f` is a fork 24 commits ahead
  (filter chains for WVN and elevation_mapping_cupy, twist topic changes).
- README L3 calls it SE(2) (planar) local planners. L10 says it supports only ROS 1.
- Plugins: RMP (Mattamala RA-L 2022), FALCO (port of CMU), APF, trackline.
- **Traversability** ([filter_chain.yaml L41-57](https://github.com/ori-drs/field_local_planner/blob/f1f8f0fd5fcb38527026747eea469ff19cdd853e/field_local_planners/field_local_planner_rmp/field_local_planner_rmp_plugin/config/filter_chain.yaml#L41-L57)):
  - half from slope, `1 - slope/0.6`;
  - half from a height threshold 0.3 m below `base`;
  - then an SDF and a geodesic field.
- **RMP paper** (arXiv 2201.03938, PDF text read). ANYmal C, 8 x 8 m map at 4 cm. The paper's words "stair" and
  "ramp" do not occur. The experiments are indoor clutter and an underground mine.
- **Stair evidence:** none.

## A8. PUTN and traversability_mapping

- **PUTN.**
  - `jianzhuozhuTHU/putn` `a12c900d0965a7a7ea3d4bb7408f8ccf3afdafad`, GPL-3.0, ROS 1 Melodic, "UGV" in the README.
  - PF-RRT* global planner, GPR traversability, NMPC local planner.
  - Plane-fit weights for flatness, slope and sparsity (`general.yaml` L16-27).
  - Scenes are slopes, forest and bridges. No stairs.
  - The only "successor" found is `WilsonGuo/MoveBase3D` (no license, UGV).
- **traversability_mapping.**
  - `TixiaoShan/traversability_mapping` `ab9f2b37e42b902df6dd22c62e15e840032fcc90`, GPL-3.0, ROS 1, VLP-16 UGV.
  - Step difference threshold 0.10/0.15 m and slope 20 deg (`utility.h` L93-94), so stairs are obstacles.

## A9. TRG-planner

- `wasahaiah/TRG-planner` `fc6f1e47d1e642eedcf87892f341794dc91890ec`. The README badge points to
  `url-kaist/TRG-planner`, which returns 404.
- License: Apache-2.0 **with Commons Clause** (README L125), which restricts selling.
- ROS 1 Noetic and ROS 2 Humble. It is a global planner on a prebuilt map (`indoor.yaml`: `heightThreshold` 0.15,
  `robotSize` 0.3).
- Paper, via WebFetch (arXiv 2501.01806): global planner of the team that won the ICRA 2023 Quadruped Robot
  Challenge. Stairs are not stated.
- An alternative to PCT, not a local planner.

## A10. mesh_navigation (MeshNav)

- `naturerobots/mesh_navigation` `main` `2fd7ada704a48d4b463746cad1268fe9f9ea2220`, BSD-3-Clause, ROS 2
  Humble/Jazzy. It uses Move Base Flex.
- Layers: HeightDiff, Roughness, Steepness, Ridge, Clearance, Inflation.
- Controllers: vector field and MeshMPPI, which is DiffDrive/Bicycle only per the README table.
- The steepness layer header says it is useful to **avoid** stairs
  ([steepness_layer.h L47](https://github.com/naturerobots/mesh_navigation/blob/2fd7ada704a48d4b463746cad1268fe9f9ea2220/mesh_layers/include/mesh_layers/steepness_layer.h#L47)).
- Needs a mesh map. No stair-climbing evidence.

## A11. Nav2 MPPI plus elevation layers

- Nav2 has no step concept; its obstacle band is fixed in world z (prior notes B7). MPPI consumes the same 2-D
  costmap.
- Community plugins found:
  - `SirErico/nav2_gridmap_traversability_layer` `7c1d538a` (BSD-3, ROS 2 Jazzy, consumes elevation_mapping_cupy
    traversability);
  - `abulhasnat-abdullah/nav2_traversability_layer` `ad8f66f1` (MIT, slope/step/roughness from FastDEM; created
    2026-09-11);
  - `Ikhyeon-Cho/FastDEM` (BSD-3, ROS 1/2 elevation mapping; **not pinned or read**).
- None has stair evidence. A 2-D costmap also cannot represent overlapping stair flights.

## A12. Stair hand-off stacks (pattern references)

- `Xiong-z-x/go2w_navigation_stack` `8b738dcf` (no license, ROS 2 Humble, Gazebo Fortress only).
  - Nav2 runs flat segments and a `/stair_exec` skeleton runs stair edges ("flat/stair/flat gate").
  - Simulation-only acceptance docs. Go2-W is wheeled-legged.
- `real-lsy/That-nav` `38b12d8d` (Apache-2.0, Go2-W + MID-360). The README tells the user to switch the robot to its
  stair-climbing mode by remote or app, so there is no autonomous stair logic.
- `tu-darmstadt-ros-pkg/hector_stairs_planner` `724a18ad` (BSD-3, ROS 1, 2020, tracked robots).
  - SBPL planner with forward-only motion primitives.
  - A `hector_change_map` node switches map layers at stairs.
  - Same idea as our need for a straight stair approach.

## A13. Leads without usable code

- **RAEM** (arXiv 2608.25366, paper via WebFetch).
  - Go2 with a single MID-360.
  - The local planner is a modified EGO-Planner on a rolling inflated 3-D grid. That grid has four states:
    unknown, occupied, free and **traversable**. The traversable state comes from a local tomography map, with
    clearance and gradient criteria.
  - Reported: complete exploration of multi-floor structures and a five-floor stairwell. No numbers were read.
  - Code "upon acceptance". `Shua1ge/quadruped_exploration_planner` (BSD-3, 2026-09-04) says it is based on RAEM
    but holds only a package skeleton.
  - The method is the closest to adding a terrain class to SCAN's occupancy map.
- **Quad-SDK** (`robomechanics/quad-sdk` `50b58ce8`, MIT, ROS Noetic). Model-based footstep/NMPC locomotion
  stack. No stairs in the README, and it has no cmd_vel output to a blind policy. Excluded.
- **DeepRoboticsLab/Lite3_Navigation** `b091cee1` (no license). hdl localization plus fast_gicp; no stair planner.
- **Learned planners with stairs** (ViPlanner, iPlanner, FDM, SRU): family B, not assessed here.

---

## Fit analysis for our chain (lead proposal, not evidence)

Our needs:
1. Tell treads and nosings apart from obstacles.
2. Take PCT's route as guidance.
3. Hand V12 a straight, moderate-speed approach to stairs via cmd_vel.
4. Build on Foxy (bridge) or Humble (PCT).

**Strongest candidates.**

1. **CMU base autonomy (autonomy_stack_go2, `foxy-humble`), with a stairs-tuned profile and a PCT look-ahead
   waypoint node.**
   - The only stair-capable geometric local planner found that already builds on Foxy and Humble, takes a waypoint
     and outputs cmd_vel.
   - It separates steps by height above local ground, which is the rule SCAN lacks.
   - The PCT -> `/way_point` pattern exists in Dimensional's fork. Re-implement it; do not copy.
   - Gaps: no stair evidence anywhere; tread-depth sensitivity and overhead-flight obstacles (derived); no
     heading-alignment rule.
2. **dimos nav_3d evaluator (Apache-2.0) as an offline stair benchmark, and the MLS planner as an algorithm
   reference.**
   - It is the only open code with a Go2-sized body band, ground-support and step checks plus real MID-360 stair
     recordings.
   - Not ROS; no published results.
3. **ArtPlanner's geometric reachability check (BSD-3).**
   - Best-founded step-versus-obstacle rule: torso box clear, feet reach ground.
   - A candidate to port into SCAN's footprint check rather than to adopt whole (ROS 1, ANYmal, 0.5 Hz, path
     only).
4. **RAEM's method (paper only).**
   - EGO-lineage local planner plus a live tomography "traversable" class, on a Go2 with MID-360 over a
     five-floor stairwell.
   - Closest to fixing SCAN in place. Code is not released.
5. **Stair-mode trigger** (Real_Time_Stair_Detector or PCT-map stair tags) with a straight approach at bounded
   speed, as in the hand-off stacks. Useful whichever local planner is chosen, because V12 is blind.

## UNVERIFIED items

- Any stair success, failure or contact data for the CMU stacks, the Dimensional stairs profile and the dimos MLS
  planner. None was found.
- ArtPlanner IROS 2021 stair experiments; ArtPlanner and field_local_planner behaviour on stairs; ROS 2 dev
  branches of elevation_mapping_cupy.
- RAEM numbers, controller (built-in or RL) and code release. TRG-planner stair tests.
- FastDEM (not read). dimos LFS stair datasets (not downloaded).
- Paper summaries obtained through WebFetch (ArtPlanner, TRG, RAEM) need a PDF check before citation.
- The derived stair behaviour of CMU terrain analysis (window, crop, overhead) has not been simulated.

## Claim boundary

`surveyed` only. Commits are branch heads read on 2026-09-18. Licenses are GitHub SPDX or the files read; unlicensed
or disputed code (A2) must not be copied.
