# Lite3 shell visibility in recorded replay

Stage: experiment + analysis, 2026-09-27. Dr Sun reports that some leg shells
look cut open, exposing internal structure. The standing frame also shows the
symptom, so it is not limited to the homing pose.

## Scope before edits

The smallest gap is correct outward shell visibility for mirrored URDF meshes.
The pinned Newton file loader bakes signed scale into vertices but keeps source
triangle order and source normals. Its viewer's instance-scale mirror handling
cannot see that baked transform. Four single-axis-reflected visuals therefore
have reversed winding; a fifth double reflection needs its normals transformed.

Ranked checks: (1) mirrored winding/normals; (2) missing source shell surfaces;
(3) motion-induced overlap. Replay identical states while changing only mesh
orientation data. Compare geometry against the installed Trimesh
`apply_transform`, which already handles reflection and normals.

Expected edits: add a targeted replay-renderer regression in
`scripts/test_robot_rendering.py`; update `prepare_robot_appearance` in
`scripts/render_episode.py` to use an original-mesh display copy transformed by
Trimesh; record provenance and validation beside the experiment. Preserve the
original source files, physical model, controller, states, collision/sensor
geometry and previous videos. No new physics episode or robot access is needed.

Acceptance: the mirrored visuals agree with the upstream Trimesh transform;
all vertex positions, bounds and geometric triangles are unchanged; collision
objects and unscaled visuals remain unchanged; the same-frame A/B removes the
cut-open shell; a full replay decodes and uses the identical recorded-state hash.
Keep source-authored cavities rather than inventing surfaces to conceal them.

## Rear view follow-up

Dr Sun requested a view from behind to inspect the right legs. Add one explicit
`--view rear-right` option to the existing replay renderer, preserving its
default camera. This changes only the display camera and its recorded metadata.
Render the same `factory_zero_stand01` states, inspect crouch/zero/standing
frames for right-leg visibility, verify unchanged state identity and zero
physics steps, and deliver a separate complete MP4. No additional unit test is
needed for this camera-only adjustment; the actual replay is the validation.
