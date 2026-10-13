# Original Newton navigation repair through v114

Stage: experiment + analysis. One original-scene run now reaches the requested
goal and completes measured stop. This is not repeated-run reliability,
uninterrupted navigation, sustained30Hz acceptance, or Jetson validation.
The selected historical reference remains v48.

## Result

- Native source/runtime: frozen v114; display only: v115.
- Platform: actual Mac Newton physics plus local Linux ARM64 / Ubuntu20.04 /
  ROS2 Foxy Nav2. No real robot actuation or GPU job.
- Run: v114_mac_trial01_attempt01, original Building corner start and final goal,
  original factory/PD/V12 policy, geometric Mid360 rays and safety thresholds.
- Nav2 authoritative terminal: action status4, arrived. Final physical result:
  FINISHED, native arrival and measured PD hold. Applied-state hash copyback passes.
- Measured path26.551m; navigation RTF0.999965; no dropped physics steps or fall.
- Final body(2.068587,-2.927243,4.819465)m. XY error0.128538m and Z error0.013565m,
  within unchanged0.25m/0.20m tolerances. Independent final11 measured samples
  span0.999451s, maximum speed0.000541m/s and angular speed0.000573rad/s.
- Two protected route stops and Nav2 retries remain: body timestamp29.984ms ahead
  of the controller clock at sim35.942s; observation age254.860ms at sim43.463s.
  The actual final goal stop is at approximately48.8s and the task succeeds at50.1s;
  later stationary frames are the final measured hold, not a navigation stall.
- Whole recorded navigation-window successful replanning17.984Hz, max round
 128.411ms. The window includes final holding. Sustained30Hz is not validated.

## Repair and evidence

The original native scheduling blocked real ROS-clock updates while the planner
manually drained newer body messages. v100 isolated the real clock callback;
v101 admitted original body samples only when their source time became eligible.
v102 retained the valid current-curve safety check during replanning. v103-v104
fixed superseded output tickets and the demonstrated Foxy executor cancel-before-
spin shutdown race. v105-v106 corrected launcher qualification and removed Mac
bind-mount audit I/O from the applied-command acknowledgement hot path, preserving
its100ms deadline. v107 admitted exact curve/proof pairs atomically; v108 diagnosed
source ages. v109 increased the mapper scheduling cap to100Hz without fabricating
observations. v110 attached the real final native proof to each new curve.

v112 isolated native mapping CPU work on268 actually captured moving scans.
v113 optimized equivalent inflation columns: every per-frame map hash and14
sliding-boundary hashes remain identical; paired total CPU time fell about43%.
Its physical run still failed3.70m short of goal on delayed periodic proof.

v114 gives the Nav2 controller its own actual native full remaining-curve check,
using the executing tracker phase, a pinned immutable map revision, independent
query caches and the original controller body pose/clock. Native negative safety,
emergency and cancel messages still revoke output. Positive native timer messages
cannot replace the independently checked proof. Original body/proof100ms and
observation250ms limits remain. Publishing rechecks the original body time,
including validation work elapsed after compute began.

Validation: six affected native packages rebuilt over the verified14-package v102
underlay;34 colcon entries/31 GTest cases pass;27 actual native queries agree with
the original map; map hashes unchanged; future/stale body, wrong frame, invalid
rotation, stale observation and out-of-map curve reject. Separate clock, immutable
publication pinning, writer fault propagation and subsequent writer progress pass.
The existing actual native publication/replan/emergency/wait/stale probes pass.
Exact runtime receipt verifies2657 source/install/dependency files.

## Review and next boundary

Video: output/2026-09-27_lite3_versions/v114_original_corner_arrived_review_v115.mp4
(54.833s,1645frames,1280x720,30FPS). It replays recorded physical states at original
wall1:1 timing without interpolation or a new physics run. Full decode and first/
middle/final visual inspection pass. The final arrived status is visible. PCT
route overlay is recorded; native SCAN spline overlay was not captured.
Video SHA256:31fb6d21061bba2525933b8e5550ddc7d8e395e2fd53f1facfd3877a3b61d575.

The remaining simulation work is repeatability and the two measured source-age
stops, with unchanged validity gates. Jetson access is unavailable today per
Dr Sun; Foxy/Ubuntu20.04 receive-only startup remains pending. Do not promote
this result to real-robot navigation or main30Hz/continuity acceptance.

Local files and the runtime are retained for continuation. Bulk evidence archive
verification is recorded separately in STORAGE.json. The archive contains native
runtime files, raw successes and failures; the Docker execution image itself is
retained locally and is not included. No temporary roots were deleted.
