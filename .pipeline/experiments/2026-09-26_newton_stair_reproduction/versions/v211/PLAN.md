# v211: full v210 recorded-state video

Reuse frozen v207 timeline, camera, materials, native-curve overlay and streaming
encoder. Rebind input paths and integration identity to v210_linux_full_attempt01.
Preserve startup, all navigation pauses and final observed state. Navigation
plays at its recorded wall time; untimed startup uses its original simulation
timestamps. No interpolation, new physics or acceptance changes.

Source: local VLA repository; execution/rendering: gpu5070ti. Verify parent
manifests and raw/analysis hashes before and after rendering. Return a regular
MP4, complete decode/frame mapping proof, provenance and representative decoded
frames. Both successful and failed physical outcomes must remain visible.
