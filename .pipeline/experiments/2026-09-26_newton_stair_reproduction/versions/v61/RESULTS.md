# v61 display validation

Stage: experiment + analysis, 2026-10-03. **Display accepted; physical navigation remains v59 and does not pass the 30 Hz or uninterrupted-progress gates.**

The camera uses a 1.1 m trail, 0.6 m height, 0.25 m look-ahead, 0.2 m downward framing and 0.5 s yaw smoothing. It clears the ceiling while retaining the whole robot. This frozen display-only child of v60 changes no simulation state, native source, recording time or selected frame index.

The final review is [v59_realtime_trial01_review_v61.mp4](../../../../../output/2026-09-27_lite3_versions/v59_realtime_trial01_review_v61.mp4): H.264, 1280×720, 30 FPS, 2,449 frames, 81.633333 seconds, 10,488,224 bytes. SHA-256: `03ade05cdc1f51e9c75650cb686f85dcfed6d53e8271ab3a9e6832814f8acc1a`.

Full decode and local SHA verification pass. All 2,449 frame timestamps, state selections and non-image metadata match the original render. First/middle/last and three frames around the 81-second pause were visually checked; the whole robot, stairs and corner remain readable. Separate all-frame screening finds no near-uniform scene-area frame (minimum gray spatial standard deviation 9.1393, threshold 1.0). This screen supplements the six visual samples; it is not a claim of manual inspection of every frame.

The HUD's local **26.68 Hz** denotes attempts; the report's **26.43 Hz** denotes successful plans. The original v59 camera's ceiling occlusion and v60's cropped rear legs remain recorded as failed display attempts on gpu5070ti. Their MP4s were not retained locally after verifying the final replacement and remote originals.

[Full provenance and regeneration](REVIEW_VIDEO.json), [local verification](local_video_verification.json), [physical repair report](../v59/REPAIR_REPORT.md). Actual camera overrides are recorded in the hashed remote `heading_camera.json`; the reused frame manifest's camera fields describe the original renderer defaults. Raw states, frame arrays and failed renders remain remote.
