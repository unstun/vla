# v249 — native support association repair

Frozen parent: v247. Stage: experiment + analysis; zero physics steps.

The installed baseline optimizer completed all 11 routable first attempts.
Rejection occurred afterwards in support projection:10
`pct_support_height_missing_surface`, 1(A03)
`pct_support_height_invalid_layer`; B09 failed graph search independently.
PCT truncation/canonical-cell disagreement and missing intermediate slice
aliases hid floors still present in the native raw/scored support snapshot.
Mutable trial height hints and legacy unconstrained HeightSmoother could then
spread a wrong-storey association. A03 / R12 were not missing real ground.

Physical mode now queries actual continuous native floors within the original
height band, uses deterministic reference heights, and recomputes output
heights without that legacy smoother. It preserves final static admission.
All 11 routable height projections pass, but this alone does not repair the
remaining oriented gap refusals. Do not call projection success admission.

Six CTest targets/42 cases pass; source/build inventories are frozen. Full
qualification belongs to composed v251, not this intermediate version.
See the [combined audit](../../audits/2026-10-18_v249_generic_mechanism_repairs/RESULTS.md).
