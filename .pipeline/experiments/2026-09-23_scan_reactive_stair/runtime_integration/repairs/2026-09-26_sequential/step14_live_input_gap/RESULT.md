# Fresh-input search diagnosis

The original fresh-input first search exhausts 1,315 reached nodes, checks only
two exact-goal connections within 0.10 m, and rejects both on Unknown support.
A post-failure diagnostic finds a clear 0.154980048606 m terminal edge at the
14th nearest reached node. The unchanged full segment predicate checks its
endpoints and interior, with body and clock both at 5.56999988 seconds.
`TERMINAL_RESULT.json` records the witness and raw log hash.

This demonstrates that the two-cell terminal candidate restriction excludes a
feasible edge under the existing sampled graph model. The diagnostic preserves
SEARCH_ERR and an empty result. It does not establish curve or live feasibility.

The separate live sensor-origin Unknown observation is not resolved here.
That cell is known in the full-history CPU replay, which still fails at the
terminal connection. Do not conflate the two effects or mark Unknown free.

Next: retain normal strict near-connector behavior; after queue exhaustion only,
check longer reached-node terminal edges ordered by existing path cost plus
connection length, under the same total 0.2-second acceptance budget. Require
native regression, source review, full Foxy build, identity and same fresh-input
replay before a live candidate. No occupancy or dynamic thresholds change.
