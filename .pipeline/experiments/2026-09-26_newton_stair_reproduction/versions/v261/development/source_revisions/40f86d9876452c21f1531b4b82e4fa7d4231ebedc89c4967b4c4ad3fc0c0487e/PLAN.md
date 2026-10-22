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

## Performance qualification and generic position-to-pose fallback

The diagnostic reverse floor-only distance lower bound reduced A04 from5.23s
to5.03s; it was insufficient and was removed. Its source and passing consistency
test remain in development/source_revisions, not the selected candidate.

Reuse native PCT's position search first, with exactly checked pose connections
and the same ENV225 curve objective. Recheck the complete actual heading chain
before accepting this candidate. If a position state cannot retain the incoming
heading needed for a valid connection, fall back to the existing16-heading
search. Both paths preserve actual endpoint XYZ/yaw, share hard geometry and
soft costs, pass the same GPMP boundary anchoring and full static review. No
coordinate condition, endpoint snap or scene rule chooses the search mode. This
is feasible-path search; no global optimum claim is made for merged position
states. A regression requires finite actual heading checks and forces complete
refusal when the pose callback rejects every edge.
