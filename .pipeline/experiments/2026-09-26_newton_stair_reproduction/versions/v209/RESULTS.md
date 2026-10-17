# v209 recorded stop comparison

[Play video](delivered/newton_stair_recorded.mp4). Left: original v206 hold.
Right: v208 candidate. Two separate ten-second initialized-state probes, at
1x simulation time. First fixed PD: 2.359 / 2.299 s for the candidate. Neither
original control completed fixed PD during its ten-second observation.

604 frames, 20.133333 seconds, 1280x720, 30 FPS. Full decode and returned-file
SHA-256 pass. Causal per-frame mapping passes. Forward-kinematics torso pose
exactly matches recorded native pose; no state interpolation or physics steps.
Authored materials and original geometry are preserved. Reviewed decoded frames
75, 377 and 603 show leg geometry, readable labels and both PD transitions.

This is display evidence for the existing short tests, not full-route validation.
Frozen v206 and v208 source hashes remain unchanged. Heavy raw logs are archived
and member-hash verified on gpu5070ti; see delivered/inputs.json.

Regenerate on gpu5070ti using the Newton worker interpreter, EGL and the
existing host_python/runtime_sources/bridge PYTHONPATH:
`render_comparison.py --output /data/sun/vla_mppi_20261009/video_v209/NEW_RUN`.
The output must not exist. Source/dependency pins are in manifest.json.
