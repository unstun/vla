# v270 — Source-cap recall and native conformance

v269's512scene query comparison found3binary/4margin differences. Exact
diagnosis identifies open vertical faces1131,2225and2204. Disabling every
closed-volume label leaves the C++ result unchanged. Replacing only the
reference's exact projected-intersection prefilter with bounding-box recall
eliminates all4differences; original3Dhalfspaces, inputs and0.35mremain fixed.

This version fixes broad-phase candidate recall in the independent model and
reference. Actual finite3Dcap clipping remains authority. It also requires the
native self-floor shortcut to satisfy the existing projected-area predicate,
and the closed-object shortcut to have complete eligible upward caps. Tiny
open/closed source controls prevent over-aggressive material exclusion.

Keep every preceding source/model/failed query ledger. Require all14native
physical controls and the same512original scene queries without substitution
before integrating either planner. No planning, physics or baseline promotion.
