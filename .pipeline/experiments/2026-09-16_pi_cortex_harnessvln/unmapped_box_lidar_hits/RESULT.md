---
origin: ai_with_source_check
reviewed: false
date: 2026-09-21
task: .trellis/tasks/09-20-isaac-lidar-unmapped-box-hits
machine: gpu5070ti (Isaac Lab on the RTX 5070 Ti); analysis local
claim_boundary: "LiDAR hit-confirmation only. Not SCAN, not navigation success, not harness validated."
---

# Unmapped box in Isaac LiDAR: first stand_probe pair

OSS pins (status `surveyed`, not imported): Isaac Lab v2.3.2 `37ddf626`
sibling extra-target; pinned fallback `single_box` Cuboid/AABB pad 0.01 m
at `848b4aec` (file SHA-256 `6104fe68…`). Survey:
`.pipeline/survey/2026-09-20_unmapped_obstacle_lidar_hits_upstream_survey.md`.

## Verdict

| Criterion | Status | Evidence |
|---|---|---|
| AC0 surveyed spawn/target/AABB | pass | Executed runner SHA-256 `f0f10206…`. Cuboid at `/World/unmapped_box` (not under `/World/ground`). `lidar` appends that prim **string**; `spawn` does not. AABB pad 0.01 m. |
| AC1 spawn, 0 AABB hits after 1 s | **fail as frozen** | Median 5 hits / 21 scans. All at z = 1.56083–1.56093 m, the platform slab at the box bottom. See below. |
| AC2 lidar, every scan ≥1 and median ≥10 | **pass** | Median 30, min 30, max 36 / 21 scans. |
| AC3 frozen PCT tomogram | pass | `ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da` in both packages; box is not written into that pickle. |
| AC4 claim boundary | stated | This file. Strongest label: LiDAR target **integrated** for the positive control. AC1 as frozen did not pass. Not SCAN, not navigation, not `validated`. |

No post-result amendment. Frozen `unmapped_box_thresholds.json` SHA-256
`727d84805067aa4f07191add3d59196bbd9ba1965307a0dcaa8582ba12b44c97` is unchanged.

## Pair

Both 8 s `stand_probe`, `--stance-hold auto`, host idle before each
`--execute` (182 MiB GPU, no compute apps, no podman, stand ports free).
Returned hashes matched (26/26).

| Run | Mode | Clouds SHA-256 | Median AABB | Min/max | Above local ground + 0.02 m (report only) |
|---|---|---|---|---|---|
| `stand_20260921T072340Z_unmapped_spawn` | spawn | `708d448c…` (4 713 334 B) | 5 | 5 / 6 | 0 / 0 / 0 |
| `stand_20260921T072340Z_unmapped_lidar` | lidar | `6e88c5d4…` (4 719 642 B) | 30 | 30 / 36 | 30 / 30 / 36 |

Box centre (both): `(0.887, -4.399, 1.961)` m. Size 0.4 × 0.4 × 0.8 m.
Local ground = centre z − 0.4 = 1.56088 m. Prim `/World/unmapped_box`.
`lidar_target` false then true.

Executed patched runner SHA-256 `f0f1020651173a22c37e61476905ee901ac7ee1554ce676a115cfee6368e6ee0`
(four-group). Previous three-group hash `0649747e…` unchanged. Frozen
source `1490dc85…` unchanged.

## Why AC1 failed as frozen

PRD R4 counts every raw world point in the expanded AABB and forbids the
fallback planner floor-filter mask. The cuboid sits on the Building
platform, so the AABB includes the slab (z ≈ 1.5609 m, pad 0.01 m). Those
five points per scan are floor triangles from `/World/ground` /
`/World/ground/terrain`, which remain LiDAR targets in both modes.

They are not a Warp leak of the cuboid: spawn never lists
`/World/unmapped_box` in `mesh_prim_paths`, and every spawn hit is at the
slab z, not on the 0.8 m faces.

The pinned fallback `single_box` count (L4723–4734) uses the same AABB pad
**and** `hits_w[:, 2] > planner_floor_filter_max_z` (default 0.05 m). That
default is a **world-z** cut for a course whose ground is near z = 0. It
does not transfer to this Building stand (ground z ≈ 1.56 m). A
ground-relative cut `z > local_ground + 0.02` m, still on
`raw_points_sensor_frame`, would make spawn 0 and leave lidar at median 30.

That cut is **report-only** here. It is not an AC1 pass.

## Claim boundary

- The extra string target makes the cuboid appear in `/quad_0/cloud` (AC2).
- Omitting that string does not remove Building-floor points that share the
  box footprint (AC1 as frozen).
- Not SCAN occupancy, not a collision series, not Pi `navigate_to`, not
  harness `validated`.
