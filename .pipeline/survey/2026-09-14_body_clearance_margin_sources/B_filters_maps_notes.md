# Survey B: runtime safety filters and distance fields for footprint clearance

- Surveyor: B (filters + maps). Date: 2026-09-14. Label: **surveyed** only (nothing imported, run, reproduced, integrated or validated).
- Method: `gh api repos/...` (metadata, LICENSE endpoint, git trees, commits/BRANCH SHA) and `raw.githubusercontent.com/<owner>/<repo>/<SHA>/<path>` source reads. No clone, no build, no install, no execution.
- License column = GitHub license API SPDX + LICENSE file presence at root. "no license" = no LICENSE file and API 404 => **not reusable** (all rights reserved by default).
- Line ranges were read from the raw file at the pinned SHA; permalinks use `https://github.com/OWNER/REPO/blob/SHA/PATH#Lx-Ly`.
- Problem restatement (from brief): upstream CasADi MPC treats Lite3 as a point; path passed 0.13 m outside a box corner; FR hip hit at 514 N. Lite3 body ~0.61 x 0.39 m (approx), hips at +-0.1745 x, +-0.062 y. Loop: pure Python, 10 Hz MPC -> (v, w) -> bridge (clamp, 250 ms watchdog) -> RL locomotion (vx, vy, wz). Sim sensor: head RGB-D 640x480, HFOV 79 deg. Real: D435i, Livox MID-360 (leads), ROS 2 Foxy. GPU headroom ~2.3 GiB.

---

## 1. tkkim-robot/safe_control

| Field | Value |
|---|---|
| URL | https://github.com/tkkim-robot/safe_control |
| License | **NONE** (license API 404; root has no LICENSE file: `.gitignore README.md attitude_control dynamic_env envs examples position_control pyproject.toml robots shielding tracking.py utils`; README has no license statement). **No license: not reusable.** |
| Default branch / SHA | `main` / `8fdf87b5015a74a75d96f678ddc81b371b06cf0e` |
| Last commit | 2026-08-24T05:46:42Z ("Merge pull request #42 from Kane-Weng/quick_patch") |
| Stars / open issues | 305 / 0 |

Mechanism
- Robot footprint = a single disc: `robot_spec.setdefault('radius', 0.25)`, comment "including padding" — [robots/robot.py#L49-L50](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/robots/robot.py#L49-L50).
- Obstacles = circles `[x, y, r]` (plus superellipsoid `[ox, oy, a, b, e, theta, flag]` per README "Superellipsoid obstacles to approximate rectangles").
- Unicycle CBF (continuous): `h = ||p - p_obs||^2 - beta*(r_obs + r_robot)^2 - sigma(s)`, with heading-dependent sigma term — [robots/unicycle2D.py#L107-L128](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/robots/unicycle2D.py#L107-L128). Discrete-time version for MPC — [#L130-L149](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/robots/unicycle2D.py#L130-L149).
- CBF-QP filter: `min ||u - u_ref||^2 s.t. A u + b >= 0, |v|<=v_max, |w|<=w_max` (hard constraints, no slack), solved with **`solver=cp.GUROBI`** hard-coded — [position_control/cbf_qp.py#L47-L61](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/position_control/cbf_qp.py#L47-L61), [#L151-L203](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/position_control/cbf_qp.py#L151-L203).
- MPC-CBF: do-mpc (CasADi + IPOPT) with DCBF nonlinear constraint `d_h + alpha*h_k >= 0` per obstacle — [position_control/mpc_cbf.py#L295-L325](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/position_control/mpc_cbf.py#L295-L325).

I/O and dynamics: state `[x, y, theta]`, input `[v, omega]` (kinematic unicycle, [unicycle2D.py#L22-L68](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/robots/unicycle2D.py#L22-L68)). CBF-QP takes nominal `u_ref` + obstacle list and returns safe `u`; MPC-CBF takes goal/reference and returns `u`.

Runtime: Python; deps numpy==1.26.4, scipy, cvxpy, casadi, do-mpc[full], shapely, **gurobipy** (pyproject.toml). CPU only, no ROS. Callable from our loop: yes in principle, but CBF-QP needs a Gurobi licence (or a one-line solver change, which is a local modification of unlicensed code). 10 Hz feasibility: UNVERIFIED (not run).

Perception: "unknown obstacles" are detected by a simulated FOV/ray test against ground-truth circles ([utils/detection.py#L28-L60](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/utils/detection.py#L28-L60)), default `fov_angle` 70 deg ([robot.py#L53-L60](https://github.com/tkkim-robot/safe_control/blob/8fdf87b5015a74a75d96f678ddc81b371b06cf0e/robots/robot.py#L53-L60)). No depth/pointcloud ingestion.

Legged evidence: none found in README (grep for legged/quadruped/hardware: no hits).

Limitations for Lite3: disc footprint (a 0.61 x 0.39 m rectangle needs r >= 0.36 m circumscribing disc — conservative in corridors); obstacles must be pre-fitted circles/superellipses; no license.

---

## 2. HybridRobotics/cbf (duality-based polytope-to-polytope DCBF in NMPC)

| Field | Value |
|---|---|
| URL | https://github.com/HybridRobotics/cbf |
| License | **Apache-2.0** (LICENSE at root; API spdx Apache-2.0) |
| Default branch / SHA | `master` / `d3412d229cd957a215b2ca562ca505fc4a4a33f8` |
| Last commit | 2022-08-12T22:26:20Z ("Fix DCBF margin distance implementation"); repo pushed 2024-02-22 |
| Stars / open issues | 217 / 6 open issues+PRs |
| Paper | Thirugnanam, Zeng, Sreenath, "Safety-Critical Control and Planning for Obstacle Avoidance between Polytopes with Control Barrier Functions", ICRA 2022, arXiv:2109.12313 (README L22-L23) |

Mechanism (this is the only surveyed Apache/MIT code that treats the **robot body itself as a rotated polytope**)
- Robot footprint = `RectangleRegion(-L/2, L/2, -W/2, W/2)` in body frame — [models/dubin_car.py#L48-L55](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/models/dubin_car.py#L48-L55); H-representation `A x <= b` — [models/geometry_utils.py#L20-L32](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/models/geometry_utils.py#L20-L32); general polytope / convex hull — [#L45-L61](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/models/geometry_utils.py#L45-L61).
- Obstacles = convex polytopes (H-rep). Minimum distance between robot polytope and obstacle polytope is encoded by its **dual** (lambda, mu multipliers) as extra NLP variables, with a discrete-time CBF decay `>= omega_i * gamma^(i+1) * (h_curr - margin) + margin` — [control/dcbf_optimizer.py#L129-L180](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/control/dcbf_optimizer.py#L129-L180). Safety margin = `margin_dist` (default 0.00) — [#L9-L20](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/control/dcbf_optimizer.py#L9-L20). Hard constraints with a relaxed decay rate omega (penalised `pomega*(omega-1)^2`).
- Obstacles farther than a braking-distance-based `safe_dist` are skipped — [dcbf_optimizer.py#L182-L194](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/control/dcbf_optimizer.py#L182-L194), [dubin_car.py#L39-L45](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/models/dubin_car.py#L39-L45).
- Initial distance per obstacle is computed by a separate IPOPT solve each step — [geometry_utils.py#L67-L88](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/models/geometry_utils.py#L67-L88).
- The whole `ca.Opti` problem is rebuilt every call (`setup`) and solved with IPOPT — [dcbf_optimizer.py#L203-L231](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/control/dcbf_optimizer.py#L203-L231).

I/O and dynamics: state `[x, y, v, theta]`, input `[a, omega]` (acceleration-unicycle "Dubin car") — [dubin_car.py#L9-L30](https://github.com/HybridRobotics/cbf/blob/d3412d229cd957a215b2ca562ca505fc4a4a33f8/models/dubin_car.py#L9-L30). Takes a reference trajectory (horizon 11, DCBF horizon 6 by default) and returns an optimal input sequence. Not a nominal-(v,w) filter; it is a replacement MPC.

Runtime: Python, casadi, numpy, sympy, polytope, matplotlib (requirements.txt). CPU, no ROS. Callable from Python: yes. 10 Hz: UNVERIFIED; the Opti rebuild + per-obstacle IPOPT distance solve each step is a known cost risk. Open issue #32 "DCBF constraints are hard constraints, why collisions still occur?" and #26 "Evaluate behavioral change for margin and other hyperparameters" are directly relevant (titles read via API; bodies not read).

Legged evidence: none in this repo. Related sibling `HybridRobotics/quadruped_nmpc_dcbf_duality` (C++, legged_control based) extends the duality idea to quadrupeds but has **no license** (see section 13).

Limitations: obstacles must be convex polytopes (needs a segmentation/convex-decomposition step from depth or map); dynamics are acceleration-level (our MPC outputs v, w); IPOPT per-step solve time unmeasured; no perception.

---

## 3. bardhh/cbfkit

| Field | Value |
|---|---|
| URL | https://github.com/bardhh/cbfkit |
| License | **BSD-3-Clause** (root LICENSE; API spdx). Bundled G1 MJCF has its own LICENSE under `src/cbfkit/systems/mujoco/models/g1/`. |
| Default branch / SHA | `main` / `c4a326e10c63e8147825eaa221dc076882aff060` |
| Last commit | 2026-09-12T23:19:10Z ("README overhaul and G1 showcase renderer ... (#381)") |
| Stars / open issues | 111 / 2 |
| Paper | arXiv:2404.07158 (README badge) |

Mechanism
- Generic control-affine CBF-QP / robust / stochastic / risk-aware CBF controllers (JAX), plus a **standalone `SafetyFilter`** that takes `(state, nominal action)` and returns a filtered action; README "Quick start" (L98-L148 at the pinned SHA, `shield.filter` at L130) shows `SafetyFilter.from_cbf_qp(dynamics=..., barriers=..., control_limits=..., dt=...)` then `u, info = shield.filter(x, u_nom)`.
- **Fallback on QP failure defaults to `"passthrough"`** (returns the nominal, unsafe command) — [src/cbfkit/wrappers/safety_filter.py#L60-L70](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/src/cbfkit/wrappers/safety_filter.py#L60-L70), [#L158-L222](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/src/cbfkit/wrappers/safety_filter.py#L158-L222). The batched filter instead defaults to NaN ([wrappers/batched.py#L15-L49](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/src/cbfkit/wrappers/batched.py#L15-L49)). For us the fallback must be set explicitly (e.g. `zero`).
- Footprint: a **rotating-ellipse footprint barrier** in the body frame, `h_i = || diag(1/(lon+r), 1/(lat+r)) R(theta)^T (p - p_i) || - 1`, lifted to high-order CBF — [src/cbfkit/systems/mujoco/reduced_order.py#L802-L859](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/src/cbfkit/systems/mujoco/reduced_order.py#L802-L859); measured G1 footprint constant `G1_FOOTPRINT = {"lon": 0.16, "lat": 0.28}` — [#L746-L748](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/src/cbfkit/systems/mujoco/reduced_order.py#L746-L748). Disc vs ellipse comparison example: [examples/mujoco/g1_corridor.py#L1-L20](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/examples/mujoco/g1_corridor.py#L1-L20). Margin = axis inflation by obstacle radius `r` (plus `robust` disturbance bound).
  - Surveyor note (own geometry, not from the repo): inflating ellipse semi-axes by `r` is not a superset of the Minkowski sum ellipse+disc when lon != lat (e.g. lon=1, lat=0.1, r=1: point (1.5, 0.866) is 1 m from the ellipse tip but outside the (2, 1.1) ellipse). With point obstacles (r = 0) this issue vanishes. A rectangle body needs a circumscribing ellipse (minimal-area: semi-axes x sqrt(2)), i.e. 0.431 x 0.276 m for a 0.61 x 0.39 m Lite3 body.
- Unicycle model and ellipsoidal obstacle barrier also exist: `src/cbfkit/systems/unicycle/models/olfatisaber2002approximate/certificates/barrier_functions/ellipsoidal_obstacle.py` (144 lines; not line-read in detail).

I/O: nominal action in, safe action out (filter form). Obstacles enter as state/closure parameters; no perception module in the library.

Runtime: Python >= 3.x with jax, jaxopt (OSQP default), optional custom interior-point "fast" solver, CVXOPT/CasADi extras (README "QP solver"). No ROS dependency; ROS2 node **code generation** only (README "ROS2"). Optional Torch/Isaac Lab bridge via DLPack (`examples/isaac_lab/README.md`); "CUDA tensors require CUDA-enabled JAX on the same GPU". JAX preallocates 75% of GPU memory by default (JAX docs, https://docs.jax.dev/en/latest/gpu_memory_allocation.html) — with 2.3 GiB headroom, run JAX on CPU or set `XLA_PYTHON_CLIENT_PREALLOCATE=false`. Callable in our 10 Hz loop: yes (CPU JAX), solve time on our hardware UNVERIFIED.

Legged evidence (simulation only): Unitree G1 in MuJoCo/MJX (README L243-L285; README "Scope" L158 states the certificate covers a reduced-order model, walking-policy tracking error enters as a disturbance bound). Isaac Lab warehouse demo filters world-frame velocity requests before a frozen **ANYmal-C** walking policy, obstacle state from the simulator (not perception), contact sensors for evaluation, `SAFE_RADIUS = 1.60` empirical — [examples/isaac_lab/warehouse_model.py#L1-L61](https://github.com/bardhh/cbfkit/blob/c4a326e10c63e8147825eaa221dc076882aff060/examples/isaac_lab/warehouse_model.py#L1-L61); WAREHOUSE.md L81-L106 ("The inflated geometry is an empirical margin"). No real-robot legged evidence found. (Note: `examples/isaac_lab/README.md` has a heading "Real robot example" but the text describes the simulated warehouse demo.)

Maintenance: very active (commits within 2 days); 2 open issues.

Limitations: footprint barrier shape is disc/ellipse only; obstacles must be supplied as parametric agents/discs/ellipses (a pointcloud needs a fixed-size nearest-K selection for JAX static shapes); fail-open default fallback; the G1 heading-augmented double integrator is a different model from our (v, w) unicycle.

---

## 4. StanfordASL/cbfpy (redirected from danielpmorton/cbfpy)

| Field | Value |
|---|---|
| URL | https://github.com/StanfordASL/cbfpy |
| License | **MIT** (root LICENSE) |
| Default branch / SHA | `main` / `f5bff8b93609d6a164fd8beeef962c92e4476dcb` |
| Last commit | 2026-07-22T00:40:14Z ("Ruff format") |
| Stars / open issues | 223 / 0 |
| Paper | Morton & Pavone, OSCBF, IROS 2025, arXiv:2503.06736 (README L15-L28) |

Mechanism: generic JAX CBF-QP; user subclasses `CBFConfig` with `f, g, h`; `safety_filter(z, u_des)` is `@jax.jit` and solves with `qpax` — **relaxed (slack) QP by default** (`relax_qp=True`, `cbf_relaxation_penalty=1e3`) — [cbfpy/cbfs/cbf.py#L149-L180](https://github.com/StanfordASL/cbfpy/blob/f5bff8b93609d6a164fd8beeef962c92e4476dcb/cbfpy/cbfs/cbf.py#L149-L180), [cbfpy/config/cbf_config.py#L83-L95](https://github.com/StanfordASL/cbfpy/blob/f5bff8b93609d6a164fd8beeef962c92e4476dcb/cbfpy/config/cbf_config.py#L83-L95). No robot-geometry or footprint abstraction; examples are point robot, drone, ACC, arm joint limits.

I/O: nominal `u_des` in, safe `u` out. Runtime: Python, jax + qpax; CPU fine; no ROS. Callable at 10 Hz: yes in principle (UNVERIFIED timing). Legged evidence: none. Limitation: soft constraint by default; footprint barrier must be written by us; fixed barrier dimension under JIT.

---

## 5. ntnu-arl/composite_cbf (+ ntnu-arl/cbf_pc_selector)

| Field | Value |
|---|---|
| URL | https://github.com/ntnu-arl/composite_cbf |
| License | **BSD-3-Clause** (root LICENSE) |
| Default branch / SHA | `main` / `0a7b6f54af68dfe0663afe2a3a61a50f5ae22ea6` |
| Last commit | 2025-11-01T00:55:01Z ("fix declare_parameter in node"); pushed 2026-05-26 |
| Stars / open issues | 13 / 0 |
| Companion | `ntnu-arl/cbf_pc_selector`, BSD-3-Clause, `main` / `bff402bfc7b84e7e05b903a5085a6974c3bc5fe0`, 2026-04-24 (not source-read) |
| Papers | Harms, Jacquet, Alexis, ICRA 2025, arXiv:2502.04101; Misyats et al., ICUAS 2025, arXiv:2504.15850 (README) |

Mechanism: **reactive, map-free** filter on a downsampled body-frame point cloud. Robot = sphere of radius `epsilon` (per-point barrier `||p_i||^2 - epsilon^2`), second-order (acceleration) CBF per point, composed with a log-sum-exp soft-min, closed-form single-constraint QP solution — [src/CbfSafetyFilter.cpp#L44-L117](https://github.com/ntnu-arl/composite_cbf/blob/0a7b6f54af68dfe0663afe2a3a61a50f5ae22ea6/src/CbfSafetyFilter.cpp#L44-L117). Obstacle and command timeouts clear obstacles / zero the command — [#L14-L36](https://github.com/ntnu-arl/composite_cbf/blob/0a7b6f54af68dfe0663afe2a3a61a50f5ae22ea6/src/CbfSafetyFilter.cpp#L14-L36). Note: an obstacle timeout **clears obstacles and then passes the command through** ([#L50-L53](https://github.com/ntnu-arl/composite_cbf/blob/0a7b6f54af68dfe0663afe2a3a61a50f5ae22ea6/src/CbfSafetyFilter.cpp#L50-L53)) — fail-open on stale perception.

I/O & dynamics: body acceleration setpoint + body velocity + points in; filtered acceleration out (holonomic double integrator, multirotor). Not (v, w).

Runtime: C++/Eigen, ROS 2 (tested Humble), mavros-msgs (README). Algorithm core is ~100 lines and has no ROS dependency in `CbfSafetyFilter.cpp`, so porting the math to Python is small, but that is a re-implementation. Legged evidence: none in repo. Limitations: sphere footprint only; FOV-limited case not implemented ("The node implements the unconstrained-FoV case", README) — directly relevant to a 79 deg head camera.

---

## 6. ros-navigation/navigation2 — `nav2_collision_monitor` (and `nav2_mppi_controller` footprint critic)

| Field | Value |
|---|---|
| URL | https://github.com/ros-navigation/navigation2/tree/main/nav2_collision_monitor |
| License | Package **Apache-2.0** (`nav2_collision_monitor/package.xml` `<license>Apache-2.0</license>`); repo-level API = NOASSERTION, root LICENSE lists LGPL-2.1-or-later and Apache-2.0 portions. `nav2_mppi_controller/package.xml`: MIT. |
| Default branch / SHA | `main` / `f31c7f49bf7afb9e32f4651ef91fb46f5636c88c` |
| Last commit | 2026-09-13T13:56:30Z |
| Stars / open issues | 4705 / 102 |
| Distro availability | `nav2_collision_monitor` directory **absent on `foxy-devel` and `galactic`**, present on `humble` (contents API 404 vs 9 entries). Same for `nav2_mppi_controller` (absent on foxy-devel, present on humble). |

Mechanism (veto/scale, not optimisation)
- Shapes: polygon / circle / velocity polygon zones with STOP, SLOWDOWN, LIMIT, APPROACH actions; **robot footprint polygon (static or `footprint` topic) is used by the APPROACH model** (README L37-L38).
- APPROACH: forward-simulates the current twist `(vx, vy, wz)` in `simulation_time_step` increments up to `time_before_collision`, transforming sensor points into each predicted body frame and checking points inside the footprint polygon (`min_points` threshold) — [src/polygon.cpp#L339-L388](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_collision_monitor/src/polygon.cpp#L339-L388); constant-twist projection — [src/kinematics.cpp#L44-L67](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_collision_monitor/src/kinematics.cpp#L44-L67); velocity scaled by `collision_time / time_before_collision` — [src/collision_monitor_node.cpp#L608-L638](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_collision_monitor/src/collision_monitor_node.cpp#L608-L638).
- Pointcloud source keeps points between `min_height` (default 0.05) and `max_height` (default 0.5) — [src/pointcloud.cpp#L174](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_collision_monitor/src/pointcloud.cpp#L174), [#L190-L192](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_collision_monitor/src/pointcloud.cpp#L190-L192).
- Reported timing (README L90-L99): approach model, polygon footprint, 24K-point cloud 20.67 ms; circle 10.87 ms; LaserScan 360 points ~4.9 ms. Hardware for these numbers not stated in the lines read.
- MPPI `CostCritic` with `consider_footprint` uses full-footprint costmap collision checking (`inCollision`, `collision_cost` 1e6) — [nav2_mppi_controller/src/critics/cost_critic.cpp#L28-L33](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_mppi_controller/src/critics/cost_critic.cpp#L28-L33), [#L192-L215](https://github.com/ros-navigation/navigation2/blob/f31c7f49bf7afb9e32f4651ef91fb46f5636c88c/nav2_mppi_controller/src/critics/cost_critic.cpp#L192-L215). Planner (cost), not a filter.

I/O: `cmd_vel_in` twist -> `cmd_vel` twist; sources = LaserScan / PointCloud2 / Range / polygon. Runtime: C++ ROS 2 lifecycle node, Humble or newer; **not Foxy**, not callable from our pure-Python loop. Legged use: not verified. Relevant open issue: #6346 "Collision monitor brakes for walls the robot is intentionally driving up to".

Limitations: purely reactive per-frame (no memory) — points that leave the sensor FOV no longer exist; constant-twist prediction; slows/stops rather than steers around.

---

## 7. hanruihua/NeuPAN

| Field | Value |
|---|---|
| URL | https://github.com/hanruihua/NeuPAN |
| License | **GPL-3.0** (root LICENSE) — copyleft; linking into our stack would impose GPL on distributed derivatives. |
| Default branch / SHA | `main` / `f5ae6d848b54aeae0340af1eb49e3a809dea00a5` |
| Last commit | 2026-06-21T14:03:09Z |
| Stars / open issues | 1098 / 30 |
| Paper | T-RO 2025, arXiv:2403.06828 (README L7, L39) |

Mechanism
- Robot footprint = **convex polygon** from `vertices` or `length/width` (`G x <= h`) — [neupan/robot/robot.py#L32-L53](https://github.com/hanruihua/NeuPAN/blob/f5ae6d848b54aeae0340af1eb49e3a809dea00a5/neupan/robot/robot.py#L32-L53), [#L318-L370](https://github.com/hanruihua/NeuPAN/blob/f5ae6d848b54aeae0340af1eb49e3a809dea00a5/neupan/robot/robot.py#L318-L370). A learned DUNE network maps each obstacle point to the dual variables of point-to-polygon distance; must be retrained when size/shape changes (README FAQ "When should I retrain the DUNE model?").
- NRMP (cvxpylayers, ECOS) MPC: collision term is a **squared-hinge penalty** `0.5*ro_obs*sum_squares(neg(I))` — [robot.py#L183-L198](https://github.com/hanruihua/NeuPAN/blob/f5ae6d848b54aeae0340af1eb49e3a809dea00a5/neupan/robot/robot.py#L183-L198); distance variable bounded `d_min <= d <= d_max` and rewarded by `-eta*sum(d)` — [neupan/blocks/nrmp.py#L357-L383](https://github.com/hanruihua/NeuPAN/blob/f5ae6d848b54aeae0340af1eb49e3a809dea00a5/neupan/blocks/nrmp.py#L357-L383). So clearance is soft in the optimiser, plus a hard **stop veto** when `min_distance < collision_threshold` — [neupan/neupan.py#L105-L170](https://github.com/hanruihua/NeuPAN/blob/f5ae6d848b54aeae0340af1eb49e3a809dea00a5/neupan/neupan.py#L105-L170).

I/O & dynamics: `forward(state [x,y,theta], points (2,N), velocities)` -> `(v, w)` action for `diff` kinematics (also `acker`, `omni`); needs an initial path (waypoints / global planner). It **replaces** our MPC rather than filtering it.

Runtime: Python, PyTorch + cvxpy/cvxpylayers; CPU recommended ("cvxpy is not supported on GPU", README L117); README L263 claims >15 Hz on an Intel i7 (UNVERIFIED). ROS/ROS2 wrapper in separate repo `hanruihua/neupan_ros` (not inspected). 2D points only; 3D lidar must be projected (README FAQ).

Legged evidence: none found in README. Open issues (titles, translated from Chinese): #74 "diff-drive Gazebo: avoidance fails when an obstacle suddenly appears, stops in front", #69 "cannot get around obstacles, both sim and real", #46 "path keeps going to obstacle edges, detached from global path", #53 "tilted lidar mounting", #67 "should ground points be removed".

Limitations: GPL; convex footprint; soft collision cost; 2D; per-geometry DUNE training; CPU cost.

---

## 8. nvidia-isaac/nvblox (`nvblox_torch`) and NVIDIA-ISAAC-ROS/isaac_ros_nvblox

| Field | nvblox | isaac_ros_nvblox |
|---|---|---|
| URL | https://github.com/nvidia-isaac/nvblox | https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox |
| License | **Apache-2.0** (file is `LICENSE.md`, which is why the API reports NOASSERTION; text read: "Apache License Version 2.0") | **Apache-2.0** |
| Default branch / SHA | `public` / `24eee4948768682fa1ffb969b881efee4fca29c2` | `main` / `ef47346399c71a4342c03bdbec2136ec735da4b8` |
| Last commit | 2026-07-03T11:20:11Z | 2026-08-19T02:33:41Z (release-4.6) |
| Stars / open issues | 1293 / 54 | 748 / 55 |

Mechanism (distance field provider, not a filter)
- GPU TSDF/occupancy integration from depth frames, ESDF update, and batched queries. `Mapper(voxel_sizes_m, integrator_types)`, `add_depth_frame(depth, T_W_C, sensor)`, `update_esdf()` — [nvblox_torch/nvblox_torch/mapper.py#L58-L100](https://github.com/nvidia-isaac/nvblox/blob/24eee4948768682fa1ffb969b881efee4fca29c2/nvblox_torch/nvblox_torch/mapper.py#L58-L100), [#L177-L185](https://github.com/nvidia-isaac/nvblox/blob/24eee4948768682fa1ffb969b881efee4fca29c2/nvblox_torch/nvblox_torch/mapper.py#L177-L185).
- `query_layer(QueryType.ESDF / ESDF_GRAD, query)`: "For queries in the ESDF layer, an extra column containing point radii may be provided. This radii will be subtracted from the retrieved distances" — [mapper.py#L326-L350](https://github.com/nvidia-isaac/nvblox/blob/24eee4948768682fa1ffb969b881efee4fca29c2/nvblox_torch/nvblox_torch/mapper.py#L326-L350). This is a direct **sphere-set footprint clearance query** (distance and gradient) usable as a CBF `h` and `dh/dx`. Open issue #129 says the radius column is actually required (Nx4) despite the docstring.
- isaac_ros_nvblox: ROS 2 nodes; ESDF "is sliced into an output cost map which is provided through a cost map plugin into Nav2" (README L28-L29); package `nvblox_nav2`.

Runtime
- nvblox_torch pip supported on x86 + dGPU, Ubuntu 20.04/22.04/24.04, CUDA 11.4-13.2, compute capability >= 7.5 (docs/pages/installation.rst L23-L38). Callable from our Python loop: yes (PyTorch). GPU: required.
- Memory: "scales with the volume of mapped space, and cubicly with increasing resolution ... will happily run out of memory and crash" and nvblox_torch "hasn't been optimized to the same degree" (docs/pages/limitations.rst). **Actual footprint for a local 0.05 m map is UNVERIFIED**; must be measured against the 2.3 GiB headroom. Open issue #90 "Memory Leak in nvblox_torch mapper"; #99 "`libpy_nvblox.so` fails to load with PyTorch 2.9".
- Published core timings (isaac_ros_nvblox README performance table): Replica 0.05 m ESDF 0.8 ms on x86 + 3090 (no 4090 column).
- isaac_ros_nvblox: Isaac ROS targets **ROS 2 Jazzy**, Ubuntu 24.04 (https://nvidia-isaac-ros.github.io/getting_started/index.html, fetched 2026-09-14) — incompatible with the robot's Foxy without a bridge/container.
- Dynamic scene handling not supported in nvblox_torch (limitations.rst).

Legged evidence: not verified in these repos (Isaac ROS docs mention Nova Carter etc.; not checked).

Limitations: maps only what the depth camera has seen (a head camera with 79 deg HFOV leaves the flanks and rear unobserved unless remembered in the map); depends on odometry accuracy for fusion; GPU memory contention with the VLA.

---

## 9. leggedrobotics/elevation_mapping_cupy

| Field | Value |
|---|---|
| URL | https://github.com/leggedrobotics/elevation_mapping_cupy |
| License | **MIT** (root LICENSE on `main`; LICENSE on `ros2` branch read: "MIT License, Copyright (c) 2022 ETH Zurich, Takahiro Miki"; ros2 `package.xml` MIT) |
| Default branch / SHA | `main` (ROS 1, catkin) / `20a8a26b67a995b43eb44c23568854d1fed82a52`, 2025-05-14T15:09:55Z |
| ROS 2 branch | `ros2` / `8fd49565f622ae1481c0a22d6c8897441f7e2b7e`, 2026-07-20T11:05:33Z; also `release/jazzy`, `dev/jj/g1/ros2_humble` branches exist (not inspected) |
| Stars / open issues | 1088 / 46 |
| Paper | Miki et al., IROS 2022, arXiv:2204.12876 (README L41-L52) |

Mechanism: GPU (CuPy) 2.5D elevation map from point clouds with drift compensation, traversability filter (learned), plugins. `ElevationMap` core class imports numpy/cupy, not rclpy — [ros2: elevation_mapping_cupy/elevation_mapping_cupy/elevation_mapping.py#L92-L95](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/8fd49565f622ae1481c0a22d6c8897441f7e2b7e/elevation_mapping_cupy/elevation_mapping_cupy/elevation_mapping.py#L92-L95); `input_pointcloud(raw_points, channels, R, t, position_noise, orientation_noise)` — [#L479-L510](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/8fd49565f622ae1481c0a22d6c8897441f7e2b7e/elevation_mapping_cupy/elevation_mapping_cupy/elevation_mapping.py#L479-L510). **Footprint-polygon safety check**: `get_polygon_traversability(polygon)` masks the polygon on the map and declares unsafe if cells below `safe_thresh` exceed `max_unsafe_n` — [#L921-L966](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/8fd49565f622ae1481c0a22d6c8897441f7e2b7e/elevation_mapping_cupy/elevation_mapping_cupy/elevation_mapping.py#L921-L966) (params `safe_thresh 0.7`, `safe_min_thresh 0.4`, `max_unsafe_n 10` in `config/core/core_param.yaml`).

Runtime: Python + CuPy + CUDA; ROS 1 on main, ROS 2 on branches; core class usable without ROS (import path check only; not run). GPU memory UNVERIFIED (default `map_length 20.0`, `resolution 0.1` in ros2 core_param.yaml). Legged evidence: designed for and evaluated on ANYmal (paper title "for Locomotion and Navigation"; README). Limitations: 2.5D (cannot represent overhangs; fine for box obstacles); a map, not a filter — a veto/CBF still has to be built on top; traversability model trained on ANYmal data.

---

## 10. tud-amr/mpc_planner

| Field | Value |
|---|---|
| URL | https://github.com/tud-amr/mpc_planner |
| License | **Apache-2.0** (root LICENSE) |
| Default branch / SHA | `main` / `3002da6a5e43b3577f584381bbcad569c82a381b` |
| Last commit | 2025-03-30T15:35:37Z |
| Stars / open issues | 401 / 8 (e.g. #18 "MPC failed: QP Failure: UNKNOWN", #10 "Missing files in ROS2 build of mpc_planner_solver") |

Mechanism: robot = `n_discs` discs placed along the longitudinal axis (`ego_disc_i_offset`), each disc constrained to lie in a convex free-space polytope built by DecompUtil from occupied costmap cells: `a1*x_disc + a2*y_disc - (b + slack) <= 0` — [mpc_planner_modules/scripts/decomp_constraints.py#L68-L98](https://github.com/tud-amr/mpc_planner/blob/3002da6a5e43b3577f584381bbcad569c82a381b/mpc_planner_modules/scripts/decomp_constraints.py#L68-L98); "Map is already inflated" — [src/decomp_constraints.cpp#L60-L86](https://github.com/tud-amr/mpc_planner/blob/3002da6a5e43b3577f584381bbcad569c82a381b/mpc_planner_modules/src/decomp_constraints.cpp#L60-L86). Ellipsoid/Gaussian/scenario constraint modules for dynamic obstacles. Slack => soft.

Runtime: C++ ROS/ROS2 planner; solver generation in Python for **Forces Pro (licensed) or acados**; "we used Forces Pro for the results in our paper" (README L82). Not callable from our Python loop without ROS/C++ build. Legged evidence: none (Jackal, Dingo configs). Limitations: heavy integration; costmap dependency.

---

## 11. rst-tu-dortmund/teb_local_planner (reference only)

| Field | Value |
|---|---|
| License | BSD-3-Clause (API, default branch); `ros2-master` package.xml `<license>BSD</license>` |
| Default branch / SHA | `noetic-devel` / `8f429538601d7c4102aa345e8b5ba8dfae989c00` (2026-01-09) |
| ROS 2 | `ros2-master` / `e4562a62bac75f6004b74661ba1538be9cd07608` (2024-11-10); **`foxy-devel` / `d6865b419ba70bf637f5125317c380e00f7944c3` (2021-01-04)** |
| Stars / open issues | 1346 / 153 |

Mechanism: footprint models point / circular / two-circles / line / **polygon** with `calculateDistance(pose, obstacle)` — [robot_footprint_model.h#L541-L600](https://github.com/rst-tu-dortmund/teb_local_planner/blob/e4562a62bac75f6004b74661ba1538be9cd07608/teb_local_planner/include/teb_local_planner/robot_footprint_model.h#L541-L600); clearance is a **soft penalty** `penaltyBoundFromBelow(dist, min_obstacle_dist, penalty_epsilon)` in g2o — [g2o_types/edge_obstacle.h#L85-L105](https://github.com/rst-tu-dortmund/teb_local_planner/blob/e4562a62bac75f6004b74661ba1538be9cd07608/teb_local_planner/include/teb_local_planner/g2o_types/edge_obstacle.h#L85-L105). C++ ROS local planner; the only surveyed footprint-aware planner with a Foxy branch, but 2021-era. Not Python-callable. `rst-tu-dortmund/mpc_local_planner` (GPL-3.0, `master` `5b4e465fec718245484e8668e6dd45539ca37983`, last commit 2021-01-04, ROS 1) was metadata-checked only.

---

## 12. elena-ecn/mpc-cbf

| Field | Value |
|---|---|
| URL | https://github.com/elena-ecn/mpc-cbf |
| License | **MIT** (root LICENSE) |
| Default branch / SHA | `main` / `aa6f12250d23b9645c830af4fcdd76c77c44e369` |
| Last commit | 2022-12-24T04:57:20Z |
| Stars / open issues | 194 / 2 |

Mechanism: do-mpc (CasADi/IPOPT) unicycle MPC with either distance constraints (MPC-DC) `-(dx^2+dy^2) + (r + r_obs + safety_dist)^2 <= 0` or discrete CBF constraints — [mpc_cbf.py#L172-L230](https://github.com/elena-ecn/mpc-cbf/blob/aa6f12250d23b9645c830af4fcdd76c77c44e369/mpc_cbf.py#L172-L230); robot radius `r = 0.1`, `safety_dist = 0.03`, `T_horizon = 20` in [config.py](https://github.com/elena-ecn/mpc-cbf/blob/aa6f12250d23b9645c830af4fcdd76c77c44e369/config.py). Static obstacles are baked into the NLP at setup (constants), so runtime obstacle updates need rebuild or refactor to time-varying parameters (moving obstacles already use `_tvp`). Closest in structure to our N=20 CasADi unicycle MPC, but a disc-only teaching example; stale.

---

## 13. Legged-specific leads that are NOT reusable (license) or stale

| Repo | License finding | SHA / last commit | What it does | Status |
|---|---|---|---|---|
| HybridRobotics/quadruped_nmpc_dcbf_duality | No root LICENSE; only `legged_control/LICENSE` (third-party subtree). `cbf_duality` (the paper code) unlicensed. | `master` `57516db14c55111dbddfcc7d61f17c038f6bfb61`, 2023-01-02 | NMPC + duality DCBF for Unitree A1 in narrow spaces, ROS 1 (README: arXiv:2212.14199, `roslaunch`) | **no license: not reusable** (cbf_duality part) |
| HybridRobotics/depth_cbf | No LICENSE anywhere in tree (53 files) | `main` `501ca1a918f6ef05565bfed17a1bf65a270320ee`, 2024-11-12 | Fits local quadratic CBF over point clouds; quadrotor sim + TurtleBot3 hardware (README) | **no license: not reusable** |
| LeCAR-Lab/ABS | No root LICENSE; README L13 declares **CC BY-NC 4.0** (non-commercial) | `main` `9b95329ffb823c15dead02be620ff96938e4d0a3`, 2024-07-11 | Go1 agile policy + learned reach-avoid value + recovery policy; 11 planar rays over +-45 deg, max 6 m — [training/legged_gym/legged_gym/envs/go1/go1_pos_config.py#L137-L144](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/go1/go1_pos_config.py#L137-L144); RSS 2024 | NC-licensed; requires retraining for Lite3; not a (v, w) filter |
| tayalmanan28/Safe-Legged-CollisionCone-CBF | Apache-2.0 (`LICENSE.txt`, inherited from a motion_imitation fork) | `main` `b136f9306e1120bdc68ae4c1923eebf07c2583ab`, 2024-11-16 | C3BF for legged robots; README is a single title line; repo contains compiled `.so` and egg-info | reusable license but stale/undocumented; 5 stars |
| tkkim-robot/safe_control | none | see section 1 | unicycle CBF/MPC-CBF zoo | **no license: not reusable** |

---

## 14. Distance-field / mapping alternatives (metadata + brief)

| Repo | License | Default branch / SHA / last commit | Notes |
|---|---|---|---|
| ethz-asl/voxblox | BSD-3-Clause | `master` / `c8066b04075d2fee509de295346b1c0b788c4f38` / 2021-11-22 | CPU TSDF->ESDF, ROS 1 catkin; 77 open issues; effectively unmaintained |
| HKUST-Aerial-Robotics/FIESTA | MIT | `master` / `d01ce1b4602340a417a68ec7bb5f6b5a6790207e` / 2019-09-10 | Incremental ESDF, ROS 1; unmaintained |
| ethz-asl/wavemap | BSD-3-Clause | `main` / `db4f2fffdc1da1bec042d51bfff58029c0c9c827` / 2024-12-10 | CPU wavelet occupancy; `pywavemap` Python bindings (`library/python/src/*.cc`), occupancy/classification queries in Python examples; ESDF only as C++ example `examples/cpp/planning/occupancy_to_esdf.cc`; ROS 1 interfaces |
| NVlabs/curobo (cuRoboV2) | Apache-2.0 (LICENSE + README L44-L46) | `main` / `78fd485fa82d9b9a063fb4985e371814587e666a` / 2026-09-10 | GPU ESDF mapper from depth (`curobo/_src/perception/mapper/integrator_esdf.py`, jump-flooding EDT), sphere fitting (`curobo/_src/geom/sphere_fit/`), scene-collision cost. Manipulator/high-DoF focus; mobile-base use UNVERIFIED; PyTorch+Warp+CUDA; v2 API break (README L10) |
| scipy.ndimage.distance_transform_edt | BSD-3 (SciPy) | n/a | Lightweight option: egocentric 2D occupancy grid from depth -> EDT on CPU. Not surveyed in code; lead only |

---

## 15. Isaac Sim / Isaac Lab native geometry queries (simulation-only oracles)

- **PhysX scene queries** (Omni Physics docs, https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/extensions/runtime/source/omni.physx/docs/dev_guide/scene_queries.html, fetched 2026-09-14): `overlap_box(extent, origin, rotation, callback, ...)`, overlap sphere/shape/mesh; sweep variants (sphere, cube, mesh, shape) returning hit position, normal, distance "identical to those of the corresponding Raycast queries". A swept oriented box equal to the Lite3 body along the predicted MPC trajectory gives a **ground-truth** footprint clearance/veto. No repo SHA (product API). Uses simulator ground truth, so it is an evaluation oracle / upper bound, not a deployable filter.
- **Isaac Lab RayCaster** (isaac-sim/IsaacLab, BSD-3-Clause; default branch `release/3.0.0-beta2` / `0603cb1710dcda13087665f63abf9ac483b63c05`, where ray_caster files were refactored into `base_ray_caster.py` etc.; `main` / `b0542fe2d45bf91c4e1d9ef6952b9c709c80b4e8`, 2026-07-24): "Currently, only static meshes are supported" and single mesh prim — [main: source/isaaclab/isaaclab/sensors/ray_caster/ray_caster.py#L50-L53](https://github.com/isaac-sim/IsaacLab/blob/b0542fe2d45bf91c4e1d9ef6952b9c709c80b4e8/source/isaaclab/isaaclab/sensors/ray_caster/ray_caster.py#L50-L53); `multi_mesh_ray_caster.py` advertises dynamic mesh tracking (docstring L51-L54 at main). A body-mounted 360 deg planar ray ring would give ABS-style distances in sim without camera FOV limits; again not transferable to the real sensor suite. Which Isaac Lab version our sim uses: UNVERIFIED here.

---

## 16. Cross-cutting analysis for Lite3 (surveyor derivations; not from any repo)

Footprint approximations of a 0.61 x 0.39 m rectangle (half extents 0.305 x 0.195):
- circumscribed disc r = sqrt(0.305^2 + 0.195^2) = 0.362 m (lateral over-margin 0.167 m);
- 2 discs at x = +-0.1525: r = 0.248 m (lateral over-margin 0.053 m);
- 3 discs at x = 0, +-0.203: r = 0.220 m (lateral over-margin 0.025 m);
- minimal-area circumscribing ellipse: semi-axes 0.431 x 0.276 m;
- exact: rectangle/polygon (HybridRobotics/cbf duality, NeuPAN, Nav2 approach, TEB, elevation_mapping polygon check, PhysX box sweep).
- Incident context: the MPC path passed 0.13 m from the corner, i.e. inside even the inscribed half-width 0.195 m, before any margin.

Perception geometry: a head camera with HFOV 79 deg sees a point at lateral offset y only when its forward distance from the camera exceeds y / tan(39.5 deg) = 1.21 y. A box corner 0.30 m to the side leaves the view when it is still ~0.36 m ahead of the camera, so the hip passes it "blind". Any purely per-frame reactive filter (composite_cbf, Nav2 collision monitor with the head camera only, NeuPAN fed with current-frame points) therefore needs a persistent local map (nvblox, elevation_mapping_cupy, or an odometry-registered 2D grid) or a wider sensor (MID-360 on the real robot). The camera mounting offset from body centre is UNVERIFIED.

Model mismatch: all filters above certify a kinematic or double-integrator reduced model; the RL locomotion policy's tracking error of (vx, vy, wz), the 250 ms watchdog and the 2.5 Hz / 10 Hz rate split are outside every certificate (cbfkit README L158 says exactly this for G1).

---

## 17. Ranking (best fit first) and what was not verified

| # | Repo | License | Pinned SHA | Mechanism (one line) | In our Python loop | Fit notes |
|---|---|---|---|---|---|---|
| 1 | bardhh/cbfkit | BSD-3-Clause | c4a326e10c63e8147825eaa221dc076882aff060 | CBF-QP `SafetyFilter(state, u_nom)`; rotating-ellipse footprint HOCBF | yes (JAX CPU) | Active; ANYmal-C Isaac Lab + G1 MuJoCo sim evidence; fail-open default; ellipse not rectangle; no perception |
| 2 | HybridRobotics/cbf | Apache-2.0 | d3412d229cd957a215b2ca562ca505fc4a4a33f8 | Duality DCBF: rotated rectangle robot vs convex polytope obstacles, hard NLP constraints in CasADi Opti/IPOPT | yes | Exact footprint in CasADi; acceleration unicycle; polytope obstacles; stale 2022; timing unmeasured |
| 3 | nvidia-isaac/nvblox (nvblox_torch) | Apache-2.0 | 24eee4948768682fa1ffb969b881efee4fca29c2 | GPU depth->ESDF, query with per-sphere radius subtraction + gradient | yes (GPU) | Supplies h and grad for a multi-disc footprint and remembers out-of-FOV geometry; GPU memory vs 2.3 GiB UNVERIFIED |
| 4 | ros-navigation/navigation2 nav2_collision_monitor | Apache-2.0 (pkg) | f31c7f49bf7afb9e32f4651ef91fb46f5636c88c | Footprint-polygon time-to-collision veto/scale on points | no (C++ ROS 2 Humble+, not Foxy) | Mature reference design; reactive only |
| 5 | leggedrobotics/elevation_mapping_cupy | MIT | 20a8a26b67a995b43eb44c23568854d1fed82a52 (main) / 8fd49565f622ae1481c0a22d6c8897441f7e2b7e (ros2) | GPU 2.5D map + footprint polygon traversability check | partial (core class ROS-free, CuPy GPU) | Legged-proven (ANYmal); map not filter |
| 6 | StanfordASL/cbfpy | MIT | f5bff8b93609d6a164fd8beeef962c92e4476dcb | Generic JAX CBF-QP filter, relaxed by default | yes | No geometry; soft by default |
| 7 | hanruihua/NeuPAN | GPL-3.0 | f5ae6d848b54aeae0340af1eb49e3a809dea00a5 | Point-level polygon-footprint MPC (DUNE + cvxpylayers), soft penalty + stop veto | yes (replaces MPC) | Copyleft; per-geometry training; open issues on avoidance failures |
| 8 | ntnu-arl/composite_cbf | BSD-3-Clause | 0a7b6f54af68dfe0663afe2a3a61a50f5ae22ea6 | Log-sum-exp composite CBF over point cloud, sphere radius, closed-form QP | no (C++ ROS 2); ~100-line core portable | Multirotor acc model; unconstrained-FoV only; fail-open on obstacle timeout |
| 9 | tud-amr/mpc_planner | Apache-2.0 | 3002da6a5e43b3577f584381bbcad569c82a381b | Multi-disc footprint in DecompUtil free-space polytopes, slack constraints, acados/Forces | no (C++ ROS) | Heavy; paper results with licensed Forces Pro |
| 10 | rst-tu-dortmund/teb_local_planner | BSD-3-Clause | e4562a62bac75f6004b74661ba1538be9cd07608 (ros2-master); d6865b419ba70bf637f5125317c380e00f7944c3 (foxy-devel) | Polygon footprint distance, soft penalty in g2o | no | Only Foxy-branch footprint planner; 2021-era |
| 11 | elena-ecn/mpc-cbf | MIT | aa6f12250d23b9645c830af4fcdd76c77c44e369 | do-mpc unicycle MPC with disc distance or DCBF constraints | yes | Same structure as our MPC; disc only; static obstacles baked in; stale |
| - | tkkim-robot/safe_control | none | 8fdf87b5015a74a75d96f678ddc81b371b06cf0e | Disc-robot unicycle CBF-QP (Gurobi) and MPC-CBF | yes | no license: not reusable |
| - | HybridRobotics/quadruped_nmpc_dcbf_duality | none (cbf_duality) | 57516db14c55111dbddfcc7d61f17c038f6bfb61 | A1 NMPC + duality DCBF | no (ROS 1) | no license: not reusable |
| - | HybridRobotics/depth_cbf | none | 501ca1a918f6ef05565bfed17a1bf65a270320ee | Point-cloud quadratic CBF regression | partial | no license: not reusable |
| - | LeCAR-Lab/ABS | CC BY-NC 4.0 (README) | 9b95329ffb823c15dead02be620ff96938e4d0a3 | Learned reach-avoid value + recovery policy (Go1) | no | NC; retraining needed |

UNVERIFIED items (explicit): all runtime/solve-time claims; nvblox_torch and elevation_mapping_cupy GPU memory; NeuPAN ">15 Hz on i7"; Nav2 timing hardware; Isaac Lab version in our sim; camera mount offset on Lite3; D435i depth FOV/min range; any legged use of nvblox, Nav2 collision monitor, NeuPAN, composite_cbf; ROS 2 Foxy EOL date (not fetched; docs.ros.org returned Access Denied).
