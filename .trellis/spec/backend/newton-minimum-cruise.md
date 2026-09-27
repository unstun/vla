# Minimum planned cruise speed

## 1. Scope

Local Newton/SCAN v7 adds Dr Sun's 0.6 m/s **planned horizontal cruise** minimum.
This is not an unconditional lower bound on actual body velocity, acceleration,
braking, short stop-to-stop moves, in-place turning or stationary holds.

## 2. Signatures

- ROS double `manager.min_cruise_speed`: default `0.0` disables the contract;
  v7 Building and flat YAMLs select `0.6`.
- `measureMinimumCruise(UniformBspline curve, double minimum_speed,
  double acceleration, double jerk) -> CruiseSpeedReport`.
- `SCANPlannerManager::enforceMinimumCruise(UniformBspline &curve,
  vector<Eigen::Vector3d> &boundary, double &interval) -> bool`.

## 3. Contracts

The manager is the owner; never implement this by raising downstream Twist
values independently of the timed curve. Require a finite nonnegative minimum
no greater than the nominal maximum, with finite positive acceleration/jerk
parameters when enabled. Disabled mode does not change the curve.

Measure native cubic XY velocity and cumulative XY length at <=10 ms intervals.
Entry/exit distances reserve a symmetric acceleration transition from the actual
boundary speed to the requested minimum. For speed difference `dv`, nominal
acceleration `a` and jerk `j`, transition time is `dv/a + a/j` if `dv >= a*a/j`,
otherwise `2*sqrt(dv/j)`; distance is mean boundary/cruise speed times this time.
This reserves boundary distance; it does not newly enforce an actual jerk limit.
Zero eligible samples mean **no cruise was exercised**, never a cruise pass.

If the eligible portion is slow, reuse existing SCAN knot reallocation, hard
boundary-PVA fitting and refinement, at most three times. Each adjustment retains
the native upper feasibility gates. The normal final PVA, dynamic and complete
collision checks still run before publication. Failure rejects the candidate.
No speed floor can create observed free space or bypass a planner stop.

The previous feasibility tolerances remain unchanged. Nominal limits alone do
not describe the full old admission thresholds. Report sampled planned speed,
commanded/effective velocity and measured body velocity separately.

## 4. Validation and errors

| Condition | Required result |
|---|---|
| Disabled minimum | Byte-identical curve |
| Long constant 0.2 m/s curve | Below-minimum rejection |
| Long constant 0.65 m/s curve | Cruise accepted |
| Stationary or insufficient-distance move | No cruise samples; not proof of reaching 0.6 |
| Non-finite/negative parameter, invalid positive limits | Reject |
| Retiming violates upper dynamics, PVA or collision | Reject; do not publish slower cruise as a fallback |
| Missing native terminal result after a physical bound | Retain missing result; no fabricated driver/PD success |

## 5. Cases

The actual v3 `flat_3` curve has a sampled cruise minimum 0.598556 m/s.
`v7_retime_probe01` loads original measured flat clouds and the original floor
prior, then calls the actual native manager. Its result is 0.607834 m/s with
duration 6.296695 s instead of 6.654634 s; native boundary, dynamics and complete
collision checks pass. The original Building short continuation remains
byte-identical at the result level in two repeated v7 probes, including negatives.

`v7_speed_06_control01` passes two direct 0.6 m/s walks and three PD holds, but
measured forward speed after the first second averages about 0.566 m/s. This
does not establish a measured 0.6 m/s lower bound or navigation success.

## 6. Required checks

Compile the actual native library; run `versions/v7/test_minimum_cruise.cpp`
against original recorded curves and negative cases. Exercise actual native
retiming with original sensor/support inputs and independently check PVA,
dynamics and the full resulting curve. Keep physical startup failures separate
from speed-policy failures. Score **published** curves, not every optimizer
candidate that logged a successful intermediate speed check.

## 7. Wrong versus correct

Wrong: clamp every nonzero Twist to 0.6; call `samples=0, passed=1` a cruising
success; equate a 0.6 command with 0.6 measured motion.

Correct: constrain the planned travel interval, preserve ramps/stops and all
existing guards, then measure the physical result and report its remaining gaps.
