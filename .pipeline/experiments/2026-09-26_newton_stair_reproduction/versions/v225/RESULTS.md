# v225 recorded-input results

Status: component-validated performance candidate. No physics, new sensor run,
formal training or robot actuation. Parent v224 remains frozen. GPMP route
quality and final native admission remain unresolved in this version.

The runtime uses an offline single-cylinder XYZ atlas and analytic derivatives.
Both centers remain at actual body Z. Weights and every hard predicate are
unchanged. Nine packages built; 164 colcon records comprise 144 distinct test
cases plus 20 wrappers, with zero failures/errors/skips. Whole-factor WNOJ/WNOA
and turning SCAN derivative checks passed.

## Performance and actual route probes

Same archived Building map/endpoints, same host/container as v224:

| Measurement | v224 | v225 |
|---|---:|---:|
| Shared PCT search + smoothing | 8.023 s | 0.113 s |
| Search only | 7.859 s | 0.074 s |
| Active SCAN environmental value + gradient | 35.24 ms | 0.043 ms |

The atlas scorer measured 0.158 microseconds/query; 30,060 PCT/SCAN score
pairs had zero discrepancy. These are offline component timings, not a live
planner deadline or physics acceptance result. Logs: `results/atlas_probe01.log`,
`results/field_probe02.log`, `results/evidence/attempt01/test-result.log`.

On v225's selected seed, the shared graph improves minimum edge margin from
0.02272 to 0.12560 m. After smoothing the shared route has 0.07605 m minimum
edge margin and 30/3481 native-static rejected samples. Actual installed PCT
admission with three raw-graph repair rounds still returns no route in both
modes: legacy 0.203 s, shared 0.378 s, each with one remaining WrongHeight.
No legal executable route is claimed. See `results/admission_probe02.log`.

## Approximation, including its failures

21,788 poses compare against the frozen v224 raw point-cloud oracle. Edge
margin error is at most 5.56e-17 m. For 19,448 known-floor queries outside a
height-association switch band, solid absolute error p95 is 0.00200 m, p99
0.00778 m, maximum 0.01167 m. Across all poses the maximum is **0.27684 m**,
and maximum cost error is **1.0**. Do not present the ordinary percentile as
a global error bound.

All >2 cm optimism and >0.1 cost-error cases occur in the 2,000 uniform XYZ/yaw
queries, absent from the 3,006 original queries, 13,782 archived route/graph
samples and 3,000 local perturbations. Source material exclusion changes
discontinuously when body height crosses floor+0.04 or floor+0.56 m. A 5 cm
atlas interpolates across that discontinuity. Future optimizer trials can
enter these bands; the atlas is a soft prior, not hard clearance evidence.

87,127 smooth derivative axes have maximum relative finite-difference error
1.78e-5, zero rows above 1e-3; 25 nonsmooth axes are separately reported.
Gradient agreement validates derivatives of the interpolated field, not its
agreement with discontinuous raw geometry. See `results/oracle01.csv` and
`results/oracle_summary01.json`.

Atlas: 381 x 371 x 136 float32 margins, XYZ spacing 0.05 m, SHA-256
`7ec06542ef9e2451fe63e89a3baf24d225aa3efcbe5ea025c287eb1b67bbdd84`.
Large bytes remain at gpu5070ti:
`/data/sun/vla_mppi_20261009/environment_lookup_v225/fixtures/building/environment225.env`.
Regenerate with `tools/build_atlas.cpp` against the frozen v224 raw field;
110.636 s export is recorded in `results/export_attempt01.log`. Manifest and
original PCD identities are returned in `results/fixtures/building/environment225.json`.

## Follow-up diagnosis, not production changes

Six identical-seed GPMP ablations show explicit zero is identical to absent
scoring. Disabling relative termination changes neither final geometry nor
the final zero-improvement step. Do not land a tolerance workaround.

The legacy objective is 50*max(c-15,0)^4; the new objective is 100*C, not a
comparison of raw residual maxima. The first seed linearization's position
gradient norms are 2.62e9 versus 458. A real witness at local
(159.613472,147.491558) has corner costs [4.972656,50,1.213867,50], but old
half-cell patch arithmetic yields 73.267061, negative corner weights, and a
73.666623 -> 50 jump across y=147.5. Integer-anchored interpolation removes
that seam. See `results/gpmp_sweep03.log`.

22 diagnostic cases compare interpolation, fixed-seed heading and objective
multipliers on the same 730-point raw seed. With corrected interpolation,
unchanged weight and velocity-coupled heading, minimum edge/solid margins are
0.14205/0.14657 m, versus 0.02627/-0.09362 m before correction. Fixed heading
also improves this seed, but requires more modeling changes and is not selected.
Large objective weights are not monotone improvements. These diagnostic copies
are private executables, never installed production source. A subsequent
version tests the minimal interpolation correction through the actual adapter.

The original v224 final WrongHeight points are interpolated raw-graph samples,
not smoothed endpoints: segment 691,u=0.5 and segment 359,u=0.5. Native
navigation/physical grid origins differ by near-integer offsets with ~1e-7 m
residuals. Boundary lookup selects a depressed navigation proxy despite a
correct physical floor in all four local quadrants. PCT float16 quantization
is only millimetres here. `results/height_trace01.log` retains the actual
installed-service path reconstruction and native queries. The independent
support-cell correction belongs to a later version; no hard threshold changes.

Preserved failed attempts: height tools first lacked a CMake dependency;
field_probe01 used invalid ROS_DOMAIN_ID=233 and failed DDS initialization.
Both corrected build/run attempts are separately retained. No failed outputs
were overwritten or promoted to success.
