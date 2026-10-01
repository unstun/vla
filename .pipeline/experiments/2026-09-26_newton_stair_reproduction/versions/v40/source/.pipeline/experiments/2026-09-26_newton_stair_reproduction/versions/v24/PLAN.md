# v24: distinguish the body reference from footprint support samples

Stage: experiment + analysis. Parent: v23. One terrain-query behavior change;
no FSM, geometry, map, speed, height-tolerance or step-limit change.

The real v23 30s body reference is [-5.295183, 4.905429, 0.482619]. Its original
selected center floor is 0.194552 m, within the existing 0.30 +/- 0.12 m height
contract. The front collision-cylinder center reaches the next tread at
0.330916 m. Treating that forward sample as a second body reference rejects
the actual straddling posture: apparent clearance 0.151703 m. All 154 front
and 99 rear raw occupied contributors are positively classified terrain.
No unclassified obstacle needs to be removed to expose this error.

Retain raw occupancy and map-boundary queries at the same original front/rear
XYZ. Validate body-center support with the existing height contract. Associate
each footprint sample with the nearest unambiguous original ground layer
within the existing strict step limit, then require its paired scored layer
to remain supported. Do not skip a closer Unknown/Unsupported layer in favor
of a farther supported one. Keep unknown, stale, excessive-step, mismatched
source, ambiguous-layer and all actual nonterrain occupancy rejection.

Only the support-height query uses its associated terrain elevation plus the
original clearance; robot position, planned curve and obstacle query do not
move. A direct legacy point query without a body reference keeps its old
behavior. The same rule must apply through AStar, optimization, publication
and safety checks.

Reuse the existing ETH-derived layer association and scored support. The
pinned ETH footprint source is an architectural reference, not a claim that
this local multi-floor adapter reproduces its ROS 1 implementation. Avoid
extrapolating the current body's pitch along an unobserved future trajectory.

Validate the actual v23 stopped-state continuation, older stopped states,
input/source guards, all eight original unmapped fixtures, and explicit closer
Unknown/Unsupported, ambiguous floors, exact/excessive step and center-height
negative cases. Report the existing mapped low-protrusion semantics separately.
Freeze before physical execution; a component pass is not physical acceptance.
