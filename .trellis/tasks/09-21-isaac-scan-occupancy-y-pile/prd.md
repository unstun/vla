# Diagnose why SCAN occupancy piles at Building y

Stage: experiment + analysis. Parent: `09-16-emos-harnessvln-reimplementation`.
Sibling of `09-21-isaac-scan-occupancy-aabb-miss` (miss class **xy-range**
on `stand_20260921T151214Z_livox_rviz_gpu`). Dr Sun (2026-09-21) authorized
this follow-on: why occupancy mass sits at y ≈ −5.875, not a SCAN retune,
not PCT.

## Goal

Explain the occupancy xy-range miss’s **pile location** using the existing
stand receipts plus pinned `scan_04` `GridMap` source. Do not change
`planner.yaml`.

## User value

A PCT / local-avoidance test of the unmapped box is still not evidenced.
The previous child showed occupancy z overlaps the box while xy hits are 0
and the occupancy median is `(0.025, −5.875, 1.925)`. Without a source-level
reason for that median, the next change would be a guess.

## Confirmed facts

- Same run `stand_20260921T151214Z_livox_rviz_gpu`. Occupancy AABB 0/1022,
  miss class xy-range, cloud AABB median 232. `planner.yaml` SHA `42a265a3…`.
- `/quad_0/cloud` and `/quad_0/cloud_raw` are **sensor-frame** (`frame_id=lidar`);
  Isaac `world_hits_to_sensor_points` then Foxy publish. AABB marker transforms
  with `/quad_0/lidar_pose` before counting. Occupancy audit does not; SCAN
  publishes `/grid_map/occupancy` in `world`.
- `scan_04` `GridMap::publishMap` skips voxels with
  `pos.z > ray_pos.z + vis_height` (`vis_height: 0.3`).
- `cloud_is_world: false` applies `pt_world = R * pt_sensor + ray_pos` from
  `sensor_pose:=/quad_0/lidar_pose`. That matches the AABB marker.

## Requirements

- Replay stored `clouds.jsonl` through the SCAN world transform and the
  vis_height / local-range tests. Cite `grid_map.cpp`.
- RESULT: why occupancy median y is ≈ −5.875; whether vis_height also
  explains **zero** box xy hits (yes/no, with numbers).
- No `ground_height` / `vis_height` change. No PCT. No 09-20 AC1 amendment.

## Acceptance Criteria

- [x] AC0. Offline replay of scan 80 from
      `stand_20260921T151214Z_livox_rviz_gpu/clouds.jsonl` plus `scan_04`
      `publishMap` vis_height rule.
- [x] AC1. RESULT states the pile cause with numbers. Does not retune SCAN.
- [x] AC2. RESULT says whether vis_height explains occupancy AABB 0 (it does
      not: 202 of 238 box hits survive the z clip).

## Out of scope

- PCT, waypoints, `closed_loop_controller`, Pi.
- Changing pinned `planner.yaml`.
- GPU `--execute` unless offline evidence is insufficient (it was sufficient).
- 09-20 frozen AC1 amendment.
