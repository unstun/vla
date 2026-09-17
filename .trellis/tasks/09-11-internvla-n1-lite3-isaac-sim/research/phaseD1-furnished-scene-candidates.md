# Research: Phase D.1 furnished indoor scene candidates

- **Query**: Primary-source comparison of furnished indoor scenes for D.1 ("Select a furnished interior and run the
  collision/performance admission check"). Priority after Dr Sun chose the Kujiale/InteriorAgent route (2026-09-15):
  InteriorAgent first; GRScenes-100 and the NVIDIA scenes are cut down to a short comparison.
- **Scope**: mixed (the pinned InternNav snapshot, Hugging Face, GitHub, NVIDIA S3/docs, papers)
- **Date**: 2026-09-15
- **Evidence label**: `surveyed` only. Nothing here was imported, reproduced, integrated or validated. No scene was
  loaded in Isaac Sim, and nothing ran on the rented 4090.
- **Machine for every check below**: the local Mac research workstation (macOS, Darwin 25.5.0). It used HTTPS fetches
  (HF API, GitHub API, S3 ListObjectsV2, NVIDIA docs), `pdftotext`, and `usd-core` 0.26.8 (`pxr`) in a throwaway
  session-scratchpad venv. The 5070 Ti results quoted from machine-dog-nav are that project's previews on a different
  machine. They are hints only.
- **What was fetched, and why**: no full scene and no texture. To answer the collision question, small USD layer
  files were read into the session scratchpad (outside the repo) and inspected:
  - InteriorAgent: one top-level `.usda` (112,015 B) and 11 object `.usd` files (about 2.9 MB);
  - NVIDIA: 2 top-level layers and 48 prop layers (about 4 MB);
  - episode JSON files and licence/paper PDFs.
  Nothing entered the repository.
- **Labels**: `verified (URL)` means read directly from that primary source on this date. `unverified/lead` means not
  confirmed.

---

## 1. InteriorAgent licence and access

- The HF dataset card declares `license: other`, `license_name: interioragent-terms-of-use`, `license_link:
  https://kloudsim-usa-cos.kujiale.com/InteriorAgent/InteriorAgent_Terms_of_Use.pdf`.
  verified (https://huggingface.co/datasets/spatialverse/InteriorAgent/blob/ac599fe2d2285ed0ddfafb70ba56e489462e0650/README.md)
- **The HF repository is not gated.** The HF API returns `gated: false, private: false`, so HF enforces no
  approval step. verified (https://huggingface.co/api/datasets/spatialverse/InteriorAgent)
- ToU PDF as fetched on 2026-09-15:
  - size and format: 64,594 bytes, 1 page, PDF 1.7;
  - **SHA-256 `e7db118650cf4426d7a463686588719a3fceb985b718e2bea00b6d8e824dd1ef`**.
  verified (URL above)
- ToU wording, verbatim apart from line breaks:
  - Preamble: "Before we are able to offer you access to the database, please agree to the following terms of use.
    After approval, you (the "Researcher") receive permission to use the InteriorAgent database(the "Database")."
  - 1. "Researcher shall use the Database only for non-commercial research and educational purposes."
  - 2. "Researcher shall not redistribute the downloaded data, in whole or in part, through other media, but shall refer
    to the Database website (https://github.com/manycore-research/InteriorAgent)."
  - 3. "Researcher shall cite the dataset appropriately in each publication based on Database."
  - 4. "Manycore Tech Inc. makes no representations or warranties regarding the Database …"
  - 5. The Researcher "accepts full responsibility … and shall defend and indemnify Manycore Tech Inc. …, including …
    use of any copies of copyrighted 3D models that he or she may create from the Database."
  - 6. "Manycore Tech Inc. reserves the right to terminate Researcher's access to the Database at any time."
  - 7. A for-profit employer is also bound.
  - 8. "governed by the laws of P.R. China".
- The ToU refers to an "approval" step, but the HF repo is ungated. No approval form or record was found.
  unverified/lead: whether Manycore expects a separate approval.
- The "Database website" named in clause 2, `github.com/manycore-research/InteriorAgent`, returns **404** from the
  GitHub API. The `manycore-research` organisation lists Structured3D, SpatialLM, InteriorGS, SpatialGen and others,
  but no InteriorAgent repository.
  verified (https://api.github.com/repos/manycore-research/InteriorAgent, https://api.github.com/orgs/manycore-research/repos)
- InteriorAgent_Nav, the episode files, is a separate repo: `license: cc-by-nc-4.0`, `gated: false`, and a card that
  holds only the licence line. verified (https://huggingface.co/api/datasets/spatialverse/InteriorAgent_Nav)
- Consequences under the project rules:
  - clause 2 matches AGENTS.md: the bytes stay local-only with provenance and SHA-256, never in git;
  - clause 1 (non-commercial) and clause 3 (citation) bind any publication. The card gives a BibTeX entry,
    `@misc{InteriorAgent2025, … SpatialVerse Research Team, Manycore Tech Inc.}`.

## 2. Pinned revisions and per-scene sizes

| Repo | Revision (sha) | lastModified | Files | Size |
|---|---|---|---|---|
| `spatialverse/InteriorAgent` | `ac599fe2d2285ed0ddfafb70ba56e489462e0650` | 2025-09-28T11:05:40Z | 13,621 tree entries | sum of file sizes 13.23 GiB; HF `usedStorage` 9,941,254,188 B (lead: likely LFS dedup, e.g. the identical HDR in every scene) |
| `spatialverse/InteriorAgent_Nav` | `7d8306f41f4c4dd12e9276774972c89876a3149b` | 2025-07-30T06:59:04Z | `train/`, `val_seen/`, `val_unseen/` `*.json.gz` | 704,968 B |

verified (HF API `tree/<sha>?recursive=true`, paginated). InteriorAgent_Nav file SHA-256s, computed locally:
- `train.json.gz`: 610,093 B, `9a9b27d36f77ff1cd07800c86f6730a8c798d4b7793cd8c155b7c7fd5e3db568`;
- `val_seen.json.gz`: 43,592 B, `494f4677856c56517fe214bc694f4f53ea6c99758d32ba837f24136b79946737`;
- `val_unseen.json.gz`: 51,283 B, `c141fb12a593502fd81648b1bd54ebad661a1206e64d6ebb083a0a4d3cc9203f`.

**25 scenes.** Every scene folder holds:
- `kujiale_XXXX.usda`, the top-level layer, 98–205 KB;
- `Meshes/*.usd`, one file per object;
- `Materials/*.mdl` plus textures;
- `limpopo_golf_course_4k.hdr`, about 25 MiB;
- `rooms.json`.

Sizes in MiB at the pinned sha. verified (HF tree API):

| Scene | Total | Meshes | Materials | HDR | Episodes? |
|---|---|---|---|---|---|
| `kujiale_0003` | 503.3 | 187.4 | 291.1 | 24.5 | train, val_seen |
| `kujiale_0004` | 391.8 | 91.4 | 275.5 | 24.5 | train, val_seen |
| `kujiale_0008` | 467.9 | 67.6 | 375.8 | 24.3 | train, val_seen |
| `kujiale_0009` | 1111.6 | 777.1 | 309.3 | 25.0 | train, val_seen |
| `kujiale_0020` | 417.8 | 163.6 | 229.1 | 25.0 | train, val_seen |
| `kujiale_0021` | 592.9 | 230.0 | 337.8 | 25.0 | train, val_seen |
| `kujiale_0022` | 339.1 | 59.3 | 254.6 | 25.0 | train, val_seen |
| `kujiale_0024` | 422.6 | 104.4 | 293.0 | 25.0 | train |
| `kujiale_0025` | 477.2 | 165.5 | 286.5 | 25.0 | train, val_seen |
| `kujiale_0026` | 372.8 | 205.4 | 142.2 | 25.0 | train, val_seen |
| `kujiale_0030` | 416.9 | 262.3 | 129.4 | 25.0 | train, val_seen |
| `kujiale_0031` | 493.7 | 79.2 | 389.4 | 25.0 | **val_unseen** |
| `kujiale_0032` | 683.2 | 309.8 | 348.3 | 25.0 | train, val_seen |
| `kujiale_0033` | 893.9 | 274.3 | 594.3 | 25.0 | train, val_seen |
| `kujiale_0034` | 526.0 | 93.9 | 406.9 | 25.0 | train, val_seen |
| `kujiale_0035` | 352.5 | 49.7 | 277.7 | 25.0 | none |
| `kujiale_0036` | 580.8 | 94.2 | 461.4 | 25.0 | **val_unseen** |
| `kujiale_0037` | 583.9 | 120.3 | 438.4 | 25.0 | train, val_seen |
| `kujiale_0038` | 353.6 | 117.6 | 210.8 | 25.0 | train, val_seen |
| `kujiale_0040` | 1254.8 | 414.3 | 815.3 | 25.0 | train |
| `kujiale_0042` | 539.7 | 127.5 | 387.0 | 25.0 | train, val_seen |
| `kujiale_0043` | 797.3 | 231.5 | 540.7 | 25.0 | train, val_seen |
| `kujiale_0065` | 200.0 | 52.0 | 122.8 | 25.0 | train |
| `kujiale_0066` | 518.6 | 71.3 | 422.1 | 25.0 | **val_unseen** |
| `kujiale_0067` | 257.7 | 87.0 | 145.5 | 25.0 | train, val_seen |

- Total 13.23 GiB: meshes 4.33 GiB, materials 8.29 GiB, HDR 0.61 GiB.
- Per scene: minimum 200.0 MiB, median 493.7 MiB, maximum 1,254.8 MiB.
- The download is per scene (`git lfs` or `hf_hub_download` with an include pattern). No split archive is involved.
- Download size does not measure GPU memory. GPU memory needs a D.1b measurement on the 4090.

Format and card claims. verified (dataset card at the sha):
- The card says: "`.usd` and `.usda` format", "physics-ready geometry", and materials in NVIDIA MDL "tested with Omniverse
  RTX renderer".
- `rooms.json` holds room polygons (`room_type`, `polygon`) in the world X–Y plane.
- The card's frame wording is "X is forward, Y is right, Z is upward". Handedness was not checked against the USD;
  treat it as unverified/lead.

## 3. InteriorAgent_Nav episodes

All counts were computed locally from the three files at `7d8306f4`. verified (files above)

| Split | Episodes | Scans | Notes |
|---|---|---|---|
| train | 649 | 21 | unique `trajectory_id` = 649 |
| val_seen | 44 | 18 | the scans are a subset of train |
| val_unseen | 99 | 3 | `kujiale_0031`, `kujiale_0036`, `kujiale_0066`, 33 each; disjoint from train |

- 24 of the 25 scenes have episodes; `kujiale_0035` has none.
- Episode fields: `start_position`, `start_rotation`, `instruction{instruction_text, instruction_tokens}`,
  `reference_path`, `goals{position, radius}`, `scan`, `scene_id`, `episode_id`, `trajectory_id`,
  `info{geodesic_distance}`.
- **Goal positions exist, and `goals.radius = 3` in all 792 episodes.** This is the challenge's 3 m success rule
  (`scripts/iros_challenge/README.md:460`).
- Geodesic distance, median: train 7.56 m, val_seen 7.79 m, val_unseen 7.37 m. Range 4.43–17.61 m.
- Instruction length, median words: 64, 64.5, 59.
- **Furniture-word statistics.** A crude regex count over a 40-term furniture list tests whether a word is present,
  not whether the object is visible or grounded.
  - At least one term appears in 98.2% of train, 95.5% of val_seen and **100% of val_unseen** instructions.
  - val_unseen top terms: table 62, dining 60, tv 45, bed 36, sofa 30, coffee table 25, sink 18, chair 17,
    cabinet 16, armchair 11.
  - Example (`kujiale_0031`, val_unseen): "Walks straight down a hallway, passing a wall-mounted TV on the right. Turns
    left into a doorway. … enters a bedroom. Stops near the bed, with the large window positioned behind the bed."
- **Start z and coordinate frame against the USD.**
  - `start_position[2] = 0` in all 792 episodes.
  - For `kujiale_0021`, the only scene checked (33 episodes), `goals.position[2]` and every `reference_path` z are
    also 0.
  - `kujiale_0021.usda`: `metersPerUnit = 1`, `upAxis = "Z"`, `defaultPrim = "Root"`. Every sampled object `.usd`
    also has metres-per-unit 1 and Z up.
  - Range check, `kujiale_0021`: the episode `reference_path` spans x 0.48–13.10 and y −3.40–3.31. The USD object
    `xformOp:translate` values span x −0.10–15.59 and y −4.59–4.64. Floors `floor_0000..0004` sit at z 0 and
    `floor_0005` at z −0.30.
  - This is consistent with using the episode coordinates directly in metres at scale 1. It is a bounding-range
    check on one scene only, not a per-room polygon test.
  verified (files above and https://huggingface.co/datasets/spatialverse/InteriorAgent/blob/ac599fe2d2285ed0ddfafb70ba56e489462e0650/kujiale_0021/kujiale_0021.usda)
- **InternNav uses kujiale coordinates without remapping.** Pinned snapshot
  `references/upstream/2026-09-08_dualvln/source/InternNav` @ `7a5c6240`:
  - `internnav/env/utils/episode_loader/dataset_utils.py:572,580`: kujiale and grscene episodes are grouped by
    `scan`. The axis and quaternion remap applies only `if dataset_type == 'mp3d'` (`:592`).
  - `internnav/model/utils/utils.py` `load_dataset`: the axis remap applies only to `dataset_type == 'r2r'`.
    Kujiale episodes are keyed as `trajectory_id_episode_id`.
  - `generate_episode.py:29-35` loads `<scene_data_dir>/<scan>/<scan>.usda`. The robot is placed at the episode
    `start_position` and `start_rotation`, and `vln_default_config.py:190,277` adds a spawn offset of
    `robot_offset = [0, 0, 1.05]` (H1).
  verified (local files)
- **Scene-scale conflict in InternNav.**
  - `internnav/env/utils/episode_loader/generate_episode.py:68-70` sets `scene_scale = (1, 1, 1)` for `kujiale` and
    passes it into `VLNEvalTaskCfg` at `:88`.
  - `internnav/configs/evaluator/vln_default_config.py:297-304` builds the kujiale `SceneCfg` with
    `scene_scale=(0.01, 0.01, 0.01)`, and grscene likewise at `:293`.
  - `grep scene_scale` over `internnav/` and `scripts/` finds no other reader of `SceneCfg.scene_scale`, so the
    episode path uses (1, 1, 1), which matches the metre-scale USD above.
  verified (local grep). unverified/lead: whether InternUtopia itself reads `SceneCfg.scene_scale`; its source is not
  pinned locally. A 0.01 scale would shrink a 15 m home to 15 cm, so D.1b's metre-scale check catches it either way.

## 4. Physics authoring in sampled InteriorAgent USD files

Sample, at sha `ac599fe2`:
- 9 object files in `kujiale_0021`: floor_0000, wall_0000, dining_table_0000, table_0000, chair_0000, sofa_0000,
  book_0000, door_0000, doorsill_0000;
- 2 object files in `kujiale_0003`: bed_0000, cabinet_0000.

The files were read with `pxr.Sdf`/`pxr.Usd` (usd-core 0.26.8). This covers 11 of the 6,149 files under `Meshes/` across 25 scenes, so the findings are a pattern, not an inventory. verified (files under
`https://huggingface.co/datasets/spatialverse/InteriorAgent/tree/ac599fe2d2285ed0ddfafb70ba56e489462e0650/`)

- **Top-level `.usda`**:
  - no physics API, no physics attribute, and no `PhysicsScene` prim (0 matches);
  - objects are Xforms with `prepend references = @./Meshes/<obj>.usd@`, grouped under room scopes such as
    `/Root/Meshes/kitchen_753`, carrying only `xformOp` values.
  So D.1b must author a PhysicsScene itself.
- **Standard object pattern** (floor, wall, table, dining_table, chair, sofa, book, bed, cabinet):
  - the object prim `/Root/Meshes/<obj>` is an **Xform, not a Gprim**;
  - its `apiSchemas` are prepended `[SemanticsAPI:Semantics, PhysicsRigidBodyAPI, PhysicsCollisionAPI,
    PhysicsMeshCollisionAPI, Physx<approx>CollisionAPI, PhysxMeshMergeCollisionAPI]`;
  - it carries `physics:kinematicEnabled = true`, `physics:rigidBodyEnabled = true` and
    `physics:collisionEnabled = true`;
  - the relationship `collection:collisionmeshes:includes` lists the descendant `Mesh` prims. The child `Mesh` and
    `Xform` prims carry no collision API; their `apiSchemas` list-ops explicitly delete the collision APIs.
- **Collision approximations**:
  - floor_0000, wall_0000: `none` (triangle mesh);
  - chair, dining_table, table, bed, book: `convexHull` (`hullVertexLimit` 64, `minThickness` 0.001);
  - sofa, cabinet: `convexDecomposition` (`maxConvexHulls` 256, `voxelResolution` 500000, `errorPercentage` 0.011,
    `shrinkWrap` true).
- **Furniture is nameable**. Every sampled object except doorsill has `semantic:Semantics:params:semanticType =
  "class"` and `semanticData = "<category>"` (chair, sofa, dining_table, bed, cabinet, …). Prim names repeat the
  category (`sofa_0000`).
- **Door (`kujiale_0021/Meshes/door_0000.usd`)**:
  - `/Root/Meshes/door_0000` (Xform) has `[SemanticsAPI:Semantics, PhysicsRigidBodyAPI]` with
    `kinematicEnabled = true` and **no collider of its own**;
  - `/Root/Meshes/door_0000/group_0000` (Xform) has `[PhysicsRigidBodyAPI, PhysicsCollisionAPI,
    PhysicsMeshCollisionAPI, PhysxTriangleMeshCollisionAPI, PhysxMeshMergeCollisionAPI]`,
    `rigidBodyEnabled = true`, approximation **`none`**, and 18 included meshes;
  - `kinematicEnabled` is **not authored** on `group_0000`. The UsdPhysics schema default is `0`
    (`generatedSchema.usda`: `bool physics:kinematicEnabled = 0`), so `group_0000` is a **non-kinematic (dynamic)
    rigid body nested under a kinematic one**, with a triangle-mesh approximation;
  - `/Root/Meshes/door_0000/group_0001` (23 meshes) has no physics.
- **`doorsill_0000`**: no physics API and no semantics.
- **What OpenUSD's reference parser does with these prims.** Source verified in
  `pxr/usd/usdPhysics/parseUtils.cpp` at OpenUSD `v25.08`
  (https://github.com/PixarAnimationStudios/OpenUSD/blob/v25.08/pxr/usd/usdPhysics/parseUtils.cpp):
  - `_GetCollisionType` (lines 101–196):
    - it first checks caller-supplied `customTokens` against the prim's applied API schemas and type name, which
      gives `CustomShape`;
    - it then assigns a shape type only if `prim.IsA<UsdGeomGprim>()` (Mesh, Cube, Sphere, Capsule, Cylinder, Cone,
      Plane, Points);
    - an `Xform` with `PhysicsCollisionAPI` and no matching custom token returns `UsdPhysicsObjectType::Undefined`.
  - Collision dispatch (lines 2884–2912, switch at 2990–2996): `Undefined` emits `TF_DIAGNOSTIC_WARNING("CollisionAPI
    applied to an unknown UsdGeomGPrim type, prim %s.")`. No shape descriptor is created for that prim.
  - `_GetBodyPrim` (lines 927–946) binds a collider to its nearest ancestor with `RigidBodyAPI`. For the door, the
    `group_0000` collider therefore belongs to `group_0000`, not to the kinematic `door_0000`.
  - Schema text (usd-core 0.26.8 `usdPhysics/generatedSchema.usda`): `PhysicsCollisionAPI` "Applies collision
    attributes to a UsdGeomXformable prim". `PhysicsMeshCollisionAPI` "Attributes to control how a Mesh is made into
    a collider".
  - **Verified in source, therefore**: with no PhysX custom-shape registration, the reference parser ignores these
    Xform-level colliders apart from a warning.
  - **Not verified, and only a run can show it**: whether Isaac Sim 5.1's `omni.physx` handles
    `PhysxMeshMergeCollisionAPI` on an Xform as one merged collider built from `collection:collisionmeshes`, which
    is what the schema name and the authored collection suggest. Also unverified are three behaviours:
    - how 5.1 treats a dynamic rigid body nested under a kinematic body without `resetXformStack`;
    - how 5.1 treats a dynamic body with `approximation = none` (a triangle mesh);
    - the cost of about 200 kinematic rigid bodies per scene.
- **Corroborating lead, not 5.1 evidence**:
  - InternUtopia's GRScenes navigation preprocessing authors the same Xform-level pattern
    (`set_collider_with_approx` + `set_mesh_merge_collision` on the instance Xform: `toolkits/grscenes_scripts/preprocess.py:124-160,252-255,396-428`
    @ `b0a9520c`, https://github.com/InternRobotics/InternUtopia/blob/b0a9520c586317c2743023c153cbf7c4f04f4732/toolkits/grscenes_scripts/preprocess.py).
  - The IROS 2025 track ran physically simulated H1 robots in these Kujiale scenes and reports Fall Rate and Stuck
    Rate (`scripts/iros_challenge/README.md:435,451-466`), on InternUtopia, which requires Isaac Sim 4.5.
  - Together these suggest the colliders took effect under 4.5. That is unverified/lead for 5.1.

## 5. Isaac Sim compatibility claims

- The InteriorAgent card claims only Isaac Sim 4.2 and 4.5: "Fully compatible with **Isaac Sim 4.2** and **4.5** on
  both Windows and Linux", and "Tested with: Isaac Sim v4.2, Isaac Sim v4.5, … Ubuntu 22.04". It makes **no 5.x
  claim**. verified (card @ `ac599fe2`)
- The InternNav/InternUtopia evaluation path that consumes these scenes targets Isaac Sim 4.5.0:
  - InternUtopia v2.2.1 README (`b0a9520c`) lists the prerequisites "NVIDIA Omniverse Isaac Sim 4.5.0" and
    Python 3.10.16;
  - its `Dockerfile` starts `FROM nvcr.io/nvidia/isaac-sim:4.5.0`;
  - issue #63 "[Enhancement]: Support Isaac Sim 5.0" is open. The maintainer wrote on 2025-08-07 that support would
    come after adaptation, and user comments continue to 2025-12-17.
  verified (https://github.com/InternRobotics/InternUtopia/blob/b0a9520c586317c2743023c153cbf7c4f04f4732/README.md,
  https://github.com/InternRobotics/InternUtopia/issues/63)
- So InternNav's `internutopia` evaluator is not a drop-in on our Isaac Sim 5.1 + Isaac Lab 2.3.2 stack. The scenes
  and episodes are plain USD and JSON and can be loaded independently of that evaluator. unverified/lead, pending
  D.1b.
- unverified/lead 5.x risks to check in D.1b:
  - the legacy `SemanticsAPI:Semantics` schema may need conversion to the newer labels API;
  - the MDL `OmniUe4*` materials must compile;
  - `PhysxMeshMergeCollisionAPI` and the other PhysX schema tokens must parse.
- The Isaac Sim 5.1 docs now carry the banner "Isaac Sim 5.1.0 is no longer supported". verified
  (https://docs.isaacsim.omniverse.nvidia.com/5.1.0/assets/usd_assets_environments.html)

## 6. Did InternVLA-N1 / InternData-N1 training use these Kujiale scenes?

No published evidence says it did. The individual findings:

- **InternVLA-N1 technical report** (https://internrobotics.github.io/internvla-n1.github.io/static/pdfs/InternVLA_N1.pdf).
  verified (text extracted locally; no "kujiale", "interior" or "manycore" string):
  - InternData-N1 = VLN-N1 + VLN-CE + VLN-PE;
  - VLN-N1 scene sources: Replica, Matterport3D, Gibson, 3D-Front, HSSD, HM3D (Sec. 3.1);
  - VLN-PE: "8,679 episodes across 61 scenes from the Matterport3D dataset" (Sec. 3.3);
  - System-1 evaluation used ClutterEnv and InternScenes-Home/Commercial, citing InternUtopia (Sec. 5.2).
- **DualVLN paper**, arXiv 2512.08186v1 (local `docs/research/papers/Wei2026InternVLA.pdf`). verified (no
  kujiale/interior string):
  - System 2 "follow[s] the data recipe of StreamVLN" (Sec. 3.3);
  - VLN-PE results are R2R/MP3D, "not being fine-tuned on VLN-PE trajectories";
  - Social-VLN uses 60 MP3D scenes.
- **Public training script** `scripts/train/qwenvl_train/train_dual_system.sh:29`:
  `vln_datasets=r2r_…,rxr_…,scalevln_…` with `system1=nextdit_async`. The script's own comment reads "replace with
  public dataset names", so the internal run may differ. verified (local, `7a5c6240`)
- **InternData-N1 on HF** @ `7b05993b21813c3787f2f7f604bfc22b80c48c8e` contains:
  - `vln_ce/{r2r,rxr,scalevln}`;
  - `vln_n1/traj_data/{3dfront,gibson,hm3d,hssd,matterport3d,replica}_{d435i,zed}`;
  - `vln_pe/{r2r,r2r_aliengo,r2r_flash}`;
  - no `interiornav` or `kujiale`.
  verified (https://huggingface.co/api/datasets/InternRobotics/InternData-N1; gated "auto", CC BY-NC-SA 4.0)
- **Kujiale training trajectories do exist publicly** for challenge participants.
  `InternRobotics/IROS-2025-Challenge-Nav` @ `050824be` has:
  - `vln_pe/traj_data/interiornav/kujiale_*.tar.gz`, one archive per scan, matching exactly the 21 InteriorAgent_Nav
    train scans;
  - `vln_pe/raw_data/interiornav/{train,val_seen,val_unseen}`.
  InternNav has `scripts/train/base_train/configs/challenge_train_kujiale_cfg.py:43,47` for the CMA/RDP baselines.
  Nothing links them to InternVLA-N1. verified (https://huggingface.co/api/datasets/InternRobotics/IROS-2025-Challenge-Nav)
- unverified/lead: `internnav/dataset/navdp_lerobot_dataset.py:593` names a developer-local test file,
  `dataset_lerobot_v05_with_interiorgs.json`. So InteriorGS (Manycore's 3DGS interiors, a different asset set) may
  appear in some NavDP data build. It is not tied to the DualVLN checkpoint.
- Interpretation (inference): by scene source, InteriorAgent is outside InternVLA-N1's published training
  distribution. Stylistic overlap with the 3D-Front/HSSD synthetic homes is possible but unmeasured. The val_unseen
  label only means "unseen by challenge-trained baselines".

---

## 7. GRScenes-100 (InternUtopia), short

- HF `InternRobotics/GRScenes` @ `4760b9031881c985e3582075cb2d8dbde1530a68` (2025-07-24). verified
  (https://huggingface.co/datasets/InternRobotics/GRScenes):
  - licence CC BY-NC-SA 4.0 and `gated: false`, **but** the InternUtopia README says users "MUST complete the User
    Agreement for GRScenes-100 Dataset Access" (Google Form) (README @ `b0a9520c`);
  - 99 environments: 69 home, 30 commercial;
  - home is a **split zip** of 20.0 + 20.0 + 7.45 GiB, and all parts are needed to extract any home scene;
  - commercial is a single 22.16 GiB zip. There is no per-scene download.
- Format: USD + MDL. The card installs `isaacsim==4.2.0.2`; InternUtopia requires 4.5.0; Isaac Sim 5 support is
  open (#63). Each scene ships `start_result_raw/navigation/interaction.usd`, per the card.
- Collision: the navigation preprocessing gives every model a static merged triangle-mesh collider, and deactivates
  non-main doors and joints (`preprocess.py:396-428`). verified (source)
- Episodes: `benchmark/sn_episodes.json` has 300 object-goal dialogue episodes (test 200 over 20 scenes, validate 100
  over 10) with `start_point`, `target_point`, `path` and a target instance; targets include toilet, desk, tvstand.
  `mm_episodes.json` has 420 manipulation episodes. No R2R-style route instructions were found. InternNav contains
  `grscene` loader code but no GRScenes VLN episode files. verified (files)
- Known loading problems: MDL `KooPbr` compile errors (#88, closed) and home scenes that fail to load (#93, open).
  verified (GitHub issues)
- Training distribution: the InternVLA-N1 report evaluated System 1 on "InternScenes-Home/Commercial", citing
  InternUtopia, and Scene-N1 ships `n1_eval_scenes/internscenes_{home,commercial}`. How these relate to GRScenes-100
  is unverified/lead.

## 8. NVIDIA Isaac Sim 5.1 Office / Hospital / Simple Warehouse, short (from material already gathered)

- S3 prefix `Assets/Isaac/5.1/Isaac/Environments/`. Every object has LastModified 2025-10-14. verified (S3
  ListObjectsV2):

| Folder | Objects | Total | USD layers | PNG textures | Top-level ETag |
|---|---|---|---|---|---|
| `Office/` | 2,288 | 706.2 MiB | 8.1 MiB | 698.0 MiB | `office.usd` `5aa2ea3a344747527d53979269115c81` |
| `Hospital/` | 1,637 | 1,046.9 MiB | 10.6 MiB | 1,020.1 MiB | `hospital.usd` `0ed1f898c67f91e45af6fb9917c561f8` |
| `Simple_Warehouse/` | 2,713 | 513.3 MiB | 19.1 MiB | 494.1 MiB | `warehouse_with_forklifts.usd` `fa2f7faa6cf6a2aaecc0194e479f8315` |

- Collision per NVIDIA docs:
  - the environment page describes the scenes without any collision statement;
  - the ROS 2 multi-robot navigation tutorial builds occupancy maps of Hospital and Office, and the Occupancy Map
    Generator "uses physics collision geometry in the Stage". So colliders exist in the 0.1–0.62 m band (inference).
  verified (…/5.1.0/ros2_tutorials/tutorial_ros2_multi_navigation.html,
  …/5.1.0/digital_twin/ext_isaacsim_asset_generator_occupancy_map.html)
- Sampled layers:
  - 4 named furniture props per scene, plus 20 random props per scene (seed 20260915), **all** carry
    `PhysicsCollisionAPI` + `PhysicsMeshCollisionAPI` with `approximation = none` and no rigid body. They are static
    triangle meshes, applied on Mesh prims;
  - the `hospital.usd` top layer has 126 CollisionAPI, 1,626 MeshCollisionAPI and 10 NavMeshAreaAPI specs;
  - the `office.usd` top layer has 1 CollisionAPI.
  verified (sample only)
- Instructions and goals: none are shipped. Prop names can serve as furniture names (`SM_Sofa`, `SM_ReceptionDesk_01a`,
  `SM_HospitalBed_01b`), but the prim names are not semantic labels.
- Licence: the 5.1 docs' "NVIDIA Isaac Sim Additional Software and Materials License" restricts use to Isaac Sim or
  Isaac Lab, and forbids distribution (2.2) and derivative works (2.4). unverified/lead: that this licence is the one
  covering the S3 environment assets.
- Cost: the only official 5.1 numbers are for `full_warehouse.usd`. On an RTX 4080 Super under Ubuntu it loads in
  49.6 s and renders at 210.53 FPS; no memory figure is given. Nothing official exists for Office or Hospital.
  verified (…/5.1.0/reference_material/benchmarks.html)
- Hints from the 5070 Ti (machine-dog-nav):
  - full Office gave no first frame;
  - Hospital rendered only a 4 m clay subset;
  - Simple Warehouse rendered with 792 meshes, all with CollisionAPI.
  The texture share above (99% of bytes) suggests texture load dominates. That is a lead.

## 9. Other Isaac-native furnished interiors, leads only (not verified; not padded)

- `spatialverse/SAGE-3D_InteriorGS_usdz`, `SAGE-3D_Collision_Mesh` and `SAGE-3D_VLN_Data` exist on HF (ungated,
  2026-07-27). They appear to combine InteriorGS 3DGS scenes with separate collision meshes and VLN data. Their
  content, Isaac Sim version and licence were not inspected. unverified/lead
- `InternRobotics/InternScenes` exists on HF (gated "auto", 2026-06-15), with Scene-N1 `n1_eval_scenes/internscenes_*`.
  Not inspected. unverified/lead

---

## Comparison table

| Candidate | Size | Format / Isaac version | Collision on furniture | Licence / access | Episodes & instructions | In InternVLA-N1 training distribution? | Main risk |
|---|---|---|---|---|---|---|---|
| **InteriorAgent + InteriorAgent_Nav** (Kujiale/Manycore) | 25 scenes, 200–1,255 MiB each (median 494), 13.23 GiB total; episodes 0.7 MB | USD/USDA + MDL; card: Isaac Sim 4.2/4.5 only | Yes as authored: per-object Xform, kinematic RigidBody + MeshMerge collider (hull, decomposition or triangle), semantic class labels. 5.1 parsing unverified; doors dynamic-nested or non-colliding; doorsill none | ToU PDF (non-commercial, no redistribution, cite, revocable); HF not gated; episodes CC BY-NC-4.0 | 792 R2R-style episodes (649/44/99), goals + radius 3 m, furniture words in ≥95% | No published evidence; sources are MP3D/HM3D/Gibson/Replica/3D-Front/HSSD (inference: out of distribution) | Xform-level colliders and nested door bodies under 5.1 physics; 4.x-only claims; GPU memory unknown |
| GRScenes-100 (InternUtopia) | 99 scenes in 47.45 GiB split zip (home) + 22.16 GiB (commercial) | USD + MDL; Isaac Sim 4.2/4.5; no 5.x | Navigation USD: static merged triangle mesh on every model | CC BY-NC-SA 4.0 + mandatory User Agreement form | Object-goal dialogue (300) + manipulation (420); no route instructions | Lead: "InternScenes" used for System-1 evaluation | 70 GiB all-or-nothing download; MDL KooPbr load failures |
| NVIDIA Office / Hospital / Simple Warehouse (5.1) | 706 / 1,047 / 513 MiB (≥97% PNG) | Native 5.1 S3 assets | Yes in sample: static triangle-mesh colliders on props | NVIDIA licence (lead); no redistribution | None; would be authored in D.3 | Not in the published sources | Render cost (5070 Ti hints: Office/Hospital first-frame failures); warehouse is not a home |

## Recommendation, with trade-offs (Dr Sun has selected InteriorAgent)

- **Why InteriorAgent fits AC8/AC9 best among the surveyed options**:
  - it is the only candidate that ships language instructions naming furniture together with goal positions;
  - it downloads per scene at about 0.2–1.3 GiB;
  - furniture carries collision and semantic labels as authored;
  - the ToU permits local, non-commercial research use without redistribution.
- **Trade-offs to carry into D.1a–D.1d**:
  - Physics under 5.1 is the open question. D.1b's CollisionAPI inventory must count the MeshMerge Xform colliders.
    Counting only Gprim `CollisionAPI` would report zero. D.1c probes should include the doors (dynamic nested body
    or no collider) and the doorsill (no collider).
  - The card claims only 4.2/4.5. Semantics, MDL and PhysX schema parsing on 5.1 are unverified.
  - The InternNav/InternUtopia evaluator is tied to 4.5, so only the scene and episode data transfer, not the
    evaluator.
  - Goal radius 3 m is the challenge rule; AC9's success radius is ours to freeze.
  - Episodes spawn at z = 0 with an H1 offset of 1.05 m; a Lite3 needs its own offset. Routes were generated for an
    H1, so Lite3 clearance needs D.2.
  - To pick a scene, the smaller val_unseen scans (`kujiale_0031` 494 MiB, `kujiale_0066` 519 MiB, `kujiale_0036`
    581 MiB) keep download and texture load modest. GPU memory can only come from D.1b/D.1d on the 4090.

## Caveats / Not found

- Collision findings come from 11 of the 6,149 InteriorAgent `Meshes/` files (2 scenes). The NVIDIA findings come
  from 48 of 837 `Props/*.usd` layers; the named and random samples may overlap.
- The furniture-word counts are a keyword heuristic, not a visibility or grounding check.
- Not found: any approval process behind the ToU "After approval" wording, and the ToU's referenced GitHub
  repository (404).
- Not checked: whether the IROS-2025-Challenge-Nav `raw_data/interiornav` copy is byte-identical to
  `spatialverse/InteriorAgent_Nav`.
- Not measured anywhere: GPU memory or RTF for any candidate on the rented 4090.
