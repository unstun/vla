# v190: display-only review video of v189_mac_full_attempt01

Stage: experiment + analysis. Display-only version; parent `v189`, display
parent `v178`, physical source `v189_mac_full_attempt01`. Preserve the recorded
status of `v189_mac_full_attempt01`: Nav2 reported arrival (`requested_goal_reached`
at `175.495 s` with `0.1155 rad` yaw error), 20/20 measured-stop replacement
proofs and state copyback passed, while the final held yaw after the subsequent
8.5 s zero-command RL stepping drifted to `-2.238823 rad` (`0.377481 rad > 0.25 rad`),
so `full_route_verification.passed` remains `false`.

Preserve original physical frame 0, factory PD startup, complete route, every
pause and recovery, and terminal hold. No interpolation, stitching, resetting,
prefix removal or acceleration. Startup uses recorded simulation timestamps;
navigation uses original wall timestamps at 1:1. Cyan is the controller-admitted
local SCAN curve; orange is the global PCT reference. Solve timing shows only
the latest completed solve available at that frame, including failures.

Construct the pinned CPU model on Mac ARM64 (`Darwin/arm64` Cocoa invisible
ViewerGL window) and execute zero physics steps. Verify source hashes before and
after rendering, all 6,708 frame indices and causality, full MP4 decoding, and
beginning/middle/corner/end visual frames. Deliver the regular MP4 to
`versions/v190/delivered/v189_mac_full_attempt01.mp4` and archive the remote
copy to `gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v189_20261013/`.
