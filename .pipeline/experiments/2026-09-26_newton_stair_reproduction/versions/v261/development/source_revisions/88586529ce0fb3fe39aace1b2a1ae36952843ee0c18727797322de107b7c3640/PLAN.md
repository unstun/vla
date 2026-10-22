# v261 — Continuous endpoint pose geometry

Parent v260. Keep real requested XYZ and start/goal yaw. Search endpoint connectors use the same native hard support/solid predicate over dense continuous pose interpolation; ordinary one-cell neighbours are retained. A finite Hermite endpoint curve can align the actual terminal tangent, and an actual-start in-place turn is accepted only after its full sweep is checked. No snap, coordinate exception, permanent state machine or new radius/step rule. Feed the connector and heading boundary into existing GPMP. Return optimized yaw alongside projected XYZ through an optional legacy-compatible RoutePolicy heading provider, rather than discarding it and inferring another orientation. Dense native whole-reference/SCAN checks remain final authority. Unit tests cover walls, real cliffs, arbitrary rotations, exact endpoints, both GPMP orders, reversed headings, nonfinite inputs and unconfigured legacy behavior.

## Reproduction-driven search correction

D07/S04 passed the initial connector change, but E03 still failed because a
position-only closed set discarded alternate arrivals with different headings.
Original-mesh witness search certifies E03/E02 reachable; native lattice pose
screening confirms valid neighbours, so this is not an endpoint relocation need.
Reuse PCT A* with an eight-heading physical pose state, a forward neighbour and
two checked heading turns. Real endpoints attach through fully checked geometric
pose connections. Preserve body headings in the raw reference; GPMP smooths its
translational projection and the complete output is checked again. Exact static
directed edge queries may be memoized until the map/constraints change. Legacy
position search stays available when no pose headings are requested. No new RL
policy, reverse execution contract, scene rule, endpoint snap or hard threshold.

## Open-space certificate and physical steering

The naive whole-map eight-heading prototype reached E03 but regressed cross-floor
planning to 16-21 seconds and did not reach E02. It is not an accepted result.
The current candidate uses 16 heading samples plus checked Hermite steering
primitives. In open cells, headings may merge only after BOTH native support and
solid geometry certify the entire continuous rotation free. An eight-disc cover
of the rotational envelope is a sufficient free proof, never a hard 0.53 m mask.
Unknown/near-boundary certificates fall back to distinct headings and exact
queries. Recover actual parent turns when reconstructing the pose path. This
merging preserves reachable exits, not a claim of globally minimum pose-turn
cost; every returned movement/turn still pays the same ENV225 objective and
receives full native static review. Reset all certificates/edge caches on any
map or repair/feedback constraint change. Preserve unmodified original geometry
queries and test every certified random Building pose at 256 headings.

GPMP receives original pose-search control knots, not the dense collision
samples; raw fallback keeps the exact validated steering curves. Real endpoints
and requested yaw remain unchanged. The final release still requires original52,
independent mesh-certified clean50 full native/SCAN gates, and latency acceptance.

## Performance qualification

A floor-only relaxed distance reduced A04 from5.23s to5.03s and was inadequate.
A position-first candidate also failed its complete pose-chain review on A04
and added6.69s before pose fallback; it was rejected. Both source revisions and
logs remain development evidence and are not selected implementations.

The candidate keeps one pose search and supplies a relaxed geometric distance
through real floor nodes, removing only nodes whose unavoidable central body
core already intersects a solid. The derived core radius sqrt(R*R-d*d) is
contained in the two-cylinder union at EVERY yaw. Its collision therefore proves
that no exact orientation can use that node. Obstacles, footprint constraints,
turn costs and ENV225 remain relaxed elsewhere in this distance graph. Include
every real forward/steering displacement with chord-length lower costs and the
actual goal attachments, so the graph distance remains a lower bound. Full
0.35m oriented queries and output checks are unchanged. Test every certified
core collision at256 Building headings, along with query-value equivalence and
primitive-wise lower-bound consistency. This is search acceleration, not an
additional hard safety mask or a new runtime acceptance rule.

## Exact query work elimination

Discard graph nodes only when the precomputed all-heading necessary body core
proves them unusable. Check pure edge cost before expensive collision work if
that exact cost cannot improve the target, with identical floating addition
association. Reuse adjacent ENV values without changing the integral. Dense
static support/gap arrays preserve source record ordering and shared rules;
70928queries are independently compared with frozen v260 typed results, gap
values/gradients and height associations.

A request-owned cylinder memo reuses exact signed-distance bounds at identical
Z or within a proved invariant floor-exemption class. Candidate-group identity
and analytic common/union exemption intervals establish that the relevant
source point set is unchanged; the capped cylinder SDF is then1-Lipschitz in
XYZ. Cache bins select candidates only and never quantize query coordinates. A proof on either side of zero avoids a KD query; uncertain
points still use the unchanged exact formula. A1e-9 guard declines certificates
near numerical boundaries, never changes physical admission. The immutable
field has no mutable shared memo; cache ownership retains its source and resets
per PCT request. Compare cached booleans with isolated frozenv256 over70928
poses and5000edges, while all original value/gradient/witness checks remain.
