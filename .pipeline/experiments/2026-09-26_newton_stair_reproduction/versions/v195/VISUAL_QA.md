# v195 review video visual QA

Stage: experiment + analysis; display review only. Physical parent and native
implementation are v194; display parent is v193. The source is the one completed
v194_mac_full_attempt01: FINISHED, route_arrived=true,
full_route_verification.passed=true and final_pd_hold=true. No new physical trial
or physics step was executed.

Inspected all ten decoded MP4 samples in the contact sheet, individual decoded
frames 898, 2243 and 4124 at full resolution, and the renderer's original first
and midpoint samples. The close camera retains the robot and building. Text is
legible at the delivered 1280 x 720 resolution, with no blank samples or missing
robot mesh. Original geometry/body occlusion can hide a short selected local
curve, as at frame 2243; no path coordinates were changed to force visibility.

| Frame | Video time (s) | Physics time (s) | Observation |
|---|---:|---:|---|
| 0 | 0.000 | 0.000 | Original physical frame 0; initial_state; no route or curve |
| 120 | 4.000 | 4.000 | Factory zero-return posture retained |
| 301 | 10.033 | 10.000 | Factory standing posture before navigation |
| 898 | 29.933 | 30.015 | Landing/corridor turn; cyan SCAN #475 and orange PCT visible |
| 1950 | 65.000 | 64.296 | Beginning of the recorded pillar pause; orange route, no active cyan |
| 2243 | 74.767 | 74.471 | Near the end of the same pause; #1359 selected but its short curve is occluded by the robot |
| 2548 | 84.933 | 85.005 | Later corridor; cyan SCAN #1659 and orange PCT visible |
| 3219 | 107.300 | 105.993 | Upper stair approach; cyan SCAN #2297 and orange PCT visible |
| 4018 | 133.933 | 134.003 | Arrival caption on upper landing; no active cyan |
| 4124 | 137.467 | 137.528 | Final source index 6462; arrived (nav2_arrived); FIXED_STAND with no active cyan |

Decoded samples, per-frame metadata and SHA-256 values are in
[returned/visual_qa/samples.json](returned/visual_qa/samples.json); see the
[contact sheet](returned/visual_qa/contact_sheet.jpg). The extraction script and
exact FFmpeg frame-selection command are retained beside the samples.

The regular delivered MP4 is 1280 x 720, 30 fps, 4,125 frames,
137.500000 s: 332 startup frames and
3,793 navigation frames. Startup follows original simulation
timestamps; navigation follows original wall timestamps at 1:1. All source
indices, first/last state coverage, curve/route/solve causality and full decoding
passed. There is no interpolation, stitching, removed pause or speedup. The
original 10.194397 s physics pause near the pillar is retained. The ceiling grid
includes the exact final physical state at 137.5282745361328 s.

All 10 overlay tests and 4 timeline tests passed. The overlay/timeline code and
tests are byte-identical to v193. Cyan was selected for
3,242 frames, and orange for 3,757
frames; these counts describe causal selection, not guaranteed pixel visibility.
The original Option B direct Bspline/Twist stream has no P2B admission identities.

Final navigation text is exactly `arrived (nav2_arrived)`. The physical state is
FIXED_STAND, with zero command and policy_owns_joints=false. The last retained
normal spline #3005 ended at 134.17977532648638 s;
the last recorded zero direct command is
4.646917318 s old on the wall clock and
4.652709961 s old on the simulation clock.
The verifier checks these exact causal reasons for terminal trajectory_id=null.
The route and outcome checks passed; metrics.json's separate
full_qualification=false is preserved in the receipt instead of silently rewritten.
This review does not establish repeated reliability, sustained 30 Hz or broader
navigation acceptance.

All 12 protected trees matched every file SHA-256/size, symlink target, directory
entry, mode and modification time, with zero additions, removals or changes.
This includes frozen v189 through v194, recovery_v176, recovery_v189,
recovery_v191, recovery_v194, and both v192/v194 complete trial directories.
See [comparison](returned/protected_after.json).

One initial display attempt was explicitly stopped after detecting that an added
checker assertion confused the Retina framebuffer (2560 x 1440) with the encoded
MP4 (1280 x 720). Its partial output and logs are retained; only the assertion was
corrected to inspect the encoded stream, then run_mac.py completed a fresh full
render and verification. See [attempt record](returned/framebuffer_check_attempt01/resolution.json).
The successful execution log is [returned/run_mac.log](returned/run_mac.log).

Regular local file: `delivered/v194_mac_full_attempt01.mp4`,
13,030,771 bytes. SHA-256:
`d3f6ea4caae09a9f607428061362581fbabdffb44ecb2e4fa45431a0176d61b4`.
Remote archive:
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v194_20261014/v194_mac_full_attempt01.mp4`.
Remote SHA-256 and size match; see [remote proof](returned/remote_video_verification.json).
