---
origin: ai+primary_sources+local_experiment_records
reviewed: false
date: 2026-09-14
stage: planning
status: surveyed
task: .trellis/tasks/09-11-internvla-n1-lite3-isaac-sim (Phase D, step D.0; PRD decision 4)
---

# Body-clearance margin for the Lite3 VLA loop: open-source comparison

**Why this survey exists.** In Phase C's `phase_c_green_box_v1`, System 1's averaged path passed 0.13 m outside a box
corner. The upstream MPC tracks a point robot, so the robot's front-right hip struck the corner at 514 N
(`.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/RESULT_PHASE_C.md`).

**Dr Sun's constraint (2026-09-14).** Phase D gets a body-size margin, but it must come from existing open-source code,
chosen by comparison, not hand-built.

**Status of everything below: `surveyed`.** Nothing was cloned into the project, imported, built, run or installed.

## Method and verification

Three read-only surveyors worked in parallel, one per family: navigation-stack layers, safety filters and distance
maps, and learned/legged safety. They read source at pinned commits through `gh api`. Their notes, with line-level
permalinks and UNVERIFIED markers, are in [the sources folder](2026-09-14_body_clearance_margin_sources/) (AI-written,
SHA-256 in `SHA256SUMS.txt`).

**What I re-checked myself on 2026-09-14** (the rest is the surveyors' reading, not re-derived):
- **Commits and licenses:** the HEAD commit and license of every candidate in the tables below, through `gh api` and
  the LICENSE text.
- **Mechanisms, against the source lines:**
  - Nav2 `collision_monitor`: stop, slowdown and approach models, footprint use, and absence on `foxy-devel`;
    `VelocityPolygon` is on `main`, not `humble`;
  - neonavigation `safety_limiter`: `footprint` and `d_margin`, and issue #314;
  - cbfkit: the filter's `fallback="passthrough"` default;
  - HybridRobotics/cbf: its `RectangleRegion` robot geometry;
  - nvblox_torch: the per-query radius subtracted from ESDF distances;
  - CARE: trajectory rotation clipped to ±45° and per-robot `safety_margin` 0.05 / −0.1 / 0.2 m;
  - OCR: filter `threshold: 0.35`, `slack_coeff: 1000`, `v_x_min: 0.0`.
- **Licenses needing a note:** ABS states CC BY-NC 4.0 in its README and has no LICENSE file. NavDP has no LICENSE
  file; its README states CC BY-NC-SA 4.0.
- **Our own stack**, in the pinned InternNav snapshot `7a5c624` (`references/upstream/2026-09-08_dualvln`):
  - `controllers.py` MPC has only v/w bounds;
  - the DualVLN `nextdit` System 1 branch ignores `depths_dp`, so it plans from RGB only;
  - the real-world agent follows `np.mean` over the sampled trajectories (`internnav/model/utils/vln_utils.py` line 131,
    `num_sample_trajs = 32`).

## What a margin needs here

**The body, from the pinned Lite3 URDF.**
- **Torso:** x −0.269…0.279 m, y ±0.109 m.
- **Hip joints** at (±0.1745, ±0.062). Each hip collision cylinder (r 0.04) sits a further 0.05 m outboard, and thigh
  links reach y ±0.18 m.
- **Footprint:** a static rectangle of about 0.55 × 0.37 m before leg swing. That is smaller than the 0.61 × 0.39 m the
  surveyors were given, so their disc-cover numbers are slightly conservative.

**Two separate gaps have to close:**
1. **Seeing the obstacle when it matters.** The head camera's HFOV is 79°. A corner beside the hip leaves the image
   before the hip reaches it, so a filter that uses only the latest head frame cannot see what the hip hits. The fix
   is memory (a distance-field or height map) or a wide sensor. The real Lite3 carries a Livox MID-360 LiDAR (lead
   from `machine-dog-nav` docs); the simulator has no equivalent yet.
2. **Enforcing clearance for the footprint.** The candidate enforcement points are:
   - a filter on (v, w) at 10 Hz, before the bridge;
   - a check or modification of System 1's trajectory at about 2.5 Hz;
   - a footprint constraint inside the MPC.

**A prerequisite, which is not a safety layer.** Before any margin is credited with removing corner cuts, compare
following one sample (or a critic-selected one) with the upstream mean of 32 samples. If samples split left and right
of a box, the mean can run between them. This is a hypothesis: Phase C logs kept only the mean.

## Candidates that address our failure

| candidate | license | pinned commit | margin mechanism | ROS | fit to our loop |
| --- | --- | --- | --- | --- | --- |
| [Nav2 `nav2_collision_monitor`](https://github.com/ros-navigation/navigation2/tree/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_collision_monitor) | Apache-2.0 | `f31c7f49bf7afb9e32f4651ef91fb46f5636c88c` (main, 2026-09-13) | Stop and slowdown zones (polygon or circle, at least N sensor points inside). An approach model projects the current twist and keeps a time-to-collision against the footprint polygon. Filters `cmd_vel`. | ROS 2 Humble or newer; not in Foxy | The right position (planner output to velocity command). Mature, and usable unmodified. Reactive, with no map memory, so it needs a sensor that sees the flanks. It would put ROS 2 back into the simulation loop as a sidecar. No published legged evaluation (Nav2 issue #1676 open since 2020). |
| [nvblox / nvblox_torch](https://github.com/nvidia-isaac/nvblox/tree/24eee4948768682fa1ffb969b881efee4fca29c2) | Apache-2.0 | `24eee4948768682fa1ffb969b881efee4fca29c2` (public, 2026-07-03) | GPU TSDF/ESDF from depth; `query_layer` subtracts per-point radii, so a multi-disc footprint gets clearance and gradient | Python library (ROS wrapper is separate) | It remembers geometry after it leaves the camera view, the gap our failure needs closed. It is a clearance source, not an enforcement layer. GPU memory against our 2.3 GiB headroom is unmeasured. |
| [cbfkit](https://github.com/bardhh/cbfkit/tree/c4a326e10c63e8147825eaa221dc076882aff060) | BSD-3-Clause | `c4a326e10c63e8147825eaa221dc076882aff060` (main, 2026-09-12) | A barrier QP filter: (state, nominal command) in, safe command out. Ships a heading-dependent ellipse footprint barrier. | Python (JAX) | Actively maintained. Legged use is simulation only (ANYmal-C in Isaac Lab, G1 in MuJoCo; surveyor's reading). Its default on solver failure is to pass the unsafe command through, which must be set to stop. The footprint is an ellipse, not a rectangle. It has no perception: obstacles must come from somewhere else, such as nvblox. |
| [HybridRobotics/cbf](https://github.com/HybridRobotics/cbf/tree/d3412d229cd957a215b2ca562ca505fc4a4a33f8) | Apache-2.0 | `d3412d229cd957a215b2ca562ca505fc4a4a33f8` (master, 2022-08-12) | Duality-based barrier: a rotated rectangle robot kept clear of convex polygon obstacles, as hard constraints in CasADi | Python + CasADi | The only reusable code that models the real rectangle, and it uses the same solver family as our MPC. Unmaintained since 2022. Needs convex polygon obstacles, not raw depth. Acceleration-input unicycle. |
| [neonavigation `safety_limiter`](https://github.com/at-wat/neonavigation/tree/5fe952229b181e989faa6c119380631c97510105/safety_limiter) | BSD-3-Clause | `5fe952229b181e989faa6c119380631c97510105` (master, 2026-04-23) | Projects the current twist, checks the polygon footprint against a point cloud, subtracts `d_margin`, and caps speed to what a set deceleration can stop | ROS 1 only | Closest to "limit this command for this body", but ROS 1 and would need porting. Its own issue #314 says it cannot stop a collision when the turn rate changes near a wall, which is our corner case. |

## Screened out for this failure

- **[CARE](https://github.com/airlab-sogang/CARE/tree/fc916451651353b13e03ded213c40819ff32d953)** (MIT, `fc91645`).
  Only rotates the whole trajectory, by at most ±45°, away from repulsive depth points. Its margin is one hand-tuned
  distance per robot. It has no width model and cannot shift a path sideways past a corner. Tested on wheeled robots.
- **[OCR safety filter](https://github.com/albertklin/observation-conditioned-reachability/tree/92d14861fcb0bf9ca663738e93a7c156afa62b0a)**
  (MIT, `92d1486`). Tested on a real Go1, but:
  - it models the robot as a point;
  - it needs a 360° planar LiDAR scan;
  - its QP is softened (slack weight 1000);
  - its weights sit behind a Hugging Face access request.
- **NavDP critic** (`InternRobotics/NavDP` `bff5eb8`; InternNav's w-NavDP System 1 has `use_critic=False`). Learned
  scoring trained for a 0.25 m disc robot, and non-commercial. Switching to it is a model change, not a margin.
- **Would replace our MPC or policy rather than wrap it:**
  - Nav2 costmap inflation with MPPI or DWB footprint critics (surveyor notes: edge-only footprint rasterisation,
    collision as a cost);
  - TEB (soft penalty, low activity);
  - `mpc_local_planner` (GPL-3.0, stale);
  - NeuPAN (GPL-3.0, retrained per robot shape);
  - `tud-amr/mpc_planner` (heavy C++/ROS);
  - MRPT reactive navigation (a full navigator);
  - ViPlanner and iPlanner (width only in training cost);
  - legged-loco and X-NavDP (retrain the walking or navigation policy).
- **Not reusable as code:**
  - `tkkim-robot/safe_control`, `HybridRobotics/depth_cbf`, `HybridRobotics/quadruped_nmpc_dcbf_duality`: no license;
  - `LeCAR-Lab/ABS`: CC BY-NC 4.0;
  - `HybridRobotics/NMPC-DCBF`: does not exist; the similar repo is MATLAB.
- **References only:** `cbfpy` (generic, softened by default), `ntnu-arl/composite_cbf` (sphere robot, C++/ROS 2, passes
  through on timeout), `elevation_mapping_cupy` (MIT; a 2.5D map with a footprint traversability check, built for
  ANYmal), `cob_collision_velocity_filter` (ROS 1, rectangle only).

## Options for Dr Sun

| option | pieces | what is upstream | what we would still write | main risks |
| --- | --- | --- | --- | --- |
| **A. Reference stack, unmodified** | Nav2 `collision_monitor` in a ROS 2 (Humble or Jazzy) sidecar. It filters the MPC's (v, w) against the URDF footprint plus padding, fed by a 360° point cloud from a simulated MID-360-like ray-cast LiDAR. | All safety logic | Thin transport: publish `/clock`, odometry, point cloud and `cmd_vel` from the lockstep, and read the filtered command back; plus a sensor configuration | ROS 2 returns to the simulation loop, against design Decision 1. The robot baseline is Foxy, where it does not exist. It has no memory, so the result depends on the 360° sensor. Lockstep timing through ROS sim time must be proven. Legged use is unproven. |
| **B. Python-native map + filter** | nvblox_torch ESDF from head depth (later LiDAR) plus a cbfkit QP filter on (v, w), with fallback set to stop | Mapping and the QP filter | The barrier formulation that turns ESDF samples into cbfkit constraints for a multi-disc or ellipse footprint. This is new safety logic of ours, which the PRD decision asks to avoid. | GPU memory against 2.3 GiB headroom; ellipse rather than rectangle; latency; examiners will treat the glue as our method |
| **C. Measure first, choose after** | The 32-sample mean against single-sample ablation, plus simulator-only ground-truth clearance over the green layout (PhysX box sweeps; API use in our Isaac version unverified), before selecting A or B | Nothing new | Analysis only | Delays the margin, but tells whether averaging or perception causes most of the clearance loss |

**Recommendation: C, then A.**
- **Why C first.** It costs no new safety code, and it separates two causes the Phase C evidence cannot tell apart:
  planner averaging and the absence of any body model.
- **Why A next.** It is the only candidate whose safety logic can be used unmodified. That is closest to "don't build
  it yourself".
- **Where A falls short.** It fixes the failure only if a sensor sees the flanks, so it must come with a simulated
  360° LiDAR. It also means reversing the no-ROS decision for the simulation loop.
- **When to choose B instead.** If ROS 2 in the loop is unacceptable. B's gain is memory of out-of-view geometry; its
  cost is a barrier formulation we would own.

## Claim boundary

- `surveyed` only. No candidate has been run on Lite3, in Isaac Sim or on any legged robot by us.
- Legged-robot evidence for every candidate is simulation-only or absent, apart from OCR's Go1. No result here says
  any candidate prevents the Phase C collision.
- Every filter certifies a simplified model: a unicycle or double integrator. None covers the walking policy's tracking
  error, the 250 ms watchdog or the 2.5 Hz / 10 Hz rate split. Minimum body clearance must be measured independently,
  for example with PhysX sweeps, alongside success, oracle success and contact force.
- Commit pins are the branch heads on 2026-09-14 and will move. The pins, not the branches, are the reference.
