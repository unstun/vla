# Curve position, heading and timing diagnosis

The scan_27 post-failure observer passed full Foxy build, 461-file install
identity and the same-input CPU replay. Initial and optimized curves first
fail at 2.33 seconds with rear WrongHeight. At the initial point, the nearest
seed edge is only 0.15233 mm away, but its heading differs by 42.78748 degrees.
Keeping the curve position and replacing only the heading changes occupied
to clear. Projecting to the seed edge while retaining the curve heading still
fails. All four footprint comparisons retain body stamp 5.00999989 and clock
5.01000000. This directly isolates heading at that point, not a large fitting
deviation or a moving pedestrian.

Scaling every initial knot by the native required ratio plus one ppm
(16.888221583092) keeps the centerline unchanged and changes fixed-0.8-second
preview heading. All 9,324 full-interval samples pass on the frozen map.
Native component velocity/acceleration bounds also pass. Duration becomes
93.222983 seconds. Start velocity error rises from 0.000003432 to
0.000524627 m/s; this is not a PVA-preserving initialization or accepted output.
The native ratio reported after a successful feasibility check is not a
required scale; its sqrt(2) value comes from the native sentinel initialization.

The original optimizer still fails and publishes no moving trajectory. The
diagnostic does not validate manager norm dynamics, physical yaw tracking,
future map coverage, replan timing or a 93-second motion. An independent source
review confirms that the complete curve gate and current controller share the
0.8-second desired-heading formula; changing only the checker to seed yaw would
make the checker disagree with execution.

Next isolate initialization timing: preserve measured/target PVA with explicit
boundary control points, fit internal points, and derive bounded time increases
from the original native limits before rebound optimization. Recheck all
original final gates. Account explicitly for any later refit that would soften
the boundary constraints. Do not adopt the diagnostic scaled curve as a fallback.
