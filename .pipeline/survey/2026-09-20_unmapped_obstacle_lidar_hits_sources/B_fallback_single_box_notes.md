---
origin: local
reviewed: false
date: 2026-09-20
status: surveyed
pin: references/upstream/2026-09-11_lite3_sim_bridge/source/lite3_sim_bridge/run_isaac_v12_fallback.py
commit: 848b4aecd01237805e0564c88d3ba09146fd2353
file_sha256: 6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3
claim_boundary: "Read the pinned local file. Not executed as course=single_box for this note."
---

# Pinned Lite3 fallback `single_box` LiDAR pattern

Local file (SHA-256 matches `references/upstream/2026-09-11_lite3_sim_bridge/SHA256SUMS.txt`):

`references/upstream/2026-09-11_lite3_sim_bridge/source/lite3_sim_bridge/run_isaac_v12_fallback.py`

Constants (L103–106):

- `COURSE_OBSTACLE_CENTER = (2.0, 0.0, 0.4)`
- `COURSE_OBSTACLE_SIZE = (0.6, 1.2, 0.8)`
- `GROUND_MESH_PRIM = "/World/ground"`
- `OBSTACLE_MESH_PRIM = "/World/ground/scan_obstacle"`

Spawn when `args.course == "single_box"` (L1934–1948): `AssetBaseCfg` with
`sim_utils.CuboidCfg(size=..., collision_props=CollisionPropertiesCfg(),
visual_material=PreviewSurfaceCfg(diffuse_color=(0.8, 0.1, 0.1)))`,
`init_state.pos = COURSE_OBSTACLE_CENTER`.

Raycast targets (L2128–2131): `environment_targets = [GROUND_MESH_PRIM]`;
if `single_box`, `environment_targets.append(OBSTACLE_MESH_PRIM)` as a
**string** (Isaac Lab static conversion). Forest instead appends tree
proxy prims. Office appends a `RaycastTargetCfg` for `{GROUND}/terrain`.

Hit count (L4723–4734): world `hits_w` inside
`center ± half_size ± 0.01`, also requiring finite hits, not self-occluded,
and `z > planner_floor_filter_max_z`. Camera path at L4985 repeats the
AABB with the same size tensor.

The Building runner `run_pct_scan_building.py` has **no** `single_box`
course. That is the gap: port this spawn + extra-target + AABB pad onto
`stand_probe`, do not invent a new sensor API, and do not switch the
stand launcher to this fallback (Office/forest path).
