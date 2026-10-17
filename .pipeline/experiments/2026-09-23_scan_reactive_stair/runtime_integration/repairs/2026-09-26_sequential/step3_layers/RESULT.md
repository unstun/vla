# Same-level terrain association

Status: **native regression, full-map audit, build and recorded-input replay
verified**. Navigation remains blocked; there is no accepted moving trajectory.

The old nearest-layer function used a 6.08 m upper floor when a neighboring
cell lacked the active 0.058 m lower floor. scan_23 changes only the terrain
scoring header: both passes require an unambiguous neighboring layer within
the existing 0.26 m step capability. If one is missing, the entire local
scoring window remains Unknown. The equality case still reaches the original
hard height rejection; no numeric threshold is relaxed.

The actual old header fails the new cross-floor counterexample. scan_23 passes
cross-floor, second-window propagation, layer ordering, ambiguity, missing
cell, invalid input and threshold boundary fixtures. The prior tall-box and
thin-wall cases now have an Unknown label and still fail the final collision
decision and terrain-return waiver.

The native audit covers all 86,775 records in the exact original selected PCT
payload (SHA-256 `71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577`).
No newly traversable record appears. All 14,282 Unsupported records become
Unknown; an additional 13 Flat and two Stair records become Unknown. An
independent reviewer recomputed the comparison and checked the one-header diff.

The pinned Foxy build passes and its 458-file install identity is
`ce85e47f660d1ca3a9fd1088117664b8d0a522e5143f3328c12742494608ca3a`.
The identical recorded input prefix still has zero checked seeds and zero
moving splines, with no search time-cap hit. This conservative semantic repair
cannot by itself recover a blocked path.

Evidence: `native_audit_v1/result.json`, both native support CSVs,
`scan23_same_inputs/`, and `RESULT.json`. `verify_layers.py` and
`../run_candidate_replay.py` provide fresh-directory reproduction entry points.
The next diagnostic is a separate first-search frontier trace, not another
threshold or input change.
