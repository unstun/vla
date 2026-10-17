---
origin: ai_with_source_check
reviewed: false
date: 2026-09-21
task: .trellis/tasks/09-21-isaac-scan-occupancy-aabb-miss
machine: gpu5070ti (Isaac Lab on the RTX 5070 Ti); analysis local
claim_boundary: "Diagnosis only: SCAN occupancy xyz extents vs frozen unmapped-box AABB on a standing Livox snapshot. Not navigation success, not a SCAN retune, not a physical MID-360, and does not amend 09-20 AC1."
---

# SCAN occupancy missing the unmapped-box AABB

Sibling of `09-21-isaac-rviz-urdf-scan-occupancy` (visualization; occupancy
AABB was 0 / 991 with no xyz). This child only classifies that miss.
`scan_planner_node` only. No `closed_loop_controller`, no PCT, no Pi.

## Verdict

| Criterion | Status | Evidence |
|---|---|---|
| AC0 local extents, xy/z split, planner-only | pass | `python3 test_run_rviz_probe.py` 8/8. Helper remains `scan_planner_node` + `cloud:=/quad_0/cloud`. No new clusterer. |
| AC1 gpu5070ti occupancy receipts with xyz + AABB splits | pass | `stand_20260921T151214Z_livox_rviz_gpu`. `planner.yaml` SHA `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e` unchanged. |
| AC2 miss class with numbers; no retune; no 09-20 AC1 amendment | pass as diagnosis | **xy-range**. SCAN not retuned. 09-20 frozen AC1 not amended. |

This is not a claim that SCAN occupied the box, and not a navigation test.

## Miss class

**xy-range.** Occupancy voxels sit in the box z-band, but none fall in the
box xy footprint. The leading z-band hypothesis (`ground_height: 0.0` +
`vis_height: 0.3` vs box z ≈ 1.56) is **not** what this run shows.

Frozen box AABB (from `unmapped_box_setup.json`):

| | x | y | z |
|---|---|---|---|
| min | 0.677 | −4.609 | 1.551 |
| max | 1.097 | −4.189 | 2.371 |
| centre | 0.887 | −4.399 | 1.961 |

Robot spawn `(−1.609, −4.543, 1.911)` m; box is 2.49 m ahead in x.

Occupancy receipts (`occupancy_receipts.jsonl` SHA
`e3da3d7fc95b65b231d27a21885f90c905b8f843412ab06f1093e800f983d8d6`):

AABB fields start at receipt 388, when `unmapped_box_setup.json` became
readable. The 387 earlier receipts are empty and have no AABB keys.

| Field | Value |
|---|---|
| Receipts | 1409 |
| With AABB (setup present) | 1022 |
| Nonempty | 909 |
| Points min / median / max (all 1409) | 0 / 3209 / 3308 |
| Points min / median / max (1022 AABB receipts) | 0 / **3243** / 3308 |
| `aabb_hits` | **0 / 0 / 0** over 1022 (`detected=false`) |
| `aabb_xy_hits` | **0 / 0 / 0** over 1022 (nonzero: 0) |
| `aabb_z_hits` | 0 / **3243** / 3308 (nonzero: 909); **equals `points` on every AABB receipt** |
| `miss_class` | **xy-range 909**, empty 113, z-band 0, both 0, overlap 0 |
| Occupancy z (all 909 nonempty) | min always 1.575 m; max 2.225 or 2.275 m; median z 1.875 or 1.925 m |
| Occupancy xyz median (last nonempty, #1409) | `(0.025, −5.875, 1.925)` m |
| Occupancy xyz extent (last nonempty) | x [−4.175, 3.425], y [−5.975, −1.725], z [1.575, 2.275] |
| `frame_id` | `world` |

Occupancy z **overlaps** box z (1.551–2.371). Occupancy's overall xy
extent also overlaps the box rectangle as a range, but **zero occupancy
points** lie inside that 0.4×0.4 m footprint. Occupancy mass sits at
y ≈ −5.875 m (Building structure ~1.5 m in −y from the box), not at the
box `(0.887, −4.399)`.

Live `/quad_0/cloud_raw` AABB hits still median **232** (min 209, max 263;
171 samples). LiDAR still sees the box; SCAN occupancy does not mark it.

## Run

20 s livox `stand_probe`, `--unmapped-box lidar`, `--stance-hold auto`,
GPU RViz + `scan_04` planner-only. Host idle before `--execute` (259 MiB
GPU, no compute apps, ports 46240/46241 free). WiFi `mt7925e` blacklisted
on this host after the 09:28 EDT kernel panic; that panic was not NVIDIA.
Returned hashes 46/46.

| Field | Value |
|---|---|
| Run | `livox_mid360_stand_probe/runs/stand_20260921T151214Z_livox_rviz_gpu` |
| Isaac | `EXTERNAL_EPISODE_FINISHED`, `passed=true`, travel_xy 0.074 m |
| Renderer | NVIDIA GeForce RTX 5070 Ti (`nvidia_renderer_verified`) |
| SCAN | `scan_planner_node` only, FSM `INIT` / `wait for goal` |
| `planner.yaml` | `ground_height: 0.0`, `vis_height: 0.3`, `cloud_is_world: false`, SHA `42a265a3…` |
| scan_04 | `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04` |

## What this is / is not

- **Is:** occupancy xyz vs frozen box AABB on one standing Livox snapshot.
- **Is not:** PCT, a waypoint, SCAN retune, 09-20 AC1 amendment, or a
  claim that occupancy visualization equals obstacle avoidance.

Why occupancy voxels collect at y ≈ −5.875 instead of the box xy is
outside this child's AC. Do not change `ground_height` / `vis_height`
from these numbers alone.
