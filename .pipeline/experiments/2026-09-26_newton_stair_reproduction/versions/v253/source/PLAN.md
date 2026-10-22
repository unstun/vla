# v253 — Continuous endpoint graph attachment

Parent frozen v251. Preserve actual start/goal XYZ and all original physics,
RL, 0.35 m support radius, 0.18 m offsets, 0.26 m legal floor transition,
ENV225 weights/0.15 m soft target, and 0.1 s scan deadline/period.

Ranked hypotheses: (1) rounded start attaches to a physically invalid virtual
centre; (2) the same lossy mechanism affects goal exits; (3) GPMP initial/goal
priors target the graph centres rather than requested continuous endpoints.
The recorded v252 A02 request and frozen v251 C++ no-route are the red witness.

Add two transient endpoint nodes, not endpoint motion. Each connects only to
its ordinary one-cell neighbouring grid centres, across the same legal native
floors. Every swept edge is checked at 0.025 m or finer, including its true
endpoint and planning heading. ENV225 scores those same coordinates. Search
results include the endpoints; GPMP priors use those positions and interpolated
boundary states retain them exactly. The existing dense height projection and
full static/SCAN review remain admission authorities. Legacy mode is unchanged.
No route identifiers, component labels, snapping, radius changes or recovery FSM.

Validate fractional starts/goals, reverse directions, actual unsupported
endpoints and cliffs, near-coincident requests, both GPMP orders, original unit
and 97 native regressions. Replay exact measured A02 request; run unchanged
12x5 matrix and H00. Require at least the previous 55 first-GPMP admissions,
without graph fallback in admitted routes. Freeze hashes before any physics.
Physical scope: one new A02 formal attempt on qualified code, with G07/R11
covered by the full offline matrix and their retained v252 physical controls.
Return the complete A02 recording, including a failed prefix if it fails.
