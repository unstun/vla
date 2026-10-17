---
origin: ai+web
reviewed: false
date: 2026-09-20
stage: planning
status: surveyed
task: .trellis/tasks/09-20-isaac-lidar-unmapped-box-hits
claim_boundary: "Surveyed only. Nothing cloned, imported, or run. Pins were re-checked through GitHub raw files at the Isaac Lab v2.3.2 tag and the local pinned fallback."
---

# Unmapped obstacle in simulated LiDAR: open-source patterns

**Question (Dr Sun, 2026-09-20).** Do not invent a closed-door box spawn.
How do open-source stacks make a spawned obstacle appear in a raycast /
LiDAR cloud, and how do they confirm hits?

**Status: `surveyed`.** No candidate was cloned, built, or executed for this
note. Inspection notes:
`2026-09-20_unmapped_obstacle_lidar_hits_sources/`.

## Criteria

1. Spawn a box or mesh that is not the terrain USD.
2. List that prim as a LiDAR / MultiMeshRayCaster target.
3. Count or assert hits on that object.
4. License copyable (BSD/MIT/Apache) or already pinned in this repo.

## Ranking

| Rank | Source | Reuse | Do not reuse |
|---|---|---|---|
| 1 | Isaac Lab v2.3.2 `37ddf626` MultiMeshRayCaster, `check_multi_mesh_ray_caster.py`, demo `multi_mesh_raycaster.py` `objects` | Extra prim as a **sibling** of ground; append to `mesh_prim_paths`; string target ⇒ `track_mesh_transforms=False`; `CuboidCfg` is valid on MultiMeshRayCaster | Demo `GridPatternCfg`; `track_mesh_transforms=True` (our box is static); spawning under `/World/ground` |
| 2 | Pinned Lite3 fallback `run_isaac_v12_fallback.py` `single_box` @ `848b4aec` (file SHA-256 `6104fe68…`) | `AssetBaseCfg` + `CuboidCfg` + collision; extra **string** in `mesh_prim_paths`; world AABB pad **0.01 m**; height **0.8 m** | Office/forest courses; prim `/World/ground/scan_obstacle` on the Building runner; planner floor-filter mask; 0.6 × 1.2 m footprint on an unmeasured Building stand corridor |
| 3 | Isaac Lab `test_multi_mesh_ray_caster.py` | Assert finite hits / distance / `mesh_ids` on a box | Warp-only; no USD scene |

## Why the fallback prim path is unsafe on Building

The Building patched runner already lists `/World/ground` plus
`/World/ground/terrain` (`merge_prim_meshes=True`). Isaac Lab’s
`RaycastTargetCfg.merge_prim_meshes` defaults to True, and
`_initialize_warp_meshes` concatenates every child mesh under a target.
A cuboid spawned at `/World/ground/scan_obstacle` can therefore enter
the **parent** target even when the extra string is omitted, which would
break the already-chosen negative control.

Isaac Lab’s own extra-object examples put the object **outside** the
ground prim (`{ENV_REGEX_NS}/Object`, `/World/envs/env_0/object_{i}`).
Keep that sibling rule. Keep the fallback **mechanism**.

## Recommendation (for the PRD)

Port the surveyed pattern onto Building `stand_probe`; do not write a
new raycast API; do not switch the launcher to `run_isaac_v12_fallback.py`.

1. Spawn `AssetBaseCfg` `CuboidCfg` at `/World/unmapped_box` (sibling of
   `/World/ground`), collision on, before LiDAR init.
2. `--unmapped-box spawn`: do not append the prim (negative).
3. `--unmapped-box lidar`: append the prim **string** to
   `mesh_prim_paths` (positive; Isaac Lab static-string rule).
4. Count world `raw` hits in `center ± half_size ± 0.01` m (fallback
   L4723–4734 pad only; do not apply the planner floor filter).
5. Keep box height 0.8 m. Keep xy 0.4 × 0.4 m on the Building stand
   route (recorded deviation from fallback 0.6 × 1.2 m until corridor
   clearance is measured).

**Not found:** an upstream spawn-but-omit zero-hit test. That negative
control remains our experiment design.

## Labels

`surveyed` only. Not `imported` (no new snapshot). Not `reproduced`.
SCAN, PCT, and Pi are out of this note.
