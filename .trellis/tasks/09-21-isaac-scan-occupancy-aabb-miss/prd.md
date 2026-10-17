# Diagnose SCAN occupancy missing the unmapped box AABB

Stage: experiment + analysis. Parent: `09-16-emos-harnessvln-reimplementation`.
Sibling of `09-21-isaac-rviz-urdf-scan-occupancy` (visualization; that
child stays `in_progress` and does not start PCT). Dr Sun (2026-09-21)
chose this occupancy gate before any waypoint / PCT / SCAN dodge.

## Goal

Record where `/grid_map/occupancy` points sit in xyz, and why 0 of them
fell in the frozen unmapped-box AABB while live Livox `/quad_0/cloud_raw`
still had median 232 AABB hits. Diagnosis only. Do not retune SCAN.

## User value

A PCT global + SCAN local avoidance test of this box is not evidenced
yet: occupancy Status Ok (~3300 voxels) missed the box footprint.
Without xyz extents we cannot tell z-mismatch (`ground_height: 0.0` vs
Building slab z≈1.56 / `vis_height: 0.3`) from xy-range miss.

## Confirmed facts

- Run `stand_20260921T105823Z_livox_rviz_gpu`: occupancy receipts 1122,
  nonempty 910, points median 3231, AABB hits **0 / 991**. Cloud AABB
  median 232. `frame_id=world`. See
  `livox_mid360_stand_probe/RESULT_urdf_scan_occupancy.md`.
- Receipts store counts only, not xyz. Existing jsonl cannot answer z.
- Pinned `planner.yaml`: `ground_height: 0.0`, `vis_height: 0.3`,
  `cloud_is_world: false`, `max_ray_length: 5.0`,
  `local_update_range_{x,y}: 5.0`, `frame_id: world`.
- Frozen box AABB z ≈ `[1.551, 2.371]` m; robot LiDAR ≈ z 2.01 m;
  box centre ≈ `(0.887, -4.399, 1.961)` m.
- Occupancy audit already unpacks xyz and reuses
  `aabb_hit_marker.count_in_aabb`. No new detector.

## Requirements

- Extend occupancy receipts with xyz min/max/median and AABB splits:
  3D hits (existing), xy-only hits, z-only hits. Same frozen AABB.
- One livox stand on gpu5070ti: `--unmapped-box lidar`,
  `scan_planner_node` only, same `planner.yaml`. No PCT, no
  `closed_loop_controller`, no Pi, no `ground_height` change.
- RESULT: occupancy z-band vs box z vs cloud AABB; which miss
  (z, xy, or both). Claim diagnosis, not navigation, not AC1 amendment.

## Acceptance Criteria

- [x] AC0. Local tests: extents on a fixture cloud; xy-only vs z-only
      split; no `closed_loop_controller`; no new clusterer.
- [x] AC1. gpu5070ti livox stand records occupancy receipts with xyz
      extents and AABB splits. `planner.yaml` SHA unchanged
      (`42a265a3…`).
- [x] AC2. RESULT states the miss class (z-band, xy-range, or both)
      with numbers. Does not retune SCAN. Does not amend 09-20 AC1.

## Out of scope

- PCT, goal waypoint, two-goal 41 checks, Pi `navigate_to`.
- Changing `ground_height` / `vis_height` without a later decision.
- Invented clustering or a new LiDAR.
- 09-20 frozen AC1 amendment.

## Open questions

- None. Dr Sun 2026-09-21: occupancy gate first; then this plan.
