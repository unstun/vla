# v264 — Saved-output heading-protocol audit only

No planner/source changes, scored route calls, physics, endpoint substitutions
or gate relaxation. Preserve frozen v261/v262 and original52 outputs verbatim.
The old evaluator's local margin CSV uses0.1s heading lookahead, while the
installed native full-curve checker uses GridMap::collision_heading_lookahead_s
(0.8s). Reconstruct each saved published cubic from its original exact controls
and knots, with its own unchanged paired scan/body fixtures. First require the
0.1s replay to reproduce old samples/verdicts, then assess the same saved curve
using the runtime constant. Preserve both views, hashes and all case outcomes.
This is a protocol audit, not a new planning attempt or physical result.

Separately extract source-solid witnesses for every refused clean endpoint.
Compare immutable support verdict, exact padded SDF, original unpartitioned
SciPy oracle with/without conservative voxel padding, and the pre-score
original-mesh certificate. Do not remove padding or change hard admission.
Any proposed geometry-domain change requires an explicit reviewed boundary;
accelerator equivalence of the existing source/model is already frozen.
