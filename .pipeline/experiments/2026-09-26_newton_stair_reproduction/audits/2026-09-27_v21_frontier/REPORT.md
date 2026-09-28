# Captured v21 continuation failure

The actual `v21_building_route01` advances 2.558 m but does not reach its short
stair goal. This audit retains 189 original paired sensor/body measurements,
the original route and captured local spline, and enters the actual
`GEN_NEW_TRAJ` start-state path. It does not substitute a predicted spline end
for the measured stopped body position.

At the captured state, two inflated contributors retain genuine measured
sloped-tread points as historical nonterrain. Original PCT cell [23,127] has 51
samples and no sample of the relevant sloped top. Its highest relevant sample
is a vertical-face point at 0.525343657 m. Two recorded returns at
0.575821224 and 0.575373321 m lie on Building mesh triangle 3020 to submicrometre
plane error. Their differences from the old surface slightly exceed the
unchanged 0.05 m classification band. These are real floor returns, not a person
or robot return, and not a global vertical registration error.

The pinned Trimesh sampler adds samples from all surfaces of the same static
Building, retaining every original point. An added point at 0.571860731 m in
the relevant cell reduces those errors to about 4.0 and 3.5 mm. Four further
blocking voxel contributors are actual vertical stair-face returns and need
the existing paired-tread riser rule, not merely the floor-height band.

| Counterfactual | Original scored navigation support | Native continuation |
|---|---|---|
| Original v21 inputs and classification | Retained | Fails |
| Original broader source with full riser rule | Retained | Fails |
| Dense selected input, extra floor band only | Retained | Fails |
| Dense raw qualified input, extra floor band only | Retained | Fails |
| Dense raw qualified input, full original floor/riser rule | Retained | Passes |

The last row accepts a **1.256635186 m XY prefix**, not the initially requested
longer target. It lasts 3.269448844 s; all 328 full-curve samples pass, endpoint
position/velocity/acceleration checks pass, and terminal velocity/acceleration
are zero. No-progress, out-of-map and stale-input rejection remain active.
The reviewer independently reconstructed the spline boundary values from its
logged actual controls and knots.

This diagnostic replaced only the raw classification snapshot. The equivalent
production implementation must select the explicit source, rather than OR two
different classification predicates. Density alone is frozen separately as v22;
the source-selection behavior belongs to v23 and requires its own compiled
regression and physical run. No full-route success is inferred here.

Evidence: `dense_execution.json`, `dense_raw_surface.json`,
`dense_raw_riser.json`, `dense_raw_riser_negatives.json`, the corresponding raw
logs and query CSVs, plus `../2026-09-27_dense_static_sampling/receipt.json` and
`raw_receipt.json`. The denser input is an offline simulation prior repair;
it is not evidence that a real robot's SLAM map has equivalent coverage.
