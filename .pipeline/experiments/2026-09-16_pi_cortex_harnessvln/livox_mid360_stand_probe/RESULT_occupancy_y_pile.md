---
origin: ai_with_source_check
reviewed: false
date: 2026-09-21
task: .trellis/tasks/09-21-isaac-scan-occupancy-y-pile
machine: local replay of gpu5070ti stand_20260921T151214Z_livox_rviz_gpu; scan_04 GridMap read on gpu5070ti
claim_boundary: "Diagnosis of occupancy pile location from stored Livox clouds and pinned scan_04 publishMap. Not a SCAN retune, not navigation, not 09-20 AC1 amendment."
---

# Why SCAN occupancy piles at y ≈ −5.875

Sibling of `RESULT_occupancy_aabb_miss.md` (miss class **xy-range**). This
note only explains the occupancy **median**, using the same stand and
without another GPU run.

## Verdict

Occupancy mass sits on the Building’s south wall because
`/grid_map/occupancy` **does not publish** voxels above `lidar_z + vis_height`
(0.3 m). That drops ~70% of Livox world points (the high returns). What
remains is the slab / wall band around z ≈ 1.95 m, whose densest structure
is y ≈ −5.95 m.

`vis_height` does **not** explain occupancy AABB 0. On scan 80, **202 of 238**
box hits are still below the vis cut. Zero box xy occupancy is a separate
insertion / clearing question. `planner.yaml` was not changed.

## Evidence

Pinned `scan_04` `GridMap::publishMap`
(`/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04/src/plan_env/src/grid_map.cpp`):

- Skip voxel if `has_ray_pose_ && pos.z > ray_pos.z + vis_height_`.
- `cloudCallback` with `cloud_is_world: false`: `pt_world = R * pt_sensor + ray_pos`
  from remapped `sensor_pose:=/quad_0/lidar_pose`. Same as the AABB marker.

Offline replay of `clouds.jsonl` scan **80** (sensor-frame → world with stored
lidar pose; box AABB from `unmapped_box_setup.json`):

| Quantity | Value |
|---|---|
| Sensor | `(−1.421, −4.526, 1.977)` m |
| vis cut `lidar_z + 0.3` | **2.277 m** |
| Livox points | 19689 |
| After vis cut | **5786 (29%)** |
| Livox world z median (all / clipped) | 2.743 / **1.951** m |
| Livox world y median (all / clipped) | −4.489 / −4.492 m |
| Box AABB hits (all / after vis cut) | 238 / **202** |
| Wall band y ∈ [−6.05, −5.70] | 2386 points |
| vis-clipped 0.05 m voxels | 2797; top y-bin **(−5.95, 941)**; box voxels **115** |
| Occupancy receipt median (same run) | `(0.025, −5.875, 1.925)` m |

Occupancy z median 1.925 m matches the vis-clipped Livox z median 1.951 m.
Occupancy y median −5.875 m matches the densest remaining wall bin, not
the unclipped Livox y median (−4.49 m, next to the robot / box).

Box hits remain in range (`local_update_range` 5 m, `max_ray_length` 5 m,
0 skipped). So SCAN is given the box in the same frame it uses for walls.

## What this is / is not

- **Is:** why published occupancy looks like a wall at y ≈ −5.875.
- **Is not:** a retune of `vis_height` / `ground_height`; a claim that the
  box is absent from Livox; PCT; 09-20 AC1 amendment.

Why those 202 surviving box hits never become occupancy voxels is still
open (raycast hit/miss log-odds). Do not flip `cloud_is_world` or
`vis_height` from this note alone.
