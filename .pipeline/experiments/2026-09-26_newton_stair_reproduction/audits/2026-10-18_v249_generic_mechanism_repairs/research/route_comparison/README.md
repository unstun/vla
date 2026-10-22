# Returned-route geometry: frozen v247 versus v251

The actual returned paths have a much smaller planar heading-change tail in
v251. This holds on equal spatial sampling and within the height-changing
stair/ramp sections. It is a geometric result, not evidence of fewer physical
stops or successful execution.

Only completed `rep01` outputs are compared. All 12 requests are unchanged
v242 fixtures; 11 cases return an admitted route in both versions. B09 has no
returned route in either version. No planner, simulator, map or production
source was changed or run by this analysis.

## Definitions

- `route.csv` is the path actually returned by the installed C++ plugin's
  `createPlan`, not a raw A* search trace or an invented spline. See
  `versions/v251/native_probe.cpp:108–116` (the v247 writer is equivalent).
- A native geometric heading is `atan2(dy,dx)` for each nonzero XY segment;
  a jump is the absolute shortest circular difference between adjacent segment
  headings. Stored pose-yaw jumps are recorded separately in the JSON.
- Native sampling densities differ: G07 has 825 versus 3926 poses, R11 has
  725 versus 3369. The primary comparison therefore uses both polylines on a
  common **0.10 m XY-arclength grid**, beginning at the unchanged requested
  start. The final shorter-than-0.10 m remainder is excluded from this turn
  statistic; it remains included in all length measures. Quantiles use NumPy's
  linear interpolation. These are angle changes at the stated spatial scale,
  not time derivatives or a curvature guarantee.
- The coordinate-free vertical-transition neighborhood is
  `abs(z(s+0.5 m)-z(s-0.5 m)) >= 0.10 m`, using each route's interpolated height.
  It identifies height-changing stair/ramp context, not semantic stair labels
  or foot-contact coverage. Gray plot spans show the v251 neighborhood.

## Primary results

Angles below use the common 0.10 m grid, including the requested-start
connector. Lengths also include that connector.

| Case / version | XY length m | 3-D polyline length m | Heading p95 / max deg | Vertical-context p95 / max deg | Global planning s |
| --- | ---: | ---: | ---: | ---: | ---: |
| G07 v247 | 88.945 | 90.771 | 27.14 / 45.00 | 9.91 / 40.07 | 1.513 |
| G07 v251 | 88.392 | 92.112 | 4.98 / 10.12 | 2.47 / 5.29 | 0.895 |
| R11 v247 | 76.376 | 78.192 | 27.76 / 45.00 | 17.29 / 42.79 | 1.755 |
| R11 v251 | 75.859 | 79.457 | 5.05 / 9.84 | 2.30 / 4.32 | 0.953 |

The native, unequal-density geometry p95/max is 45.00/45.00 deg for both old
routes, 1.58/7.30 deg for new G07, and 1.97/7.13 deg for new R11. The common-grid
result prevents attributing the entire change to the denser returned path.
The new routes distribute small heading changes over longer runs, while the
old graph has long straight segments and discrete turns. Consequently the
median can increase even while the upper tail decreases; all quantiles are
retained in `comparison_metrics.json` and `comparison_metrics.csv`.

The XY lengths decrease slightly, but the actual 3-D piecewise-linear lengths
**increase**. Total absolute vertical variation also changes: G07
4.930 to 5.385 m, R11 4.930 to 5.247 m. The plots retain the support-aligned
height profile rather than flattening it. No claim that every route-quality
measure improves follows from the heading result.

The timing is the recorded steady-clock duration of `createPlan`, under the
frozen fixture/ROS epoch and Docker's 2-CPU / 6-GB component configuration
(`versions/v251/probe.py:7–14`). These are single-repetition component timings,
not live scheduling latency, deadline compliance or independent physics runs.

## Start connection and terminal heading

The requested starts are identical across versions. v247 returns that start
as its first point. The upstream GPMP soft prior places v251's first returned
point approximately 0.100000 m away in XY for both cases. This analysis does
not reinterpret that optimized point as the requested spawn or move either
request. The actual requested-start-to-first-point connector is included.

| Case | v251 connector length m | Connector-to-first-geometric-segment jump deg | Actual measured-start to first stored pose-yaw rotation deg, v247 / v251 |
| --- | ---: | ---: | ---: |
| G07 | 0.100000069 | 0.495 | 19.572 / 19.077 |
| R11 | 0.100000070 | 0.486 | 0.000055 / 0.486 |

`sampleReference` starts from the actual request pose and checks translation
and rotation
(`versions/v230/src/lite3_nav2_plugins/include/lite3_nav2_plugins/shared_traversability.hpp:21–50,96–101`).
The successful v251 STATIC_ONLY review includes those connectors: G07
0/4277 rejected samples, R11 0/3695. Old counts are 0/4624 and 0/4128.
Thus the main heading reductions are not an omitted initial connector.
For these fresh infer-heading sessions, the last stored yaw agrees with the
last nonzero geometric tangent in all four routes; terminal orientation
overrides do not account for the reported maxima. A later replan with an
already cached canonical terminal pose is outside this comparison.

## Feasibility and attribution boundary

The old G07 and R11 logs record two
`pct_support_height_missing_surface` optimization failures, then a statically
admitted third-attempt graph fallback. v251 admits both on the first GPMP
attempt, with no graph fallback. In both versions the route passes its native
shared static review and the frozen cold first-SCAN/independent-curve component
check. The exact selected per-call outcomes are retained with the inputs.

This compares two complete frozen treatments. v249 repaired native floor
association and height-band projection; v250 made the existing uncertain-gap
mask continuous; v251 lets GPMP hard residual and the unchanged ENV225 soft
objective see that oriented gap domain. Accordingly, passing each version's
gate does not establish that the old route passes the new domain, nor isolate
one residual as the sole cause of the geometric difference. The original
0.35 m radius/support limit, request fixtures and RL policy binding remain
recorded in the frozen manifests. ENV extra-edge values also use their
version-specific field wrapper and should not be treated as an unchanged
standalone oracle.

## Artifacts and reproduction

- `route_geometry_comparison.png/.pdf`: returned XY paths, height profiles and
  common-grid turn traces for G07/R11; all panels were visually inspected.
- `vertical_transition_turns.png/.pdf`: common-grid turn CDFs in the defined
  vertical-transition neighborhoods.
- `comparison_metrics.json/.csv`: all 11 paired admitted rep01 cases, full
  quantiles, raw/connected lengths, start connection, gates and remote paths.
- `collection_receipt.json`: remote SHA-256/size/path for every returned compact
  input, exact endpoint/scenario text, frozen source bindings, selected log
  lines, and completion status. Source-binding SHA values were checked against
  local frozen manifests, probe, run script and native source inventory.
- `inputs/`: verified compact route CSVs and summaries only. Raw point clouds,
  scans, videos, builds and caches remain remote. These inputs were verified
  against each completed summary's recorded SHA before analysis.
- `artifact_sha256.json`: local scripts, reports, metrics, figures and input
  checksums (excluding the checksum file itself).

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v249_generic_mechanism_repairs/research/route_comparison/collect_routes.py
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/vla_route_comparison_mpl python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v249_generic_mechanism_repairs/research/route_comparison/compare_routes.py
```

`collect_routes.py` only reads completed outputs over SSH; it launches no
native query. `compare_routes.py` uses NumPy/Matplotlib on the local CPU.
The original remote roots are:

```text
gpu5070ti:/data/sun/vla_mppi_20261009/physical_traversability_v247/evaluation/scored/{CASE}/rep01/route.csv
gpu5070ti:/data/sun/vla_mppi_20261009/generic_mechanisms_v251/evaluation/scored/{CASE}/rep01/route.csv
gpu5070ti:/data/sun/vla_mppi_20261009/generalization_v242/cases/{CASE}/endpoints.txt
```
