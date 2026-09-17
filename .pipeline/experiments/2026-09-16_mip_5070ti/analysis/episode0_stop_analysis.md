---
origin: ai_only
reviewed: false
date: 2026-09-17
stage: experiment_and_analysis
note: Read-only analysis of the one recorded episode, written before Dr Sun halted MIP on 2026-09-17.
---

# MIP episode 0 (R2R-CE ep 7, x8F5xyUWy9e): failure analysis

1. Per-step pose and distance were not recorded. One pose snapshot shows the agent was still ≥7.75 m from the goal after step 134, so the last 22 actions made most of the progress.
2. 72% of actions were turns, mostly in two turn-in-place surveys. 11 of the 43 forwards were blocked.
3. Best classification: the agent stopped too early at the right landmark (the near end of the bar); medium confidence. This is one exploratory run on the 5070 Ti host.

`RUN` = `.pipeline/experiments/2026-09-16_mip_5070ti/runs/nonstd_deepseek_flash_bare_20260916T105741013685Z/`. `AC` = `references/upstream/2026-09-16_mip/source/AgentCanvas/` (pinned b2b363af). L = 1-based line.

## 1. Trajectory

- **Not recorded:** per-step position, heading and distance. `RUN/live_0/actions.log` and the step results hold only counters.
- **Start and end:** start-to-goal geodesic distance 10.45 m (`AC/coding-agent/bridges/splits/r2r_rand100/rand100.json.gz`, ep 7). Final distance 4.7544 m, path length 6.87 m, oracle success 0 (`RUN/summary.json`), so no step came within 3 m.
- **One pose:** `.pipeline/experiments/2026-09-16_mip_5070ti/setup/real_episode0_observer_pose.json`.
  - Its timestamp falls between the step-134 and step-138 events (`RUN/raw/episode_0.dsh.jsonl` seq 270/279).
  - Its yaw is exactly 180° from the start yaw, matching the 36 net right turns up to step 134.
  - At that pose the agent was 7.75 m from the goal in a straight line; geodesic distance is at least that.
- **Estimate** (assumes no collisions after step 134): dead-reckoning the remaining 13 forwards ends about 4.5 m from the goal, consistent with the evaluator's 4.75 m.

## 2. Action pattern (`RUN/live_0/actions.log`)

| Steps | Lines | F | R | L | Phase |
|---|---|---|---|---|---|
| 1–48 | 1–6 | 0 | 42 | 6 | 540° survey spin, ends facing the route |
| 49–89 | 7–17 | 21 | 14 | 6 | Forward bursts into the wall |
| 90–117 | 18–21 | 0 | 10 | 18 | Second survey |
| 118–156 | 22–35 | 22 | 9 | 7 | Short approach moves, then STOP |

Blocked forwards: these frame pairs are byte-identical: obs_0009/0010 (4F), obs_0011/0012 (3F) and obs_0015/0016 (4F). The model wrote "Still blocked" (`RUN/episode_0.jsonl` L60, L80). Budget was not the limit: 344 actions remained (actions.log L35).

## 3. Observations (`RUN/live_0/`)

- **Start:**
  - obs_0001 (step 0): striped wall at close range. The start heading is about 158° off the route direction.
  - obs_0004 (step 18): pool.
  - obs_0007 (step 48): the hall ahead, with the bar counter and armchairs in the distance.
- **Middle:**
  - obs_0009 (step 56): the agent is pressed against the left wall.
  - obs_0022 (step 117): nearly the same view as obs_0007.
  - obs_0026 (step 130): pool on the right, bar far ahead-left. This contradicts the model's "moved past the bar" (L128).
- **Last three** (obs_0033–0035, steps 151–155):
  - Bar counter on the left; its near end looks about 1–2 m ahead (visual estimate).
  - Armchairs on the right; loungers and doorways behind.
  - The gap between the bar and the chairs is still ahead.
- **Match:** the view shows a corner of the bar, but only the near end. The estimate puts the goal almost straight ahead, about 4.5 m down that gap.

## 4. Classification

The agent **stopped too early at the right landmark**. Confidence: medium (~60%).

- **Right landmark:** the same bar lies on the route axis from step 48 onward.
- **Turning did not cause the failure:** budget remained and the final heading was on course.
- **Unchecked self-report:** the model claimed it was "well within 3 meters" (L173).

**What would change this:** per-step poses, or the goal projected into obs_0035.
- A goal behind the counter would make this the wrong corner of the right landmark.
- A goal outside this lounge would make it the wrong landmark.
- A different observer-pose provenance would invalidate the step-134 estimate. The file records no producer or step index.

## 5. Fields to record next time

| Field | Simulator provides | Recorded? |
|---|---|---|
| Pose per action | `step()` (`AC/workspace/nodesets/env/env_habitat.py` L535–536) | No: dropped in `AC/coding-agent/bridges/mcp_bridge.py` L373–402 |
| Pose per observation | `observe_egocentric` (env_habitat.py L1763) | No: `_capture_view` keeps only RGB (mcp_bridge.py L227–237) |
| Geodesic distance per step | `evaluate()` works mid-episode (L853–878) | No: called once, at the end (`setup/simulator_20260916T105738Z.log` L360) |
| Collision flag | `sim.previous_step_collided` (L787, used only in `step_path`) | No |
| Goal position | `get_episode_info()` (L992) | No: only in the pinned split file |
| Step index per frame | n/a | Yes: in the frame file names |
