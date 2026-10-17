# Complete sampled spline interval

scan_24 adds a final publication gate after optimization, time refinement and
dynamic feasibility checks. The same helper covers the FSM's remaining active
trajectory interval. It includes both endpoints and uses relative B-spline time,
the original 0.8 s heading lookahead and measured-yaw fallback. The existing
collision rules, optimizer objectives, tolerances and Unknown blocking remain.

The helper validates dimensions, degree, finite values, knot order and every
reachable de Boor denominator before evaluation. Sampling is at most 0.01 s,
and tighter when the derivative control-point norm bound requires it to keep
center displacement at most half a voxel. Invalid clocks/curves and more than
10,000 samples fail closed. Expired time still checks the exact endpoint.
This is sampled collision coverage, not continuous rotating-footprint proof.

The frozen Foxy native fixture compiles the actual UniformBspline class and
passes tail-only/endpoint obstacles, nonzero and nonuniform knot domains,
high-speed sampling, expired and invalid time, stationary-yaw freshness and
malformed geometry cases. The full native build passes; 459 installed files
have identity SHA-256
`cf72039c31843a39953eedf2bb84ae705779ba76a5cea8521511314afb3f3dd6`.
An independent reviewer found no blocking issue.

`scan24_same_inputs/` preserves the unchanged no-moving-spline outcome on the
same recorded input. It does not exercise an accepted moving curve through
the final gate, so actual GridMap cost on such a curve remains unmeasured.
The native fixture's roughly 1.8 ms is not a runtime performance result. No
short-prefix probe code or threshold relaxation is included in scan_24.
