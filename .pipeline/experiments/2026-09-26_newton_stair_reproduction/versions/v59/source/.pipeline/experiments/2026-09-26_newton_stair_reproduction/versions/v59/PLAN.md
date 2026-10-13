# v59 shared trajectory time origin

Stage: experiment + analysis. Parent frozen v58; separate logical repair authorized by Dr Sun's "fix the prblem" after the post-70-second diagnosis. v49 remains excluded. v58 physics is blocked by another gpu5070ti evaluation, not a planner failure.

## Change boundary

A spline-derived initial PVA denotes a state at a particular time. Preserve that time as the replacement curve's origin through warm and native fallback solves. At receipt, initialize controller execution from elapsed time since that origin, instead of resetting a delayed curve to zero. Retain the existing incremental execution clock and heading/final-yaw freezing after receipt.

Only `planner_manager.{h,cpp}` and the receipt-time initialization in `closed_loop_controller.cpp` change. The original fixed-input PVA fit/check, full-curve occupancy/stair support, dynamics, minimum cruise, goal/yaw tolerances, control gains, cancellation/stop and recovery logic stay unchanged. No solve budget, abort deadline, new stop reason, forced speed floor or predicted future handover.

An origin is usable only for a valid, current old curve and a start PVA matching its requested sample. Odometry/initial/expired-curve restarts retain their existing completion-time origin. A new curve already elapsed at publication is invalid and cannot be published; it follows the existing planning-failure path, without a wall-time solve limit or stop-protocol change.

## Acceptance

1. Reproduce the receipt-reset error in the actual parent controller with delayed analytical curves; use 0/40/80/600 ms cases, including nonzero velocity and acceleration. At the same handover instant, corrected evaluation matches the original trajectory PVA to numerical precision for geometrically identical curves.
2. Native recorded-map replans with an 80 ms old sampled start retain the sample timestamp and all original PVA/dynamics/whole-curve checks. Test graph fallback as well as warm initialization. Compare the new curve and previous curve at the same actual handover time and report P/V/A differences (newly optimized geometry may differ after their common C2 boundary).
3. Verify receipt behavior, subsequent incremental phase, heading freeze/resume, emergency stop, cancellation and new-goal behavior; keep all inherited native/cache/goal/warm/freshness/physical-floor/backend checks.
4. Bounded 90 s physical validation on gpu5070ti once its required resources are available. Measure complete-window successful Hz and tails, command cadence/speed, physical tracking, pauses and actual common-time curve transitions. Target: remove the systematic timestamp backstep; reduce the late median along-track error relative to v57's approximately one meter. Full-route and sustained 30 Hz remain separate gates.
5. External build/test/run supervisors are resource bounds, not planner deadlines. Keep heavy records/builds remote; compact results/provenance/plots and review MP4 only return locally.
