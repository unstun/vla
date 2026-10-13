# v187: bounded terminal correction fails into existing Nav2 recovery

Stage: experiment and analysis. Semantic baseline: v177. Binary underlay: v186.
Preserve rejected v185/v186 sources and all outcomes. v186 still produced a
5.477s terminal crawl despite its measured-progress watcher: millimetres of
motion can renew that watcher. Its full-route result is2/5. The unchanged v177
06-10 control is being run separately; do not interrupt it for another build.

One controller behavior change from v177: when the accepted curve has expired,
remaining XY error is below5cm, and its nonzero horizontal correction command
is below0.1m/s, allow at most1.5s of uninterrupted correction for that curve.
Then publish zero, revoke that exact owner and throw a FollowPath failure
through the existing `stopLocked` path with reason
`scan_terminal_correction_timeout`. Existing Nav2 behavior waits for measured
stop before replacing the owner and replans from its normal measured-state
path. This is failed tracking, not successful arrival or a local completion
latch. Ordinary2cm capture remains exactly the v177 behavior, including later
reacquisition if the body moves outside it. There is no relaxed tolerance or
progress-based renewal. New curves, zero correction, leaving the terminal
region, mission-yaw alignment and heading-only rotation reset the timer.

This uses the Nav2 progress-checker *failure -> recovery* pattern rather than
transplanting its mission-goal XY latch into local trajectory completion.
The1.5s/5cm/0.1m/s thresholds belong to this bounded experiment, not upstream
numeric defaults or a claim about training limits. Do not extend this timeout
to ordinary cruise or global goal checking.

No RL, observation, stance, gains, physics, map, start, goal tolerances,
collision/PVA/freshness gates, retry counts or planner geometry changes.
Verify baseline-default parity, recorded4.9246cm inward command, no early
failure at1.4s, failure at1.6s, ordinary2cm stop without latching, new-curve
reset, cancellation/emergency priority and no timeout outside the terminal
region. Add an actual loaded-plugin regression asserting PlannerException,
exact-owner cancel, zero published command, and no false goal success.

After baseline control closes: rebuild controller/bridge, run controller and
profile tests plus host/loaded-graph checks, freeze source, verify remote hashes,
then five serial original-start Building/historical_full routes on admitted
gpu5070ti. Keep the unchanged prospective v185 endpoint criterion and full-route
verification; preserve every failure. No pooling or picking successful runs.
Local VLA is authoritative; heavy raw captures stay on gpu5070ti, with compact
results, actual RL input audits and hash provenance returned locally.
