# v7: minimum planned cruise speed

Stage: experiment + analysis. Parent: immutable v6. Dr Sun requested a minimum
speed of 0.6 m/s after reviewing the Building trial. This version interprets it
as a minimum **planned horizontal cruise speed**, with acceleration, braking,
stationary hold and insufficient-distance moves explicitly outside cruise.
Actual body speed remains a separately measured tracking result.

## Change boundary

The existing nominal maximum is 1.0 m/s; it is not a minimum. Add one optional
`manager.min_cruise_speed` contract (default 0, selected 0.6). Check the native
optimized B-spline. If a sufficiently long trajectory cruises too slowly, reuse
SCAN's existing time reallocation, hard boundary-PVA refit and refinement; allow
at most three attempts. Every resulting curve must still pass the original
native dynamic, PVA and complete collision checks. Reject an infeasible speed
request instead of silently publishing a slower cruise or raising Twist values.

Cruise excludes boundary acceleration/braking distance calculated from the
requested speed, actual boundary speeds and the existing nominal acceleration
and jerk parameters. This is an explicit boundary envelope, not a new claim
that the old planner enforces jerk. Short windows have no cruise interval and
must be reported as such. Sample the curve at <= 10 ms for this contract, retain
the observed minimum and eligibility counts, and report sampling resolution.

Expected production paths: a small native `minimum_cruise.h` measurement helper,
manager declaration/implementation and two version-specific planner YAMLs.
The velocity controller, occupancy/support, route selection, PD/RL controls,
watchdogs and factory startup stay byte-identical. Retain all prior versions.

## Upstream reuse

Inspect the pinned Nav2 MPPI velocity-deadband critic and Regulated Pure Pursuit
minimum-speed/approach ordering. These distinguish travel preference from
approach and collision handling. They are surveyed references, not imported
controllers. Executable timing/refitting remains the existing SCAN implementation.
Record URLs, licenses and SHA-256 under `upstream_reference/`.

## Prospective checks

1. Preserve parent source/install identities, freeze v7 source/config/diff before
   native compilation or simulation.
2. Native checks must exercise the real cubic curve, not just a copied formula:
   default disabled parity; slow long cruise rejected/retimed; ordinary >=0.6
   cruise accepted; stationary/short segments identified; invalid/non-finite
   parameters rejected; velocity/acceleration/PVA checks still reject violations.
3. Reuse recorded accepted v3 curves and the actual v6 short continuation. A
   short-window exception is not a successful 0.6 m/s cruise.
4. Run the same bounded 12 m empty-floor physical condition and the original
   Building condition. Report planner speed separately from requested, effective
   policy commands and measured motion. Retain startup/communication failures.
5. Deliver recorded-state video with version and outcome, without time scaling.

The v6 Building trace contains three moving curves of approximately 0.571,
0.240 and 0.174 m (3D lengths), and emergency hold curves. Its first moving curve
is replaced after about 0.38 simulation seconds. Changing minimum cruise alone
does not establish that the existing obstacle/support stoppage is repaired.
