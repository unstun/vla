# A02: original mesh support versus the inherited gap-mask rasterization

Stage: experiment + analysis, 2026-10-18. Read-only recorded-input geometry.
Production code, RL, radius, offsets, poses, source mask and physics were unchanged.

## Finding

**A02's measured-start SupportGap rejection is a target-cell rasterization
false positive.** Both continuous radius-0.35 m circles fit entirely on the
original simulator mesh within the existing support height band. The rear
circle has 0.028376919 m remaining clearance to the true uncovered domain.
None of the six negative source squares that trigger the inherited mask
intersects that actual circle. No relaxation of the 0.35 m radius is needed
to distinguish this pose from a real support gap.

Two archived GPMP stair refusals have the same cause. At G07's separately
requested exact failed-start pose, removing target-cell overreach eliminates
the gap-mask rejection at initial-edge yaws 0 and pi; other directions retain
either source-cell conservatism or a genuine mesh gap. These are geometric
predictions for the narrow proposed mask correction, not a completed planner
replay or execution acceptance result.

## Method and identity

`analyze_geometry.py` ran in the existing gpu5070ti worker environment with
CPU affinity `[0]`, one BLAS/OpenMP thread, numpy 2.5.3 and shapely 2.1.2.
The three invocations took 0.5105, 0.6979 and 2.3928 seconds. No physics,
planner, controller or GPU execution occurred.

The script independently re-opened the original metre/Z-up USD mesh, applied
the same local-to-world transform and float32 vertex conversion as
`scripts/scene_assets.py:33`, and checked exact elementwise equality with
all **16,448** archived triangles. It clipped each triangle against
`body.z - .30 +/- .26 m`, projected the resulting polygon into XY, and
computed their union. For a covered center, distance to that union's boundary
is the distance to the uncovered domain. Continuous radius-0.35 m coverage
is determined by this distance, rather than by finite circle samples.
The optional uncovered-area calculation uses an inscribed circle polygon
with 4096 segments per quadrant; it does not determine the coverage verdict.

For each front/rear center, the script reproduced the inherited source-square
to target-square expansion, enumerated every height-compatible triggering
source cell and all 16 original subcell samples, then compared against the
actual continuous center-to-source-square distance. A separate barycentric
vertical-intersection calculation checked each sampled mesh-coverage result.
All these checks passed.

The original source inputs are hash checked on every invocation:

| Input | SHA-256 |
|---|---|
| `inputs/building.usda` | `e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39` |
| `fixed_curve_input/physical_floor.f32` | `20acd5cf1ef156c5bd336b12651efe9a18e9959816905b05178ed44b1a181c96` |
| `support_coverage_v134/partial.txt` | `219d7982eca6c7af94545158ec97fb3b0186ff0f2166f8697d53c0b0726c56d8` |
| `inputs/static_background/building2_9.pcd` | `8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae` |

The transformed-triangle cache hash, exact remote paths, input sizes,
analysis-script hash and pose-input hash are recorded in each
`attemptNN/geometry_report.json`. `attemptNN/output_inventory.json` binds
the returned outputs. Raw mesh triangles and the 48 MB original PCD stay
remote. Compact GeoJSON includes only the local review windows.

## A02 measured pose

Primary pose is the exact original final measured record:
`(-6.1107869148254395, 6.87894868850708, .3989008665084839)`, yaw
`-.7858018918788338`; ground hint `.0989008665084839`.
Source: prior audit
`physical/A02/results/execution_receipts/result.json`, actual JSON key
`last_backend.measurement_body_pose`. The `remote_payload` parent-name text
in `pose_input.json` is descriptive shorthand, not the original JSON key;
the copied coordinates themselves match `last_backend` exactly.

| Side | Center XY | Inherited mask sources | Exact source-square intersections | Distance to uncovered mesh | Margin above .35 |
|---|---|---:|---:|---:|---:|
| Front | `(-5.983559091, 6.751618092)` | 0 | 0 | .635748117 | .285748117 |
| Rear | `(-6.238014739, 7.006279285)` | 6 | 0 | .378376919 | **.028376919** |

Both discs have zero uncovered area. The six rear source cells each contain
12 failed generator samples: **72 actual missing-mesh samples, all outside
the current rear disc**. The closest failed sample is .394839534 m from its
center. The closest *entire source square* is .357299955 m away, still
7.299955 mm beyond the unchanged radius. Yet the inherited target-square
test reports .295314693 m because it uses every point of target cell
`[-6.3,-6.2) x [7.0,7.1)` as a potential query center.

All six source cells have x `-6.645314693450928`, ground elevation
`.058030345737934114`, and y values from `6.813188552856445` to
`7.313188552856445`. Their exact center-to-square distances are
`.384887276, .359888922, .357299955, .361803737, .390235577, .440074573 m`.
Full 16-sample intersection heights and coordinates are retained in
`attempt01/mask_source_samples.json`; source-cell witnesses are in
`attempt01/mask_trigger_sources.json`.

Original PCD corroboration: 213 front and 221 rear points fall within the
respective disc and query height band, all with horizontal normals and
z `.05803000181913376`. Nearby physical-floor records have elevations
`.05803032338619232..058030345737934114`. This is consistent with the
original mesh floor. Positive PCD/raw solid margins alone would not prove
continuous support; the exact mesh union provides that evidence here.

Archived controls remain independently named, not substituted for the pose:

| Archived observation | Rear mesh distance | Rear extra clearance | Inherited mask |
|---|---:|---:|---|
| Goal submission, exact pose from prior replay requests | .378383666 | .028383666 | rejects |
| First recorded post-factory policy telemetry, 11.040831566 s | .379041479 | .029041479 | rejects |
| Nominal preflight request | .444551129 | .094551129 | clear |

The raw telemetry's first row explicitly says `controller_phase=policy` and
`stance_mode=FIXED_STAND`. The retained telemetry/backend/observation records
inspected here do not separately identify the first RobotExecutionState
ACTIVE transition; this report does not relabel that row as an exact ACTIVE
observation.

## GPMP stair samples

The supplementary inputs use exact original dense-query CSV rows:

| Sample | Original row | Front mesh distance | Rear mesh distance | Inherited front sources | Exact intersecting source squares |
|---|---|---:|---:|---:|---:|
| A02 | segment 296, fraction .75 | .537374105 | .660896353 | 1 | 0 |
| G07 | segment 367, fraction .5 | .534306797 | .659075871 | 1 | 0 |

Both refer to source cell 5496 at
`(7.654685020446777,6.01318883895874,3.0675892543792727)`. Its original
16-sample coverage has one missing point. Source-to-target-square distance
is .325466175 m, but the actual front-center to source-square distance is
.441225059 m for A02 and .437984522 m for G07. The closest missing samples
are .560797030 and .557852277 m away. All four actual discs have zero
uncovered area. Thus an exact center-to-source-square check removes these
two particular SupportGap vetoes without changing source cells or radius.

## G07 exact failed-start directions

Additional original query: 102.110511780 s,
`(7.710203647613525,6.484551906585693,3.35550594329834)`. The original XYZW
quaternion is
`(.0014319225447252393,.004865983035415411,.9972338080406189,.07415612787008286)`;
its planar yaw is **2.9931316606892713**. Source identity and all original
pose/twist values are preserved in `pose_input_g07_failed_start.json`, bound
to `../G07/returned/validation_receipt.json`.

The actual-yaw pose has no inherited mask hits. Its front/rear continuous
mesh distances are .511197616 and .525784875 m. The eight A* edge headings
rotate the two-cylinder proxy; every one receives an inherited mask hit.
These zero-length heading queries explain how a standable current
orientation can coexist with all immediate graph directions being refused.

| Equivalent double-cylinder headings | Old mask sources on limiting side | Exact source squares still intersecting | Limiting continuous mesh distance | Meaning |
|---|---:|---:|---:|---|
| 0, pi | 3 | **0** | .484572689 | target-cell overreach; narrow correction removes gap veto |
| pi/4, -3pi/4 | 7 | 4 | .357293614 | mesh covered with 7.294 mm margin; whole-source-cell conservatism remains |
| pi/2, -pi/2 | 4 | 4 | **.314982632** | genuine mesh coverage deficit under .35 m envelope |
| 3pi/4, -pi/4 | 2 | 1 | .413220590 | mesh covered; whole-source-cell conservatism remains |

For the pi/2 pair, two failed subcell samples lie inside the limiting disc;
the uncovered area is approximately `.00189453275 m2`. That veto should
remain under the original geometry contract. The proposed target-cell-only
correction is not an assertion that every seed direction should pass.

## Source semantics and scope

The existing generator is `versions/v134/support_coverage.cpp:29`, with
source identity and retention in `v134/generate_coverage.py:13` and
`v135/support_coverage_input.json`. The inherited rasterization is
`v134/src/plan_env/include/plan_env/support_gap_mask.h:38`; query lookup is
line 52. Current common support admission is
`v247/src/plan_env/include/plan_env/static_support.h:54`, using the original
two-center helper `v221/src/plan_env/include/plan_env/footprint_query.h:9`.
The old v135 all-heading `.53 m` PCT preprocessing is a separate operation
and was not used by this analysis.

This report diagnoses geometry and mask approximation. It does not establish
future footstep coverage, dynamic balance, successful live replanning or route
execution. All production repair and runtime acceptance remain with the main
task. The finite source-cell representation itself remains conservative even
after removing the extra target-cell quantization.

## Regeneration

Remote audit root:
`/data/sun/vla_mppi_20261009/generic_mechanisms_v249/a02_geometry`.
Use the existing worker Python and preserve prior output directories:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/sun/vla_exec/envs/newton_worker/bin/python analyze_geometry.py \
  --task-root /data/sun/vla_mppi_20261009 \
  --pose-input pose_input.json --output fresh_attempt
```

`pose_input_supplement.json` regenerates attempt02;
`pose_input_g07_failed_start.json` regenerates attempt03. The script sets
its own CPU affinity to one allowed core and refuses an existing output
directory. `compact_summary.csv` collects every per-circle result. The local
figure uses the already returned GeoJSON, not another mesh query. Its initial
remote plotting attempt lacked matplotlib; analysis results were unaffected.
The portable plotting script renders locally with matplotlib 3.10.8 and no
shapely dependency.
