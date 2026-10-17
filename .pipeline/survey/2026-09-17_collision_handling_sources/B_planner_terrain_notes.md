---
origin: ai+web
reviewed: false
date: 2026-09-17
status: surveyed
stage: planning
family: B - navigation stacks, step/stair vs obstacle separation, clearance
---

# B. Planner terrain handling and clearance: notes

**Scope.** How navigation stacks separate traversable terrain (steps, stairs) from obstacles, and what clearance
they keep. The survey starts with our own PCT -> SCAN -> V12 pipeline. Nothing was cloned into the project,
installed, built or run. Every item is `surveyed` only. None is reproduced, integrated or validated.

**Method.**
- Upstream code: read at pinned commits through `gh api .../contents/PATH?ref=SHA`. Temporary copies are in the
  session scratchpad, not in the project.
- Local code: our vendored PCT-SCAN files. The mapping, FSM, optimizer, A*, config and PCT files listed below are
  byte-identical to upstream pin `1cf45a1c`. I checked this with `diff` against `gh api` content.
- Papers: arXiv HTML pages read through WebFetch, which returns a model-written summary. Every paper number below
  therefore needs a check against the PDF before anyone cites it in writing. These items are marked **(paper, via
  WebFetch)**.
- Derived numbers: computed by me from code and config. They are marked **(derived)**.

---

## B1. Our pipeline: PCT global planner (tomogram)

- **Repo.** <https://github.com/byangw/PCT_planner>
- **License.** GPL-2.0 (GitHub SPDX). The README states GPLv2. The PCT-SCAN NOTICE says GPL-2.0-or-later.
- **Commit.** `35cd73fd82bcd51bc538429294af7646b2a09815` (HEAD, 2025-02-17).
- **Paper.** Yang, Cheng, Xue, Jiao and Liu, *Efficient Global Navigational Planning in 3-D Structures Based on
  Point Cloud Tomography*, IEEE/ASME TMECH 2024, [arXiv 2403.07631](https://arxiv.org/abs/2403.07631).
- **Our copy.** `references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_global/src/pct/`.
  - It comes from the PCT-SCAN-ROS2 pin.
  - Tomography logic is the same as upstream. The diffs are only a `float16` typo in upstream `getIndexLine`,
    packaging changes, and stub bodies for two unused A* methods.

### How the tomogram encodes terrain

**Slices** ([kernels.py L99-130](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/kernels.py#L99-L130)).
- For each 2-D cell and slice height `h0 + k*slice_dh`:
  - ground `G` = the highest point at or below the slice;
  - ceiling `C` = the lowest point above it.
- Interval = `C - G` ([tomogram.py L121](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/tomogram.py#L121)).

**Step/slope signal** (tomogram.py L110-119).
- `grad_mag_sq`: the sum of the squared maximum x and y neighbour height differences of `G`, on a 0.1 m grid.
- `grad_mag_max`: the larger of those two squared differences.

**Traversability kernel** ([kernels.py L143-183](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/kernels.py#L143-L183)).
Checks run in this order:
1. Interval `< interval_min` gives a **barrier** (`cost_barrier`, 50). Otherwise add `20*max(0, interval_free - interval)`.
2. `grad_mag_sq <= step_stand^2` means **standable**: add up to 15.
3. Otherwise, `grad_mag_max <= step_max^2` means a **crossable step**. It must still have at least `standable_th`
   standable cells in a `kernel_size^2` window. If it does, add up to 20. If not, it is a barrier.
4. Otherwise it is a **barrier**.

Parameter definitions ([tomogram.py L14-20](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/tomogram.py#L14-L20)):
- `step_stand = 1.2*res*tan(slope_max)`;
- `standable_th = int(ratio*k^2) - 1`;
- `half_inf_k = int((safe_margin+inflation)/res)`.

**Steps versus obstacles.** A cell edge is a step only if it passes both tests below. Anything taller, or anything
without enough flat cells around it, is an obstacle:
- the neighbour height jump is at most `step_max`;
- enough nearby cells are flat.

**Inflation** ([tomogram.py L54-63](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/tomogram.py#L54-L63), [kernels.py L201-226](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/scripts/kernels.py#L201-L226)).
- `inflated = max over window(cost * w)`, with `w = clip(1 - (d - inflation)/(safe_margin + res), 0, 1)`.
- Full cost applies out to `inflation`, then falls linearly to zero at `inflation + safe_margin + res`.

**Search and optimizer thresholds.**
- The wrapper calls `init_map(20, 15, res, n_slice, 0.2, ...)`
  ([planner_wrapper.py L79-80](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/planner/scripts/planner_wrapper.py#L79-L80)).
  The arguments are A* cost threshold 20, optimizer `safe_cost_margin` 15, and step-cost weight 0.2.
- A* ([a_star_search.cc L148-165](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/planner/lib/src/a_star/a_star_search.cc#L148-L165)):
  - it skips cells with cost above 20;
  - exception: gateway cells (layer transitions, `|ele| >= 0.5`) are allowed when the height change is at most 0.3 m;
  - step costs below 5 are zeroed.
- The GPMP obstacle factor penalises `(cost - 15)^2` only above 15. Source: our copy's
  `pct_planner/lib/src/trajectory_optimization/gpmp_optimizer/factors/gp_obstacle_factor.cc` lines 17-22.
- Output height is ground plus `reference_height_` (default 0.1 m), smoothed below the ceiling. Source: our copy's
  `gpmp_optimizer.cc` L193-200 and `gpmp_optimizer.h` L66.

**Upstream Building scene defaults** ([scene_building.py L13-22](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/config/scene_building.py#L13-L22)):
res 0.10, slice 0.5, kernel 7, interval_min 0.50, interval_free 0.65, slope_max 0.40, **step_max 0.17**,
standable_ratio 0.20, barrier 50, safe_margin 0.4, inflation 0.2.

### Our executed tomogram profile (`preflight03`)

- **Source.** `machine-dog-nav/.pipeline/experiments/2026-09-08_new_building_pct/runs/preflight03/generation.json`
  lines 5-18, with the README at lines 18 and 24-29.
  - This directory is **untracked** in machine-dog-nav (`??`), so treat it as a lead.
  - The tomogram SHA `ab5499ff...` matches `baseline_config/pct_inputs.json`.
- **Values.** res 0.10, slice 0.5, kernel 7, interval_min 0.5, interval_free 0.5, slope_max 0.4, **step_max 0.30**,
  standable_ratio 0.5, barrier 50, **safe_margin 0.5, inflation 0.1**.
  - The machine-dog-nav README says step 0.30 was the scene author's value.
  - With step_max 0.17 (preflight04), no cross-floor path was found.
- **(derived)**
  - `step_stand` = 0.051 m.
  - `standable_th` = 23 of 49 cells (upstream: 8).
  - `half_inf_k` = `int(5.999...)` = 5 cells, because of float rounding, where 6 might be expected.
  - Inflated barrier cost is 50 out to 0.1 m, 41.7 at 0.2 m, 33.3 at 0.3 m, 25 at 0.4 m and 20.8 at 0.45 m.
    It is 16.7 at 0.5 m, where the kernel is cut off.
  - So **PCT A\* keeps cell centres at least ~0.46 m from barrier cells** (cost at most 20). The optimizer term
    (cost above 15) acts out to ~0.5 m.
- **Soft centreline bias (lead).** The machine-dog-nav README also records `preferred_clearance` 0.50 m and
  `clearance_cost` 20.
  - This is PCT-SCAN's `DynamicLayerTomogramPlanner`
    ([dynamic_planner.py L16-19, L47-55](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/integration/pct_scan_bridge/pct_scan_bridge/dynamic_planner.py#L16-L55)
    and
    [clearance_cost.py L9-60](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/integration/pct_scan_bridge/pct_scan_bridge/clearance_cost.py#L9-L60)).
  - It adds a linear soft cost within the preferred clearance of any cell above threshold, capped at 20. It never
    closes a passage.
  - It uses step weight 1.0, and costs below 5 are still zeroed. The bias therefore only acts within about 0.375 m
    of the boundary **(derived)**.
  - **UNVERIFIED:** whether our p2b/native runs loaded this wrapper. `pct_inputs.json` hashes only the four
    `pct_planner` modules.
- **Implication for a later stairs test (derived).** A mapped box with a flat top up to 0.30 m tall can be classified
  as a *crossable step* in our profile, not as an obstacle. This matters only for mapped objects.

### Paper, via WebFetch (arXiv HTML)

- **Table I.**
  - `[d_s, d_min, d_ref]` = [0.50, 0.50, 0.65];
  - `[theta_b, theta_s, theta_p]` = [1.70, 0.36, 0.20]. Here theta_b is a gradient: 1.7 x 0.1 m = 0.17 m step,
    matching `step_max`.
  - `[c_B, alpha_d, alpha_b, alpha_s]` = [50, 20, 20, 15].
- **Eq. 6** inflates untraversable cells by `d_inf >= r_c` and adds a safe margin `d_sm`.
- **Real-world test.** A DeepRobotics **Jueying Mini** quadruped on stairs and boxes.
- **Metrics.** Planning time, optimization time, length, curvature, success, and nodes visited.
- **Collisions and failures.** No collision or contact counts are reported. "Failure" means no solution found.
- **Limitations.**
  - The method needs a dense, high-quality prior point cloud.
  - It does **not** handle unmapped or dynamic obstacles.
  - The authors say missing terrain information in unobserved regions may lead to dangers.
  - The PDF has not been re-read. Section numbers are **UNVERIFIED**.

**Consequence.** PCT never sees an unmapped box. On the real robot its route depends on the prior map and SLAM
relocalization. All live obstacle handling falls to SCAN.

---

## B2. Our pipeline: SCAN local planner, as in PCT-SCAN-ROS2

**Repos, licenses, commits.**

| Repo | Commit | License |
|---|---|---|
| PCT-SCAN-ROS2 ([link](https://github.com/yagami-light7/PCT-SCAN-ROS2)) | `1cf45a1c12ca785ce533293302be09d51daf0ccb` (our pin, HEAD 2026-08-08) | Multi-license. SCAN packages Apache-2.0; PCT, tomography and the bridge GPL-2.0-or-later; `local_sensing_node` and `mockamap` GPL-3.0-only; Go2 packages BSD-3-Clause. GitHub reports NOASSERTION. |
| SCAN-Planner, original ([link](https://github.com/wuyi2121/SCAN-Planner)) | `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` (HEAD 2026-07-29) | Apache-2.0 |

- License sources: our copy's `NOTICE`, `THIRD_PARTY_NOTICES.md` and `LICENSE`.
- **What "SCAN" means.** **S**patial **C**ollision-**A**ware local planning for route-guided long-range quadruped
  **N**avigation. Zheng, Chen, Fu, Yang and Qin, [arXiv 2606.19555](https://arxiv.org/abs/2606.19555), submitted
  2026-06-17.
  - The optimizer code is EGO-Planner lineage: a comment in `bspline_optimizer.cpp` L58-60 dates it to 2020.
  - The upstream defaults are tuned for Unitree Go2
    ([README L101](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/README.md?plain=1#L101)).
- **Our copy.** `references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base/src/`.
  - The executed Foxy port (`pct_scan_foxy`) changes only callback signatures in `grid_map.cpp` and `.h`.
  - It also adds a body-to-world twist rotation in `scan_replan_fsm.cpp` L423-428. I checked this with `diff`.
  - No mapping or collision logic changed.

In the table below, "pin" means the path at `1cf45a1c` (for example `src/planner/plan_env/src/grid_map.cpp`).
Local line numbers equal pin line numbers.

### Our executed values

From `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/baseline_config/planner.yaml`.

| Item | Our value (planner.yaml line) | Upstream SCAN default | Mechanism (code) |
|---|---|---|---|
| Voxel resolution | 0.05 m (L12) | 0.05 | 3-D log-odds occupancy |
| Local map (sliding) | 10 x 10 x 5 m (L13-15), re-centred on the sensor when it moves 0.2 m (L19-20) | same | `grid_map.cpp` L324-421 |
| Local update range | +/-5 x 5 x 2.5 m (L16-18) | same | cloud points outside are skipped unless beyond max ray (`grid_map.cpp` L917-923) |
| Max ray length | 5.0 m (L46) | 5.0 | longer rays are truncated and mark free (L579-593) |
| Hit/miss probabilities | p_hit 0.85, p_miss 0.30, clamp 0.12-0.98, occupied if above 0.80 (L41-45) | same | (derived) log-odds +1.735 / -0.847. From unknown, **2 hit-scans** are needed to become occupied. From saturated, **3 miss-scans** clear a voxel. Per scan, hits and misses are voted per voxel (L678-703). |
| Decay | none | none | Occupancy persists until ray-cleared or slid out. No time decay. |
| Ground removal | **none in SCAN** | none | `cloudCallback` (L872-938) inserts every finite point. Upstream SCAN `grid_map.cpp` L856 behaves the same. |
| Bridge terrain filter | **off**: `unfiltered_planner_cloud: true`, `native_policy.terrain_filter: false` | n/a | A local-minimum filter exists (0.3 m cells, 0.12 m threshold) but was disabled. See `native_nominal_scope.json` L35-43, L141-148 and the bridge `isaac_adapter_core.py` L410-500 / `run_pct_scan_building.py` L1089-1115. |
| Horizontal inflation | `double_cylinder_radius` 0.25 (L21) | 0.25 | offsets with norm **strictly < 0.25** (`grid_map.cpp` L208-226). (derived) At 0.05 m that reaches **0.20 m on the axes and 0.224 m at most**. |
| Footprint | two discs at **+/-0.18 m** along heading (L22) | 0.18 | `getInflateOccupancy` checks the front point, then the rear point (`grid_map.h` L371-389) |
| Vertical inflation | z_up 0.1, z_down 0.1 (L24-25), each 2 voxels | 0.1 / 0.1 | a query at z is flagged by occupied voxels in about **[z-0.10, z+0.15)** (derived, voxel-quantised) |
| body_height | **0.0** (L23), because the route is already a body reference at 0.35 m nominal (L1 comment; `native_nominal_scope.json` L122-126) | **0.4** added to the ground route | `reference_path_utils.h` L119 |
| Optimizer clearance | `dist0` 0.2 m, `lambda_collision` 1.0 (L56, L59) | same | See the optimizer paragraph below. |
| Safety check | every 50 ms (fsm L78-79) | same | See the safety-check paragraph below. |
| Speed limits | max_vel 1.0, max_acc 0.5 (L49-50, L60-61) | 0.75 / 0.5 | |

Two unit-level notes on the table above:
- `sliding_map_thresh` is 0.2 m; that is the re-centring distance.
- The vertical window from z_up/z_down is asymmetric after quantisation, hence `[z-0.10, z+0.15)`.

**Optimizer clearance.**
- `dist0` 0.2 m sets `cps_.clearance` (`bspline_optimizer.cpp` L64-67).
- Base points sit on the boundary of the *inflated* footprint map (L274-296).
- The cost is a cubic/quadratic penalty on `dist0 - dist` (L402-441). It is zero once the control point is 0.2 m
  outside the inflated boundary.
- It is a **soft** rebound margin, applied only to control points in detected collision segments.
- Acceptance is a hard check on the **inflated footprint only**, over the first 2/3 of the trajectory (L1017-1040).
- If that check fails, `lambda_collision` doubles and the optimizer restarts, up to 3 times (L979, L1049-1051).

**Safety check.**
- Every 50 ms, the first 2/3 of the current trajectory is checked with the footprint (fsm L855-900).
- If a collision is found, SCAN replans.
- If replanning fails and the collision is less than `emergency_time` 1.0 s ahead (planner.yaml L9), the FSM enters
  `EMERGENCY_STOP`. It then publishes a stop spline at the odometry pose (L715-739, L950-984).
- `fail_safe` true (L10) lets it replan once the speed is below 0.1 m/s.
- After `max_replan_fail_count` 1000 failures it stops and waits for a new target (L748-759).

**Other behaviours (code facts).**
- **Unknown space is free.** Only occupied voxels are inflated (`grid_map.h` L309-337, L371-389). Out-of-map returns
  -1, which callers treat as occupied (fsm L876, L1028-1032).
- **Blocked targets move.** An occupied local target is shifted along the global route to the nearest free sample
  (fsm L1032-1060). An occupied final target is pulled back (L306-345).
- **A\* is 2.5-D.** It expands 8-connected in xy on a plane whose z is interpolated linearly from start to goal
  (`dyn_a_star.cpp` L169-180, L227-259), with the same yaw-aware footprint check (`dyn_a_star.h` L69).

### Stair edge versus box in SCAN (code facts plus derivation)

**No semantic distinction exists.** Both are just occupied voxels from LiDAR returns. The only discriminator is
geometric: does an occupied voxel lie inside the vertical slab around the trajectory point, and within ~0.20-0.22 m
horizontally of the front or rear disc centre?

**(derived) Our 0.35 m body reference.**
- The slab is about **0.25-0.50 m above the route's ground**, give or take one voxel.
- **Box (unmapped).**
  - Top about 0.25-0.30 m or higher: side and top hits fall inside the slab, so it is an obstacle.
  - Top below about 0.25 m: SCAN ignores it, so V12 must step over it or onto it.
- **Stair.**
  - Treads and risers are ignored while they stay below the slab.
  - On an ascent the front disc (0.18 m ahead) sits over higher ground. The nosings are higher than the smoothed
    route line.
  - So stair geometry can enter the slab and trigger replans or `EMERGENCY_STOP`. This is an inference; it has not
    been measured.

**Upstream guidance matches this.**
- SCAN README L98: raise body, keypoint or path height if the robot cannot climb stairs.
- The paper defines the down-clearance as nominal centre height minus the maximum traversable step height:
  `d_down = h_centre - d_step` **(paper, via WebFetch)**. For us, (derived) d_step is about 0.25 m.
- PCT-SCAN-ROS2 README
  [L217-218](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/README.md?plain=1#L217-L218):
  video mode defaults to `enable_local_sensing:=false`. PCT then owns traversability, so that the dense stair cloud
  is not inflated into a closed obstacle by SCAN.
- The PCT-SCAN "validation" is an **RViz Go2 kinematic animation** (README L3, L21, L28-33). It has no physics and
  no contact evaluation.

**Mismatch to note (derived).**
- PCT allows steps up to 0.30 m in our profile. SCAN's implicit d_step is about 0.25 m.
- Features between 0.25 and 0.30 m pass the global planner but can block SCAN.

### SCAN paper, via WebFetch (arXiv HTML v1)

**Method.**
- Yaw-aware twin-cylinder footprint with clearances `d_xy`, `d_up` and `d_down` (Section IV-B).
- Height-regularised initialisation: z follows a linear profile (Section IV-C1).
- No explicit ground removal is described.

**Evaluation.**
- Simulator: MARSIM, which appears kinematic or LiDAR-rendering only. **UNVERIFIED** whether it has any physics.
- 50 trials per scene, 120 s timeout. Metrics are SR, CR and SPL (Table II).
- Only the Dense Obstacles scene is quantified:

  | Planner | SR | CR |
  |---|---|---|
  | SCAN | 1.00 | 0.00 |
  | EGO-2D | 0.96 | 0.04 |
  | EGO-3D | 0.76 | 0.24 |
  | CMU-Planner | 0.92 | 0.08 |
  | ART-Planner | 0.44 | 0.56 |

- Stairs, multi-floor and real-world results (Mid-360 LiDAR) are qualitative only.
- No clearance or minimum-distance metric is reported.
- **The collision definition is not stated (UNVERIFIED).**
- No failure cases are described.
- The paper's future work mentions terrain analysis.

---

## B3. Harness fact that gates the unmapped-box test

This is not part of the navigation stack, but it decides whether SCAN can see the box at all.

**Sources.**
- `references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge/lite3_sim_bridge/run_pct_scan_building.py`
  L421-431.
- `run_isaac_v12_fallback.py` L2121-2136 and L2987-2995.

**What they show.**
- The Building navigation LiDAR ray-casts **only** against `/World/ground` and the merged
  `/World/ground/terrain` mesh, with `track_mesh_transforms=False`.
- The older fallback runner adds `/World/ground/scan_obstacle` only for `--course single_box`.

**Consequence.** A new box prim must be added as a ray-cast target before the test. If the box can move, it also
needs tracked transforms. Otherwise the simulated LiDAR, and so SCAN, never sees it. Confirm this with box hit
counts before judging the planner.

**Sensor geometry.**
- 16 channels, -7 to +52 degrees vertical, 2 degree horizontal resolution, 0.1-12 m range, 10 Hz.
- Mounted +0.182 m forward and +0.109 m up, pitched 15 degrees (`native_nominal_scope.json` L23-36).
- Pitch direction: a rotation about +y by `sensor_pitch_degrees` (fallback L2121-2126).
- **UNVERIFIED** whether that pitch points the sensor down. Check it by render before computing the near blind zone.

---

## B4. CMU autonomy stack: terrain_analysis and local_planner

**Repos.**

| Repo | Branch | Commit | License |
|---|---|---|---|
| [HongbiaoZ/autonomous_exploration_development_environment](https://github.com/HongbiaoZ/autonomous_exploration_development_environment) | `noetic` | `bf0cba71365271ebff09831a05afd78578150300` | No root LICENSE. `package.xml` declares **BSD**. |
| [jizhang-cmu/autonomy_stack_go2](https://github.com/jizhang-cmu/autonomy_stack_go2) | `foxy-humble` | `43d5f54b389b251713f0097893c30fa76c870d54` | No root LICENSE. `local_planner/package.xml` declares BSD. |

**Steps versus obstacles.** Terrain analysis builds a relative-height cloud
([terrainAnalysis.cpp L502-574](https://github.com/HongbiaoZ/autonomous_exploration_development_environment/blob/bf0cba71365271ebff09831a05afd78578150300/src/terrain_analysis/src/terrainAnalysis.cpp#L502-L574)):
- The ground elevation of each 0.2 m planar voxel is its minimum z, or a quantile when `useSorting`.
- Each point's intensity is its height above that local ground, `disZ`.
- A point is kept if `0 <= disZ < vehicleHeight`, which is 1.5 m in
  [launch L24](https://github.com/HongbiaoZ/autonomous_exploration_development_environment/blob/bf0cba71365271ebff09831a05afd78578150300/src/terrain_analysis/launch/terrain_analysis.launch#L24).
- `considerDrop` uses `|disZ|`, so drops count as obstacles.
- Decay: 2 s beyond 4 m (`decayTime` and `noDecayDis`, launch L5-6). Dynamic-obstacle clearing is on.
- `noDataObstacle` is false in the base stack and **true** in the Go2 stack (L21).

The local planner then thresholds that height
([localPlanner.cpp L754-759](https://github.com/HongbiaoZ/autonomous_exploration_development_environment/blob/bf0cba71365271ebff09831a05afd78578150300/src/local_planner/src/localPlanner.cpp#L754-L759)):
- A point with `h > obstacleHeightThre` blocks path candidates.
- A point with `groundHeightThre < h <= obstacleHeightThre` only adds a penalty.

Thresholds:

| Setting | obstacleHeightThre | groundHeightThre | Vehicle | Source |
|---|---|---|---|---|
| Base stack | 0.15 m | 0.10 m | 0.6 x 0.6 m | [local_planner.launch L16-29](https://github.com/HongbiaoZ/autonomous_exploration_development_environment/blob/bf0cba71365271ebff09831a05afd78578150300/src/local_planner/launch/local_planner.launch#L16-L29) |
| Go2 stack | **0.30 m** | n/a | 0.3 x 0.7 m | [local_planner.launch L18-29](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/launch/local_planner.launch#L18-L29) |

- The code default for `obstacleHeightThre` is 0.2 (L48).
- The Go2 README says to keep every obstacle **> 0.3 m** tall, because the L1 LiDAR cannot distinguish low
  obstacles
  ([README L204](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/README.md?plain=1#L204)).

**Clearance.**
- Pre-computed path/voxel correspondences use `searchRadius` 0.45 m (`localPlanner.cpp` L85; `path_generator.m`
  L113-114).
- The planner scales paths down (`pathScale`) and then shortens range until some path is free.
- If none is free, it publishes a single zero pose, so the robot stops (L918-925).
- `pathFollower` also honours an external `/stop` topic (L176-178, L329-330).

**Evaluation.** Collision statistics in the CMU papers were **UNVERIFIED**; I read only the arXiv 2110.14573
abstract. The SCAN paper uses "CMU-Planner" as a baseline: CR 0.08 in dense obstacles.

---

## B5. ETH elevation mapping and traversability filters

### leggedrobotics/elevation_mapping_cupy

- **Repo:** [link](https://github.com/leggedrobotics/elevation_mapping_cupy). **License:** MIT.
- **Commit:** `20a8a26b67a995b43eb44c23568854d1fed82a52` (main HEAD, 2025-05-14).

**Traversability.**
- It is a **learned** small CNN over the elevation layer: three dilated 3x3 conv branches plus a 1x1 output, weights
  from `weights.dat`
  ([traversability_filter.py L12-40](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/elevation_mapping_cupy/script/elevation_mapping_cupy/traversability_filter.py#L12-L40)).
- There are no explicit step or slope thresholds in this repo.
- How it was trained is **UNVERIFIED**; the paper abstract, arXiv 2204.12876, does not say.

**Virtual ceiling.**
- Points higher than `max_height_range` 1.0 m above the sensor are dropped.
- A distance-ramped limit also applies: `z > max(d - 1.0, 0)*0.3 + 0.2`
  ([core_param.yaml L22-25](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/elevation_mapping_cupy/config/core/core_param.yaml#L22-L25)).

**Footprint safety check** (L36-38). A polygon is unsafe if either condition holds:
- any cell is below 0.4;
- more than 10 cells are below 0.7.

### leggedrobotics/traversability_estimation (explicit filters, ROS 1)

- **Repo:** [link](https://github.com/leggedrobotics/traversability_estimation).
- **License:** BSD-style text, Copyright 2015 Peter Fankhauser. GitHub reports NOASSERTION.
- **Commit:** `14d24c059e1c43466aadf328280adf6394d78039`.

**Filters.** Slope, step and roughness scores are averaged
([robot_filter_parameter.yaml L10-33](https://github.com/leggedrobotics/traversability_estimation/blob/14d24c059e1c43466aadf328280adf6394d78039/traversability_estimation/config/robot_filter_parameter.yaml#L10-L33)).
- **Slope:** critical 1.0.
- **Step:** critical height **0.12 m**, windows 0.04 m, 4 critical cells.
  - Score = `1 - step/critical`, and 0 above the critical height (`StepFilter.cpp` L165-173).
- **Roughness:** 0.05.

**Footprint.** 0.9 x 0.6 m polygon, circle radius 0.541 m (`robot_footprint_parameter.yaml` L3-6).

---

## B6. leggedrobotics/art_planner (ArtPlanner)

- **Repo:** [link](https://github.com/leggedrobotics/art_planner). **License:** BSD-3-Clause.
- **Commit:** `2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f` (HEAD, 2023-08-09).

**Steps versus obstacles: reachability abstraction.**
- **Torso.** The torso box must be **collision-free** against the height map. The code uses ODE box-heightfield
  `dCollide`
  ([height_map_box_checker.cpp L15-24, L58-72](https://github.com/leggedrobotics/art_planner/blob/2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f/art_planner/src/validity_checker/height_map_box_checker.cpp#L15-L72)).
- **Feet.** Per-foot reach boxes (0.2 m cubes offset below the hips) must **touch** terrain.
- **Size and offsets** ([params.yaml L53-71](https://github.com/leggedrobotics/art_planner/blob/2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f/art_planner_ros/config/params.yaml#L53-L71)):
  ANYmal torso 1.31 x 0.65 x 0.3 m.
- **Why steps pass.** A step is traversable because the torso box clears it while the foot boxes still reach
  ground.

**Safety settings** ([params.yaml L8-18](https://github.com/leggedrobotics/art_planner/blob/2f3fde68b8ac55f6f91083acc4d09df2b10f3c1f/art_planner_ros/config/params.yaml#L8-L18)):
- `traversability_thres` 0.15;
- `unknown_space_untraversable: true`;
- foothold erosion margin 0.3 m, which ignores holes up to 0.3 m, drops up to 0.3 m and steps of at least 0.3 m;
- learned motion-cost risk threshold 0.5, with risk weight 5 (L32-37).

**Paper** (Wellhausen and Hutter, *ArtPlanner*, Field Robotics 2023, [arXiv 2303.01420](https://arxiv.org/abs/2303.01420)),
**via WebFetch**:
- **Deployment.** DARPA SubT Finals, four ANYmal-C robots, 90 min, with no planning or locomotion failure
  (abstract).
- **Metrics (Table 1)** are computed over planned path poses:
  - "collision" = any path pose intersecting the environment;
  - "severe" = more than 1/3 of poses in collision.
- **Results.**

  | Planner | Any collision | Severe collision |
  |---|---|---|
  | ArtPlanner | 4.50% | 0.05% |
  | Motion-cost baseline | 25.44% | n/a |
  | Exploration path + cost optimizer | 37.17% | n/a |

  The authors attribute the residual collisions to map changes, artifacts and drift. They report actual physical
  collisions separately: 1 during the event.
- **Stairs.** At subway-station stairs, older network weights produced elevated risk.
- **Other failures.** Negative-obstacle risk at a platform edge was mitigated by foothold erosion. The robot caught
  a scaffolding pole because of 500 ms latency and map artifacts.
- **Stance on contact.** The authors note learned-cost planners may graze obstacles. They argue even slight bumps
  should be avoided, because they can snag the robot or damage its payload.
- Section and table numbers are **UNVERIFIED** against the PDF.

---

## B7. Nav2 obstacle/voxel layers and STVL (2-D costmaps)

### ros-navigation/navigation2

- **Repo:** [link](https://github.com/ros-navigation/navigation2). **Commit:** `e9b5a24b057835e51d216d564ea99b94d3b33690`
  (main, 2026-09-18).
- **License:** the repo is NOASSERTION. `nav2_costmap_2d/package.xml` declares BSD-3-Clause and Apache-2.0.

**Height filtering.** `min_obstacle_height` and `max_obstacle_height`:
- default 0 and 2.0 at layer level
  ([voxel_layer.cpp L73-79](https://github.com/ros-navigation/navigation2/blob/e9b5a24b057835e51d216d564ea99b94d3b33690/nav2_costmap_2d/plugins/voxel_layer.cpp#L73-L79));
- also set per observation source (`obstacle_layer.cpp` L145-148);
- applied to points **after transforming them into the global frame**
  ([observation_buffer.cpp L109-139](https://github.com/ros-navigation/navigation2/blob/e9b5a24b057835e51d216d564ea99b94d3b33690/nav2_costmap_2d/src/observation_buffer.cpp#L109-L139)).
- That is a fixed world-z band, not height above local ground. There is **no step or stair concept**: a stair or
  slope inside the band is an obstacle.

**Clearance** comes from the inflation layer:
- lethal inside the footprint, inscribed cost at the inscribed radius;
- then `exp(-cost_scaling_factor*(d - r_inscribed))` (`inflation_layer.hpp` L121-132);
- default `inflation_radius` 0.55 and `cost_scaling_factor` 10 (`inflation_layer.cpp` L95-99);
- bringup uses 0.70 and 3.0 (`nav2_params.yaml` L261-262, L343-344).

Nav2's `collision_monitor` was covered in the 2026-09-14 survey.

### SteveMacenski/spatio_temporal_voxel_layer (STVL)

- **Repo:** [link](https://github.com/SteveMacenski/spatio_temporal_voxel_layer). **License:** LGPL-2.1.
- **Commit:** `16cdf3b823e0b14886eb7571cd5f559b97fea19d` (`ros2`, 2026-09-17).
- **Height filtering.** The same world-frame `min_obstacle_height` / `max_obstacle_height` band, per source. The
  example uses 0.3 to 2.0 m
  ([README L114, L131-132](https://github.com/SteveMacenski/spatio_temporal_voxel_layer/blob/16cdf3b823e0b14886eb7571cd5f559b97fea19d/README.md?plain=1#L114-L132)).
- **Clearing.** Voxels decay over time (`voxel_decay`, `decay_model`), and frustum-based clearing replaces
  ray-tracing (README L58, L109-110).
- **No step concept.** The MID-360 vertical-FOV offset is documented (L149).
- **Evaluation of collisions on stairs or rough terrain:** none found in either repo (**UNVERIFIED** beyond
  README/code).

---

## Cross-stack observations relevant to acceptance criteria (analysis, not evidence)

1. **Every stack separates steps from obstacles with a height threshold relative to something.** They differ in the
   reference:
   - SCAN: the body-reference slab. Its implicit d_step is about 0.25 m for us, 0.3 m upstream.
   - CMU: height above local ground. 0.15 m base, 0.30 m on Go2.
   - PCT: the per-cell neighbour jump. 0.17 m upstream, 0.30 m ours.
   - ETH filter: step height, 0.12 m.
   - Nav2 and STVL: a world-z band.
   - ArtPlanner: torso-box clearance plus foot reachability.

   None of these guarantee no contact below the threshold. Low objects are deliberately handed to locomotion.
2. **Published evaluations rarely measure physical contact.**
   - SCAN reports SR and CR in a planning simulator.
   - PCT reports planning metrics only.
   - ArtPlanner reports planned-pose intersection rates plus an anecdotal count of physical collisions.

   Our harness already records non-foot contact force per link: 5 N threshold, record-only in the native policy
   (`native_nominal_scope.json` L40-42, L141-148). That is a stronger measurement than the upstream papers use.
3. **Our local evidence (leads, machine-dog-nav, gpu5070ti).** Source:
   `machine-dog-nav/.pipeline/experiments/2026-09-11_pct_scan_upstream_baseline/REPORT.md` L1-12 and L95-99,
   committed at `8541edbe`.
   - `native_full02` (native PCT/SCAN, same profile): Building stairs route, 98.08 s, **zero non-foot force** on
     all 13 non-foot links.
   - An earlier native episode had **left-shank contacts**.
   - The report itself says one run does not show repeatable collision-free behaviour.
   - Older modified-stack runs had these results (from the untracked `2026-09-10_pct_scan_full_building/REPORT.md`
     L162-167):
     - `full_stairs01`: FR_SHANK 64.4 N;
     - `full_navigation01`: an emergency stop on a collision prediction.
