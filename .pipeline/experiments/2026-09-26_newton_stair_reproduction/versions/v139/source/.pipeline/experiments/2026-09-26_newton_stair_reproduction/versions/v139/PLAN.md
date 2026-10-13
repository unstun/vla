# v139: feed full-curve footprint collisions back to rebound optimization

Return to frozen v137; v138 all-heading local veto is rejected (all 3 pilots
blocked at start). Keep the v135 static global map and original v137 local mask.
The v137 third failure repeatedly smooths into a footprint forbidden by the
controller's 0.8 s lookahead, while optimizer tangent/partial checks miss it.

Add a bounded fallback after the optimizer's ordinary successful solve: use the
existing full-curve checker and controller heading. For a collision, look for a
nearby same-height free footprint and feed a direction constraint to the four
contributing cubic controls, weighted by their basis influence. Preserve fixed
endpoint controls. Reuse the existing rebound cost, weight escalation and three
restart bound; original final feasibility, minimum-cruise, boundary-PVA, current
map, publication and stop checks remain authoritative. A witness is an optimizer
hint, never a command or free-space grant. No map/safety threshold changes.

Test the recorded failed seed on both installed native versions before freezing.
Then exactly 3 fresh pilots; only 3/3 arrivals/no falls permits the fixed six-per-
arm comparison (baseline nativev137, candidatev139). All heavy work gpu5070ti.

Build01 still rejects the recorded case: later minimum-cruise refinement can
reintroduce the collision. Preserve its source/build/probe results. Build02 also
feeds final post-refinement collisions into that optimizer, bounded to two
additional complete attempts. Each attempt retains original boundary state,
execution epoch, feasibility, cruise and final publication gates. Its workspace
is recovery_v139_02; the original recovery_v139 is not overwritten.
