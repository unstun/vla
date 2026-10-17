# v230: mission-scoped local obstruction feedback

Parent frozen v229. Reuse the existing Header -> BT ComputePath trigger, native
immutable query view, CheckTraversability STATIC_AND_LIVE mode, RoutePolicy
context/cache, PCT rejection constraints, derived map/gradient rebuild and
bounded three-round repair. No new transport/session protocol or mapper.

At each managed createPlan, pull a bounded forward/local portion of the current
reference and outstanding witnesses. Native LIVE returns exact typed verdicts
from the unchanged two-cylinder query, with source fingerprints, observation
stamp and map revision. Only fresh StaticObstacle witnesses become directional,
height-associated constraints. Failures/unknown/outside/stale do not assert an
obstacle. Recheck the candidate after solving, including cached terminal/error
returns, before the existing full native static check and publication.

Memory binds to RoutePolicy mission plus session epoch and stable native source
IDs, independent of Path refresh. At most 128 witnesses, 384 queries, 3 m forward
reference radius; outstanding witness queries use actual provider coverage.
Two seconds steady-clock expiry is a planning-hint lifetime, not a live free-space
grant. Only a strictly newer Free at the exact retained pose/yaw clears it early;
unknown never clears. Source change/mission end or replacement clears memory.

Apply persistent constraints separately from per-call repairs. Reuse existing
A* oriented transition predicate and GPMP derived costs/gradients; final reference
and connector/rotation samples use the same pose-matching rule. Do not alter RL,
body/support thresholds, source freshness, goal, speed, retry budget or ongoing
SCAN trajectory. Formal physics acceptance remains a separate task.

Validate native LIVE/binary parity, explicit unknown handling, source/mission/
TTL/newer-Free rules, alternate actual PCT routes and blocked cache rejection;
retain nine-package regression and v229 Building/recorded-window gates. Return
compact source-bound evidence; no compilation cache is a research artifact.

A STATIC_ONLY solid verdict, when a provider supplies it, is expanded only by
explicit native checks of the four undirected graph headings (<=800 probes),
not by assuming every orientation blocked. Candidate retry budget remains three.
Per-call static repairs are rechecked by the authoritative native final query;
only persistent LIVE memory adds a separate final mask.
