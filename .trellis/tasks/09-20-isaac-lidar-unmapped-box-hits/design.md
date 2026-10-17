# Design: Isaac LiDAR hits on one unmapped box

Survey (status `surveyed`):
`.pipeline/survey/2026-09-20_unmapped_obstacle_lidar_hits_upstream_survey.md`.

## 1. Boundaries

- **Keep** the Building / patched `run_pct_scan_building.py` path used by
  `qualify_stand_runner.py`. Do not switch to
  `run_isaac_v12_fallback.py` `course=single_box`.
- **Port, do not invent.** Copy fallback Cuboid spawn (L1938–1948), extra
  **string** target (L2130–2131), and AABB pad 0.01 m (L4723–4734). Copy
  Isaac Lab v2.3.2 sibling-prim extra-object layout
  (`check_multi_mesh_ray_caster.py`, demo `objects`): the box is **not** a
  child of `/World/ground`.
- **Do not edit** the frozen reference runner in place
  (`EXPECTED_SOURCE_SHA256` `1490dc85…`). Add a new materializer anchor
  group `unmapped_box`, same as stance-hold: exact replacements on a copy,
  regenerate `runner_external_episode.patch` and `source_hashes.json`.
- **Launcher:** `qualify_stand_runner.py` only. `run_two_goal_pilot.py` is
  unchanged.
- **Not touched:** SCAN, PCT process, backend_ros, `machine-dog`,
  `machine-dog-nav`, V12 weights, two-goal 41 checks.

## 2. Box and sensor contract

Frozen before any Isaac run (PRD D3/D4):

| Field | Value | Source |
|---|---|---|
| Size xyz (m) | 0.4, 0.4, 0.8 | Height from fallback; xy smaller than `(0.6, 1.2)` until corridor clearance is measured |
| Prim | `/World/unmapped_box` | Isaac Lab sibling-of-ground extra object; **not** fallback `/World/ground/scan_obstacle` |
| Spawn | `AssetBaseCfg` + `CuboidCfg` + `CollisionPropertiesCfg` | fallback L1938–1948 |
| Extra target | string `/World/unmapped_box` | Isaac Lab string ⇒ `track_mesh_transforms=False`; fallback L2130–2131 |
| Offset | 2.5 m along `start_tangent_yaw` from `platform_segment.start_ground_xyz_m` | this task (stand pose) |
| Centre z | start ground z + 0.4 m | half of 0.8 m height |
| AABB expand | 0.01 m | fallback L4731–4732 |
| Settle | 1.0 s | this task |
| Duration | 8.0 s (`DEFAULT_DURATION_SECONDS`) | existing `stand_probe` |
| Cloud | `clouds.jsonl` `raw_points_sensor_frame` → world via recorded sensor pose | existing stand runner |

World point: rotate sensor-frame xyz by `sensor_quaternion_wxyz`, then add
`sensor_position`. Do not use `planner_points_sensor_frame` (terrain
filter). Do not apply the fallback `planner_floor_filter_max_z` mask.

Fail closed at setup if the expanded box AABB intersects a conservative
robot AABB (torso plus 0.25 m, from the 09-14 footprint notes) at the
spawn pose.

Do **not** wrap the box in `RaycastTargetCfg` unless a later measured
need appears. A string is the documented static path.

## 3. Runner flags

`--unmapped-box {off,spawn,lidar}`, default `off`.

- `off`: today’s runner. Existing stand_probe packages stay valid.
- `spawn`: Cuboid in the scene; `mesh_prim_paths` unchanged (AC1).
- `lidar`: Cuboid plus append `"/World/unmapped_box"` after the
  building-mesh targets (AC2).

Isaac Lab caches Warp meshes per target list. The Building comment at
patched L1989–1991 stays: building terrain remains an explicit target.
Height scanners stay on `TERRAIN_MESH_PRIM`.

## 4. Analysis

New `isaac_runner/analyze_unmapped_box_hits.py` plus unit tests with
synthetic `clouds.jsonl` (sensor-frame points, known pose). Thresholds
frozen in `isaac_runner/unmapped_box_thresholds.json` and hashed into
RESULT before C runs:

- AC1: after settle, every scan `aabb_count == 0`.
- AC2: after settle, every scan `aabb_count >= 1` and median `>= 10`.

AABB test: `|p - center| <= half_size + 0.01` on all axes (fallback
formula without floor filter / self-occlusion flags).

A local CPU geometry check (ray-AABB against the 16-channel / 2° pattern)
is allowed as a preflight; it does not replace AC1/AC2.

## 5. Evidence layout

`.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/unmapped_box_lidar_hits/`

- `RESULT.md` (includes R7 pin citations)
- `runs/stand_*_spawn/` and `runs/stand_*_lidar/` packages from
  `qualify_stand_runner.py --execute`
- analyzer JSON, tomogram SHA-256, patched-runner SHA-256
- claim boundary matching AC4

`clouds.jsonl` for 8 s at 10 Hz is on the order of 10 MB, not the 650 MB
stand/walk dumps. Keep it in the returned package; path-specific ignore
only if a run exceeds the 5 MB staged-file rule.

## 6. Rollback

`--unmapped-box off` restores the previous stand_probe. Revert the new
materializer anchors to recover patched SHA `0649747e…`. No SCAN or
two-goal launcher change to roll back.
