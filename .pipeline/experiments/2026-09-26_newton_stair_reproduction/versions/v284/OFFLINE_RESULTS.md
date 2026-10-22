# v284 complete 50+3 offline result

The once-only scored matrix and independent geometry audits are complete.
Strict frozen offline gate: **FAIL**. Legal full-chain passes:
**48/50 (96.0%)**;
illegal controls correctly refused: **3/3**.
Global admissions: 49/50. Global median:
**1.649325 s**, excluding initialization, versus
1.301129 s in v283. The requested approximately 1.3 s target and
the prewritten 1.5 s operational ceiling are evaluated separately from geometry.

## Fixed protocol and identity

- Native manifest SHA256: `660842708af904fad2b5d63f3499c655422d2c1bddacf323e0cb981e185d3e32`.
- Source inventory: 329 composed files; 45 owned frozen source/metadata files and
  snapshots; 172 native tests in 20 suite executions. See the component receipt.
- Same v283 cohort/captured LiDAR/endpoints and all 50 start certificates, byte for
  byte. No planner-score resampling. G05 and CM02 retain the uniform v283 start
  replacements. See [all 50 start audit](../../audits/2026-10-19_v284_static_continuity/all50_start_audit.csv).
- Exact hard radius 0.35 m, cylinder offset 0.18 m, vertical profile unchanged;
  scanner period/deadline 0.1 s. Policy, factory PD and goal tolerances unchanged.
- 53 scored native calls completed before 53 independent audits. CPU quota 2 for
  native timing; shared host, no exclusive-machine claim. Initialization median
  3.756448s is reported separately. No new physics here.
- Frozen evaluator executable inventory SHA256:
  `f7b640597c7ae2b04071d70d350777a5aff4e7519bd90101fae2fba9cb372d8d`. Source/install/evaluator identity
  checks run before and after the matrix.

Full-chain offline pass means global route admission and one local trajectory
publication from captured stationary inputs, with independent checks. It does
not mean 50 complete physical missions. The separate ten-route Newton batch is
needed to assess actual movement, stalls, arrival, PD and measured geometry.

## Aggregate result

| Metric | v283 | v284 |
|---|---:|---:|
| Legal full-chain passes | 49/50 | 48/50 |
| Illegal refusals | 3/3 | 3/3 |
| Global admissions | 49/50 | 49/50 |
| First GPMP pass / all legal | 47/50 | 47/50 |
| First GPMP pass / admitted | 47/49 | 47/49 |
| Median global seconds | 1.301129 | 1.649325 |
| p95 global seconds | 1.803867 | 2.090908 |
| Maximum global seconds | 1.956208 | 2.288371 |

Zero admitted negative source/raw margin: **True**.
Zero published negative source/raw margin or native support refusal:
**True**.
The fixed ten route identities are A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03.
Their individual full-chain outcomes are retained in the table below.

## Failures retained

- CD11: global=True, local publication=False; first_planning_round_failed.
- CS01: global=False, local publication=False; not_evaluated_global_rejected.

CD11's captured trace reaches optimization but fails refinement/dynamic admission
after retiming and the existing fixed-height recovery. It is not relabeled as a
source-field publication veto. CS01's native no-route remains a distinct failure.
Full per-case logs and independent source/raw witnesses remain in the offline
return; no failed formal call is retried.

The unchanged explicit endpoints themselves limit soft-margin improvement:
CD12's requested goal has only +0.005710 m source-solid margin, and CE03's
requested goal +0.019715 m. These values equal their global minima. A soft
cost cannot move fixed endpoints; no uniform 3–5 cm clearance is claimed over
entire paths including those exact goals. Actual arrival-window clearances are
left to the physical measurements, without moving goals or adding a new veto.

## All 53 cases

Margins below are extra metres beyond the unchanged 0.35 m profile; positive
values may saturate at +0.15 m. Missing local margins mean no local publication,
not a zero clearance. Source-triangle and raw-point evidence stay separate in
the machine-readable case summaries.

| Case | Expected | Global | First GPMP | Local | Full pass | Global source min m | Local source min m |
|---|---|---|---|---|---|---:|---:|
| A04 | admit | True | True | True | True | 0.150000 | 0.150000 |
| G05 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU01 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU02 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU03 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU04 | admit | True | True | True | True | 0.144199 | 0.150000 |
| CU05 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU06 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU07 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU08 | admit | True | True | True | True | 0.115604 | 0.150000 |
| CU09 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU10 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU11 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU12 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CU13 | admit | True | True | True | True | 0.150000 | 0.150000 |
| D07 | admit | True | True | True | True | 0.092581 | 0.150000 |
| CD01 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD02 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD03 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD04 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD05 | admit | True | True | True | True | 0.145615 | 0.150000 |
| CD06 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD07 | admit | True | True | True | True | 0.053126 | 0.150000 |
| CD08 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD09 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD10 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD11 | admit | True | True | False | False | 0.150000 | — |
| CD12 | admit | True | True | True | True | 0.005710 | 0.150000 |
| CD13 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CD14 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CM01 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CM02 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CM03 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CM04 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CM05 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CM06 | admit | True | True | True | True | 0.138816 | 0.150000 |
| CM07 | admit | True | True | True | True | 0.138549 | 0.150000 |
| CM08 | admit | True | True | True | True | 0.150000 | 0.150000 |
| S04 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CS01 | admit | False | False | False | False | — | — |
| CS02 | admit | True | False | True | True | 0.150000 | 0.150000 |
| CS03 | admit | True | True | True | True | 0.059271 | 0.150000 |
| CS04 | admit | True | True | True | True | 0.150000 | 0.150000 |
| CS05 | admit | True | True | True | True | 0.150000 | 0.150000 |
| E02 | admit | True | True | True | True | 0.150000 | 0.150000 |
| E03 | admit | True | True | True | True | 0.046468 | 0.150000 |
| CE01 | admit | True | False | True | True | 0.011273 | 0.150000 |
| CE02 | admit | True | True | True | True | 0.047675 | 0.150000 |
| CE03 | admit | True | True | True | True | 0.019715 | 0.150000 |
| CE04 | admit | True | True | True | True | 0.052092 | 0.150000 |
| CI_E04 | reject | False | False | False | False | — | — |
| CI_E05 | reject | False | False | False | False | — | — |
| CI_E06 | reject | False | False | False | False | — | — |

## Evidence

The audit's `offline/` directory contains the original native/audit ledgers,
matrix summary/table, gate, completion certificate and every compact case result.
`results/component_review.json` and qualification logs retain parent/candidate
contrasts and all development failures. The four five-case development batches
are unscored pre-freeze checks; they are not additional formal 53-case matrices
or physical attempts. Heavy captured inputs/builds remain on gpu5070ti.

Source-wall repulsion is a soft bias, not an admission proof: strength 0.1,
extra range 0.07 m, source XY/yaw gradient at actual height and zero soft Z
derivative. SCAN integrates that term at map-resolution quadrature; its legacy
atlas and hard checks keep their original sampling. A safe published curve
does not prove that a dynamically displaced physical robot follows it safely.
