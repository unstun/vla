# Confirm Isaac LiDAR hits on one unmapped box

Stage: planning. Parent: `09-16-emos-harnessvln-reimplementation`.

## Goal

Prove that the Isaac navigation LiDAR returns raw points on one tall box
that is absent from the frozen PCT map. This is executor honesty for the
HarnessVLN `navigate_to` tool: SCAN cannot be judged on unmapped obstacles
until the cloud contains them.

## User value

Without this check, later collision, recovery, and Pi-owned `navigate_to`
work would be scored against a sensor that silently ignores the obstacle.

## Background

Dr Sun, 2026-09-20: the project is an independent HarnessVLN-style harness.
PCT→SCAN→V12 is the bottom executor, built first because
`AgibotGeneral/harnessvln` is still a README placeholder. The next small
goal is live LiDAR seeing one unmapped box before Pi joins the real
service.

Facts already in this repo:

- Collision survey (`surveyed`):
  `.pipeline/survey/2026-09-17_collision_handling_upstream_survey.md`. The
  Building LiDAR ray-casts the merged building mesh; a new box is invisible
  until it is its own prim **and** an extra `mesh_prim_paths` entry.
- OSS follow-up (`surveyed`):
  `.pipeline/survey/2026-09-20_unmapped_obstacle_lidar_hits_upstream_survey.md`.
  Copy Isaac Lab v2.3.2 extra-target + pinned fallback `single_box`
  Cuboid/AABB. Do not invent a sensor API.
- Observer path: `qualify_stand_runner.py` `--case stand_probe` already
  writes `clouds.jsonl` `raw_points_sensor_frame`. Sensor:
  translation `(0.182, 0, 0.109)` m, pitch +15° about Y, vertical FOV
  −7°…52°, range 0.1–12 m
  (`p2b_execution/baseline_config/native_nominal_scope.json`). Localization
  is simulator truth pose.

## Decisions

- D1 (Dr Sun, 2026-09-20). Standing observer. Reuse `qualify_stand_runner.py`
  `--case stand_probe`: zero command, no SCAN, no PCT motion publisher.
- D2 (Dr Sun, 2026-09-20). Two Isaac episodes on `gpu5070ti`: negative
  control then positive control. Duration is the existing 8 s `stand_probe`
  default, not the 60 s hold stand.
- D3 (lead, 2026-09-20; AABB pad amended from the OSS survey). Box
  0.4 × 0.4 × 0.8 m on local ground, 2.5 m ahead of the frozen stand start
  along `start_tangent_yaw`. Cuboid centre at ground z plus 0.4 m. Stance
  hold stays `--stance-hold auto`. Analyze raw (unfiltered) points
  transformed to world. AABB expansion **0.01 m** (fallback
  `run_isaac_v12_fallback.py` L4723–4734). The 0.4 × 0.4 m footprint is a
  recorded deviation from fallback `(0.6, 1.2, 0.8)` until Building-stand
  corridor clearance is measured; height 0.8 m is copied.
- D4 (Dr Sun, 2026-09-20). Survey-first. Implementation ports the surveyed
  Isaac Lab sibling-prim extra-target and the pinned fallback Cuboid spawn
  plus AABB pad. No novel Warp/raycast API. Do not spawn the box under
  `/World/ground`.

## Requirements

- R1. Spawn exactly one rigid box as its own prim, not a child of
  `/World/ground`, not merged into the Building mesh, and not present in
  the frozen PCT tomogram. Spawn uses `AssetBaseCfg` + `CuboidCfg` +
  `CollisionPropertiesCfg` (fallback L1938–1948), at `/World/unmapped_box`,
  before LiDAR init.
- R2. Negative control: the box exists in the scene and is omitted from
  `mesh_prim_paths`.
- R3. Positive control: the same pose and box; append the prim **string**
  `/World/unmapped_box` to `mesh_prim_paths` after the existing
  building-mesh targets (Isaac Lab static-string rule; fallback L2130–2131).
- R4. Count world-frame raw LiDAR points inside the expanded box AABB on
  every recorded scan after a 1.0 s settle. Do not apply the fallback
  planner floor-filter mask.
- R5. Fail closed before physics if the spawn AABB intersects the robot AABB.
- R6. Evidence under `.pipeline/experiments/` with hashes. Label at most
  `integrated` for this sensor check.
- R7. RESULT names the OSS pins (Isaac Lab `37ddf626`, fallback `848b4aec`
  / SHA-256 `6104fe68…`). Any deviation from those patterns is recorded
  there.

## Acceptance criteria

- [ ] AC0. Spawn, extra target, and AABB pad match D4/R1/R3/R4. RESULT
      cites the survey. No new raycast sensor class.
- [ ] AC1. Negative control, after 1.0 s settle: every recorded scan has 0
      points in the expanded box AABB.
- [ ] AC2. Positive control, after 1.0 s settle: every recorded scan has at
      least 1 point in the AABB, and the median count is at least 10.
- [ ] AC3. The frozen PCT tomogram SHA-256 matches
      `native_nominal_scope.json`
      (`ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da`);
      the box is not written into that map.
- [ ] AC4. RESULT states the claim boundary: LiDAR hit-confirmation only.
      Not SCAN, not navigation success, not harness `validated`.

## Out of scope

- SCAN occupancy, A* failures, emergency stops, or path deviation.
- Contact classification, a 1 N noise floor, or a collision-free success series.
- Stairs, Pi/Cortex, RGB-D, SLAM, language, graph memory.
- Editing `machine-dog` or `machine-dog-nav` in place.
- Changing the 41 two-goal checks.
- Switching the stand launcher to `run_isaac_v12_fallback.py`
  `course=single_box` (Office/forest path). That file is a pattern source
  only.
- Adopting the fallback 0.6 × 1.2 m footprint or spawning under
  `/World/ground`.

## Blocking open questions

None. Remaining work is implementation after explicit approval of this
summary.
