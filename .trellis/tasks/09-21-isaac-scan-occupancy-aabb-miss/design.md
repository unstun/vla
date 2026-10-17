# Design: occupancy xyz extents vs frozen box AABB

## 1. Boundaries

- **Keep** livox stand RViz probe (CSV, sensor-rig, SCAN planner-only,
  bridge `--ipc=host`, occupancy_audit).
- **Add** xyz summary fields on the same occupancy PointCloud2 unpack
  already used for AABB counts.
- **Not started:** PCT, closed_loop_controller, goals, Pi.
- **Not changed:** `planner.yaml`, 09-20 AC1, four-group patched SHA.

## 2. Receipt fields (world frame)

Reuse `aabb_hit_marker.unpack_xyz` and `count_in_aabb`.

| Field | Meaning |
|---|---|
| `xyz_min` / `xyz_max` / `xyz_median` | per-axis over occupancy points; omitted if empty |
| `aabb_hits` | 3D frozen box (existing) |
| `aabb_xy_hits` | ignore z |
| `aabb_z_hits` | ignore xy |

Miss class:

- z-band: `aabb_xy_hits > 0` and `aabb_hits == 0`
- xy-range: `aabb_z_hits > 0` and `aabb_hits == 0`
- both: both split counts 0 while occupancy nonempty
- overlap: `aabb_hits > 0` (unexpected on current evidence)

Leading hypothesis: occupancy z near `ground_height + vis_height`
(0.0 + 0.3 m) while box z is `[1.55, 2.37]`.

## 3. Execute

Same wrapper as occupancy visualization: livox 20 s stand, GPU RViz
optional (extents come from the audit node, not the video). Fail closed
if SCAN helper dies. Do not subsample Livox.

## 4. Rollback

Omit the extra receipt fields; previous occupancy jsonl remains valid.
