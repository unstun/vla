# v206 — route continuity and bounded velocity commands

Navigation parent: frozen v204; v205 is its unchanged-physics video release.
This is an explicitly authorized tracking behavior change, not another behavior-
preserving architecture extraction. No Trellis task is created for this session.

## Change boundary

- MotionExchange uses generation for goal/cancel lifetime and revision for normal
  same-goal geometry refresh. Preserve completed output and execution feedback
  across ordinary refreshes, including a solve crossing that refresh.
- TrackingNode smoothly attenuates translation with heading error and retains
  turn-in-place hysteresis across spline replacement (enter 1.0, exit 0.6 rad).
- One dt-based command limiter owns x/y translation and yaw, including the outer
  controller's normal final brake. Acceleration/deceleration defaults are
  1.0/2.0 m/s^2 and 2.0/3.0 rad/s^2. The command clock is independent of spline
  receipt. Emergency, cancellation and absent-valid-trajectory stops remain zero.
- Retain the original 2 cm local capture and final XYZ/yaw/physical-hold tests.
  Once a local spline has expired and only a sub-0.20 m/s correction remains,
  brake that spline to zero and await the next native spline; this is NOT goal
  completion. A new spline can resume tracking. Active short/reverse correction
  is not cut off simply because its speed is small. Ramps may cross the low-speed
  interval; a stopped expired spline must not restart due to position noise.
  Final position/yaw convergence also reaches exact zero in finite time.

The 0.20 threshold is an explicit expired-spline command policy, not a proven
universal V12 training dead zone: the archived V12 configuration enabled dynamic
command resampling, while the 0.20 training clip is in the other branch.

Owned code is scan_nav2_controller (exchange, tracking, controller brake adapter,
configuration and regression tests), plus a versioned launch identity and docs.
PCT, SCAN geometry/optimizer/support, 1 Hz global refresh, the six ordinary
retries and typed non-retry stand timeout remain byte-identical to v204.

## Execution and acceptance

Local repository is the source of truth. Compose verified v204 sources locally,
overlay v206, hash every source file, transfer only that execution copy to
gpu5070ti, verify hashes before building, and build/test there. Return build
logs, native test XML, source/install identity and image digest locally.
No local compilation, full-route simulation, new training or robot operation.
Check refresh/solve overlap, goal/cancel rejection, yaw threshold oscillation,
all-axis slew bounds and sign reversal, spline replacement, clock reset,
emergency reset, expired-tail stop versus active short correction, actual plugin
terminal braking, original goal/retry tests and unchanged native geometry bytes.
Component checks do not establish physical route performance.
