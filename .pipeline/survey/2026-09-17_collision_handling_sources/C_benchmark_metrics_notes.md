---
origin: ai+web
reviewed: false
date: 2026-09-17
status: surveyed
stage: planning
family: "C: navigation benchmark collision metrics and scoring"
---

# Survey C: how navigation benchmarks detect, score, and report collisions

**Label: `surveyed` only.** Nothing was cloned into the project, imported, installed, built, or run. Source files were
read through `gh api repos/OWNER/REPO/contents/PATH?ref=SHA` at the HEAD commit returned on 2026-09-17. Papers were
read as arXiv PDFs converted with `pdftotext`. The CARLA scoring page was read from the official leaderboard site.
Scratch copies stayed in the session scratchpad, not in the project. Line numbers refer to the pinned commit.
"Inference" marks my own reading of the code and is not an upstream statement.

**Why this survey exists.** The current Lite3 episode check is "maximum non-foot contact force = 0 N". The next test
puts an unmapped box on the route, and stairs come later. Dr Sun expects some contact to be unavoidable, especially on
stairs. This survey records how existing benchmarks define and score collisions before we set acceptance criteria.

**Terminology check.** `.pipeline/terminology/terminology.md` has no collision or contact terms yet. The terms below
("support contact", "obstacle collision event", "near-miss") are working labels for this note only. They are not
proposed project terms.

---

## 0. Summary table

| Benchmark (commit) | License | Detection | Consequence | Harmless contact / terrain | Reporting |
|---|---|---|---|---|---|
| BARN (`bf5a226`) | MIT | Gazebo contact, any entity except `ground_plane` | Ends episode, score 0 | Ground excluded by partner name; no force threshold | Mean of per-world success, collision, and timeout rates; score |
| Arena-Rosnav eval (`5480d52`) / Arena-Bench paper | none (eval) / GPL-2.0 (bench) | Any laser range ≤ robot radius; rising edges counted | ≥3 events → COLLISION label (code); paper: success = fewer than 2 | None; 2D scan-plane proxy | Collision count, success rate, clearing distance |
| MRPB 1.0 (`ae2d4aa`) | CC0-1.0 (README) | No collision test; costmap distance from robot centre | Not scored; failure = goal not reached | d_safe = 2× robot radius as a danger zone | Min distance d_o; % time within d_safe |
| habitat-lab (`0fb6f43`) + habitat-sim (`57ee494`) | MIT | Nav: navmesh step shortened (kinematic). Rearrange: PhysX contact normal force | Nav: counted only. Rearrange: optional force termination + penalty | Stairs explicitly not a collision (length test); force increments < 20 N ignored | `collisions.count` per episode; force accum/instant |
| VLN-CE (`729d141`) | MIT | Not measured | None; sliding on | n/a | SR, SPL, nDTW; no collision metric |
| iGibson (`3ad2aef`) + iGibson 0.5 paper | MIT | Any PyBullet contact, minus ignored links/bodies | Per-step −0.1; terminate if collision steps > 500 | Wheel links ignored; INS excludes floor forces | `collision_step`; INS = path + effort (mass, force) |
| OmniGibson (BEHAVIOR-1K `c26ec05`) | MIT | Any non-zero impulse, any physics substep | Per-step −0.1; fail if > 500 collision steps | `floors` category ignored | Reward/termination only |
| CARLA Leaderboard (`aec8131`) + scenario_runner (`94ff3b8`) | MIT | Collision sensor events, debounced | Not terminal; multiplicative penalty 0.50/0.60/0.65 | Ego < 0.1 m/s not at fault; sidewalk excluded | Driving score mean ± std; infractions per km |
| nuPlan (`e924167`) | Apache-2.0 | Ego box overlaps object box, once per object | Multiplier: static object 1st → 0.5, 2nd → 0; VRU/vehicle → 0 | At-fault classification; stopped ego not at fault | Per-class counts, delta-V energy |
| SocNavBench (`2724ea8`) | MIT | Obstacle: map distance < 0. People: disc overlap | Obstacle ends episode; people counted (1 s cooldown) | By class | Termination cause per episode |
| CrowdNav (`20d6780`) | MIT | Robot–human disc overlap during step | Ends episode | < 0.2 m = non-terminal "danger" | Success/collision/timeout partition; danger frequency |
| HuNavSim (`35c2d81`) | MIT | Robot–person distance − radii < 0.02 m | Counted, fault attributed | Static-obstacle metric is a stub | Counts |
| Safety Gym (`f31042f`) | MIT (archived) | MuJoCo contact of robot geom with named hazards | Cost per step (0/1 indicator) | Displacement > 1e-3 m, speed > 1e-4 m/s | Episode cost, cost rate |
| Isaac Lab (`93d7bef`) | BSD-3-Clause | Net normal contact force, max over 3-step history | Base > 1 N ends episode; thigh > 1 N penalty | Body selection only; net force over all partners | Training terms, not an eval metric |
| legged_gym (`8fa29ac`) | BSD-3 text | Contact force norm per body | Base > 1 N ends; shank/thigh > 0.1 N counted | Stairs in terrain mix; knee contact penalised, not terminal | Training terms |
| ABS (`9b95329`) | CC BY-NC 4.0 (README) | > 1 N on base/front legs, or foot horizontal > 2× vertical + 10 N | Collision ends episode | Filters contacts not near an obstacle | Reach/collision/timeout counts |
| NaVILA-Bench (`e9d2db1`) | MIT | Base contact > 1 N; tilt > 0.8 rad | Ends episode (success needs STOP) | Leg contacts ignored | SR, SPL, OSR; no collision count |
| ViNL (`6364290`) + paper | BSD-3 text | Foot stumble (horizontal > 5× vertical) or loaded foot > 5 cm high | Counted | Height test assumes flat floor | Foot collisions per metre, mean ± std |
| ROLL / Rudin 2022 / Barkour (papers) | arXiv | Base collisions per 0.1 s / collision count / obstacle touch | Count / penalty / −0.1 per failed obstacle | Rudin: non-foot contact allowed as a skill | Success, base collisions, score distribution |

---

## 1. BARN Challenge

- **Repo:** https://github.com/Daffan/the-barn-challenge. **License:** MIT. **Commit:** `bf5a226f6088ec96bf0d2dbee3253a8ea6119b83`.
- **Detection.** A C++ node subscribes to the Gazebo contacts topic
  ([collision_publisher.cpp L69](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/jackal_helper/src/collision_publisher.cpp#L69)).
  It publishes `/collision = true` for any contact where one entity is `jackal` and neither entity is `ground_plane`
  ([L21-L41](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/jackal_helper/src/collision_publisher.cpp#L21-L41)).
  There is no force, depth, speed, or duration threshold. An `airborne` flag (z > 0.3 m) is computed but never used
  ([L44-L50](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/jackal_helper/src/collision_publisher.cpp#L44-L50)).
- **Latching.** `get_hard_collision()` returns true if any message arrived since the last call, then clears
  ([gazebo_simulation.py L34-L45](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/gazebo_simulation.py#L34-L45)).
  The start pose must be collision-free before a trial begins
  ([run.py L82-L90](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/run.py#L82-L90)).
- **Consequence.** The loop polls at about 10 Hz of sim time. It stops on collision, within 1 m of the goal, or at
  100 s ([run.py L145-L153](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/run.py#L145-L153)).
  Status priority is collided, then timeout, then succeeded
  ([L161-L170](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/run.py#L161-L170)).
  Score = success × OT / clip(AT, 2·OT, 8·OT), where OT = path length / 2 m/s
  ([L184-L187](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/run.py#L184-L187)).
  Any collision therefore zeroes the trial.
- **Reporting.** `report_test.py` expects 10 trials in each of 50 worlds. It prints the mean over worlds of per-world
  means for time (successful trials only), score, success, collision, and timeout
  ([L42-L85](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/report_test.py#L42-L85)).
  No confidence interval is computed.
- **Scoring changed between years.** The 2022 report states the clip as 4·OT to 8·OT
  ([arXiv 2208.10473](https://arxiv.org/abs/2208.10473), Sec. II). The pinned code uses 2·OT as the lower bound, and the
  comment at `report_test.py` L64 still mentions 4·OT. Always cite the year or commit with a BARN score.
- **Physical finals (2022 report, Sec. III).** A trial counts as successful only if the robot reaches the goal without
  any collision. Teams were ranked by the number of successful trials, with average time as the tie-break
  (Table II: 8/9, 4/9, 2/9).
- **Terrain.** Flat ground only. The support surface is excluded by partner name, which would not cover stairs.

## 2. Arena-Rosnav evaluation and Arena-Bench

- **Repos:**
  - https://github.com/Arena-Rosnav/arena-evaluation: no LICENSE file (GitHub reports none, so all rights are
    reserved by default); commit `5480d52a9a366c351db74686dafe20bd96dd7976`.
  - https://github.com/ignc-research/arena-bench: GPL-2.0; commit `519640415718abc7603ff38bc80b2bd22c38b13c`. Its tree
    at this commit contains no metric script; evaluation lives in arena-evaluation.
  - Main repo https://github.com/Arena-Rosnav/arena-rosnav: MIT; commit `5de9d380`. Not used for metrics.
- **Detection.** A recorded sample is a collision if any laser range is at most `robot_radius`
  ([get_metrics.py L195-L220](https://github.com/Arena-Rosnav/arena-evaluation/blob/5480d52a9a366c351db74686dafe20bd96dd7976/get_metrics.py#L195-L220)).
  The radius comes from the robot's `model_params.yaml`
  ([L364-L378](https://github.com/Arena-Rosnav/arena-evaluation/blob/5480d52a9a366c351db74686dafe20bd96dd7976/get_metrics.py#L364-L378)).
  `collision_amount` counts rising edges, so one continuous contact counts once
  ([L222-L230](https://github.com/Arena-Rosnav/arena-evaluation/blob/5480d52a9a366c351db74686dafe20bd96dd7976/get_metrics.py#L222-L230)).
- **Consequence.** `MAX_COLLISIONS = 3` and `TIMEOUT_TRESHOLD = 180e9` ns
  ([L39-L41](https://github.com/Arena-Rosnav/arena-evaluation/blob/5480d52a9a366c351db74686dafe20bd96dd7976/get_metrics.py#L39-L41)).
  The episode label is TIMEOUT, then COLLISION if at least 3 events occurred, otherwise GOAL_REACHED
  ([L172-L179](https://github.com/Arena-Rosnav/arena-evaluation/blob/5480d52a9a366c351db74686dafe20bd96dd7976/get_metrics.py#L172-L179)).
  So up to 2 collisions still count as success.
  - Inference: the function does not check the goal distance itself. It relies on how the recorder ended the episode.
  - The README describes a configurable `collision_treshold`
    ([README L231-L235](https://github.com/Arena-Rosnav/arena-evaluation/blob/5480d52a9a366c351db74686dafe20bd96dd7976/README.md#L231-L235)),
    but the pinned code hard-codes it.
- **Arena-Bench paper** ([arXiv 2206.05728](https://arxiv.org/abs/2206.05728), Table I and Sec. IV.A):
  - Success rate means runs with fewer than 2 collisions.
  - A collision is counted when the laser reads less than the robot radius.
  - "Clearing distance" (avg/max/min) is reported as a safety metric.
  - The paper (fewer than 2) disagrees with the pinned code (fewer than 3). The threshold therefore depends on the version.
- **Limits (inference).** This is a 2D scan-plane proxy. Contact above or below the scan plane is not seen. For a
  non-circular footprint, the radius test is also not the same as contact.

## 3. MRPB 1.0 (mobile robot local-planning benchmark)

- **Repo:** https://github.com/NKU-MobFly-Robotics/local-planning-benchmark. **Commit:** `ae2d4aa451d8032edd24b0bcd079d613594e94e2`.
- **License:** the README states CC0-1.0
  ([README L97-L98](https://github.com/NKU-MobFly-Robotics/local-planning-benchmark/blob/ae2d4aa451d8032edd24b0bcd079d613594e94e2/README.md#L97-L98)).
  `metrics.cpp` itself carries a BSD-3-style header.
- **No collision test.** Safety is measured by clearance instead.
  - `obs_dist` is the distance from the robot pose (a point) to the nearest LETHAL cell of the local costmap. It uses an
    OpenCV distance transform plus bicubic interpolation
    ([obs_dist_calculator.cpp L36-L85](https://github.com/NKU-MobFly-Robotics/local-planning-benchmark/blob/ae2d4aa451d8032edd24b0bcd079d613594e94e2/move_base_benchmark/src/obs_dist_calculator.cpp#L36-L85)).
  - The value is logged every control cycle
    ([move_base_benchmark.cpp L1052-L1061](https://github.com/NKU-MobFly-Robotics/local-planning-benchmark/blob/ae2d4aa451d8032edd24b0bcd079d613594e94e2/move_base_benchmark/src/move_base_benchmark.cpp#L1052-L1061)).
- **Metrics** ([arXiv 2011.00491](https://arxiv.org/abs/2011.00491), eq. 1-2):
  - d_o is the minimum over the run of distance to the closest obstacle.
  - p_o is the percentage of time with d_i ≤ d_safe.
  - Code: `ComputeSafety`
    ([metrics.cpp L76-L102](https://github.com/NKU-MobFly-Robotics/local-planning-benchmark/blob/ae2d4aa451d8032edd24b0bcd079d613594e94e2/move_base_benchmark/doc/metrics.cpp#L76-L102)).
    d_safe is a command-line argument
    ([L140-L142](https://github.com/NKU-MobFly-Robotics/local-planning-benchmark/blob/ae2d4aa451d8032edd24b0bcd079d613594e94e2/move_base_benchmark/doc/metrics.cpp#L140-L142)).
  - Inference: a below-threshold stretch that lasts a single sample, or runs to the end of the log, adds zero time.
- **Paper settings.**
  - d_safe = 0.34 m, twice the 0.17 m robot radius.
  - Failure to reach the goal is shown as "-" (Sec. V).
  - "Partially unknown" scenarios blank a 13.0 × 7.7 m rectangle of the prior map to unknown, so planners must react to
    live laser data (Sec. III.C). This is the closest published analogue to our unmapped box.
- **Harmless contact.** Not addressed. The distance is measured from the robot centre, so the footprint enters only
  through the chosen d_safe.

## 4. Habitat (habitat-lab, habitat-sim, Habitat Challenge, VLN-CE)

- **Repos and commits (all MIT):**
  - habitat-lab: https://github.com/facebookresearch/habitat-lab @ `0fb6f43ffe806a8088a171b036336c093bcf604e`
  - habitat-sim: https://github.com/facebookresearch/habitat-sim @ `57ee4941dc4765240f0f91f70b2c97a919bf9038`
  - habitat-challenge: https://github.com/facebookresearch/habitat-challenge @ `ddf1575532aecc4df2f4cd4c5db173b8eada3e1e` (branch `challenge-2020`)
  - VLN-CE: https://github.com/jacobkrantz/VLN-CE @ `729d141b2ee10628061ada74dd3a5b9f70faeba5`
- **`collisions` measure.** It records `count` and per-step `is_collision` from `sim.previous_step_collided`
  ([nav.py L659-L675](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/nav/nav.py#L659-L675);
  [habitat_simulator.py L712-L724](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/sims/habitat_simulator/habitat_simulator.py#L712-L724)).
  - It is not in the default PointNav measurements
    ([pointnav.yaml L8-L12](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/config/habitat/task/pointnav.yaml#L8-L12)).
  - It is not in the VLN-CE task measurements either
    ([vlnce_task.yaml L30-L38](https://github.com/jacobkrantz/VLN-CE/blob/729d141b2ee10628061ada74dd3a5b9f70faeba5/habitat_extensions/config/vlnce_task.yaml#L30-L38)).
  - Collisions are therefore available for reporting but do not affect SR or SPL.
- **Detection is kinematic, with an explicit stairs rule.**
  - A step "collided" if the distance moved after the navmesh filter (plus 1e-5) is less than the distance moved
    before it ([object_controls.py L74-L89](https://github.com/facebookresearch/habitat-sim/blob/57ee4941dc4765240f0f91f70b2c97a919bf9038/src_python/habitat_sim/agent/controls/object_controls.py#L74-L89)).
  - The upstream comment says stairs move the filtered end point without a collision. That is why the code compares
    lengths rather than positions.
  - The velocity action uses the same rule
    ([nav.py L1294-L1312](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/nav/nav.py#L1294-L1312)).
  - No forces are involved.
- **Sliding policy.**
  - `allow_sliding` defaults to True
    ([default_structured_configs.py L1777](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/config/default_structured_configs.py#L1777)).
    VLN-CE keeps it on
    ([vlnce_task.yaml L11](https://github.com/jacobkrantz/VLN-CE/blob/729d141b2ee10628061ada74dd3a5b9f70faeba5/habitat_extensions/config/vlnce_task.yaml#L11)).
  - Habitat Challenge 2020 PointNav turned sliding off
    ([config L13](https://github.com/facebookresearch/habitat-challenge/blob/ddf1575532aecc4df2f4cd4c5db173b8eada3e1e/configs/challenge_pointnav2020.local.rgbd.yaml#L13)).
    Its README says agents exploited sliding to cut through non-navigable space, while real bump sensors force a stop
    ([README L53](https://github.com/facebookresearch/habitat-challenge/blob/ddf1575532aecc4df2f4cd4c5db173b8eada3e1e/README.md#L53)).
- **Rearrange (dynamic physics) uses force thresholds.**
  - `RobotCollisions` counts robot-object, robot-scene, and object-scene contacts separately
    ([rearrange_sensors.py L776-L811](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/rearrange_sensors.py#L776-L811)).
  - `get_coll_forces` takes the maximum |normal force| over contact points that involve the robot
    ([rearrange_task.py L346-L383](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/rearrange_task.py#L346-L383)).
    Whether this includes floor contact depends on the robot and scene (UNVERIFIED).
  - `RobotForce` adds to the accumulated force only when the per-step increase exceeds `min_force`, default 20 N
    ([rearrange_sensors.py L815-L878](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/rearrange_sensors.py#L815-L878);
    [default_structured_configs.py L848-L854](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/config/default_structured_configs.py#L848-L854)).
  - `ForceTerminate` ends the episode when accumulated or instantaneous force exceeds `max_accum_force` or
    `max_instant_force`. Both default to −1, which disables them
    ([rearrange_sensors.py L919-L976](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/rearrange_sensors.py#L919-L976);
    [configs L858-L869](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/config/default_structured_configs.py#L858-L869)).
  - The reward subtracts `force_pen` × added force, capped at `max_force_pen`. It subtracts `force_end_pen` on force
    termination and can add a count-based penalty
    ([L1040-L1095](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/rearrange_sensors.py#L1040-L1095)).
- **Agent–agent contact (social nav, cooperation).**
  - `DidAgentsCollide` is true if any physics contact point joins the two agents
    ([multi_agent_sensors.py L19-L56](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/multi_agent_sensors.py#L19-L56)).
  - The social-nav reward subtracts `collide_penalty`
    ([social_nav_sensors.py L171-L177](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/tasks/rearrange/social_nav/social_nav_sensors.py#L171-L177)).
  - Cooperative rearrange reward configs default to `end_on_collide: True`
    ([configs L1331-L1343](https://github.com/facebookresearch/habitat-lab/blob/0fb6f43ffe806a8088a171b036336c093bcf604e/habitat-lab/habitat/config/default_structured_configs.py#L1331-L1343)).

## 5. iGibson and the Interactive Gibson Benchmark

- **Repo:** https://github.com/StanfordVL/iGibson. **License:** MIT. **Commit:** `3ad2aefabcf1f370ef3dabf704d0ac3becce0df9`.
- **Detection.**
  - A collision is any PyBullet contact point on any robot body after the step. Contacts with ignored partner bodies,
    or on ignored robot links, are removed
    ([igibson_env.py L84-L87](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/envs/igibson_env.py#L84-L87),
    [L301-L331](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/envs/igibson_env.py#L301-L331)).
  - The TurtleBot configs ignore links 1-4, the wheels
    ([turtlebot_nav.yaml L52](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/configs/turtlebot_nav.yaml#L52)).
  - Support contact is therefore excluded **by robot link**, not by partner. There is no force threshold.
- **Consequence.**
  - `collision_step` counts steps with at least one contact
    ([igibson_env.py L356-L358](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/envs/igibson_env.py#L356-L358)).
  - `CollisionReward` gives −0.1 on any step with contact
    ([collision_reward.py L10-L24](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/reward_functions/collision_reward.py#L10-L24)).
  - `MaxCollision` fails the episode when `collision_step` > `max_collisions_allowed`, default 500
    ([max_collision.py L11-L26](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/termination_conditions/max_collision.py#L11-L26)).
  - Inference: with `max_step: 500` and `max_collisions_allowed: 500`
    ([turtlebot_nav.yaml L47-L48](https://github.com/StanfordVL/iGibson/blob/3ad2aefabcf1f370ef3dabf704d0ac3becce0df9/igibson/configs/turtlebot_nav.yaml#L47-L48)),
    collisions can never end a default episode. They act only through the reward.
- **Interactive Navigation Score** ([arXiv 1910.14442](https://arxiv.org/abs/1910.14442), Sec. IV):
  - INS_α = α·P_eff + (1−α)·E_eff.
  - P_eff = success × L*/l_0, equivalent to SPL.
  - E_eff averages two terms. One is the robot's mass-path product divided by the total mass-path product of all
    objects. The other is T·G / (T·G + ΣF_t), where G is the robot's weight and F_t is the force the robot applies to the
    environment **excluding forces applied to the floor for locomotion**.
  - Contact is therefore graded by displaced mass and applied force, not banned.
  - I did not find INS code in iGibson 2.x master (UNVERIFIED whether an older tag implements it).

## 6. OmniGibson (BEHAVIOR-1K)

- **Repo:** https://github.com/StanfordVL/BEHAVIOR-1K (OmniGibson subtree). **License:** MIT. **Commit:** `c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3`.
- **Detection.**
  - `MaxCollision` and `CollisionReward` both use `RigidContactAPI.is_in_contact`, ignoring objects of category
    `floors` (and the robot itself when self-collisions are ignored)
    ([max_collision.py L19-L44](https://github.com/StanfordVL/BEHAVIOR-1K/blob/c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3/OmniGibson/omnigibson/termination_conditions/max_collision.py#L19-L44);
    [collision_reward.py L18-L38](https://github.com/StanfordVL/BEHAVIOR-1K/blob/c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3/OmniGibson/omnigibson/reward_functions/collision_reward.py#L18-L38)).
  - Contact means any non-zero impulse between a pair
    ([usd_utils.py L553](https://github.com/StanfordVL/BEHAVIOR-1K/blob/c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3/OmniGibson/omnigibson/utils/usd_utils.py#L553)).
  - With `current_only=False`, a contact at any physics substep since the last environment step counts
    ([usd_utils.py L683-L700](https://github.com/StanfordVL/BEHAVIOR-1K/blob/c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3/OmniGibson/omnigibson/utils/usd_utils.py#L683-L700)).
- **Defaults.** `max_collisions` 500 and `r_collision` 0.1
  ([point_navigation_task.py L475](https://github.com/StanfordVL/BEHAVIOR-1K/blob/c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3/OmniGibson/omnigibson/tasks/point_navigation_task.py#L475),
  [L484](https://github.com/StanfordVL/BEHAVIOR-1K/blob/c26ec0574f82f38fe016d60fbcb9a72b68f0e3d3/OmniGibson/omnigibson/tasks/point_navigation_task.py#L484)).
- **Terrain.** Only the `floors` category is exempt. Inference: a staircase modelled as a separate object would count as
  a collision (UNVERIFIED in a scene).

## 7. CARLA Leaderboard (weighted infractions)

- **Repos (MIT):**
  - https://github.com/carla-simulator/leaderboard @ `aec81319de6bec57372f25aa94083c9ab0bd4223` (master)
  - https://github.com/carla-simulator/scenario_runner @ `94ff3b8af752bad2b9d464ad5105868906aa34c0` (master)
  - Also read: leaderboard `leaderboard-2.1` @ `cfecdc8d99f933a09b27176829ce7b8d63d66d8d` and scenario_runner
    `leaderboard-2.1` @ `d7bcaf0dee05fdfd720bda45740b8c9f11ee478a`.
- **Detection and debouncing** (`CollisionTest`,
  [atomic_criteria.py L280-L413](https://github.com/carla-simulator/scenario_runner/blob/94ff3b8af752bad2b9d464ad5105868906aa34c0/srunner/scenariomanager/scenarioatomics/atomic_criteria.py#L280-L413)):
  - A CARLA collision sensor is attached to the ego vehicle.
  - Events are merged: a repeat hit on the same actor within `MAX_ID_TIME` 5 s, or any hit within `COLLISION_RADIUS`
    5 m of the last one, is not counted again.
  - If ego speed is below `EPSILON` 0.1 m/s, the collision is not counted, because it is not the ego's fault
    ([L294-L296](https://github.com/carla-simulator/scenario_runner/blob/94ff3b8af752bad2b9d464ad5105868906aa34c0/srunner/scenariomanager/scenarioatomics/atomic_criteria.py#L294-L296),
    [L373-L383](https://github.com/carla-simulator/scenario_runner/blob/94ff3b8af752bad2b9d464ad5105868906aa34c0/srunner/scenariomanager/scenarioatomics/atomic_criteria.py#L373-L383)).
  - Class: static (type contains `static` or `traffic`, **but not `sidewalk`**), vehicle, or walker. Other contacts are
    dropped ([L394-L401](https://github.com/carla-simulator/scenario_runner/blob/94ff3b8af752bad2b9d464ad5105868906aa34c0/srunner/scenariomanager/scenarioatomics/atomic_criteria.py#L394-L401)).
  - The same constants appear on the `leaderboard-2.1` branch (L295-L297, L396).
- **Consequence.**
  - The route test adds `CollisionTest` without `terminate_on_failure`, so the route continues after a collision
    ([route_scenario.py L426-L436](https://github.com/carla-simulator/leaderboard/blob/aec81319de6bec57372f25aa94083c9ab0bd4223/leaderboard/scenarios/route_scenario.py#L426-L436)).
  - Only route deviation and "agent blocked" terminate.
- **Score (master).**
  - Driving score = route completion × infraction penalty.
  - The penalty multiplies one coefficient per event: pedestrian 0.50, vehicle 0.60, static 0.65, red light 0.70,
    stop sign 0.80
    ([statistics_manager.py L21-L51](https://github.com/carla-simulator/leaderboard/blob/aec81319de6bec57372f25aa94083c9ab0bd4223/leaderboard/utils/statistics_manager.py#L21-L51),
    [L361-L395](https://github.com/carla-simulator/leaderboard/blob/aec81319de6bec57372f25aa94083c9ab0bd4223/leaderboard/utils/statistics_manager.py#L361-L395)).
  - These values match the official page https://leaderboard.carla.org/evaluation_v2_0/, which describes the penalty as
    a geometric series.
- **Score (`leaderboard-2.1` branch) differs.**
  - Weights are summed (pedestrian 1.0, vehicle 0.7, static 0.6) and penalty = 1/(1 + Σw)
    ([statistics_manager.py L21-L31](https://github.com/carla-simulator/leaderboard/blob/cfecdc8d99f933a09b27176829ce7b8d63d66d8d/leaderboard/utils/statistics_manager.py#L21-L31),
    [L358-L390](https://github.com/carla-simulator/leaderboard/blob/cfecdc8d99f933a09b27176829ce7b8d63d66d8d/leaderboard/utils/statistics_manager.py#L358-L390)).
  - Which formula the live leaderboard applies is UNVERIFIED.
- **Reporting.**
  - Mean and sample standard deviation over routes
    ([master L453-L469](https://github.com/carla-simulator/leaderboard/blob/aec81319de6bec57372f25aa94083c9ab0bd4223/leaderboard/utils/statistics_manager.py#L453-L469)).
  - Infractions are reported **per km driven**, where km is weighted by route completion
    ([L471-L483](https://github.com/carla-simulator/leaderboard/blob/aec81319de6bec57372f25aa94083c9ab0bd4223/leaderboard/utils/statistics_manager.py#L471-L483)).
  - No confidence interval.

## 8. nuPlan (at-fault collision multiplier)

- **Repo:** https://github.com/motional/nuplan-devkit. **License:** Apache-2.0 per LICENSE.txt (GitHub: NOASSERTION). **Commit:** `e9241677997dd86bfc0bcd44817ab04fe631405b`.
- **Detection.** The ego footprint's oriented box must overlap a tracked object's box. Each object can be collided with
  only once per scenario
  ([no_ego_at_fault_collisions.py L87-L117](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/metrics/evaluation_metrics/common/no_ego_at_fault_collisions.py#L87-L117)).
- **Classification.**
  - Ego speed ≤ 0.05 m/s gives STOPPED_EGO. A stopped track gives STOPPED_TRACK. Otherwise the collision is classed as
    front, rear, or lateral
    ([L47-L84](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/metrics/evaluation_metrics/common/no_ego_at_fault_collisions.py#L47-L84)).
  - At fault means an active front collision, a collision with a stopped track, or a lateral collision while ego spans
    several lanes or non-drivable area
    ([L120-L160](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/metrics/evaluation_metrics/common/no_ego_at_fault_collisions.py#L120-L160)).
  - Severity is recorded as the ego delta-V with a mass ratio
    ([collision_utils.py L35-L62](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/metrics/utils/collision_utils.py#L35-L62)).
- **Score.**
  - Per-class score = max(0, 1 − n/(thr+1)), with thresholds VRU 0, vehicle 0, static object 1
    ([L204-L233](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/metrics/evaluation_metrics/common/no_ego_at_fault_collisions.py#L204-L233);
    [statistics yaml](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/script/config/common/simulation_metric/high_level/no_ego_at_fault_collisions_statistics.yaml)).
  - The first at-fault hit on a static object gives 0.5, and a second gives 0. Any at-fault VRU or vehicle hit gives 0.
  - This score is a **multiplier** on the weighted scenario score, next to drivable-area and progress multipliers
    ([aggregator yaml L14-L18](https://github.com/motional/nuplan-devkit/blob/e9241677997dd86bfc0bcd44817ab04fe631405b/nuplan/planning/script/config/simulation/metric_aggregator/closed_loop_reactive_agents_weighted_average.yaml#L14-L18)).
  - A time-to-collision bound carries weight 5 in the average (L8), so the score also contains a proactive margin term.

## 9. Social-navigation benchmarks

### SocNavBench
- **Repo:** https://github.com/CMU-TBD/SocNavBench. **License:** MIT. **Commit:** `2724ea85ff22ca61a88ee95285dfc3fa056656c6`.
- **Pedestrian collision.**
  - Triggered when centre distance < sum of radii
    ([agent_base.py L134-L157](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/agents/agent_base.py#L134-L157)).
    Robot radius is 0.24 m and agent radius 0.2 m
    ([user_params.ini L19](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/params/user_params.ini#L19),
    [L33](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/params/user_params.ini#L33)).
  - A 1 s cooldown prevents double counting
    ([L22](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/params/user_params.ini#L22);
    [agent_base.py L166-L168](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/agents/agent_base.py#L166-L168)).
- **Obstacle collision.**
  - Triggered at the first trajectory index where the FMM distance to the nearest occupied cell is negative. The episode
    ends and the trajectory is clipped there
    ([agent_base.py L272-L291](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/agents/agent_base.py#L272-L291);
    [central_params.py L464-L469](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/params/central_params.py#L464-L469)).
  - `keep_episode_running=True` continues after a pedestrian collision but not after an obstacle collision
    ([user_params.ini L11](https://github.com/CMU-TBD/SocNavBench/blob/2724ea85ff22ca61a88ee95285dfc3fa056656c6/params/user_params.ini#L11)).
  - Whether the occupancy map is inflated by the robot radius: UNVERIFIED.

### CrowdNav
- **Repo:** https://github.com/vita-epfl/CrowdNav. **License:** MIT. **Commit:** `20d678085c06831e658a65b9e20c8bb6f6ecdc10`.
- **Collision.** Triggered when the robot-to-human segment distance minus both radii is below 0 during the step. The
  episode ends with reward −0.25
  ([crowd_sim.py L330-L351](https://github.com/vita-epfl/CrowdNav/blob/20d678085c06831e658a65b9e20c8bb6f6ecdc10/crowd_sim/envs/crowd_sim.py#L330-L351),
  [L366-L389](https://github.com/vita-epfl/CrowdNav/blob/20d678085c06831e658a65b9e20c8bb6f6ecdc10/crowd_sim/envs/crowd_sim.py#L366-L389);
  [env.config L10-L13](https://github.com/vita-epfl/CrowdNav/blob/20d678085c06831e658a65b9e20c8bb6f6ecdc10/crowd_nav/configs/env.config#L10-L13)).
- **Near-miss.** Minimum distance below 0.2 m is a non-terminal "Danger" with a graded penalty.
- **Reporting.**
  - Episodes are partitioned so that success + collision + timeout equals the episode count, and the code asserts this.
  - It reports success rate, collision rate, navigation time, danger frequency (danger steps / all steps), and the
    average minimum distance during danger
    ([explorer.py L75-L89](https://github.com/vita-epfl/CrowdNav/blob/20d678085c06831e658a65b9e20c8bb6f6ecdc10/crowd_nav/utils/explorer.py#L75-L89)).

### HuNavSim
- **Repo:** https://github.com/robotics-upo/hunav_sim (default branch `v2.0`). **License:** MIT. **Commit:** `35c2d81fc0e8166a3d124558fd718dd03e8a914c`.
- **Robot–person collision.** Triggered when centre distance minus radii < 0.02 m. The collision is attributed to the
  robot or the person from relative bearing and speed
  ([hunav_metrics.py L454-L541](https://github.com/robotics-upo/hunav_sim/blob/35c2d81fc0e8166a3d124558fd718dd03e8a914c/hunav_evaluator/hunav_evaluator/hunav_metrics.py#L454-L541)).
- **Static obstacles.** `static_obs_collision` is an empty stub
  ([L1304-L1305](https://github.com/robotics-upo/hunav_sim/blob/35c2d81fc0e8166a3d124558fd718dd03e8a914c/hunav_evaluator/hunav_evaluator/hunav_metrics.py#L1304-L1305)).

## 10. Safety Gym (contact versus consequence)

- **Repo:** https://github.com/openai/safety-gym (archived). **License:** MIT. **Commit:** `f31042f2f9ee61b9034dd6a416955972911544f5`.
- **Cost terms.** Contact between any robot geom and a vase costs `vases_contact_cost` (1.0) per step. Optional
  displacement and velocity costs apply only above `vases_displace_threshold` 1e-3 m and `vases_velocity_threshold`
  1e-4 m/s
  ([engine.py L234-L264](https://github.com/openai/safety-gym/blob/f31042f2f9ee61b9034dd6a416955972911544f5/safety_gym/envs/engine.py#L234-L264),
  [L1126-L1174](https://github.com/openai/safety-gym/blob/f31042f2f9ee61b9034dd6a416955972911544f5/safety_gym/envs/engine.py#L1126-L1174)).
  `constrain_indicator` (default True) turns each step's cost into 0 or 1
  ([L1188-L1190](https://github.com/openai/safety-gym/blob/f31042f2f9ee61b9034dd6a416955972911544f5/safety_gym/envs/engine.py#L1188-L1190)).
- **Levels.** In Goal1 the vases are present but unconstrained. Goal2 constrains 10 vases
  ([suite.py L132-L147](https://github.com/openai/safety-gym/blob/f31042f2f9ee61b9034dd6a416955972911544f5/safety_gym/envs/suite.py#L132-L147)).
- **Benchmark metrics.** Normalized return, normalized constraint violation (episode cost), and cost rate over training
  ([README L127-L131](https://github.com/openai/safety-gym/blob/f31042f2f9ee61b9034dd6a416955972911544f5/README.md#L127-L131)).
- **Legged relevance (inference).** The quadruped `Doggo` robot is included. Any leg geom touching a vase counts, while
  floor contact never counts, because only named hazard classes are checked.

## 11. Legged-robot references (Isaac Lab, legged_gym, ABS, NaVILA-Bench, ViNL, ViPlanner, papers)

### Isaac Lab (the simulator we use)
- **Repo:** https://github.com/isaac-sim/IsaacLab. **License:** BSD-3-Clause. **Commit:** `93d7bef70bb2c24720a01342ab6ca58bdd906f8c` (`develop`).
- **`illegal_contact`.** Terminates when the maximum over sensor history of the net normal contact force on the
  selected bodies exceeds a threshold
  ([terminations.py L183-L191](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab/isaaclab/envs/mdp/terminations.py#L183-L191)).
  `undesired_contacts` counts the selected bodies above a threshold
  ([rewards.py L273-L283](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab/isaaclab/envs/mdp/rewards.py#L273-L283)).
- **Locomotion velocity env.**
  - The base contact threshold is 1.0 N and triggers termination
    ([velocity_env_cfg.py L321-L324](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab_tasks/isaaclab_tasks/core/velocity/velocity_env_cfg.py#L321-L324)).
  - Thigh contact above 1.0 N is penalised with weight −1
    ([L306-L310](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab_tasks/isaaclab_tasks/core/velocity/velocity_env_cfg.py#L306-L310)).
  - The contact sensor keeps `history_length=3`
    ([L120](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab_tasks/isaaclab_tasks/core/velocity/velocity_env_cfg.py#L120)).
- **ANYmal-C navigation env.** Base contact above 1.0 N terminates, with a −400 termination penalty
  ([navigation_env_cfg.py L79](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab_tasks/isaaclab_tasks/contrib/navigation/config/anymal_c/navigation_env_cfg.py#L79),
  [L112-L119](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab_tasks/isaaclab_tasks/contrib/navigation/config/anymal_c/navigation_env_cfg.py#L112-L119)).
- **Partner separation.** The net force sums every partner: ground, stair, and box alike. Per-partner forces require
  `filter_prim_paths_expr`
  ([contact_sensor_cfg.py L24-L25, L78](https://github.com/isaac-sim/IsaacLab/blob/93d7bef70bb2c24720a01342ab6ca58bdd906f8c/source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_cfg.py#L78)).
- The develop layout differs from the Isaac Lab release on the rented 4090. Which fields map onto our installed version
  is UNVERIFIED.

### legged_gym
- **Repo:** https://github.com/leggedrobotics/legged_gym. **License:** BSD-3-Clause text (GitHub: NOASSERTION). **Commit:** `8fa29acc6fd1910c3d9659eef6310bdd301cde0a`.
- **Termination.** Any termination body with contact force norm above 1 N ends the episode
  ([legged_robot.py L138-L141](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot.py#L138-L141)).
- **Collision penalty.** Counts penalised bodies above 0.1 N
  ([L849-L851](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot.py#L849-L851)).
- **ANYmal-C rough config.** Penalises SHANK and THIGH contact and terminates on base contact
  ([anymal_c_rough_config.py L75-L76](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/anymal_c/mixed_terrains/anymal_c_rough_config.py#L75-L76)).
- **Stairs.** The terrain mix includes stairs up and down
  ([legged_robot_config.py L63-L64](https://github.com/leggedrobotics/legged_gym/blob/8fa29acc6fd1910c3d9659eef6310bdd301cde0a/legged_gym/envs/base/legged_robot_config.py#L63-L64)).
  On stairs, knee and shank contact is penalised but not terminal. Base contact is terminal.

### ABS (Agile But Safe)
- **Repo:** https://github.com/LeCAR-Lab/ABS. **Commit:** `9b95329ffb823c15dead02be620ff96938e4d0a3`.
- **License:** the README states CC BY-NC 4.0. There is no root LICENSE file. The `training/legged_gym` subtree carries
  BSD-3 text.
- **Evaluation testbed: what counts as a collision.**
  - Contact force above 1 N on the base, front thighs, or front calves
    ([testbed.py L172](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L172),
    [L362](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L362)).
  - Or, on a front foot, horizontal force above twice the vertical force plus 10 N
    ([L363-L366](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L363-L366)).
  - Either case is kept only if the robot is within 0.95 m of an obstacle and moving above 0.5 m/s, or if the base
    contact exceeds 1 N
    ([L367-L371](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L367-L371)).
  - The upstream comment says this filter removes simulator collisions that cannot be explained.
- **Outcomes.**
  - Each episode is classed as reach (< 0.65 m), collision, or timeout
    ([L374-L377](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L374-L377)).
  - Collisions are also split by whether the recovery policy was active
    ([L383-L406](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/scripts/testbed.py#L383-L406)).
- **Training cost.** The per-step cost is 1 if any of collision, termination, or foot collision occurs
  ([legged_robot_pos.py L210-L215](https://github.com/LeCAR-Lab/ABS/blob/9b95329ffb823c15dead02be620ff96938e4d0a3/training/legged_gym/legged_gym/envs/base/legged_robot_pos.py#L210-L215)).

### NaVILA-Bench (legged VLN in Isaac Lab)
- **Repo:** https://github.com/yang-zj1026/NaVILA-Bench. **License:** MIT (LICENSE text; GitHub: NOASSERTION). **Commit:** `e9d2db12ce5788c0f987d734c0094100b6bc0d3a`.
- **Termination.** Go2 in Matterport scenes ends on base contact above 1 N or tilt above 0.8 rad
  ([go2_matterport_base_cfg.py L230-L245](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/isaaclab_exts/omni.isaac.vlnce/omni/isaac/vlnce/config/go2/go2_matterport_base_cfg.py#L230-L245)).
- **Success.** STOP must be called within the goal radius
  ([measures.py L239-L271](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/isaaclab_exts/omni.isaac.vlnce/omni/isaac/vlnce/utils/measures.py#L239-L271)).
  Inference: a base-contact termination therefore always scores 0.
- **Not measured.** There is no collision count. Leg contact with walls or stairs is neither counted nor terminal.

### ViNL (legged navigation over clutter)
- **Repo:** https://github.com/SimarKareer/ViNL. **License:** BSD-3 text inherited from legged_gym (GitHub: NOASSERTION). **Commit:** `636429092eef1831e6c4611b42060d96046c11b7`.
- **Metric** ([arXiv 2210.14791](https://arxiv.org/abs/2210.14791), Sec. IV).
  - Foot collisions per metre, computed only over episodes with at least 1 m travelled.
  - Contacts are counted per 50 Hz control step, so 1 s of contact counts as 50 collisions (the authors say so).
  - Results are reported as mean ± std.
- **What counts as a foot collision (code).** A step counts if either condition holds:
  - Foot stumble: horizontal foot force above 5× the vertical force.
  - A loaded foot more than 5 cm above z = 0, meaning it stands on an obstacle.
  - Code: [legged_robot.py L1446-L1488](https://github.com/SimarKareer/ViNL/blob/636429092eef1831e6c4611b42060d96046c11b7/legged_gym/envs/base/legged_robot.py#L1446-L1488);
    [legged_robot_nav.py L236-L240](https://github.com/SimarKareer/ViNL/blob/636429092eef1831e6c4611b42060d96046c11b7/legged_gym/envs/base/legged_robot_nav.py#L236-L240),
    [L409-L417](https://github.com/SimarKareer/ViNL/blob/636429092eef1831e6c4611b42060d96046c11b7/legged_gym/envs/base/legged_robot_nav.py#L409-L417).
  - The per-metre value is computed at reset
    ([L130-L137](https://github.com/SimarKareer/ViNL/blob/636429092eef1831e6c4611b42060d96046c11b7/legged_gym/envs/base/legged_robot_nav.py#L130-L137)).
- **Limits (inference).** The height test assumes a flat floor, so every stair tread would count. Only env 0 is checked
  (`rew[0]`).

### ViPlanner (map-overlap proxy)
- **Repo:** https://github.com/leggedrobotics/viplanner. **License:** BSD-3-Clause (LICENSE text). **Commit:** `6fcf3c60f6fa3b28b3a11af054d6033825923789`.
- **Metrics.** Evaluation reports goal-reached rate and an obstacle "loss" of the executed path on a cost map. It also
  reports the fraction of paths below `obs_loss_threshold`
  ([eval_utils.py L102-L141](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/viplanner/utils/eval_utils.py#L102-L141)).
- There is no contact test. The threshold value is UNVERIFIED.

### Papers without verified code
- **ROLL, resilient legged local navigation** ([arXiv 2310.03581](https://arxiv.org/abs/2310.03581), Sec. V).
  - Success means reaching the target within the 18 s episode.
  - "Average base collisions" counts base collisions in 0.1 s bins and sums them over time.
  - Base and thigh collisions are penalised but do not end the episode. The policy learns to sidestep after contact.
  - Code UNVERIFIED.
- **Rudin et al. 2022** ([arXiv 2209.12827](https://arxiv.org/abs/2209.12827)).
  - The penalties include c3·N_c, the number of collisions (eq. 2).
  - Success means finishing within 0.5 m of the target with no crash (Sec. IV).
  - The introduction motivates using contacts on other body parts when needed.
  - The crash definition and the bodies counted in N_c are UNVERIFIED.
- **Barkour** ([arXiv 2305.14654](https://arxiv.org/abs/2305.14654), eq. 1).
  - R = 1 − 0.01·max(t_run − t_allotted, 0) − penalties, with 0.1 per failed or skipped obstacle.
  - Touching the jump board lowers the score. The run ends when the score reaches 0.
  - Score distributions over about 70 trials are shown.
  - No public code located (UNVERIFIED).

---

## 12. Cross-cutting findings relevant to Lite3 acceptance criteria

These are lead proposals for review, not decisions.

1. **Every physics-based benchmark removes support contact before it calls anything a collision, but each uses a
   different key.**
   - By partner: BARN excludes `ground_plane`; OmniGibson excludes `floors`.
   - By robot link: iGibson ignores wheel links; legged_gym, Isaac Lab, and ABS select base and thigh bodies.
   - By force direction: ABS and ViNL compare foot horizontal to vertical force.
   - A partner-only rule fails on stairs, because a stair is not "floor". ViNL's height rule also fails on stairs.
     Habitat is the only code with an explicit stairs exception, and it is kinematic.
   - For Lite3, classify contacts by (robot link, partner):
     - foot × terrain = support;
     - foot × box = stumble or strike;
     - non-foot × terrain = terrain contact;
     - any link × box = obstacle contact;
     - base × anything = severe.
   - Isaac Lab needs `filter_prim_paths_expr` to separate box forces from ground forces.
2. **No surveyed code uses a 0 N criterion.**
   - Legged code uses about 1 N on net force (base termination, thigh penalty) or 0.1 N (legged_gym shank and thigh
     penalty).
   - Habitat rearrange ignores force increments below 20 N.
   - Safety Gym uses tiny displacement and speed floors.
   - OmniGibson and Isaac Lab take the maximum over physics substeps or history.
   - A noise floor plus the maximum over substeps is the norm. The current 0 N check is stricter than any benchmark.
3. **Consequences split by purpose.**
   - Benchmarks that test avoiding static obstacles make contact a failure: BARN, CrowdNav, SocNavBench (obstacles),
     NaVILA-Bench (base), and ABS. Arena allows up to 2 events (code) or 1 (paper).
   - Driving and legged benchmarks grade instead:
     - multiplicative penalties: CARLA static 0.65; nuPlan first static object 0.5;
     - fixed deductions: Barkour 0.1;
     - rates: CARLA per km, ViNL per metre, ROLL per 0.1 s;
     - effort terms: INS.
   - This supports a two-tier rule. Box contact would be a failure, since it is the capability under test. Non-foot
     contact on stairs would be a reported rate with a severity cap. Base contact and falls would be failures.
4. **The event definition changes counts by orders of magnitude.**
   - Debounced events: CARLA (5 s / 5 m), SocNavBench (1 s cooldown), Arena (rising edge), nuPlan (once per object).
   - Per-step counting: ViNL (50 per second of contact), iGibson and OmniGibson (collision steps).
   - At-fault rules: CARLA ignores collisions with ego below 0.1 m/s; nuPlan's stopped ego is not at fault.
   - A reviewable Lite3 record would list each contact interval per (link, partner) with start time, duration, peak
     force, and impulse. Both counts can then be derived.
5. **Reporting.**
   - Report success, collision, and timeout as a partition summing to N (CrowdNav asserts it; BARN and ABS do the same).
   - Keep collision-free success separate from reached-goal.
   - Add near-miss clearance metrics: MRPB min distance and % time within 2× radius; CARLA infraction rate per km.
   - CARLA reports sample std and ViNL mean ± std. **No surveyed code computes confidence intervals.** With 5 to 10
     episodes per condition, we would have to add them ourselves (e.g., a Wilson interval on success).

## 13. UNVERIFIED items (collected)

- Whether habitat rearrange `get_coll_forces` includes floor contact for a given robot.
- iGibson INS implementation in any released code.
- OmniGibson stairs-object category behaviour.
- Which CARLA formula (geometric product vs 1/(1+Σw)) the live 2.1 leaderboard applies.
- SocNavBench map inflation by robot radius.
- The Isaac Lab release mapping to our installed version.
- ViPlanner threshold value.
- ROLL, Rudin 2022, and Barkour code.
- Arena episode-end handling (whether GOAL_REACHED is checked elsewhere).
