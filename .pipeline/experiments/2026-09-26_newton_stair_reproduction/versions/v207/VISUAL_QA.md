# v207 video delivery — v206 actual failed attempt

Displayed all 3,785 frames (126.1667 s), 1280x720 at30FPS. Startup uses original
simulation time; navigation uses causal original wall time, with no interpolation,
speedup, skipped pause or extra physics. The full decoder and every source-frame/
curve index passed. 10 overlay and4 timeline cases passed remotely.

Nine decoded frames were inspected: actual initial state, crouch, factory stand,
stair/route traversal, turn and final frame. The robot/materials are visible,
orange global route and cyan local curves are distinct. The final cyan curve is
inactive and the caption explicitly reads Navigation: failed (nav2_failed).
The final wait remains in the movie. This is not a completed-route acceptance.

Linux EGL reuses the v205 camera/material/timeline/overlay. An initial display
startup failed on the inherited Mac font path before any video frames; preserved
under video_v207_font_failure. The final source uses the previously used Linux
DejaVu font. No physical recording was repeated for rendering.

Video: delivered/v206_linux_full_attempt02.mp4
Bytes: 15656980
SHA-256: 6e67870293b3f2465f671e440122af840fa2d1c77168d30aec063e5fe36fa419

The final regular file was returned from gpu5070ti and matches its verified hash.
Frozen v204/v205/v206 source files are unchanged. The former review MP4 remains.
