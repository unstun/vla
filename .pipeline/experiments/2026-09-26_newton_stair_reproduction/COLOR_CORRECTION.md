# Source-backed replay color correction

2026-09-26, experiment + analysis. Dr Sun reported strange video colors.
Scope: `scripts/render_episode.py`, source-backed appearance records and new
render outputs. The original episode, assets, motion, clouds and outcome are
unchanged. No physics rerun or new planner fix is part of this correction.

The old replay loaded the original albedo atlas but rendered all human parts
with white tint, ignoring each bound OmniPBR material. Original USD assigns a
red shirt tint(0.3057325,0,0) and a brown pants tint. Four accessories are also
authored invisible but were rendered. The Building's hard-coded display color
did not match its authored linear diffuseColor(0.52,0.63,0.71) and roughness0.85.

The renderer now resolves USD material bindings per visible mesh, applies
authored tint to the original texture and respects inherited visibility.
Original skin vertices/UVs/animation remain. Linear USD colors are encoded for
Newton's explicit gamma2.2 shader decode. Neutral viewport sky/ambient replaces
the default blue/dark sky; this is a declared display setting, not an exact
conversion of Isaac dome-light intensity. Basic ViewerGL still does not apply
OmniPBR normal/ORM textures or reproduce RTX indirect illumination.

Primary sources read before editing:

- [Newton shader at c2ca70be](https://github.com/newton-physics/newton/blob/c2ca70bec5998062b0b2d35869865cbe3a49feee/newton/_src/viewer/gl/shaders.py),
  local lines332–336 and439: object tint and texture decode, then output encode.
  The installed shader, viewer.py, opengl.py and example_basic_viewer.py all
  match the pinned source-manifest SHA-256. No upstream file was edited.
- [NVIDIA OmniPBR](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/templates/OmniPBR.html):
  diffuse_tint is an albedo multiplier;8-bit color textures use sRGB by default.
- [OpenUSD Imageable](https://openusd.org/release/api/class_usd_geom_imageable.html):
  ComputeVisibility resolves ancestral invisibility, not just local attributes.
- Original local `inputs/building.usda` and official human USD, plus a frame
  from the immutable Isaac right-human video, verify the actual authored look.

The three-frame `stair_material_preview_v1` shows the source red shirt, brown
pants, no hidden accessories and the authored Building color. The full rerender
is `stair_material_video_v3`, sourced from `stair_native_walk_v2` without physics
steps. `appearance.json` records each binding, tint, visibility and texture
hash. Verification and the regular delivery path are recorded in
`validation/color_correction_review.json`.

## Newly identified sensor limitation

The earlier geometric sensor also built its human ray mesh from all nine parts,
including the four authored-invisible accessories. This render-only correction
does not retrospectively remove those returns. Existing occlusion/skinning
controls remain evidence for their explicitly recorded nine-mesh condition;
they do not establish visible-USD/Isaac sensor parity. Requalify the sensor's
visibility selection before claiming that parity or further pedestrian
acceptance. Preserve the old cloud/state evidence and record a new sensor
condition when this is addressed.

The first full render (`stair_material_video_v1`) reached335/350frames before
its240s process deadline. Its partial frames remain intact. Upstream
`MeshGL.update_texture` decodes a supplied file again on every mesh update;
`log_mesh` also accepts an ndarray. The selected path uses public
`newton.utils.load_texture` once, then passes the exact unchanged RGBA array.
The second attempt only records a launcher argument typo; it ran no rendering.
The third has a420s offline-export cap; no physics/watchdog time limit changed.

## Robot material follow-up

Dr Sun then asked about the robot itself. Direct inspection found12 of the13
base/leg visuals lack URDF material colors; only FL_SHANK explicitly specifies
white. Newton's STL loader obtains a default0.4gray face color from trimesh for
the unspecified parts. This explains the inconsistent leg/body appearance.

The manufacturer's [DeepRobotics model repository](https://github.com/DeepRoboticsLab/deep_robotics_model/tree/5695b809bf86cccd9923d65079b5e34af5475b0a/Lite3)
was inspected at commit5695b809bf86cccd9923d65079b5e34af5475b0a. Its URDF has the
same missing-color pattern; its USD explicitly binds white diffuse materials
to all13 base/leg visuals. BSD-3-Clause license, URDF, MJCF and USD bytes/hashes
are retained under `references/2026-09-26_lite3_visual_materials/`. These files
are a material reference, not a replacement robot or an upstream dynamics run.

`prepare_robot_appearance` matches original local visuals by link and exact
mesh vertices/indices, then fills the12 missing colors from the pinned USD.
The explicit URDF white is preserved. All sensor colors/opacities, original
geometry, dynamics and recorded states remain unchanged. Prototype visibility
in the manufacturer's USD is not copied: the referenced prototype meshes are
hidden containers. Four unresolved foot-visual references in that upstream
layer remain visible in the log and are not imported or repaired here.

`robot_material_preview_v1` validates13 unique base/leg matches and unchanged
sensor colors. The full same-state rerender is `robot_material_video_v1`, with
its final checks in `validation/robot_color_review.json`. This restores the
public model's default white appearance; it is not a photorealistic coating or
high-resolution model import.
