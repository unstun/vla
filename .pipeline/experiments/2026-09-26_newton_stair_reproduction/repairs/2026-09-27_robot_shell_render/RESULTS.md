# Lite3 mirrored shell visibility correction

Stage: experiment + analysis, 2026-09-27. Dr Sun identified a cut-open shell
appearance, specifically visible internal structure on some legs.

## Cause and correction

Newton's pinned `load_meshes_from_file` multiplies vertex coordinates by the
URDF scale but retains the original triangle indices and vertex normals. Four
Lite3 visuals have a single-axis reflection: FR_HIP, FR_THIGH, HL_HIP and
HR_THIGH. This reverses outward triangle winding. Back-face culling then hides
the shell's outward-facing surface. HR_HIP has a two-axis reflection, which
preserves winding but still requires transformed normals for correct lighting.

The viewer already handles negative *instance* scale, but the URDF importer
bakes scale into vertices and then creates a unit-scale shape, so that viewer
path cannot detect this case. Sources are the pinned Newton 1.6.0
`newton/_src/utils/mesh.py:1366`, `utils/import_urdf.py:522` and
`viewer/viewer.py:2444`; source commit
`c2ca70bec5998062b0b2d35869865cbe3a49feee`.

The replay's `prepare_robot_appearance` now uses the existing
[Trimesh.apply_transform](https://github.com/mikedh/trimesh/blob/fcf660feb0a14c68fd3945789e8ed77e260f9167/trimesh/base.py#L2582)
to create five display-only copies with consistent normals and winding. The
MIT-licensed Trimesh 5.1.0 sources and license are pinned under
`references/upstream/2026-09-27_trimesh_mirrored_visuals/`; downloaded source
bytes match the already installed dependency. No new geometry repair or shell
generator was implemented, and the installed Newton source was not changed.

## Validation

- `robot_shell_red01`: the regression failed at the real appearance seam;
  3,138 of 9,420 normal components differed for the first reflected hip.
- `robot_shell_green01`: the same geometry regression passed after the fix.
  All five signed-scale visuals match the upstream transform. The four reflected
  meshes have positive signed volume. Original vertex positions and geometric
  triangle sets are identical. Every collision and unscaled source object,
  shape flag and instance scale is unchanged. Physics time and steps remain zero.
- `factory_shell_video02`: all 151 frames rendered from `factory_zero_stand01`
  without a physics rerun. Source-state SHA-256 is unchanged:
  `59a8ec538c5c37a2be3a09bd17c930d2b8e11d107394177f8840830a64f278da`.
- The standing frame and the zero-return frame at 5.44 s were inspected against
  the earlier video. The reflected thigh shells now show their exterior instead
  of their internal faces. Source-authored mesh features are retained.
- The complete H.264 video decodes without errors. `appearance.json` records
  each corrected link, source scale, winding change and output geometry hashes.

The motion, controls, calibration status, physical limits and prior test
verdicts are unchanged. This result validates the mirrored visual correction
only. The previous video is preserved.

## Replay

Run the existing `scripts/run_bounded.py` with a new output ID and invoke
`scripts/render_episode.py --source-run factory_zero_stand01` using the qualified
Newton Python environment. The resulting `frames.json` pins regenerable frames;
`delivery.json` here records the delivered MP4 and source identities.
