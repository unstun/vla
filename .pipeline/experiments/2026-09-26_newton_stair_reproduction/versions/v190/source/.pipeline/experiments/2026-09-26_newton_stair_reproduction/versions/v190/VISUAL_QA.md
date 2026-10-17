# v190 review video QA

Inspected decoded frames from `v189_mac_full_attempt01.mp4`:
- Frame `0` (video `00.00s`, native `00.00s`): original physical time 0 factory startup (`Startup: initial_state | recorded simulation time`).
- Frame `826` (video `27.53s`, native `27.00s`): first corner turn (`1.099s` stop pause).
- Frame `2481` (video `82.70s`, native `65.00s`): 180-degree pillar U-turn recovery with active cyan local SCAN curve `#1453` (`latest solve 69.58 ms`) and orange global PCT path.
- Frame `4430` (video `147.67s`, native `119.99s`): upper landing turn with active cyan local SCAN curve `#2588` (`latest solve 13.08 ms`) and orange global PCT path.
- Frame `6350` (video `211.67s`, native `175.52s`): top-floor goal arrival (`requested_goal_reached` at `175.495s`, yaw error `0.1155 rad`).
- Frame `6707` (video `223.57s`, native `187.66s`): final `FIXED_STAND` frame (`Navigation: arrived (Nav2 action status 4)`), showing the final held body yaw after the `175.5s-184.0s` zero-command RL stepping drift (`0.377481 rad > 0.25 rad` limit).

The full video is `223.600s` (`6,708` frames at `30 fps`, `1280x720`). All frame-source indices, startup simulation timestamps, navigation wall timestamps, curve causality (`4,744` visible curve frames) and full MP4 decoding passed. It replays the actual `v189_mac_full_attempt01` run without any new physics steps, interpolation, stitching or skipped pauses.

Regular local MP4: `.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v190/delivered/v189_mac_full_attempt01.mp4`, `17,515,391` bytes, SHA-256 `3ed8e52d98c3ffd16ce55cb5fe3ed19b2949fd02cb330c32d8063a7fbb7f51e9`.
Remote archive copy: `gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v189_20261013/v189_mac_full_attempt01_review.mp4`.
This display review does not promote `v189_mac_full_attempt01` to full-route acceptance; `full_route_verification.json` remains `passed: false` due to final held yaw error `0.377481 rad > 0.25 rad`.
