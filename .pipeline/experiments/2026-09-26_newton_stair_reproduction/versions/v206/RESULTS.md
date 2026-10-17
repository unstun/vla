# v206 — component checks passed on gpu5070ti

All four reviewed command/interface changes are implemented. Frozen v204 and
its v205 review video remain unchanged. No full-route or physical trial ran.

## Implemented behavior

1. Same-goal geometry refresh updates revision and route only. It retains solver
   generation, pending completed result and trajectory-bound execution feedback.
   New goal/cancel still reject late results; an actual concurrent worker test
   publishes successfully across an ordinary refresh.
2. Translation attenuates smoothly between heading errors 0.6 and 1.0 rad;
   turn-in-place enters at 1.0 and exits at 0.6. Spline/route refresh retains the
   turn state. Existing phase freeze continues during turn-in-place.
3. One Tracker output history limits x/y acceleration/deceleration to 1.0/2.0
   m/s^2 and yaw to 2.0/3.0 rad/s^2. Normal outer-controller goal braking uses the
   same history. A new spline never resets the limiter clock. Emergency/cancel,
   missing valid tracking input, or clock discontinuity can immediately zero.
4. A finished local spline with a remaining unattenuated XY command below 0.20
   m/s brakes exactly to zero and cannot restart from endpoint noise. A new native
   spline resumes it. It never claims final arrival or clears the route. Active
   short/reverse corrections remain possible; original 2 cm capture and final
   XYZ/yaw/2 s PD hold remain unchanged. This policy is not a universal V12 dead-
   zone claim. Transient acceleration/deceleration may cross the low-speed band.

## Direct verification

- Linux x86_64 gpu5070ti: 14 packages built successfully.
- 117 distinct native/ROS test cases passed; zero failures/errors/skips. Colcon's
  134 total also counts the 17 CTest wrappers, so it is not 134 distinct cases.
- One lightweight host launch-assembly check passed (fake child processes).
- Tests cover refresh/solver overlap, retained pending output, new-goal/cancel
  rejection, yaw hysteresis/threshold oscillation, per-axis acceleration and sign
  reversal, a new spline every tick, exact stop, active small/reverse corrections,
  emergency reset and actual Controller terminal braking plus physical hold.
- Existing fixed PCT, 28-request route oracle, BT retry/typed terminal timeout,
  static terrain/support and mission lifecycle regressions passed unchanged.
- Straight-path phase and settled-command parity retains a 300-sample reference.
  The old full-command heading parity is intentionally superseded by the new
  behavior checks; no claim of unchanged heading or ramp policy is made.
- 300 source files and returned evidence hashes verified. All changes in the
  composed source are inside scan_nav2_controller. PCT, SCAN core geometry,
  optimizer/support, 1 Hz tree and ordinary retry sources remain byte-identical.

The first run had one test-fixture failure: a helper advanced simulated time
1.33 s after the last stand sample, exceeding its unchanged 250 ms validity.
The test now checks the immediate refresh without that advance. The old failure
and passing repair records are retained under verification/attempt01 and attempt02.
No production freshness or completion criterion was relaxed.

## Claim boundary

These are build and fixed-input/component results, not physical acceptance.
v206's route duration, tracking error and RL/PD transitions have not been
measured in Newton. The last full-route evidence remains v204 attempt01.
