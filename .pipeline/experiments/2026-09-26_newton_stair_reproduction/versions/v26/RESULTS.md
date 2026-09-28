# v26 physical outcome: configuration repaired, route incomplete

Real ROS runtime now sends both layer fields as null. Actual PCT has631 points,
~73.41m and correct final body height4.83125m. All three historical-profile gates
pass. Seven loader tests and six actual TCP/native chain controls passed.

`v26_historical_full01` failed before any physical child due to a relative Python
path in the supervisor command. The corrected absolute invocation is preserved
as `v26_historical_full02`. This version ran110.730774simseconds; one moving
curve was published, but net XY displacement was0.05615m and goal error11.7584m.
It was explicitly stopped diagnostically through the driver's SIGINT/cancel/
failed-finish flow after sustained no progress. It did not reach its time bound,
arrive or complete the route. Final PD standing occurred at the start area.

No command reconnects, protocol or IO errors. The original source, sensing,
copyback and stop checks are retained separately in the reviews. Local review
fails execution/arrival, and Building review returns passed=false. Do not infer
success from its process exit code0: that reviewer reports verdict in JSON.

Captured local safety/replan loops require a separate repair. A legal stationary
hold is checked as a moving curve; its zero tangent falls back to measured yaw,
which can become older than100ms while synchronous planning blocks callbacks.
This is distinct from the initial moving-curve stop and the v25 wall-clock gaps.
