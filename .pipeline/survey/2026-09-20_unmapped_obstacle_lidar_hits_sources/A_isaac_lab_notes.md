---
origin: ai+web
reviewed: false
date: 2026-09-20
status: surveyed
pin: isaac-sim/IsaacLab v2.3.2 tag 37ddf626871758333d6ed89cf64ad702aef127d0
license: BSD-3-Clause
claim_boundary: "Read through raw GitHub files at the tag. Not cloned, not executed."
---

# Isaac Lab v2.3.2: extra mesh as a LiDAR target

Re-checked 2026-09-20 against tag `37ddf626871758333d6ed89cf64ad702aef127d0`
(Isaac Lab 2.3.2; our Isaac 2.3.2.post1 wheel tracks this Lab line).

## String targets are static

`source/isaaclab/isaaclab/sensors/ray_caster/multi_mesh_ray_caster.py`
`MultiMeshRayCaster.__init__`: a string in `mesh_prim_paths` becomes
`RaycastTargetCfg(prim_expr=target, track_mesh_transforms=False)`.

`multi_mesh_ray_caster_cfg.py` documents the same conversion. Defaults on
`RaycastTargetCfg`: `merge_prim_meshes=True`, `track_mesh_transforms=True`.
The string shortcut is what disables tracking.

`_initialize_warp_meshes` then walks **all** child prims of each target
whose type is in `PRIMITIVE_MESH_TYPES + ["Mesh"]` and, if
`merge_prim_meshes`, concatenates them. So a cuboid spawned **under** an
existing ground target is merged into that target unless Warp already
cached a terrain-only mesh. That makes a child-of-ground box unusable as
a negative control on the Building runner, which already lists
`/World/ground`.

## Extra object is a sibling, not a ground child

`scripts/demos/sensors/multi_mesh_raycaster.py` `asset_type == "objects"`:
Ground at `/World/Ground`; object at `{ENV_REGEX_NS}/Object` (`CuboidCfg`
among others); `mesh_prim_paths = ["/World/Ground", RaycastTargetCfg(prim_expr="{ENV_REGEX_NS}/Object")]`.

`source/isaaclab/test/sensors/check_multi_mesh_ray_caster.py`:
starts with `RaycastTargetCfg(prim_expr="/World/ground", track_mesh_transforms=False)`.
If `--num_objects != 0`, appends
`RaycastTargetCfg(prim_expr="/World/envs/env_.*/object_.*", track_mesh_transforms=True)`.
Objects are spawned at `/World/envs/env_0/object_{i}` with `CuboidCfg`, not
under `/World/ground`.

## Hit confirmation on a cube (Warp, not USD)

`source/isaaclab/test/sensors/test_multi_mesh_ray_caster.py`:
`trimesh.creation.box([2, 2, 1])`; `test_raycast_multi_cubes` asserts hit
xyz, distance 4.5, and `mesh_ids` 0 vs 1. This is Warp `raycast_dynamic_meshes`,
not a USD LiDAR scene.

## Old RayCaster Cuboid pitfall (do not cargo-cult)

[Issue #1259](https://github.com/isaac-sim/IsaacLab/issues/1259) (2024-10):
listing a `CuboidCfg` as the **only** `mesh_prim_path` of the **legacy**
`RayCaster` raised `Invalid mesh prim path: /World/cube`. Staff: a cuboid
was a shape, not a mesh. The later `MultiMeshRayCaster` (referenced from
that issue via PR #1886) documents primitive cubes as supported. The
objects demo and `check_multi_mesh_ray_caster.py` both use `CuboidCfg`.
Do not switch this task to `MeshCuboidCfg` on the basis of #1259.

A second #1259 note: the caster must initialize **after** the cuboid is
already at its pose. Scene `AssetBaseCfg` spawn (before sensor init) is
the safe order.

## Not found

No upstream test that spawns a box, omits it from `mesh_prim_paths`, and
asserts **zero** AABB hits. That negative control is our experiment
design, not an upstream script.
