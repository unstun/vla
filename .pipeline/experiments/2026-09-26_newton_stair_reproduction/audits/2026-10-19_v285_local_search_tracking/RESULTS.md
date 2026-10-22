# v285 local search and tracking results

Complete protocol: 53 scored offline cases, then ten distinct physical routes once each. Overall physical acceptance: **unmet**. Offline acceptance: **passed**. Hard radius **0.35 m** and scanner period/deadline **0.1 s** remain unchanged. No navigation scene/coordinate branches, actual retries or baseline promotion.

## Results

- Offline legal passes: **49/50 (98%)**; illegal controls: **3/3** refused.
- Global median over admitted legal routes: **1.346993 s**, p95 1.829887 s, maximum 1.925286 s. Across all 50 legal calls, including failed admission, median 1.359352 s and maximum 2.592589 s. Required median <=1.5 s.
- Physical goal plus terminal PD: **6/10**. Goal/PD plus sampled physical support and source/raw geometry: **5/10**.
- Including all recorded startup and post-navigation poses, goal/PD plus sampled physical geometry: **5/10**.
- Scanner jobs: 7080; deadline failures: 0; native process failures: 0.
- Endpoint rejection log lines: 0; original global reference geometry preserved on 10/10.

The physical repair target remains unmet. D07, S04, CM07, CS03 and CE03 pass goal/PD plus all-recorded sampled physical geometry. CD12 reaches the goal but crosses the source-solid boundary by 0.018423 m. A04, G05, CU06 and CM02 fail to complete. Pool-exhaustion and no-executable-trajectory log mentions decrease, but A-star failures and -1008 mentions increase; removing repulsion does not establish their removal. Exact comparisons and the remaining failure evidence follow below.

## Changes and native verification

Parent is immutable v284. The complete owned diff is [changes.patch](../../versions/v285/changes.patch).

1. Removed the added StaticSolidField repulsion and its GPMP/local environmental-cost calls. Retained ENV225, exact source-solid hard assessment and original hard admission.
2. Non-exact local A-star proposes finite XY endpoint adjustments on the nearest selected same-XY terrain layer plus existing body clearance. A zero-length endpoint uses available local headings; actual connectors/edges keep their original full collision checks. Neighbors follow the adjacent support layer and retain exact elevations, instead of using the endpoint sloped plane. An explored voxel cannot change its stored height. Exact endpoint search retains its contract.
3. Travel uses a positive smooth heading scale (20% through 100%) for both translation and spline phase. It keeps turning while moving. Final pure-yaw alignment remains in the original goal capture region. Reference-mode local replanning falls back to measured odometry when its prediction differs by more than 0.15 m or existing tangent-aware occupancy rejects it, and discards only that inconsistent warm seed.
4. Retained v284 static global path ownership, existing WrongHeight layer association, true gap/obstacle refusals, factory policy/PD, goal tolerances, episode bounds and scanner execution.

174 native test executions pass (including the environmental-cost suite through two entry points; not a claim of independent reproductions). Synthetic hill/corner fixtures through the actual native A-star/GridMap give v284 0/4 supported hill/corner directions with pool exhaustion on the corner pair, versus v285 4/4. Unknown support remains refused. Four translated/rotated tracker cases retain nonzero travel while phase slows; final-yaw and emergency/cancel tests pass. Initial synthetic-fixture construction failures and all development checks are preserved; they are not scored/physical attempts. Ten selected routes also passed the final unscored initial planning check before freeze.

Native manifest SHA-256: `b7e3ac56673c125540c17676723f4b2c9e479406ead783b1cc0a6f9ef23388d8`. Execution manifest SHA-256: `d1ec17d503abaf2f77f8e9e67ccee39fbec762083f7602f44e0fb828025643dc`. [Native qualification](../../versions/v285/qualification_report.json), [source inventory](../../versions/v285/results/native_source_inventory.json).

## Complete offline cohort and all legal starts

The exact frozen v283 cohort/captured scans/endpoints are reused, including the existing G05 and CM02 replacements. No score-based resampling. All 53 timed native calls finish before independent geometry audits. Native timing uses the same two-CPU limit and excludes separately reported initialization. The host is shared; this is not an exclusive-host timing claim.

All 50 legal starts are independently rechecked by the frozen v285 native support and source fields, with unchanged extra-margin requirement >=0.10 m. Minimum support-gap extra margin 0.149999905 m; minimum source-solid extra margin 0.144199199 m. Each result agrees with its frozen start certificate. [All-start audit](results/all50_start_verification.json), [all 53 outcomes](offline/matrix_table.csv), [complete offline gate](offline/offline_gate.json).

Global admission: 49/50; first GPMP pass: 47/49 admitted. Every admitted/published result is independently checked against source and raw geometry; failures remain in the matrix. The strict complete offline gate passed before physical qualification. No inherited v284 timing waiver applies.

CS01 is the sole legal offline failure; it is retained in the 50-case denominator.

## Ten actual physical attempts

A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03: one attempt each. Startup/preflight failures do not count as physical attempts; any such records are retained separately. Full failed prefixes remain failures. Clear geometry on an incomplete route is not full-route validation.

| Route | Terminal | Goal + PD | Goal + PD + geometry | Physics s | Support gap m | Source solid m | Raw solid m | Max pause after motion s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A04 | FAILED | no | no | 100.796 | 0.150000 | 0.150000 | 0.150000 | 36.740 |
| G05 | FAILED | no | no | 92.681 | 0.073152 | 0.150000 | 0.150000 | 6.297 |
| CU06 | FAILED | no | no | 136.159 | 0.150000 | 0.150000 | 0.150000 | 3.858 |
| D07 | FINISHED | yes | yes | 127.701 | 0.090580 | 0.001709 | 0.005187 | 5.957 |
| S04 | FINISHED | yes | yes | 33.033 | 0.150000 | 0.139866 | 0.140258 | 6.217 |
| CD12 | FINISHED | yes | no | 134.668 | 0.097547 | -0.018423 | -0.017353 | 4.872 |
| CM02 | FAILED | no | no | 77.709 | 0.087845 | 0.150000 | 0.150000 | 31.063 |
| CM07 | FINISHED | yes | yes | 54.702 | 0.094885 | 0.150000 | 0.150000 | 5.357 |
| CS03 | FINISHED | yes | yes | 33.013 | 0.150000 | 0.078080 | 0.078083 | 4.997 |
| CE03 | FINISHED | yes | yes | 27.716 | 0.150000 | 0.051003 | 0.051021 | 5.557 |

Margins use measured navigation-window body poses at 10 Hz and saturate at +0.15 m. Physical support-gap margin is separate from static WrongHeight/other verdicts, which remain in the compact tables. Full physical geometry means nonnegative sampled support-gap/source/raw margins; it does not mean every original static verdict is Free. Original static-Free and stricter acceptance fields are also preserved. Startup and final PD are outside the comparable navigation window, and are additionally checked in the all-recording table below. Low-speed pauses may include permitted terminal yaw alignment and are not all mid-route deadlocks.

| Route | Global epochs | Same reference | >=60 s pauses after motion | Max nonterminal pure-yaw s | Nonterminal settling samples | Local success/completed |
| --- | --- | --- | --- | --- | --- | --- |
| A04 | 1 | True | 0 | 0.260 | 29 | 1078/2152 |
| G05 | 1 | True | 0 | 0.000 | 1716 | 1066/2012 |
| CU06 | 1 | True | 0 | 0.120 | 91 | 1529/2532 |
| D07 | 1 | True | 0 | 0.020 | 0 | 3050/3081 |
| S04 | 1 | True | 0 | 0.180 | 0 | 294/296 |
| CD12 | 1 | True | 0 | 0.000 | 0 | 3189/3216 |
| CM02 | 1 | True | 0 | 0.460 | 26 | 736/862 |
| CM07 | 1 | True | 0 | 0.060 | 0 | 839/851 |
| CS03 | 1 | True | 0 | 0.000 | 0 | 239/260 |
| CE03 | 1 | True | 0 | 0.040 | 0 | 140/142 |

## Entire recording and post-navigation geometry

These values include every recorded body pose, including factory startup and the final settling/PD tail. They do not control the robot or add a publication gate. The separate navigation-window values above retain comparability with v284.

| Route | All-recorded support gap m | All-recorded source m | All-recorded raw m | Post-navigation source m | Post-navigation raw m | Goal/PD + all-recorded geometry |
| --- | --- | --- | --- | --- | --- | --- |
| A04 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | False |
| G05 | 0.072912 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | False |
| CU06 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | False |
| D07 | 0.090580 | 0.001709 | 0.005187 | 0.061271 | 0.063791 | True |
| S04 | 0.150000 | 0.139866 | 0.140258 | 0.150000 | 0.150000 | True |
| CD12 | 0.097547 | -0.018423 | -0.017353 | -0.017737 | -0.016668 | False |
| CM02 | 0.087845 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | False |
| CM07 | 0.094885 | 0.150000 | 0.150000 | 0.150000 | 0.150000 | True |
| CS03 | 0.150000 | 0.078080 | 0.078083 | 0.085025 | 0.085028 | True |
| CE03 | 0.150000 | 0.051003 | 0.051021 | 0.053632 | 0.053644 | True |

## Error comparison against unchanged v284 recordings

Counts below are per-line literal log mentions under the same extractor, including retries; they are not counts of independent crashes or failed missions. v284 had seven terminal failed routes. Current terminal outcomes are in the table above. Total physical duration differs: v284 742.488 s, v285 818.179 s, so raw count reductions alone do not establish a causal or reliability result.

| Message | v284 mentions | v285 mentions | Reduction |
| --- | --- | --- | --- |
| Ran out of pool | 90 | 23 | 74.4% |
| Endpoint adjustment failed | 90 | 218 | -142.2% |
| A-star failed | 44 | 279 | -534.1% |
| Robot inside obstacle | 331 | 314 | 5.1% |
| L-BFGS -1008 | 664 | 4915 | -640.2% |
| No executable trajectory | 54 | 20 | 63.0% |

| Route | Ran out of pool | Endpoint adjustment failed | A-star failed | Robot inside obstacle | L-BFGS -1008 | No executable trajectory |
| --- | --- | --- | --- | --- | --- | --- |
| A04 | 6 → 1 | 6 → 11 | 9 → 10 | 10 → 82 | 77 → 567 | 7 → 7 |
| G05 | 21 → 7 | 21 → 37 | 8 → 14 | 12 → 0 | 40 → 67 | 7 → 7 |
| CU06 | 11 → 7 | 11 → 12 | 9 → 7 | 12 → 0 | 49 → 2516 | 7 → 0 |
| D07 | 3 → 0 | 3 → 5 | 3 → 7 | 38 → 6 | 112 → 432 | 7 → 0 |
| S04 | 0 → 0 | 0 → 3 | 1 → 2 | 23 → 0 | 151 → 189 | 2 → 0 |
| CD12 | 31 → 1 | 31 → 3 | 12 → 11 | 81 → 0 | 1 → 567 | 7 → 0 |
| CM02 | 9 → 6 | 9 → 126 | 1 → 219 | 96 → 226 | 14 → 75 | 7 → 6 |
| CM07 | 5 → 1 | 5 → 15 | 0 → 7 | 32 → 0 | 44 → 99 | 4 → 0 |
| CS03 | 1 → 0 | 1 → 6 | 1 → 2 | 5 → 0 | 137 → 227 | 0 → 0 |
| CE03 | 3 → 0 | 3 → 0 | 0 → 0 | 22 → 0 | 39 → 176 | 6 → 0 |

Refinement-only solver-error counts use the same original `Solver error while refining` extractor as the v284 failure bill; they are reported separately from all -1008 mentions.

| Route | v284 refinement solver errors | v285 refinement solver errors |
| --- | --- | --- |
| A04 | 49 | 440 |
| G05 | 23 | 41 |
| CU06 | 24 | 2410 |
| D07 | 76 | 303 |
| S04 | 109 | 140 |
| CD12 | 0 | 406 |
| CM02 | 15 | 50 |
| CM07 | 32 | 77 |
| CS03 | 117 | 176 |
| CE03 | 44 | 142 |

| Route | Measured-seed fallbacks | Distance triggered | Occupancy triggered | Largest distance before fallback m |
| --- | --- | --- | --- | --- |
| A04 | 8 | 8 | 0 | 0.185581 |
| G05 | 6 | 6 | 0 | 0.347852 |
| CU06 | 4 | 4 | 0 | 0.174373 |
| D07 | 7 | 6 | 1 | 0.160017 |
| S04 | 2 | 2 | 0 | 0.151759 |
| CD12 | 2 | 2 | 0 | 0.152647 |
| CM02 | 0 | 0 | 0 | n/a |
| CM07 | 7 | 7 | 0 | 0.192258 |
| CS03 | 1 | 1 | 0 | 0.150346 |
| CE03 | 0 | 0 | 0 | n/a |

The remaining `The robot is inside an obstacle` warning comes from `BsplineOptimizer::check_collision_and_rebound`: after an occupied control point is found, it searches backward through control points; when none is free it logs that warning and sets `in_id=0`. It is not a direct measured-body test or, by itself, proof of a runaway initial seed. Existing native source and actual body audits must be read together. First error contexts are retained in the failure bill.

The combined v285 iteration tests all three repairs together; physical outcomes do not isolate each change's causal contribution. The fallback table records actual native FSM decisions. It does not reconstruct the internal tracker phase from wall time: v285 intentionally scales that phase. Phase/translation consistency is directly checked in the native clock tests; actual physical symptoms and geometry remain separate evidence. [Failure bill](results/failure_terminal_bill.json), [unchanged v284 baseline extraction](results/reference_v284_error_counts.json).

## Videos, source return and limits

Ten regular local MP4 files, 85926567 bytes total, cover the full actual attempts. Each is bound to its original recorded states and frozen version, fully decoded and render-only verified with zero new physics. Local frame checks are recorded separately. [All ten full videos](delivered/README.md), [compact physical table](physical_table.csv), [returned file hashes](physical_return/return_inventory.json).

Local return verification checks 480 compact files, twelve analysis-source files, all 81 frozen execution source/snapshot pairs and every MP4 SHA-256. All ten videos pass a second full decode locally. Twenty temporal samples across the ten cases are visually inspected. [Local delivery verification](results/local_physical_delivery_verification.json), [visual review](results/visual_review.json). SSH loss did not interrupt the detached physical protocol: the returned coordinator closes all ten attempts and analysis before the host restart. Reconnection resumes file transfer only.

Raw recordings stay on gpu5070ti at `/home/sun/vla_exec/physical_runs_v285`; compact source/configuration, reports/provenance and review videos return locally. Physical startup uses the previously authorized capacity admission (available RAM >=16 GiB, output disk >=10 GiB; GPU occupancy observed); physics/policy remain CPU, and rendering may share available GPU capacity. Other jobs are untouched. The five prior v283 startup-failure records and all v284 evidence remain preserved.

This is one attempt per route, not a statistical reliability study. Sampled measured-body geometry is not continuous-time clearance or foot-contact certification. A zero command is not proof that the body is stationary. Removing a cost, successful native tests or a safe reference is not itself evidence of physical success. Remaining failures and excursions are not relabeled as passes. The selected baseline remains v232/v233.
