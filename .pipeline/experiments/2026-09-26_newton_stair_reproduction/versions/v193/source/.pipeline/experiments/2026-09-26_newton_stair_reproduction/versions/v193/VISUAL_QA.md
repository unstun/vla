# v193 review video visual QA

Stage: experiment + analysis; display review only. The complete recorded
v192_mac_full_attempt01 remains FAILED/nav2_failed, with no arrival or
full-route acceptance. No navigation, physics or frozen source was changed.

Inspected ten frames decoded from the delivered MP4, plus the renderer's
original first/middle samples. The close following camera retains the robot,
building and curve overlays. Captions are legible; the samples show no blank
frames or missing robot mesh. Original geometry can occlude small local curves
near the body; the overlay never invents a larger path to hide that fact.

| Frame | Video time (s) | Physics time (s) | Observation |
|---|---:|---:|---|
| 0 | 0.000 | 0.000 | Original physical frame 0, initial_state, no route/curve |
| 120 | 4.000 | 4.000 | Factory zero-return posture, original startup preserved |
| 301 | 10.033 | 10.000 | Factory standing posture before navigation |
| 997 | 33.233 | 29.995 | Landing corner, cyan SCAN and orange PCT |
| 1928 | 64.267 | 59.139 | Mid-run stair approach, cyan SCAN #1453 and orange PCT |
| 2113 | 70.433 | 65.296 | Beginning of recorded long pause by the pillar |
| 2221 | 74.033 | 68.694 | Same pause retained through its end, no timeline cut |
| 2842 | 94.733 | 85.984 | Later stair approach, cyan SCAN and orange PCT |
| 3504 | 116.800 | 106.993 | Upper-level turn, cyan SCAN and orange PCT |
| 3856 | 128.533 | 118.886 | Final source index 5533; failed (nav2_failed); no active cyan curve |

Decoded samples, SHA-256 values and per-frame event metadata are in
[returned/visual_qa/samples.json](returned/visual_qa/samples.json); see the
[contact sheet](returned/visual_qa/contact_sheet.jpg).

The delivered video is 1280 x 720, 30 fps, 3,857 frames, 128.566667 s:
332 startup frames and 3,525 navigation frames. Startup follows recorded
simulation time; navigation follows recorded wall time at 1:1. The terminal
grid extends by less than one frame to retain the exact final source state.
All 3,857 causal source indices were checked; physical frame 0 and the final
118.88629150390625 s state are included, with no interpolation or stitching.
The source measured 72.57228851559466 m; no new physics steps were executed.

All ten overlay tests and four timeline tests passed. Full MP4 decoding passed.
Cyan was selected for 3,230 frames and orange for 3,482 frames. Every curve,
route and completed-solve timestamp was checked for causality against its
recorded source frame; terminal stale commands cannot retain cyan. This is
Option B direct Bspline/Twist evidence, without P2B admission claims.

The post-render protected inventory matched every SHA-256/size and symlink
entry in v189, v190, v191, v192, recovery_v176, recovery_v189, recovery_v191
and the complete original v192_mac_full_attempt01 folder, with zero additions,
removals or changes. See [comparison](returned/protected_after.json).

Regular local file: `delivered/v192_mac_full_attempt01.mp4`, 12,804,690 bytes.
SHA-256: `3e441643b5c42410bd21e73bbb2aad563ecde613fd7801fc4acdfe2a084956cd`.
Remote archive: `gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v192_20261014/v192_mac_full_attempt01.mp4`.
Remote SHA-256 and size match; see [remote proof](returned/remote_video_verification.json).
