# Reference target proposals and bounded stoppable prefixes

This is a separate planning-policy experiment after scan32. Its complete
stair segment still reaches the original rebound bound despite valid repair
anchors; no collision or iteration threshold changes are proposed.

For REFERENCE_PATH only, retain the admitted global curve, goal, full duration
and route identity. The occupied-goal scan produces a current free endpoint
upper bound (frontier time), not a replacement global goal or proof that the
prefix is reachable. Refresh it for each local proposal. Projection, horizon
selection and free target adjustment share this same duration bound. Reference
free means occupancy exactly zero, including at the final route point.

Local target time is a proposal until complete reboundReplan succeeds. Commit
the actual adjusted time only on success; all failures preserve the last
successful window endpoint. Do not force monotonicity: shorter successful
windows can reduce this marker. It is not measured execution progress.

Try the original local target first. If it fails, consider at most three
additional forward route times by halving the interval from the projected
start to the failed selected time. These are proposals on the same route,
with original occupancy precheck and at least the manager's existing 0.2 m
start separation. Additional prefixes request zero terminal velocity; full
hard PVA, dynamics and sampled collision gates must pass before publication.

The three additional proposals form one shared budget across the existing
three reference initialization attempts in planFromCurrentTraj. Do not multiply
the budget into twelve manager calls. GEN_NEW_TRAJ has its own per-round three
proposal budget. Existing primary initialization attempt order remains; bound
counts do not establish a hard wall-clock guarantee.

A successful partial window has selected_time < full global duration. The
existing expiry transition therefore requests replan while retaining the
global goal. No proposal/frontier/failure may mark route arrival or publish a
trajectory. Non-reference occupied-goal behavior remains legacy.

Native source tests will cover goal/duration preservation, adjusted-time commit,
all-failure rollback, prefix zero terminal velocity, shared retry budget,
Unknown/no-frontier/near-goal rejection, frontier refresh and partial expiry.
Planner/ROS boundaries in these tests are doubles. Same-input real optimizer
replay is required before any live candidate; actual tracking and timing remain
separate gates.
