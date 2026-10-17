---
origin: ai+web
reviewed: false
date: 2026-09-17
stage: planning
status: surveyed
task: none yet (proposed next foundation step: placed-obstacle Isaac episode, SCAN-fix PRD D6)
---

# Collision handling for the Lite3 navigation base: open-source comparison

**Why this survey exists.** The next foundation step puts a box that is absent from the known map on the route, so
SCAN has to see it in the live LiDAR cloud and avoid it. The lead proposed "zero robot-box contact, feet included,
plus a minimum body clearance". Dr Sun (2026-09-17) pointed out that perfect collision avoidance is very hard, that
some contact is unavoidable (for example when climbing stairs), and asked how open-source repositories handle this
before any criterion is set.

**Dr Sun's description of the stack (2026-09-17).** PCT plans on the known terrain point cloud, localised by SLAM
relocalization; SCAN needs real-time point clouds to detect and avoid obstacles that are not in the known map. In the
Isaac runs, simulator truth pose stands in for SLAM relocalization, and SCAN's cloud comes from the runner's
simulated LiDAR (`/quad_0/cloud`).

**Status of everything below: `surveyed`.** Nothing was cloned, installed, run, imported or changed.

## Method and verification

Three read-only surveyors worked in parallel, one per family. They read source at pinned commits through `gh api`
and our vendored copies locally. Their notes, with permalinks and UNVERIFIED markers, are in
[the sources folder](2026-09-17_collision_handling_sources/) (AI-written; SHA-256 in `SHA256SUMS.txt`):

- [A: legged simulation training and evaluation code](2026-09-17_collision_handling_sources/A_legged_sim_notes.md)
- [B: planners, and how they separate steps from obstacles](2026-09-17_collision_handling_sources/B_planner_terrain_notes.md)
- [C: benchmark collision metrics and scoring](2026-09-17_collision_handling_sources/C_benchmark_metrics_notes.md)

**What the lead re-checked on 2026-09-17** (the rest is the surveyors' reading):
- **Our SCAN values** in `p2b_execution/baseline_config/planner.yaml`: resolution 0.05, `double_cylinder_radius`
  0.25, `double_cylinder_offset` 0.18, `body_height` 0.0, z inflation 0.1 / 0.1, `p_hit` 0.85, `p_occ` 0.8,
  `max_ray_length` 5.0, `dist0` 0.2, `lambda_collision` 1.0, `emergency_time` 1.0, `fail_safe` true.
- **SCAN's footprint code** (vendored `plan_env`): two discs at +/- offset along the heading; inflation keeps
  offsets with norm strictly below the radius, so on the 0.05 m grid the reach is 0.20 m on the axes and at most
  about 0.224 m.
- **Isaac Lab v2.3.2 contact filtering** (`contact_sensor.py` L50-59, `contact_sensor_cfg.py` L66-70): filtered
  forces are one-to-many only, one sensor body per environment against many partners.
- **BARN** (`collision_publisher.cpp` L21-41 at `bf5a226`): any Gazebo contact of the robot with anything except
  `ground_plane` is a collision.
- **CARLA Leaderboard** (`statistics_manager.py` L21-51 at `aec8131`): static-object collision multiplies the score by
  0.65, vehicle 0.60, pedestrian 0.50.
- **Our own rule** (vendored `contact_guard.py` L253 and the base runner): one contact sensor over every Lite3 link.
  Foot contact is excluded. Any other link at 5 N or more, at any 5 ms physics substep, fails the two-goal review.
  The pilot records without stopping (`--contact-policy native_v12`). V12 keeps its own TORSO termination at 1 N.
  The 0 N in P2B is the measured maximum, not the rule. The sensor reads net force, so it cannot tell what a link
  touched.

## What others do

**No surveyed codebase fails an episode on any leg contact.** The recurring pattern:

| Group | Examples (pins in the notes) | Rule |
|---|---|---|
| Legged training and legged navigation benchmarks | Isaac Lab v2.3.2, legged_gym, NaVILA-Bench, legged-loco, robot_lab (Lite3) | Base/torso contact above about 1 N ends the episode. Thigh or shank contact is at most a penalty. Feet are always allowed. Stairs are in the terrain mix and shank-on-stair contact is not separated. |
| Parkour | extreme-parkour, robot-parkour-learning | No contact termination at all; tipping and height limits end the episode; body contact, stumbles and edge steps are penalised. |
| Obstacle-avoidance benchmarks | BARN, CrowdNav, SocNavBench, ABS, NaVILA | Contact with an obstacle is a failure, after removing support contact (by partner name, link set or force direction). |
| Driving and graded benchmarks | CARLA Leaderboard, nuPlan, Barkour | Collision is graded: a score multiplier or penalty, merged over a time or distance window, and not counted when the vehicle is stopped. |
| Navigation benchmarks without contact metrics | Habitat VLN-CE, VLN-PE, NavDP | Success, falls, stuck. VLN-PE removes stair episodes. |
| Near-miss measures | MRPB, ArtPlanner | Minimum clearance and time inside a danger zone (MRPB, 2x robot radius); ArtPlanner reports planned-pose intersections ("any" and "severe") separately from real collisions. |

**Attribution to an obstacle.** Only ABS ties a contact to the obstacle, by proximity (within 0.95 m) and a
sideways-force test on the front feet. Isaac Lab can instead filter by partner: a contact sensor on the box,
filtered against the robot links, gives box-vs-link force and excludes floor contact by construction.

**Counting.** CARLA merges repeats within 5 s / 5 m, SocNavBench uses a 1 s cooldown, Arena counts each new contact
once, and ViNL counts every control step. Recording contact intervals (link, partner, start, duration, peak force)
lets any of these be derived later.

## What our stack implies (surveyor B, lead-checked values above)

- **The simulated LiDAR cannot see a new box yet.** It ray-casts only the merged building mesh (base runner
  `run_pct_scan_building.py` L421-431). The box must be added as a LiDAR target, and its hits confirmed, before SCAN
  is judged.
- **Box height decides what is tested.** SCAN's vertical window is about 0.25-0.50 m above the route's ground. A box
  well above 0.30 m is an obstacle SCAN should avoid; a box under about 0.25 m is left to V12 to step over.
- **The hard side margin is about 2 cm.** SCAN's footprint reaches about 0.20 m from the body centreline; Lite3's
  thighs reach about 0.18 m (09-14 survey, URDF). `dist0` 0.2 m is a soft optimizer term only. Grazing contact is a
  plausible outcome, so clearance must be measured.
- **Stairs are a separate design problem.** PCT allows 0.30 m steps in our profile, SCAN's window implies about 0.25 m,
  SCAN has no ground removal and our bridge terrain filter is off, so treads and nosings enter SCAN's map. The
  PCT-SCAN-ROS2 demo disables local sensing for stairs, and its validation is an RViz animation without physics.
  The building is one merged mesh, so stair contact cannot be separated from floor contact by partner.

## Proposal (lead, for Dr Sun's decision)

**Classify every contact by (robot link class, partner)**, sampled at every physics substep:

| Class | Link | Partner | Box test (flat) | Stairs (later) |
|---|---|---|---|---|
| Support | foot | terrain | allowed | allowed |
| Obstacle contact | any link, feet included | box | collision outcome | n/a |
| Leg-terrain contact | hip, thigh, shank | terrain | existing 5 N check, unchanged | reported rate and severity |
| Body contact | torso | anything | failure (existing V12 1 N termination) | failure |
| Fall / stuck | - | - | failure | failure |

**For the unmapped-box test:**
1. **Box contact is a collision outcome, not a demand for perfection.** Each episode ends in exactly one outcome:
   success, collision, fall, stuck or timeout, summing to N. The series reports the collision-free success count with
   its one-sided Clopper-Pearson bound, as before. Report collision severity (link, peak force, duration).
2. **Noise floor 1 N** for box contact, the legged-code convention (threshold is Dr Sun's to set before any run).
3. **Attribution by partner:** a contact sensor on the box filtered against the robot links (the supported one-to-many
   direction). Fallback: one sensor per robot link. A runtime check that a static or kinematic box reports contact
   comes first.
4. **Near-miss, report only:** minimum distance between the robot's collision geometry and the box, and time within
   0.2 m (MRPB / ArtPlanner style). Not a pass/fail limit in the first series.
5. **Record intervals**, not only maxima, so any counting rule can be applied later.
6. **One tall box** (top above 0.5 m, inside SCAN's window at every range). A low step-over box belongs with stairs.
7. **The 41 existing checks stay unchanged.**

**For stairs (later task):** leg-terrain contact becomes a reported rate (per metre and per episode) with peak force.
The first stairs series is characterisation only; any severity cap is frozen from it before the next series, never
after the series it judges. Body contact and falls stay failures. The PCT/SCAN step mismatch and SCAN's stair
handling need their own design first.

## Claim boundary

- `surveyed` only. No mechanism here has been run by us. The one-to-many filtering direction is documented; whether a
  static or kinematic box reports contact in our Isaac Lab build is unverified.
- Paper-level numbers in the notes (SCAN collision rate, ArtPlanner intersections) come from WebFetch summaries of
  arXiv HTML and still need checking against the PDFs.
- Commit pins are branch heads on 2026-09-17 and will move; the pins are the reference.
