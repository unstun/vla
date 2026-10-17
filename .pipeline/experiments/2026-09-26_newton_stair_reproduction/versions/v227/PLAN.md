# v227: canonical support-query cell identity

Parent v226. Use the already-qualified physical grid as the common support-cell
identity when navigation/scored metadata match and origins differ by near-integer
cell offsets (residual <= resolution*1e-5). Map the canonical key back into the
unchanged navigation/scored arrays. Other sources retain original indexing.

Pass explicit cell indices through body, associated-floor, both footprint and
final static/live support predicates and the floor diagnostic. Query XYZ,
source clouds, heights, scored labels, ETH adjacency, LiDAR classification,
unknown/history occupancy, support-gap masks and all tolerances remain unchanged.
The .35 m evidence-fill drop guard remains intact; it is not a blanket per-query
guard on every selected cell. No edge exception or recovery connector.

Reuse existing CollisionDecision and terrain cell cache with optional explicit
support-cell arguments. Do not realign decoders or rescore by physical-floor
height. Gate with boundary/source/height/occupancy regressions, original v217
recorded-query comparison, exact v224 WrongHeight witnesses, and actual installed
PCT final route admission plus independent native recheck.
