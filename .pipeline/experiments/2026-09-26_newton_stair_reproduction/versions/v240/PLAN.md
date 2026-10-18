# v240: keep search snapshot while delivering queued inputs

Parent v239 is rejected: its real-clock approach has no emergency message but
an expired active curve leaves a0.184561s gap. Repeated map-change cancellations
cannot be promoted as continuous planning. Preserve its source/results.

Keep the20ms ordered input drain from v239, but use a new GridMap overload to
enqueue paired scans and apply due body messages without adopting a completed
map inside the search. In asynchronous mode the search keeps its immutable
read snapshot; the background mapper continues. The original caller refresh
and final publication lease adopt and fully validate the newest completed map.
Synchronous cloud/origin changes still abort the old search; stale evidence
still rejects with original0.35s/0.1s limits and200ms total search budget.

Changes: grid_map.h, grid_map.cpp and dyn_a_star.cpp. Preserve the old2-argument
refresh ABI and class layout. No RL, start/goal,0.35m guard,0.1s scan, dynamic,
PVA/epoch, minimum translation, collision, support or terminal-rule changes.

Rebuild plan_env and all static AStar/B-spline consumers. Require native tests,
141-point recorded control, real-clock approach repeats and live stair control
to show no emergency and no active-curve expiry gap. Measured body motion still
comes from v237; only a separately authorized new physics run can establish
changed actual speed/stance/arrival/PD or produce a new comparison video.
