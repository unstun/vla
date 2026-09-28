# v21 component results

Native build passed (65.727 s). Actual Linux sidecar publication has 125493
records and SHA f03b03c0b832bad2498c1823fd1c46e78ed3add1032f931571a202c208e430cf.
Three data tests and the prior three precision tests pass. The original selected
and tracking payloads are unchanged.

`v21_native_regression01` stopped at a test-precondition failure: the first
recorded stair scan had not granted positive terrain labels. It did not reach
its source-revocation assertion. The failed attempt is preserved. In
`v21_native_regression02`, the existing static mapped-ground first frame grants
17 labels; changing the valid source removes them, one later endpoint leaves
zero old grants, and nonterrain history remains intact. Five malformed layouts,
missing/wrong frame, both input timestamps and delivery order are rejected.
No production source changed between these attempts.

Old 66/67-scan continuations, v18 stopped state, and v19 actual GEN_NEW_TRAJ state
pass PVA and whole-curve checks. Accepted XY progress: 1.0384 / 1.3233 / 0.6090 /
0.3766 m. The v19 case passes twice with equal results. The initially selected
2.9746 m target is not the accepted displacement. Unknown, stale and no-progress
negative checks remain active.

All eight original unmapped case JSON outputs match their previous baseline,
including paths and sensor-staleness checks. The five mapped cases separately
expose a known-low-protrusion acceptance ambiguity; the old baseline already
permits many 13 cm platform overlaps. No universal independent-box-avoidance
claim is made. Physical trial `v21_building_route01` is the next gate.
