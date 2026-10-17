# Optimizer complete-curve contract

scan30 replaces the optimizer's two coarse prefix checks with the existing
complete curve helper already used by the manager. Both rebound and refinement
only accept Clear, retaining0.8s execution yaw,10,000-sample budget and all map
predicates. Rebound invalid/budget outcomes fail without collision restart;
actual Collision retains original early failure and bounded restart. The
manager's final PVA/dynamics/collision gates remain. Initial proxy guidance
failures are not unconditionally promoted to curve failure.

Seven actual-method fixtures cover free space, tail, exact endpoint, thin
Unknown region inside the original prefix, zero endpoint chord, sample budget,
and a narrow oracle around the recorded failed curve position/yaw. Both native
methods run with a solver and constraint-generation double. The old methods
fail six negative fixtures and pass free space; scan30 passes all seven on
local clang and pinned Foxy g++. Independent review finds no blocking issue.

Production changes are confined to optimizer.cpp. Read-only constraint counts
and control squared norms make existing retry behavior visible. An increase in
paired finite unit directions is not proof that the current curve conflict was
resolved. Full Foxy build and same-input real optimizer replays are pending.


Full Foxy build and462-file identity passed. Fresh-input replay completes with
56 checked seeds and zero moving publication. Native optimizer now rejects,
matching manager's full predicate. 168 complete checks and168 retry records
have constraint-count pairs[(0, 0)]; the first three attempts retain collision
time46.347717327670s and control squared norm21115.128579881224. Initial/retry
proxy-guidance search still fails during adjusted endpoint handling. The norm
is a summary, not a cryptographic identity proof.

Old accepted input still publishes one moving cubic; controls and knots remain
exactly equal to the previously accepted scan28 curve. Thus complete checking
preserves the positive case. Next diagnosis captures the actual failed guidance
endpoints without extra queries, then compares strict search on those same
endpoints in an independent pool after original optimizer failure. This can
separate endpoint-adjustment failure from inability to find a repair route.
