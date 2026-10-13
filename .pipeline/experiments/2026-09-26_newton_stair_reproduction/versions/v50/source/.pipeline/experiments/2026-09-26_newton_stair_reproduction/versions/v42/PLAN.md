# v42: 1:1 bounded video recording

Parent v41. Actual physics and original control dt remain 1 ms / 20 ms. After construction, bind native solver time to a monotonic wall anchor and sleep only until each absolute physical deadline. No changed timestep, no dropped physics steps, no restamping stale poses. Log actual native time, step counts, wall time, lag and actual RTF. Keep all guards and the original Nav2-aligned goal contract. Use v39 local planning at selected 30 wall Hz, original v36 controller 30 wall Hz and global PCT 1 wall Hz. Observe actual command receipt intervals without changing commands.

Run plan: complete original Building and historical route, factory startup, no added actor. First recording is bounded to 120 seconds of native simulation (including startup). A bounded preview is not complete-route navigation validation. Time goal: mean RTF within 1 percent of 1.0 after startup; local solver budget 33.333 ms, actual frequency and skipped/overrun counts must be reported.

Expected artifacts: complete process/runtime logs, original sensor/pose/control evidence, physical video states, realtime pacing and frequency JSON, actual native install identity, local SHA-verified return, display-only 30 FPS timestamp-based replay.
