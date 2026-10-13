# v183: display-only policy stopping videos

Parent physics: v182, unchanged current model, policy-only stop windows.
Render the complete recorded startup and both walk/stop cycles in every trial.
No physics step is called during rendering. Use30fps causal nearest-past recorded
states, the existing Newton renderer/material correction and streaming encoder.
Freeze the camera during each stop and mark the command-time body position.
Show command, measured speed and displacement separately. Do not fabricate
navigation curves: navigation was disconnected. Preserve failed trials and
partial recordings with their actual outcome. Full decode, frame-source hashes,
timeline monotonicity and representative visual inspection are required.

Read only closed v182 captures whose raw archive has been SHA-verified on
gpu5070ti. Temporary render output stays below the authorized private/tmp root;
return regular MP4s, compact provenance and selected review stills. Two joined
terrain videos retain all six trials; individual clips remain available.

Display parent v180 is retained: its Mac Retina framebuffer was2560x1440,
while overlays used1280x720 coordinates, causing misplaced captions. v183
normalizes the render to1280x720 before annotation and moves the review camera
closer. Physical source v182 and original source times are unchanged.

This display binds the corrected-speed v182cohort. On the measured2xRetina
Mac framebuffer, a640x360logical window produces1280x720pixels before captions,
reducing display work without changing physical state or output dimensions.
