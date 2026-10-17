# Historical PCT route diagnosis (2026-10-17)

This is a recorded-input comparison. No new simulator steps or physics runs were executed. The latest steering asks whether a change made PCT hug boundaries and requires PCT itself to retain clearance.

## Direct findings

- All four initial references (v210, v212, v217, v219) contain 649 poses and have the identical pose/orientation geometry SHA-256 `d097a347be55aa59840ab0ba943ff145cbaecd116face2916a6c269ba0ae0509`. Path and pose headers are excluded from this geometry comparison.
- Compared 122 executed source entries (the PCT package and C++ planner/route adapter/policy) from the v206, v212, v217 and v219 build inventories: no differences. v210 executes the frozen v206 install; see versions/v210/launch.py.
- Hashed the actual v210/v217/v219 execution PCT bundles: all `f4f72f27b5330d6353a3d62f3e630dedf7d70c294a97d960ec0d6b0d549aa10d`. Terrain manifests and gap masks also match. No evidence of a recent map, inflation or PCT parameter change was found in this interval.
- The old imported A* source already contains `if (step_cost < 5) step_cost = 0.0`. This dead zone motivates a scoring improvement but cannot be presented as a new regression.
- v212 changes the BT from the 1 Hz RateController to PlanOnGoalChange. Archived route deliveries in the 45-55 s stair window: v210=8, v212=0, v217=4, v219=5. Repeated delivery is not necessarily new geometry: v217 has only 2 unique geometries in its entire capture, and v219 has 3, versus 97 in v210.
- The v217 reference recomputed at 48.095 s has the same sampled stair sections, to floating-point precision, as the successful v210 reference at 45.931 s. A different refresh time/starting state is therefore a stronger lead than a changed PCT algorithm.

## Interpretation and boundary

The narrow conclusion is that the initial PCT route did not suddenly change in the recent versions. Reference-refresh behavior demonstrably changed at v212, and the later physical/SCAN behavior deteriorated. This supports investigation of stale reference geometry, changing starting state, local tracking and replan timing. It does not prove obstacle clearance was reduced or uniquely caused the SCAN failures.

The robot-body-to-reference distance is a tracking diagnostic, not wall/edge clearance. Its median within the selected recorded stair region/window is about 8.2 cm for v210, 11.5 cm for v212, 21.0 cm for v217 and 10.6 cm for v219. These use body-pose observer samples; do not mix them with earlier telemetry-frequency statistics. Each run visits the region differently, so these are not matched-state causal comparisons.

Keep two work items separately attributable: (1) investigate the refresh regression against v210; (2) improve shared hard checks and environmental scoring, including an explicit clearance preference in PCT. Do not silently restore periodic refresh under a geometry-only version, and do not claim that an added cost fixes the historical regression before a proper comparison.

## Evidence

- `historical_route_comparison/historical_route_comparison.json`: every delivered reference, recorded observation hashes, sampled stair sections, active-route timing and map hashes.
- `historical_pct_source_identity.json`: executed-source comparison.
- `compare_historical_routes.py`: read-only remote comparison; worker Python, no dependency installation.
- `historical_route_comparison/plot_data.npz`: compact returned route/body/static-surface samples.
- `historical_route_comparison/historical_routes.svg`: two-panel spatial comparison. Grey points are static surfaces, not a certified obstacle boundary.

The exact original captures remain on gpu5070ti under `/data/sun/vla_mppi_20261009/trials/vNNN_linux_full_attempt01/runs/vNNN_linux_full_attempt01/raw_capture.zip`.

## Clarification and added native margin probe

Dr Sun clarified that the concern is the current visual impression and that a route may follow a boundary if sufficient body clearance remains. Do not assume an older version must be better or make historical attribution block the requested clearance preference.

The original native support-gap predicate was rerun on sampled initial/active references with the original 0.18 m two-cylinder offset and 0.35 m cylinder radius, plus diagnostic extra margins of 0.05, 0.10, 0.15 and 0.25 m. Every sampled PCT reference in the selected stair region remains clear through an extra 0.15 m. This specifically concerns support-gap coverage and cannot certify distance to walls/solid obstacles or live occupancy. No configured threshold was changed. See the `support_gap_clearance` section in the returned JSON.
