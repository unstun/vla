# Official Isaac human mesh: probe results and inactive Building candidate

Stage: experiment and analysis. The isolated official-mesh translation probe
passed in v4 after three retained failures. The Building candidate remains
inactive. No live SCAN stair avoidance or person tracking result has passed.

## Current measured result

The nine official NVIDIA police mesh prims were the sole LiDAR target.
The actual raycaster returned 317 points at root y=0 m and 334 at y=1 m.
Hit mean y changed from 0.005859 to 0.972041 m (0.966181 m). All 88 staged
source/input files matched the local hashes before and after. This proves
rigid root-motion sensing in the isolated scene.

Actual points are in `first_hit_v4/finite_official_mesh_hits_world.npz`,
SHA-256 `4c7eddae5ac57e162166ec92b8391a1dd8889de30945616062c7237f40c7ee72`.
The complete sensor result was written before Isaac hung in stage cleanup.
A targeted SIGTERM released the verified probe process; `cleanup.json`
records that intervention. This was not a natural application exit.

The unchanged `scan_10` shape screen produced zero candidates on both real
clouds under an explicitly synthetic flat-ground fixture. Height-filtered
horizontal spans were 0.949 m and 1.636 m, above its 0.90 m gate; see
`../official_mesh_shape_review.json`. This remains a sensor-to-detector gap.
No threshold was broadened to hide it. The completed source audit in
`ANIMATED_MESH_LIDAR_AUDIT.md` confirms that this backend copies mesh points
once and updates only rigid target poses; the official skeleton's changing
joint attributes do not update its sensed triangles. The next separate gate
is an RTX animated-geometry probe. RTX skin sensing and MID-360 profile
compatibility remain unverified.

The probe-only Fabric correction has not been ported to the inactive
Building runner. That source retains mesh-ID output enabled and an unset
route approval. The current route proposal also has overlapping initial
robot/person envelopes, so it must not be used for a live episode.

## Exact source and input boundary

- `materialize_official_building_mesh.py` re-runs the pinned P2B runner
  materializer in a temporary directory and requires its resulting Building
  runner SHA-256 `2b282dc3aa589d90834fc884871dc6f4e75db1c3166b6a0a8e1bd76cc02f8a90`.
  It also verifies the source materializer, forest/Office reference runner,
  official human contract, police USD, three textures, and local retarget
  cache before writing `building_official_mesh_source/`.
- The materialized Building runner has SHA-256
  `1a0c9a688ac6528460354b7adcd3ea1f9e20d2c23c80748cc9c5645bedd6fe62`;
  its helper has SHA-256
  `19a7ac8264ec056dfd7457a0a35142a37ccb5192123985795082658310d3d1d9`.
  The candidate targets `/World/OfficialHumanVisual` itself with
  `merge_prim_meshes=True`, `track_mesh_transforms=True`, and mesh IDs enabled.
  No capsule or generated substitute is a LiDAR target. The official 90-frame
  walk cache advances while the actor moves. The actor's scheduled position
  and animation readback go to `official_human_truth.jsonl` for scoring only;
  they do not publish `/tracked_person_snapshot`.
- The candidate is **inactive**. `APPROVED_ROUTE_SHA256` is unset. The full
  Building runner refuses a stair actor route before Isaac starts. A later
  reviewed candidate needs actual Building mesh and PCT selected-ground
  heights, collision/clearance checks, and a pinned actor route hash. The
  interpolated example stair heights at x=-5.5 have two known mismatches and
  are not accepted as a route. This candidate also has no verified physics
  contact against the person mesh and no P2B process launcher.
  The built candidate still has mesh IDs enabled; the isolated v2 probe found
  an IsaacLab single-target mesh-ID tensor shape error. Do not launch the full
  candidate from this frozen source.

The character file is the code-pinned NVIDIA Isaac Sim 5.1
`male_adult_police_04.usd`, with a local reference and all three texture
dependencies pinned by SHA-256. The `.npz` is an existing official Biped
ControlRig retarget cache copied from the execution host and verified locally
against its adjacent manifest and the pinned content-hash algorithm (101
joints, 30 fps, 60 idle frames, 90 walk frames). The forest/Office bridge
source declares Apache-2.0 in `lite3_sim_bridge/package.xml`. The official
character and textures have separate NVIDIA materials terms:
[Isaac Sim Additional Software and Materials License](https://docs.nvidia.com/NVIDIA-IsaacSim-Additional-Software-and-Materials-License.pdf).

## Local checks already run

From the local VLA root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/test_official_building_human.py -v
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/test_materialize_official_building_mesh.py -v
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/smoke_official_mesh_two_poses.py --help
```

Results: 3/3 asset, route, and pre-Isaac refusal tests pass; 2/2 source
materializer tests pass; probe CLI help exits 0. The ten staged bytes in
`first_hit_sha256.txt` also match their local source files. These are local
code and identity checks only.

## Lead-only bounded first-hit probe

The smoke uses an isolated Isaac scene with **no robot** and no P2B process.
It references the local official police USD, instantiates the actual
`MultiMeshRayCaster` with only the official visual mesh as target, moves the
actor root from y=0 to y=1 m, and records finite hit counts, hit positions,
target prims, and animation evidence. v4 also saves the actual finite world
ray-hit arrays at both poses to `finite_official_mesh_hits_world.npz`, with
its SHA-256 in `result.json`. A passing result requires at least ten
hits at both poses and a 0.4 m shift in hit mean y. Raycaster initialization
or source mismatch writes an error to `result.json` and exits nonzero.

The lead's v1 failed because the sensor Xform lacked standard transform ops.
v2 reached ray updates but failed on the pinned IsaacLab mesh-ID output shape.
v3 disabled IDs and saw 317 official-mesh hits at both positions, while the
hit mean and bounds remained unchanged despite a successful USD root pose
readback. Pinned IsaacLab's `XformPrimView` syncs USD to Fabric once, then the
raycaster reads the cached view. v4 writes the official root's current pose
through that exact target view before each raycast and logs view pose before
and after. The v4 measurement above passed with the success threshold
unchanged. The official mesh remains the only
target, with no capsule or fabricated hits.

The executed v4 source is SHA-256
`0e856d6fbd91e22acbeebfc7764f14ac2cf4c55ebaa2f39f2687ae01e91beff7`
and is recorded in `first_hit_sha256.txt`. The lead's driver checks the
source hashes before and after the run, uses a fresh remote directory, and
returns all result files locally:

```sh
python3 .pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/execute_official_first_hit.py --run-id first_hit_v4
```

The local evidence is `first_hit_v4/result.json`, the finite-hit NPZ,
`smoke.log`, the source-gate transcripts, `commands.json`, and the exact
executed `source/` snapshot. The existing v4 run must not be overwritten;
future reviewed probes require a fresh ID. The pass proves only rigid
translation hits from the official mesh in an isolated scene. Skinned mesh
deformation, Building stair placement, physical collision, sensor-derived
person recognition, SCAN response timing, and robot outcome remain open.

Primary Isaac Lab source indicates the multi-mesh raycaster builds Warp
meshes from USD vertices once and updates target poses for tracked meshes;
therefore skinned limb deformation in LiDAR is not established by this probe:
[MultiMeshRayCaster source](https://isaac-sim.github.io/IsaacLab/main/_modules/isaaclab/sensors/ray_caster/multi_mesh_ray_caster.html).
