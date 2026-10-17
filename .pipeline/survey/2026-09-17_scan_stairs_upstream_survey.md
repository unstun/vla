---
origin: ai+web
reviewed: false
date: 2026-09-17
stage: planning
status: surveyed
task: none yet (foundation step after the SCAN fix and the stance hold)
---

# Stair handling for the SCAN local planner: who has done it

**Question (Dr Sun, 2026-09-17).** SCAN has no stair-specific algorithm. Has anyone on GitHub already optimised SCAN,
or a PCT-based stack, for stairs, so that we reuse rather than invent?

**Status: `surveyed`.** Nothing was cloned, built, run or imported.

## Method and verification

Two read-only surveyors worked in parallel: the SCAN lineage (all forks, issues and PRs of
`wuyi2121/SCAN-Planner` and `yagami-light7/PCT-SCAN-ROS2`, plus downstream code search) and the PCT lineage (all forks
and issues of `byangw/PCT_planner`, plus PCT-based integrations). Notes with permalinks and UNVERIFIED markers:
[A: SCAN lineage](2026-09-17_scan_stairs_sources/A_scan_lineage_notes.md),
[B: PCT lineage](2026-09-17_scan_stairs_sources/B_pct_lineage_notes.md) (SHA-256 in `SHA256SUMS.txt`). The two
surveyors shared a scratch folder and one overwrote the other's fork table; surveyor A rebuilt its census from fresh
API calls and the counts matched.

**What the lead re-checked on 2026-09-17:**
- SCAN-Planner issues #5 and #16: the owner's answers (raise `body_height_`; no semantic stairs/obstacle distinction;
  flat-stairs-flat needs three waypoints; a new 3-D global planner is planned).
- PCT_planner issue #17: a collaborator says the stair demo likely used no local planner (nearest global waypoint
  under LiDAR localization) and points to CMU `pathFollower.cpp` and arXiv 2602.00923 for local avoidance.
- `tianchaowen/PCT_planner` `8c56322` `plan.py` L514-627 and `planner_wrapper.py` L141-196: live points are kept as
  obstacles only by height above the PCT terrain surface.
- `robwawa/motion_planner` `dfeae40` `grid_map.cpp` L481-584: SCAN's map also queries PCT traversability
  (`isPctPointTraversable`). GitHub reports no license.
- `YiFanWei1/SCAN-Planner-Ros2` `dev` `ed97b93` (Apache-2.0): 42 commits ahead, including the A* vertical band and
  `diagnostics/stairs_failure_analysis.log` (see below).
- **Correction to surveyor A:** the rule that drops goals below z -0.1 is in `waypointCallback`
  (vendored `scan_replan_fsm.cpp` L147-157). Our runs use `fsm.navi_mode: 3`, which takes the route through
  `pathCallback` (L347), so this rule does not affect our pipeline.

## Findings

**Census.**
- SCAN-Planner has 58 forks, of which 11 have commits of their own.
- PCT-SCAN-ROS2 has 2 forks; only one is ahead, with Foxy-only edits.
- PCT_planner's network has 70 forks: 31 are ahead of upstream and about 23 have their own commits.
- Upstream SCAN has no commits since 2026-07-29 (`348e8a5`) and still has no ground removal, step detection or
  terrain analysis.

**Verdict: partial.** Several projects wrote stair code for SCAN or a PCT stack. None has committed evidence that it
works on stairs; the one measured stair replay shows it does not yet.

**The attempts fall into four patterns:**

| Pattern | Examples (commit, license) | Evidence |
|---|---|---|
| 1. Use the known map to decide which live points are terrain | tianchaowen/PCT_planner `8c56322` (GPL-2.0; EGO local planner, points count only if about 0.23 m or more above the PCT surface); robwawa/motion_planner `dfeae40` (SCAN plus PCT traversability; no license); AugetyVolta/M20-loc-nav `981579e` (DEEP Robotics M20; live points matching the PCT surface deleted; no license) | MuJoCo Go2; Gazebo (README says its closed loop does not validate stairs); M20 notes and bags without a success table |
| 2. Let the local search follow the route's height | YiFanWei1/SCAN-Planner-Ros2 `ed97b93` (A* z band +/-3 voxels; route segmented into near-linear-z parts; Apache-2.0); wangxx771/SCAN-Planner-ROS2-Humble `43237df` (full 3-D A*; Apache-2.0); Robot-Nav/legbot_3D_Nav `f60606a` (route z aligned to odometry; Apache-2.0) | Unit tests; one self-reported Gazebo route; YiFanWei1's replay below |
| 3. Switch mode before mapped stairs | M20-loc-nav (stairs detected 3-4 m ahead on the PCT route switch costmap, scan filter and stair gait); TheChanYe/SCAN_Planner_dmq `58c4c39` (stair mode ignores occupancy up to 0.25 m above the route) | M20 as above; TheChanYe's commit messages call it buggy and the author's other branch removes it |
| 4. Ground removal or height above local ground | xcg124110023416/SCAN_PLANNER `f22306e` (Patchwork++, BSD-2, plus one fitted slope plane; ramps, not steps); CMU terrain_analysis (BSD; stairs profile raises the obstacle threshold to 0.3 m) | Config tests; CMU stack used on real Go2, stair evidence not verified |

**The one measured stair result is negative.** YiFanWei1 replayed a real Go2 stairwell bag (Livox, "up_and_down")
through SCAN (`diagnostics/stairs_failure_analysis.log` at `ed97b93`):

| Metric | Baseline | A* z band +/-3 |
|---|---|---|
| A* plans failed | 83 of 96 | 75 of 80 |
| "Robot inside obstacle" | 113 | 6 |
| Emergency stops | 23 | 27 |

Letting the search follow the height removed most "inside obstacle" events, but almost every search still failed.
This is an open-loop bag replay, not a closed-loop run, and it was not re-analysed by us.

**Other leads (surveyor reading, not re-checked):**
- PCT's height smoother can flatten a descending staircase, with up to about 3 m height error in one fork's
  measurement (`height_smoother.cc` L21-33; fix in zhongrenjiexing `ba89d0cbd6`). This matters for us: our SCAN
  takes PCT's route height as the body reference (`body_height` 0.0).
- qiyu-lu/nav-benchmark reports that with a LiDAR pitched 45 degrees stair treads never entered the occupancy map,
  while 60 degrees worked.
- Our own lead (machine-dog-nav, gpu5070ti): one native PCT/SCAN run up the Building stairs (`native_full02`) had zero
  non-foot force; an earlier run had shank contacts.

## What this means for us (lead proposal)

- **No code to adopt as-is.** The best-matched designs (robwawa, M20) have no license; tianchaowen is GPL-2.0 and
  targets EGO-Planner. The Apache-2.0 SCAN forks only address the vertical search, which YiFanWei1's replay shows is
  not enough alone.
- **Pattern 1 fits Dr Sun's architecture.** PCT owns the known terrain; SCAN should treat only what is not explained
  by that terrain as an obstacle. It depends on localization accuracy against the map, and does not help on
  unmapped stairs.
- **Measure before changing SCAN.** Our Building stairs were climbed once by unmodified SCAN. A baseline series on
  that route, logging SCAN's planning failures (A* failures, "inside obstacle", emergency stops) and per-link
  contact, would show whether and how SCAN fails on our stairs before a fix is chosen.

## Claim boundary

- `surveyed` only. No candidate was built or run by us. Fork evidence is the authors' own; no stair success is
  established anywhere in this survey.
- Licenses are GitHub's detection or the files read; unlicensed code cannot be copied.
- Commit pins are branch heads on 2026-09-17.
