---
origin: ai+web
reviewed: false
date: 2026-09-17
status: surveyed
stage: planning
family: A (legged-robot simulation training and evaluation code)
---

# Survey A: how legged-robot sim code classifies contact and collision

**Question.** Before we set acceptance criteria for the unmapped-box test (and, later, stairs), how do
open-source legged-robot training and evaluation codebases treat contact? Specifically:

1. which bodies count, against what, at what force threshold, over what time window, and whether
   contact ends the episode, is penalised, or is only measured;
2. in navigation evaluation, what counts as a collision or failure, and how unavoidable terrain and
   stair contact is handled;
3. which Isaac Lab mechanism separates contact with one object from terrain contact, and its limits.

**Status: `surveyed` only.** Nothing was cloned into the project, imported, installed, built or run.
Source was read at pinned commits through `gh api` / `raw.githubusercontent.com` into the session
scratchpad. Papers were read as arXiv HTML. InternNav was read from the existing local snapshot
`references/upstream/2026-09-08_dualvln` (commit `7a5c624`, per its `SOURCE.md`). The local V12
config was read read-only from the sibling `machine-dog` repository (commit `24aa6ca`, file clean in
git). Anything not read directly is marked **UNVERIFIED**.

**License note.** The GitHub license detector returns `NOASSERTION` or nothing for several repos. The
licenses below come from the LICENSE file text or the README statement, as noted.

---

## 0. Summary table

| Repo (pin) | License | What counts as contact / collision | Terrain / stair contact | Thresholds / windows |
|---|---|---|---|---|
| isaac-sim/IsaacLab v2.3.2 `37ddf62` | BSD-3-Clause | Velocity task: base contact ends the episode; thigh contact is penalised. Unitree Go1/Go2/A1 configs turn the thigh penalty off; Spot ends the episode on body or any leg contact | No distinction: the sensor reads net force from every partner. The rough terrain includes 5–23 cm stairs, and shank and foot contact on stairs is free | 1 N on the max norm over a 3-physics-step history |
| fan-ziqi/robot_lab `500399e` (Lite3 config) | Apache-2.0 | Lite3: every non-foot body penalised; no contact ends the episode | Same terrain as Isaac Lab; not separated | 1 N |
| Local V12 (machine-dog `24aa6ca`) | project | Thigh and shank penalised; TORSO contact ends the episode | Not separated | 5 N penalty; 1 N termination |
| leggedrobotics/legged_gym `8fa29ac` | BSD-3-Clause (text) | Contact on `terminate_after_contacts_on` bodies (base) ends the episode; contact on `penalize_contacts_on` bodies (thigh/calf or thigh/shank) is penalised | 60% of the terrain is stairs; contact is still not separated. Known GPU trimesh contact-force caveat | Termination 1 N; penalty 0.1 N |
| leggedrobotics/viplanner `6fcf3c6` | BSD-3-Clause | Isaac demo ends on base contact. Paper evaluation uses goal-reached rate plus cost-map loss, with no contact metric | Stairs are a free-cost semantic class | 1 N; goal 0.3 m (demo), 0.5 m (paper) |
| leggedrobotics/iplanner `4a8d823` | MIT | SPL in a Gazebo wheeled sim; the repo has no sim-evaluation code | n/a | n/a |
| yang-zj1026/legged-loco `87b0d3d` (NaVILA) | MIT | Vision policy: base, hip, head or calf contact ends the episode; head/hip/thigh/calf contact is penalised | Stairs commented out; obstacles are terrain sub-meshes | Termination 1 N; penalty 0.1 N |
| yang-zj1026/NaVILA-Bench `e9d2db1` | MIT (text) | Base contact or bad orientation ends the episode; no collision metric | Not separated | 1 N; 0.8 rad |
| InternRobotics/NavDP `bff5eb8` | CC BY-NC-SA 4.0 (README; no LICENSE file) | Point/image goal: no contact term, only a stuck check. Exploration: base contact >15 N ends the episode, and Time = time to first collision | Wheeled Dingo; n/a | 15 N; stuck = moved <0.1 m over 30 steps |
| InternRobotics/InternNav `7a5c624` (VLN-PE) | MIT | Fall (roll >15°, pitch >35°, or base too low) and stuck; reported as FR and StR; no contact metric | Stair episodes filtered out of R2R (paper) | stuck = moved <0.2 m and turned <15° within a step window |
| LeCAR-Lab/ABS `9b95329` | CC BY-NC 4.0 (README; reference only) | Evaluation collision = base/front thigh/front calf >1 N, or a front-foot *horizontal* hit; counted only near an obstacle while moving, or on base contact | Flat ground with obstacles; the proximity gate removes spurious contacts | 1 N; foot `|F_xy| > 2|F_z| + 10 N`; within 0.95 m and faster than 0.5 m/s |
| chengxuxin/extreme-parkour `d2ffe27` | CC BY-NC 4.0 (LICENSE) | No contact ends the episode (only roll/pitch/height); thigh/calf/base penalised; foot stumble and foot-on-edge penalised | Edge contact measured by a geometric edge mask, not by force | 0.1 N; `|F_xy| > 4|F_z|` |
| ZiwenZhuang/parkour `5e1f413` | MIT | Go2 field: no contact ends the episode; thigh/calf/base penalised (−0.05); geometric penetration depth penalised | Termination thresholds depend on the obstacle type (stairs are in the track) | roll 1.4 rad, pitch 1.6 rad |

---

## 1. isaac-sim/IsaacLab

- **Pin:** tag `v2.3.2` = `37ddf626871758333d6ed89cf64ad702aef127d0`. This matches the
  `isaaclab 2.3.2.post1` wheel our runners use, per project memory. The default branch `develop` HEAD
  `93d7bef70bb2c24720a01342ab6ca58bdd906f8c` (2026-09-17) was read only for doc and code changes.
- **License:** BSD-3-Clause (GitHub API and SPDX headers).

### 1.1 ContactSensor mechanism (Q3)

What the code does:
- **Sensor bodies must be rigid bodies carrying `PhysxContactReportAPI`.** Initialisation raises an
  error if no matching body has the API.
  [contact_sensor.py L257-L299](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L257-L299)
- **The API goes on through the spawner flag `activate_contact_sensors`.** That flag applies it only
  to prims with `RigidBodyAPI`, with a report threshold of 0 and a sleep threshold of 0.
  [schemas.py L515-L574](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sim/schemas/schemas.py#L515-L574)
- **The sensor wraps one PhysX `RigidContactView`,** created with the sensor glob and
  `filter_patterns = filter_prim_paths_expr`.
  [contact_sensor.py L277-L290](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L277-L290)
- **`net_forces_w` (N, B, 3)** comes from `get_net_contact_forces(dt)`. It is the sum over *all*
  partners (terrain, box, own links), and its documentation says it is **normal force only** (no
  friction).
  [contact_sensor_data.py L74-L82](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_data.py#L74-L82),
  [contact_sensor.py L370-L378](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L370-L378)
- **`force_matrix_w` (N, B, M, 3)** comes from `get_contact_force_matrix(dt)`. It exists only when
  `filter_prim_paths_expr` is non-empty and holds normal force per sensor-body × filter-prim pair.
  [contact_sensor.py L350-L362](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L350-L362),
  [L380-L390](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L380-L390),
  [contact_sensor_data.py L97-L117](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_data.py#L97-L117)
- **Optional per-filter data:** contact points (averaged) and friction forces (summed). Both require
  a non-empty filter list, and `max_contact_data_count_per_prim` (default 4) sizes the buffer.
  [contact_sensor_cfg.py L23-L40](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_cfg.py#L23-L40),
  [contact_sensor.py L316-L343](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L316-L343)
- **`force_threshold` (default 1 N) drives only the air-time and contact-time bookkeeping.** It does
  not gate the force outputs.
  [contact_sensor_cfg.py L45-L50](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_cfg.py#L45-L50),
  [contact_sensor.py L416-L444](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L416-L444)

Limits, as documented and as the code implies:

- **One-to-many filtering only.** The class docstring says filtered reporting works only when *one*
  sensor body per environment is filtered against many bodies. For several bodies you must create
  one sensor per body; the docstring's own example is per-foot sensors against an object.
  [contact_sensor.py L50-L59](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor.py#L50-L59),
  [contact_sensor_cfg.py L66-L71](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_cfg.py#L66-L71).
  - The overview page states the same limit (it calls it "many-to-one", with the same meaning).
    [contact_sensor.rst L13-L15, L97](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/docs/source/overview/core-concepts/sensors/contact_sensor.rst#L13-L15)
  - The v2.3.2 code does **not** enforce the limit. It builds a (N, B, M, 3) matrix for any B, so a
    multi-body sensor with filters fails silently rather than raising (inference from the code; not
    run).
- **Root cause, in the PhysX tensor API.** `create_rigid_contact_view` pairs sensors and filter
  objects one-to-one by index. It makes an exception when a filter pattern matches a *single* prim:
  then every sensor is paired with that prim.
  [omni.physics.tensors 107.3 API](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.3/extensions/runtime/source/omni.physics.tensors/docs/api/python.html)
  (read 2026-09-17).
  - **Implication (UNVERIFIED at runtime):** with `num_envs=1` and a box that is one prim, a sensor
    over all robot links filtered against that box *may* work through the single-prim exception.
    Isaac Lab does not document or test this case.
- **The supported pattern that fits our box test is to put the sensor on the box.** The box is a
  single sensor body, and `filter_prim_paths_expr` lists the robot links.
  - `force_matrix_w[:, 0, j]` is then the box-vs-link-j normal force. Robot contact with the floor is
    excluded by construction.
  - **Requirement:** the box must be a rigid body with `activate_contact_sensors=True`.
  - **UNVERIFIED:**
    - that a kinematic or static box still reports;
    - that a filter glob matching 17 links per env resolves correctly when `num_envs > 1`.
  - The PhysX view exposes `filter_paths`/`filter_names`, which can confirm the ordering (API doc
    above).
- **Filter targets can be static colliders.** Isaac Lab's own tests filter against the ground
  `CollisionPlane` and against the generated terrain `…/terrain/mesh`.
  [test_contact_sensor.py L463, L607-L613](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/test/sensors/test_contact_sensor.py#L607-L613)
- **Stair limitation:** the terrain generator produces *one* mesh prim (`…/terrain/mesh`) for all
  sub-terrains. Filtering cannot separate a stair edge from the floor in a generated terrain.
  Separating them needs stairs authored as their own prims in the scene USD (our building USD's
  prim layout was not checked here).
- **Summing the force matrix gives the net force only if the filters cover every contacting
  object.** Stated in the develop docs.
  [develop contact_sensor.rst L42-L49](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/docs/source/concepts/sensors/contact_sensor.rst#L42-L49)
- **Develop branch (Isaac Lab 3.x, not our version).**
  - The docs still require one sensor body per env when filters are set, and state that PhysX
    `net_forces_w` is normal-only.
    [develop contact_sensor.rst L21-L49](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/docs/source/concepts/sensors/contact_sensor.rst#L21-L49)
  - The PhysX backend now passes one sensor pattern per body, each with a replicated filter list. That
    matches the tensor API's list-of-lists form and may lift the limit, but this is **UNVERIFIED**,
    and the docstring was not updated.
    [develop isaaclab_physx contact_sensor.py L377-L394](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab_physx/isaaclab_physx/sensors/contact_sensor/contact_sensor.py#L377-L394)

Sampling and time-window caveats:
- **`history_length > 0` forces a buffer update on every `scene.update`,** which runs every physics
  sub-step inside the decimation loop.
  [sensor_base.py L184-L192](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/sensor_base.py#L184-L192),
  [manager_based_rl_env.py L181-L197](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/envs/manager_based_rl_env.py#L181-L197).
- **With `history_length = 0` and `lazy_sensor_update=True` (the default), data is refreshed only
  when `.data` is read.** An episode maximum read once per policy step therefore samples 1 of
  `decimation` physics steps.
  [interactive_scene_cfg.py L80-L85](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/scene/interactive_scene_cfg.py#L80-L85).
  Whether our runner's "max non-foot contact" samples every physics step was **not checked here**.
- **The stock velocity task uses history 3 with decimation 4.** `illegal_contact` and
  `undesired_contacts` take the max over those 3 samples, so the first sub-step of every 4 is never
  inspected.
  [velocity_env_cfg.py L74, L306-L320](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/velocity_env_cfg.py#L306-L320)
- **Known issue: contact sensor readings are stale right after a reset.**
  [refs/issues.rst L8-L14](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/docs/source/refs/issues.rst#L8-L14).
  An episode maximum should skip the reset step (UNVERIFIED whether this matters for teleports in our
  runner).

### 1.2 Locomotion velocity task (Q1)

- **The sensor covers all robot links:** `ContactSensorCfg(prim_path=".../Robot/.*", history_length=3,
  track_air_time=True)`.
  [velocity_env_cfg.py L74](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/velocity_env_cfg.py#L74)
- **Penalty:** `undesired_contacts` on `.*THIGH` only, threshold 1 N, weight −1. It counts the bodies
  whose max-over-history force norm exceeds the threshold.
  [velocity_env_cfg.py L256-L260](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/velocity_env_cfg.py#L256-L260),
  [rewards.py L267-L275](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/envs/mdp/rewards.py#L267-L275)
  - A force-magnitude penalty `contact_forces` also exists: the sum of the excess over a threshold.
    [rewards.py L288-L296](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/envs/mdp/rewards.py#L288-L296)
- **Termination:** `base_contact = illegal_contact(body_names="base", threshold=1.0)`, again max over
  history.
  [velocity_env_cfg.py L271-L274](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/velocity_env_cfg.py#L271-L274),
  [terminations.py L154-L162](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/envs/mdp/terminations.py#L154-L162)
- **Terrain:** `ROUGH_TERRAINS_CFG` has 20% pyramid stairs and 20% inverted stairs, with step height
  0.05–0.23 m and step width 0.3 m.
  [rough.py L22-L37](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/terrains/config/rough.py#L22-L37)
  - So in the stock ANYmal task, **shank and foot contact with stair edges carries no penalty.** Only
    thighs are penalised and only the base terminates. The ANYmal configs do not override this (grep
    of `anymal_c/d` configs).
- **Per-robot overrides:**
  - Unitree Go2/Go1/A1 set `undesired_contacts = None` and keep only base (or trunk) termination.
    [go2/rough_env_cfg.py L54, L61](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/config/go2/rough_env_cfg.py#L54-L61)
  - Spot (flat terrain only) terminates on `body` or any `.*leg` contact above 1 N.
    [spot/flat_env_cfg.py L285-L288](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/config/spot/flat_env_cfg.py#L285-L288)
- **Curriculum:** terrain level moves by distance walked; contact is not used.
  [curriculums.py L27-L56](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/mdp/curriculums.py#L27-L56)

### 1.3 Isaac Lab navigation task (ANYmal-C pose command)

- **Only base contact above 1 N ends the episode.** It carries a termination penalty of −400. There is
  no collision metric.
  [navigation_env_cfg.py L79, L114-L118](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab_tasks/isaaclab_tasks/manager_based/navigation/config/anymal_c/navigation_env_cfg.py#L114-L118)

---

## 2. fan-ziqi/robot_lab (upstream Lite3 config) and our local V12 config

- **robot_lab pin:** `500399ed75f510aeaff28705a8ce736c514dbec3`. **License:** Apache-2.0 (LICENSE).
- **Lite3 body naming:** base `TORSO`, feet `.*_FOOT`; the other bodies are `*_HIP`, `*_THIGH` and
  `*_SHANK`.
  [deeprobotics_lite3/rough_env_cfg.py L14-L15](https://github.com/fan-ziqi/robot_lab/blob/500399ed75f510aeaff28705a8ce736c514dbec3/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/quadruped/deeprobotics_lite3/rough_env_cfg.py#L14-L15)
- **The Lite3 config penalises every non-foot body** through a negative-lookahead regex, weight −1 at
  1 N. It also penalises foot force above 100 N (weight −1.5e-4).
  [L111-L115](https://github.com/fan-ziqi/robot_lab/blob/500399ed75f510aeaff28705a8ce736c514dbec3/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/quadruped/deeprobotics_lite3/rough_env_cfg.py#L111-L115)
  - It **disables the contact termination** (`illegal_contact = None`).
    [L148-L150](https://github.com/fan-ziqi/robot_lab/blob/500399ed75f510aeaff28705a8ce736c514dbec3/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/quadruped/deeprobotics_lite3/rough_env_cfg.py#L148-L150)
  - The `feet_stumble` term (`|F_xy| > 4|F_z|`, scaled by uprightness) exists but has weight 0 for
    Lite3.
    [mdp/rewards.py L428-L436](https://github.com/fan-ziqi/robot_lab/blob/500399ed75f510aeaff28705a8ce736c514dbec3/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/rewards.py#L428-L436),
    [rough_env_cfg.py L129-L130](https://github.com/fan-ziqi/robot_lab/blob/500399ed75f510aeaff28705a8ce736c514dbec3/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/quadruped/deeprobotics_lite3/rough_env_cfg.py#L129-L130)
- **Local V12 training config** (read-only;
  `machine-dog/2_experiment/baseline_rebuild/go2_rl_robotlab_lite3_v12/source/robot_lab/robot_lab/tasks/lite3/env_cfg.py`,
  last commit `24aa6ca`):
  - the sensor covers all links with history 3 (L84-L90);
  - `undesired_contacts` covers `.*_THIGH|.*_SHANK` at **5 N**, weight −1 (L402-L406);
  - `illegal_contact` fires on `TORSO` at 1 N (L447-L453);
  - hips and feet are not penalised.
  - **Relevance:** V12 was trained to tolerate foot contact and discouraged (not forbidden) from leg
    contact. It was never trained against a zero-contact criterion.

---

## 3. leggedrobotics/legged_gym

- **Pin:** `8fa29acc6fd1910c3d9659eef6310bdd301cde0a`. **License:** BSD-3-Clause (LICENSE text; ETH
  Zurich and NVIDIA).
- **Body selection is by substring match on body names:** `penalize_contacts_on` and
  `terminate_after_contacts_on`.
  [legged_robot.py L653-L659](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot.py#L653-L659)
- **Termination:** net contact force norm above **1 N** on a termination body. Single sample, no
  history.
  [legged_robot.py L138-L143](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot.py#L138-L143)
- **Penalty:** `_reward_collision` counts penalised bodies above **0.1 N**. The default weight is −1.
  [legged_robot.py L849-L851](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot.py#L849-L851),
  [legged_robot_config.py L143](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot_config.py#L143)
  - Foot stumble (`|F_xy| > 5|F_z|`) and foot force above `max_contact_force` (100 N) exist; stumble
    has weight 0 by default.
    [legged_robot.py L895-L906](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot.py#L895-L906)
- **Robot configs:**
  - A1: penalise thigh/calf, terminate on base.
    [a1_config.py L67-L68](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/a1/a1_config.py#L67-L68)
  - ANYmal-C rough: penalise SHANK/THIGH, terminate on base.
    [anymal_c_rough_config.py L75-L76](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/anymal_c/mixed_terrains/anymal_c_rough_config.py#L75-L76)
- **Terrain mix:** 35% stairs up and 25% stairs down.
  [legged_robot_config.py L60-L64](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot_config.py#L60-L64).
  Stair contact is not separated from other contact.
- **Known issue:** `net_contact_force_tensor` is unreliable on GPU with triangle-mesh terrain. The
  README suggests foot-only force sensors as a workaround.
  [README.md L84-L85](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/README.md#L84-L85).
  This applies to Isaac Gym; whether PhysX 5 in Isaac Sim 5.x has an analogue is **UNVERIFIED**.

---

## 4. leggedrobotics/viplanner

- **Pin:** `6fcf3c60f6fa3b28b3a11af054d6033825923789`. **License:** BSD-3-Clause (LICENSE text; the
  README says it belongs to RSL, as noted in the 09-14 survey).
- **Isaac demo terminations:** time-out, base contact above 1 N, and goal within 0.3 m.
  [base_cfg.py L106-L114](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/omniverse/extension/omni.viplanner/omni/viplanner/config/base_cfg.py#L106-L114),
  [terminations.py L20-L44](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/omniverse/extension/omni.viplanner/omni/viplanner/viplanner/mdp/terminations.py#L20-L44)
- **Offline evaluation is geometric, not contact-based.** It reports goal-reached rate (distance
  tolerance) and "obstacle loss": the recorded path's cost on the cost map, with a within-threshold
  rate and maximum.
  [eval_utils.py L102-L141](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/utils/eval_utils.py#L102-L141)
- **Paper** (arXiv 2310.00982v3, Table II): 500 random start-goal paths per scene in Isaac with a
  full-body ANYmal. Metrics are goal-reached rate at 0.5 m, plus geometric and semantic cost-map loss.
  There is no contact or collision count.
  - Stairs are in the free-cost semantic class (Table I), so they are intended to be traversed.
  - A predicted collision probability above 0.5 blocks execution of a plan.

## 5. leggedrobotics/iplanner

- **Pin:** `4a8d823ff9d09c3f626b727e7e00484b38f80d49`. **License:** MIT (LICENSE, Fan Yang 2023).
- **The repo is a ROS planner with no simulation-evaluation code** (tree listing).
- **Paper** (arXiv 2302.11434): evaluated by SPL in four Gazebo environments of the CMU Autonomous
  Exploration Development Environment, 30 start-goal pairs each.
  - How collisions or failures were counted is not specified in the text read (**UNVERIFIED**).
  - The ViPlanner paper says iPlanner was evaluated with a point-robot approximation.
  - Not a legged contact reference.

---

## 6. NaVILA: yang-zj1026/legged-loco (low-level policy training)

- **Pin:** `87b0d3d18404e784abc0a62227bc41c940f29ecc`. **License:** MIT (LICENSE).
- **Go2 vision policy terminations:** base, `.*_hip`, `Head.*` and `.*_calf` contact above **1 N**
  each end the episode, as does bad orientation.
  [go2_low_vision_cfg.py L263-L285](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/config/go2/go2_low_vision_cfg.py#L263-L285)
- **Penalty:** `collision_penalty` on head/hip/thigh/calf above **0.1 N**, weight −5, plus a
  termination penalty of −200.
  [L206, L254-L261](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/config/go2/go2_low_vision_cfg.py#L254-L261),
  [objnav_rewards.py L433-L443](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/leggedloco/mdp/rewards/objnav_rewards.py#L433-L443)
- **Terrain:** random rough plus discrete obstacles 0.3–2.0 m tall. Stairs are commented out. The
  obstacles are part of the terrain mesh, so contact is not separated per object.
  [L65-L131](https://github.com/yang-zj1026/legged-loco/blob/87b0d3d18404e784abc0a62227bc41c940f29ecc/isaaclab_exts/omni.isaac.leggedloco/omni/isaac/leggedloco/config/go2/go2_low_vision_cfg.py#L65-L131)
- **Paper** (arXiv 2412.04453v2, Table V): reports a low-level "collision rate" (NaVILA 0.81 vs ROA
  3.09).
  - The metric definition, unit and denominator were **not found** in the text read (**UNVERIFIED**).

## 7. NaVILA-Bench (VLN-CE-Isaac): yang-zj1026/NaVILA-Bench

- **Pin:** `e9d2db12ce5788c0f987d734c0094100b6bc0d3a`. **License:** MIT (LICENSE text; the API says
  NOASSERTION).
- **Measures:** PathLength, DistanceToGoal, Success, SPL, ONE and OSR. **There is no collision
  measure.**
  [measures.py L99-L313](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/isaaclab_exts/omni.isaac.vlnce/omni/isaac/vlnce/utils/measures.py#L239-L272),
  [navila_eval.py L146-L153](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/scripts/navila_eval.py#L146-L153)
  - Success requires STOP to be called within the goal radius.
- **Failure path:** the Go2 environment ends the episode on base contact above 1 N or orientation
  above 0.8 rad. The evaluation loop breaks on `done`, so a base collision becomes a non-success
  outcome.
  [go2_matterport_base_cfg.py L230-L245](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/isaaclab_exts/omni.isaac.vlnce/omni/isaac/vlnce/config/go2/go2_matterport_base_cfg.py#L230-L245),
  [navila_eval.py L336-L339](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/scripts/navila_eval.py#L336-L339)
  - Leg contact with furniture or stairs neither ends the episode nor is counted.
- **Episode selection:** the paper selects 1,077 of 1,839 R2R val-unseen episodes as "traversable".
  Whether stair episodes were excluded is **UNVERIFIED**.

---

## 8. InternRobotics/NavDP (InternVLA-N1 System-1 benchmark)

- **Pin:** `bff5eb8857f50e082243fb455d312409daabc3aa`. **License:** the README states CC BY-NC-SA 4.0,
  and there is no LICENSE file.
  [README.md L305-L306](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/README.md#L305-L306)
- **Robot:** wheeled Dingo only. The contact sensor is on `base_link` only (history 10, 0.02 s
  period).
  [dingo_config.py L33-L46](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/configs/robots/dingo_config.py#L33-L46)
- **Point-goal and image-goal:** terminations are time-out, arrival (under 0.85 m and slow) and stuck
  (moved under 0.1 m over 30 steps). **There is no contact term.**
  [wheeled_task.py L72-L96, L543-L552](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/configs/tasks/wheeled_task.py#L543-L552)
  - Success is final goal distance under 1.0 m at done.
    [eval_pointgoal_wheeled.py L258-L266](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/eval_pointgoal_wheeled.py#L258-L266)
- **No-goal exploration:** base contact above **15 N** ends the episode.
  [wheeled_task.py L530-L540](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/configs/tasks/wheeled_task.py#L530-L540)
  - The metrics are Time and Area.
    [eval_nogoal_wheeled.py L303-L306](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/eval_nogoal_wheeled.py#L303-L306)
  - The paper (arXiv 2505.08712v3) defines Time as the average time before one collision happens.
- **Relevance:** in the goal tasks, collisions surface only indirectly (as stuck or time-out). No
  legged or stair evaluation.

## 9. InternRobotics/InternNav (VLN-PE physical evaluation)

- **Pin:** local snapshot `7a5c62400ac45b313d9b709c740b64191556a242`. **License:** MIT.
- **Fall check** (instantaneous): |pitch| > 35°, |roll| > 15°, or base-to-bottom height below a
  threshold (0.5 m for H1).
  [common.py L63-L89](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/evaluator/utils/common.py#L63-L89),
  [vln_default_config.py L182-L192](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/configs/evaluator/vln_default_config.py#L182-L192)
- **Stuck check:** moved under 0.2 m and turned under 15° within a window (`max_iter=2500` in
  `DoneChecker`).
  [stuck_checker.py L14-L39](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/evaluator/utils/stuck_checker.py#L14-L39),
  [tasks/utils.py L29-L49](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/env/utils/internutopia_extension/tasks/utils.py#L29-L49)
  - The paper says "50 steps". The units probably differ (agent steps vs sim steps), which is
    **UNVERIFIED**.
- **Reporting:** FR and StR are reported as failure-reason fractions.
  [result_logger.py L105-L126](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/evaluator/utils/result_logger.py#L105-L126)
  - **There is no contact-force metric.**
  - The teleport ("flash") controller does refuse moves into occupied top-down map cells (a geometric
    check).
    [vln_move_by_flash_with_collision_controller.py L139-L177](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/env/utils/internutopia_extension/controllers/vln_move_by_flash_with_collision_controller.py#L139-L177)
- **Paper** (arXiv 2507.13019v2): its RL controller does not reliably handle stairs, so episodes with
  stairs were **filtered out** of R2R. Stair contact is excluded by removing the scenario.

---

## 10. LeCAR-Lab/ABS (Agile But Safe): reference only, non-commercial

- **Pin:** `9b95329ffb823c15dead02be620ff96938e4d0a3`. **License:** the README states CC BY-NC 4.0,
  and there is no root LICENSE.
  [README.md L13](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/README.md#L13)
- **Training (Go1):**
  - penalise thigh/calf contact above 0.1 N;
  - terminate on base above 1 N;
  - `feet_collision` = any foot with `|F_xy| > 2|F_z| + 10 N`;
  - collision, feet_collision and termination all weight −100.
  [go1_pos_config.py L85-L86, L185-L202](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/go1/go1_pos_config.py#L185-L202),
  [legged_robot.py L1065-L1067, L1121-L1125](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/base/legged_robot.py#L1121-L1125)
  - The constrained-RL cost is the indicator of any of these.
    [legged_robot_pos.py L207-L215](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/base/legged_robot_pos.py#L207-L215)
  - The paper calls this "undesired collision": base, thighs, calves, and horizontal foot collisions.
  - The paper's recovery policy **allows knee-ground contact** for hard braking.
- **Evaluation testbed** (the most relevant evaluation definition found):
  [testbed.py L172-L188, L358-L377](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L358-L377)
  - **Collision** = base, front thigh or front calf above 1 N, **or** a front-foot horizontal hit.
  - The collision is then **gated by proximity**: it counts only if the robot is within 0.95 m of an
    obstacle and moving faster than 0.5 m/s, *or* if the base itself is in contact. The code comment
    says this removes simulator contacts that cannot be explained.
  - **Outcomes:** reach (under 0.65 m and no collision), collision, or time-out. The paper reports
    success, collision and time-out rates.
- **Relevance:** the one codebase that attributes contact to obstacles, and it does so geometrically
  (distance plus speed), not with per-object force filtering. Foot contact is allowed except for
  horizontal impacts.

## 11. chengxuxin/extreme-parkour

- **Pin:** `d2ffe27ba59a3229fad22a9fc94c38010bb1f519`. **License:** CC BY-NC 4.0 (LICENSE).
- **Termination has no contact term:** only |roll| or |pitch| above 1.5 rad, height below −0.25 m,
  time-out, or goals done.
  [legged_robot.py L290-L306](https://github.com/chengxuxin/extreme-parkour/blob/d2ffe27ba59a3229fad22a9fc94c38010bb1f519/legged_gym/legged_gym/envs/base/legged_robot.py#L290-L306)
  - The config lists `terminate_after_contacts_on=["base"]`, but the overridden `check_termination`
    never uses it.
    [a1_parkour_config.py L66-L67](https://github.com/chengxuxin/extreme-parkour/blob/d2ffe27ba59a3229fad22a9fc94c38010bb1f519/legged_gym/legged_gym/envs/a1/a1_parkour_config.py#L66-L67)
- **Penalties:**
  - collision on thigh/calf/base above 0.1 N (−10);
  - foot stumble `|F_xy| > 4|F_z|` (−1);
  - **feet_edge** (−1): feet in contact that sit on a precomputed terrain **edge mask** (edge width
    0.05 m), applied only at terrain level > 3.
  [legged_robot.py L1253-L1286](https://github.com/chengxuxin/extreme-parkour/blob/d2ffe27ba59a3229fad22a9fc94c38010bb1f519/legged_gym/legged_gym/envs/base/legged_robot.py#L1272-L1286),
  [legged_robot_config.py L142, L303-L310](https://github.com/chengxuxin/extreme-parkour/blob/d2ffe27ba59a3229fad22a9fc94c38010bb1f519/legged_gym/legged_gym/envs/base/legged_robot_config.py#L303-L310)
- **Relevance:** edge contact is a *soft* penalty found by geometry, not a failure.

## 12. ZiwenZhuang/parkour (Robot Parkour Learning)

- **Pin:** `5e1f4136f7fec9dac2741add63ca58d32090666f`. **License:** MIT (LICENSE).
- **The Go2 field config uses no contact termination** (`terminate_after_contacts_on = []`).
  - It penalises thigh/calf/base contact at −0.05 and penetration depth at −0.05.
  - It terminates on roll above 1.4 rad or pitch above 1.6 rad.
  - Stairs up and down (0.1–0.3 m) are in the track.
  [go2_field_config.py L150-L187](https://github.com/ZiwenZhuang/parkour/blob/5e1f4136f7fec9dac2741add63ca58d32090666f/legged_gym/legged_gym/envs/go2/go2_field_config.py#L150-L187),
  [L30-L40, L94-L106](https://github.com/ZiwenZhuang/parkour/blob/5e1f4136f7fec9dac2741add63ca58d32090666f/legged_gym/legged_gym/envs/go2/go2_field_config.py#L94-L106)
- **Obstacle-conditioned termination thresholds:** roll, pitch and z-low thresholds can depend on
  which obstacle type the robot is on.
  [legged_robot_field.py L26-L97](https://github.com/ZiwenZhuang/parkour/blob/5e1f4136f7fec9dac2741add63ca58d32090666f/legged_gym/legged_gym/envs/base/legged_robot_field.py#L26-L97)
- **Penetration penalties are geometric:** points sampled over the body volume are tested against the
  obstacle geometry for depth and volume, weighted by point speed.
  [L503-L515](https://github.com/ZiwenZhuang/parkour/blob/5e1f4136f7fec9dac2741add63ca58d32090666f/legged_gym/legged_gym/envs/base/legged_robot_field.py#L503-L515)
  - Per-episode penetration also drives the curriculum.
    [L209-L219](https://github.com/ZiwenZhuang/parkour/blob/5e1f4136f7fec9dac2741add63ca58d32090666f/legged_gym/legged_gym/envs/base/legged_robot_field.py#L209-L219)
- **UNVERIFIED:** the paper's soft-dynamics description (obstacles made penetrable in pre-training) was
  not read in the paper itself.

---

## 13. Cross-cutting findings

1. **No codebase surveyed uses "zero contact on all non-foot bodies" as its failure test.**
   - Terminations are almost always on the base/torso, at 1 N.
   - Some add hip, head and calf (legged-loco), or all legs (Spot flat).
   - Leg contact is otherwise a *penalty* (0.1–5 N), and several Unitree configs drop it entirely.
   - Parkour codebases drop contact termination altogether and use attitude and height.
2. **Feet are always exempt, apart from "horizontal foot hits".** Those use a friction-cone-like ratio:
   - legged_gym 5×;
   - extreme-parkour and robot_lab 4×;
   - ABS 2× + 10 N.
   The same ratio fires on stair risers and on box sides, so on its own it cannot tell the two apart.
3. **Navigation benchmarks mostly measure outcomes, not contact.**
   - NaVILA-Bench: base contact or orientation causes the episode to end.
   - VLN-PE: fall and stuck rates.
   - NavDP: stuck detection, plus time-to-first-collision only for exploration.
   - ViPlanner: cost-map loss.
   Only ABS counts a collision rate, and it attributes contact to obstacles with a distance and speed
   gate.
4. **Stairs are handled by exclusion or tolerance, never by zero contact.**
   - VLN-PE filters stair episodes out.
   - Isaac Lab and legged_gym stairs penalise only thigh (or thigh/calf) contact.
   - Parkour codebases use soft edge and penetration penalties with obstacle-specific thresholds.
5. **Separating object contact from terrain contact is possible in Isaac Lab but constrained.**
   - One sensor body per env when filtering, so either put the sensor on the box or use one sensor per
     robot link.
   - Terrain-generator stairs are one mesh with the floor.
   - `net_forces_w` is normal-only.
   - Sampling depends on `history_length` and lazy updates.
   No surveyed navigation code uses `force_matrix_w` for its evaluation metric.

## 14. UNVERIFIED items (collected)

- The Isaac Lab 2.3.2 multi-body sensor filtered against a single-prim box (the tensor-API single-prim
  exception): runtime behaviour.
- A box-side sensor with a robot-link glob filter when `num_envs > 1`; contact reporting when the box is
  kinematic or static.
- Whether develop's per-body sensor patterns lift the one-sensor-body limit.
- A PhysX 5 analogue of the Isaac Gym GPU trimesh contact-force caveat.
- The NaVILA "collision rate" definition. Whether NaVILA-Bench's 1,077 episodes exclude stairs.
- iPlanner's collision and failure counting in Gazebo.
- The VLN-PE stuck-window units: 2500 in code vs "50 steps" in the paper.
- The robot-parkour soft-dynamics description in the paper.
- Whether our runner's current "max non-foot contact" reads every physics step, skips the reset step,
  and uses `net_forces_w` (normal-only). Not inspected in this survey.

## 15. Not checked or skipped

- IsaacGymEnvs, rsl_rl: no contact-classification logic relevant beyond legged_gym.
- AnjieCheng/NaVILA (Apache-2.0, `76b98f2`): the VLA repo, not the simulator.
- No dedicated open-source *legged navigation benchmark with stairs and a contact metric* was found
  among the candidates. The closest are VLN-PE (stairs removed) and NaVILA-Bench (no contact metric).
