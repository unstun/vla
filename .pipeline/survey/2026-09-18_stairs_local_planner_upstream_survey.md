---
origin: ai+web
reviewed: false
date: 2026-09-18
stage: planning
status: surveyed
task: none yet (follows 2026-09-17_scan_stairs_upstream_survey.md)
---

# Local planning on stairs beyond SCAN: open-source comparison

**Question (Dr Sun, 2026-09-18).** Besides SCAN, other algorithms must handle local planning on stairs. Which exist,
and which could we reuse?

**Status: `surveyed`.** Nothing was cloned, built, run, downloaded or imported.

## Method and verification

Three read-only surveyors worked in parallel on separate families, each with its own scratch folder:
[A: map-based planners](2026-09-18_stairs_local_planner_sources/A_map_based_notes.md),
[B: learned planners and navigation policies](2026-09-18_stairs_local_planner_sources/B_learned_notes.md),
[C: vendor and robot-specific stacks](2026-09-18_stairs_local_planner_sources/C_vendor_stacks_notes.md)
(SHA-256 in `SHA256SUMS.txt`). This extends
[the SCAN/PCT lineage survey](2026-09-17_scan_stairs_upstream_survey.md).

**What the lead re-checked on 2026-09-18:**
- **CMU `autonomy_stack_go2` `43d5f54`:** `terrain_analysis.launch` uses `useSorting` true, `quantileZ` 0.25,
  `vehicleHeight` 1.5, `noDataObstacle` true; `local_planner.launch` uses `obstacleHeightThre` 0.3,
  `groundHeightThre` 0.1.
- **SanD-Planner `415589e` (Apache-2.0):** `config.py` sets `clearance_height` 0.36, and `trajectory_evaluator.py`
  L116-120 replaces every query height with it, so the default collision check is one horizontal slice. The field is
  `Optional` and can be set to None.
- **`DeepRoboticsLab/Lite3_Navigation` `b091cee`:** no license, last pushed 2024-09-13. It is ROS 1 `move_base`
  with TEB and 2-D costmaps; no stair, step, terrain or elevation files.
- **Spot SDK `04537dd` `graph_nav/map.proto` L287-361:** route edges carry `StairData` (staircase with landings) and
  a descent preference that defaults to descending in reverse.

**Local facts measured by the lead (2026-09-18):**
- **Our Building stairs are shallow.** From the horizontal faces of `p2b_execution/inputs/building.usda`, one flight
  measured in detail (x -6.33 to -4.20 m, 2.13 m wide) has 0.136 m risers and treads about 0.74 m deep, about 9
  degrees. Other flights step 0.10-0.14 m; they were not measured in detail. A typical building stair is 0.15-0.18 m
  on about 0.28 m treads, about 30 degrees.
- **V12 was trained on standard stairs.** `robot_lab/tasks/go2/mdp/terrains.py` `TERRAIN_CFG` (used by
  `tasks/lite3/env_cfg.py`) has `stairs_up` (proportion 0.25) and `stairs_down` (0.10), step height 0.05-0.257 m,
  step width 0.31 m. V12's actor is blind: its policy terms are body state only; height scans feed the critic.

## Findings

**No local planner in any family has published real-robot stair success numbers that transfer to Lite3 with a blind
walking policy.** Stair evidence everywhere is the authors' own, mostly qualitative, on other robots, and mostly with
a walker that sees terrain. None reports descent.

| Family | Best candidates (commit, license) | Stair mechanism | Stair evidence | Fit to PCT -> local -> blind V12 |
|---|---|---|---|---|
| Map-based | CMU base autonomy `43d5f54` (BSD in `package.xml`, no LICENSE file) | Height above local ground (25th percentile); obstacle above 0.3 m; no stair mode | None found | High interface fit: Foxy/Humble, waypoint in, cmd_vel out. Derived risks: an upper tread can read above 0.3 m; a flight overhead counts as an obstacle |
| Map-based | ArtPlanner `2f3fde6` (BSD-3) | Torso box must be clear, foot boxes must reach ground | SubT: deployed weights avoided the stairs | The check is portable; the planner is ROS 1, ANYmal-tuned, 0.5 Hz |
| Map-based | dimos `26665a9` (Apache-2.0) | Standable cells, step limit; stair evaluator (body box 0.25-0.45 m, ground support, 0.2 m step) | Real MID-360 stair recordings and test cases, no numbers read | LCM, not ROS; useful as an offline stair benchmark |
| Learned | FDM + MPPI `06f5d80` (BSD-3) | Learns which motions a given walker can traverse, then samples velocities | Simulation, ANYmal, stairs and ramps: 73.75% vs 33.13% for a height-scan heuristic | Could be retrained on V12 in Isaac Lab; built for Isaac Lab 2.1-2.2, ROS Noetic |
| Learned | SRU navigation stack `80f6c01` / `568a96c` (MIT / BSD-3) | Navigation policy over a frozen low-level walker (blind in the public setup) | Simulation stairs 82.8%; real robot qualitative | Retrain over V12; Isaac Lab 2.1.1, ROS 2 Jazzy |
| Learned | SanD-Planner `415589e` (Apache-2.0) | Diffusion over depth frames; picks a B-spline by distance-field check | Real Go2 stair trials, no numbers | Closest to our chain (PCT-trained, B-spline output), but released defaults are planar |
| Learned | ViPlanner `6fcf3c6` (license conflict) | Stairs as a traversable semantic class | One real ANYmal experiment, no numbers | Assumes a perceptive walker; ROS Noetic |
| Vendor | Spot SDK (proprietary; concepts only) | Route edges carry staircase geometry, an alignment line, no-turn rule, reverse descent, per-edge overrides | None public | Best specification |
| Vendor | DEEP Robotics X30 client `f70df5e` (MIT) | Each waypoint carries gait, speed, obstacle-mode, navigation-mode and terrain fields | Product only | Shows the vendor labels the route; field values undocumented |
| Vendor | CyberDog2 `77c6578` / `4d241d1` (Apache-2.0) | Stair signal pauses tracking, squares up, runs a scripted climb with timeout, resumes | Product; no data | Pause/align/resume logic is licensed code; the detector is not public |
| Vendor | DEEP Robotics Lite3 navigation `b091cee` (no license) | None: flat 2-D move_base/TEB | None | None |

**Correction (2026-09-18, after Dr Sun asked whether any success avoids route labels and learned models).** The
statement above is about repeated-trial success rates and released code. Purely geometric local planning on stairs,
with neither route labels nor a learned planner, has been demonstrated on real robots; the lead read these abstracts
through the arXiv API:
- **RAEM** (arXiv 2608.25366): a local tomography map plus a local 3-D grid with an explicit traversable category,
  a staircase-centre alignment step computed from that map, and an elevation-aware topological graph. Real quadruped
  runs include continuous exploration of a five-floor stairwell (the Go2 and single MID-360 are from surveyor A's
  WebFetch reading). Code is not released; `Shua1ge/quadruped_exploration_planner` is a skeleton.
- **TravExplorer** (arXiv 2605.19958, SCAN authors): a volumetric map that separates occupied structure from
  robot-reachable support surfaces (floors, stairs, landings), foothold-guided 3-D search and vertically constrained
  local trajectory optimisation. Fifty real-world Unitree Go2 trials, single- and cross-floor, without prior maps.
  Code "will be released"; the repository holds a README today.
  **Second correction after reading the full text:** TravExplorer is *not* geometry-only on stairs. Its geometric ray
  casting treats stairs as obstacles, so on stairs it switches to traversability from open-vocabulary segmentation
  (SAM 3), triggered by stair detections or a detected stair landmark. See
  [D: full reading](2026-09-18_stairs_local_planner_sources/D_raem_travexplorer_full_reading.md). RAEM is the only
  geometry-only case found.
- **SCAN** (arXiv 2606.19555): the abstract reports simulation and real-world stair traversal.
- **Our own lead:** `native_full02` (machine-dog-nav, gpu5070ti), unmodified PCT/SCAN/V12, climbed the gentle Building
  stairs once with zero non-foot force.

All of these use the robot's stock or RL locomotion; only the planning layer is free of learned models. Per-stair
success numbers were not read and need the PDFs.

**Common pattern in shipped products.** Stairs are handled by knowing where the stairs are (a map or route label, with
live detection as a cross-check) and switching behaviour for that segment: straight approach, heading lock, speed cap,
a different obstacle filter, then hand-back. Spot, the X30 waypoint fields, Unitree route edges, CyberDog2 and
M20-loc-nav all do this. None relies on a smarter general local planner alone. The product stacks hand the segment to
a vendor stair gait; with V12 the stair "gait" would instead be a local-planner profile, because V12 already climbs
blind.

## Proposal (lead, for Dr Sun's decision)

**Primary: route-labelled stair segments with a stair profile.**
1. **Label** stair segments on the PCT route from the known terrain (height steps along the route), in the style of
   Spot's staircase annotation: entry and exit points, direction, riser height.
2. **Switch** the local planner to a stair profile on those segments:
   - obstacle filter: count only live points not explained by the known terrain (the SCAN-lineage pattern), or
     height above local ground (CMU terrain analysis, reusable code);
   - heading locked to the stair direction;
   - speed capped;
   - exit on the landing.
3. **Cross-check** with live detection, with hysteresis, for stairs that are missing from the map.
4. **Reuse:** CMU terrain analysis (BSD, per `package.xml`) for the filter, CyberDog2's pause/align/resume structure
   (Apache-2.0), and dimos stair test cases (Apache-2.0) for offline checks. The route labelling and profile switch are
   our glue, following the Spot and DEEP Robotics designs.

**Research alternative: learn what V12 can climb.** FDM or the SRU stack, retrained on Lite3 and V12 in Isaac Lab.
Both have released code and the only quantitative stair results in simulation, but both need training runs and an
Isaac Lab version port.

**Test scene first.** Our Building stairs (about 9 degrees, 0.74 m treads) are much gentler than real stairs, so
passing them would say little. A standard stair (for example 0.15-0.17 m risers on 0.28-0.31 m treads, within V12's
training range), added as its own prim, is needed for a meaningful baseline, as are both ascent and descent.

## Claim boundary

- `surveyed` only. No candidate was built or run by us, and no stair success is established by this survey.
- Paper numbers (FDM, SRU, ArtPlanner, RAEM) come from the authors' papers read through web tools and still need a
  PDF check.
- Some repositories carrying a "Go2 stairs" profile derive from a stack GitHub blocked under a DMCA notice; do not copy
  code from them.
- Commit pins are branch heads on 2026-09-18.
