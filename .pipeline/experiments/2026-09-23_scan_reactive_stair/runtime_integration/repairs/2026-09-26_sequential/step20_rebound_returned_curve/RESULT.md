# Returned trial after an empty rebound repair

The scan31 observer preserves the original STOP_FOR_ERROR and manager failure.
Full Foxy build and 463-file identity pass. Fresh replay has zero moving output.
All recorded footprint clocks/body stamps equal 5.56999988 s. The 428 captured
stop-state control points equal the actual returned controls component for
component (maximum difference 0). This is the last callback trial, not a
solver-accepted solution: LBFGS rolls its local q back on cancellation, while
the wrapper returns cps_ from the last evaluated callback.

The returned trial still collides at 45.837742444453 s, earlier than the prior
46.347717 s collision. Native derivative limits pass using the unchanged
configured feasibility tolerance; maximum component acceleration is 0.67998,
not below the nominal 0.5. The failure is not explained by an otherwise-clear
returned curve being stopped by a proxy. No dynamic or safety rule is relaxed.

Observed failed segment is CP249→CP257 with seven interior controls. Its strict
repair route has two points equal to the original endpoints. All seven local
normal planes have route endpoints on the same side; both native-walk
reconstruction and complete route-edge enumeration find no intersection. Thus
this is not a missed crossing in the midpoint walk. Most control points have
folded beyond the short route; the original plane construction cannot generate
an anchor for them. Existing finite/zero-direction guards correctly fail.

GEOMETRY.json and RESULT.json retain the exact controls, paths, flags, counts,
full checks and scalar geometry. CSV extraction repairs only interleaved logger
records and verifies continuous control/sample/knot indices. Observed path
endpoints match captured segment columns. This observer did not emit explicit
per-path total counts; do not infer unrecorded discarded segments or map-query
history from these arrays.

Next limited candidate: only a segment with no legal geometric plane
intersection may use nearest points on its same-endpoint strict repair route.
Validate finite nonzero geometry and query each candidate under that control
point's own heading before using the original base-point ray and paired write.
Reject blocked/Unknown, mismatched, degenerate and zero-distance candidates.
Keep original intersection behavior, constraints, clearance cost, stop guard,
retry bounds and complete curve/PVA/dynamic gates. This is an experimental
constraint-generation repair, not evidence of a usable curve or physical motion.
