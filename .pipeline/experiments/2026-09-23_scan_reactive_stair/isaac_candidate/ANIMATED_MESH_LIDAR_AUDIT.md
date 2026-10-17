# Official human animation and LiDAR geometry audit

Stage: experiment and analysis. This is a read-only source and returned-data
audit. No new sensor was implemented or run here. The `scan_10` shape threshold
and the inactive Building runner are unchanged.

## What v4 established

`first_hit_v4/result.json` reports 317 and 334 finite hits from the official
police USD at root y=0 and y=1 m. Mean hit y moved 0.005859 to 0.972041 m.
The target view readback changed from y=0 to y=1 after an explicit Fabric
world-pose write. The returned `finite_official_mesh_hits_world.npz` has
SHA-256 `4c7eddae5ac57e162166ec92b8391a1dd8889de30945616062c7237f40c7ee72`,
matching the result. It records *actual raycaster hits*; it does not show that
the official walk skeleton deformed the sensed triangles. The result is a
rigid root-translation proof only. The probe's stage cleanup hung after its
result was written and the lead terminated the verified process; this is not
a natural-exit result.

The independent offline `official_mesh_shape_review.json` fed those two clouds
to the built `scan_10` shape prefilter with explicitly synthetic flat support.
It found 0 person-shape candidates in both poses. The selected-height point
spans were 0.9488 and 1.6360 m against the frozen 0.90 m maximum. This
isolated geometry test is not a Building scan or a temporal person track. It
does not justify widening the threshold to fit potentially undeformed mesh
geometry.

## Source-level answer: what MultiMeshRayCaster senses

The execution checkout is clean at IsaacLab commit
`37ddf626871758333d6ed89cf64ad702aef127d0` (origin
`https://github.com/isaac-sim/IsaacLab.git`). In that source:

- [`utils/mesh.py`](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/utils/mesh.py#L24)
  (local execution SHA-256 `ff1d7ba23e26b5c2eea4ae63e4ef9df0e4b3c7d8c7554658d0d4677a51ff0db2`)
  creates triangles by copying `UsdGeom.Mesh.GetPointsAttr().Get()` and face
  indices. It does not evaluate `UsdSkel` skinning.
- [`multi_mesh_ray_caster.py`](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sensors/ray_caster/multi_mesh_ray_caster.py#L205)
  (SHA-256 `8ec8313b9cd6068e65f41057d569f1d303ced1859860e77368b27d7fc6cf815b`)
  converts those triangles to a Warp mesh in `_initialize_warp_meshes()`.
  `_update_buffers_impl()` subsequently updates target position and
  orientation, then casts against the same cached mesh IDs. It does not
  reread mesh points or update Warp vertices per animation frame.
- The pinned bridge's `_OfficialHumanAnimationPlayer.update()` in
  `run_isaac_v12_fallback.py` (SHA-256
  `6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3`)
  writes official-cache joint transforms to `UsdSkel.Animation` translation
  and rotation attributes. It does not rewrite `Mesh.points`.

Thus, by source inspection, MultiMeshRayCaster does not incorporate the
official walk skin deformation. Its v4 returns came from the official USD
mesh's copied point array transformed by the moving root. This is a precise
reason to withhold a sensor-derived *walking human* claim, even though the
asset identity and rigid moving hits passed. It also explains why a static
bind-pose silhouette may be inappropriate for tuning the tracker, although
the source audit alone does not prove that bind pose caused both measured
spans.

The v3 stale-transform behavior had a separate cause: the cached
[`XformPrimView`](https://github.com/isaac-sim/IsaacLab/blob/37ddf626871758333d6ed89cf64ad702aef127d0/source/isaaclab/isaaclab/sim/views/xform_prim_view.py#L840)
(SHA-256 `5a05ccc9322e6f042f2ab669cbaf7fb60712726dfeb0d323913b78c87d3755b3`)
syncs USD to Fabric once. v4's direct write to the raycaster's target view
fixed *root transform* tracking, not animated vertex tracking.

## Smallest next sensing gate

The installed Isaac Sim 5.1 RTX extension contains `LidarRtx` (installed
`lidar_rtx.py` SHA-256
`2d3066f39c6a7c2fd529af3734412918a0b5af8bd7bbe90adbb89f151ec74575`).
Its `Example_Rotary` profile exists; the installed supported-profile table
(SHA-256 `4a6feaaff799a32f80dc80053f78df8591e4098bf0b1cd83498a9d17544109de`)
lists 18 asset entries and no MID-360/Livox entry. NVIDIA's Isaac Sim 5.1
[RTX LiDAR guide](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_rtx_lidar.html)
and [annotator guide](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_rtx_annotators.html)
show `LidarRtx`, render products, and
`IsaacExtractRTXSensorPointCloudNoAccumulator` / `GenericModelOutput`.
They require the simulation timeline to play and the app to update for
annotator frames. RTX uses renderer geometry, so it is the smallest
*plausible* official-visual path, but these documents do not establish that
this 5.1 build returns the animated skinned surface of this USD.

Before any Building or robot episode, a separate short RTX probe would need
to use the same pinned official USD, wrapper, and 90-frame walk cache; keep
the actor root fixed; capture point clouds at two separated official walk
frames; and repeat a fixed-animation control under the same sensor/profile.
It must record frame timestamps, sensor pose, raw returns, character prim
identity where available, and a renderer/skin-deformation reference. The
acceptance question is whether *the sensed silhouette changes with the
official skeleton at a fixed root*, above control variation. A generic
`Example_Rotary` profile can answer only that geometry question; it cannot
be called a MID-360 or silently replace the P2B scan contract. NVIDIA's
[custom RTX profile documentation](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_rtx_custom.html)
describes authoring a sensor profile, but a calibrated MID-360 pattern and
point-cloud parity with the existing `/quad_0/cloud` would be a separate gate.

The imported `lite3_sim_bridge/probe_rtx_lidar.py` (SHA-256
`d05837989616e09d2939263638498eeedd6f999d17c73993938c8c068e45a87e`)
already checks an RTX module-import child lifecycle and the installed profile
table. Its previous decision text reports an import teardown failure and no
MID-360. This audit verified the code and current installed profile table,
but did not locate a raw local import-run transcript to independently
reproduce the earlier lifecycle failure. A future RTX probe must first pass
that bounded import/teardown gate; it must not infer runtime usability from
the class file's presence.

If RTX fails to sense the official skinned surface, there is no validated
animated LiDAR producer in this candidate. A derived per-frame mesh bake from
the same official skeleton/cache would need its own geometry provenance,
sensor integration, performance gate, and human review. The current Warp
backend has no observed live-vertex update path. No procedural capsule,
simulator-truth track feed, threshold relaxation, or new sensor was substituted
in this audit.
