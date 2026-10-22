# v283 — Completed updated 50+3 offline evaluation

Status: the complete offline gate passed. All ten physical attempts and videos
are complete; the separate RESULTS.md reports failed overall physical acceptance. This is not physical
navigation validation or a baseline adoption.

Native manifest SHA-256:
`caeea41b0dbb99ca10ae74b1cf6239535d4c2c4d25327f53988d8afe7b1393f4`.
The 0.35 m hard radius, 0.18 m offset, original vertical profile, 0.1 s LiDAR
period/deadline, policy and factory PD are unchanged.

## Results

All 53 prospective native calls completed, followed by all 53 independent audit
jobs. No case was rerun for a better score.

| Metric | Result |
|---|---:|
| Legal full-chain passes | 49/50 (98%) |
| Legal global admissions / local publications | 49/50 / 49/50 |
| Illegal controls correctly rejected | 3/3 |
| First GPMP, all legal requests | 47/50 (94%) |
| First GPMP, admitted legal requests | 47/49 (95.92%) |
| CPU2 global median / p95 / maximum, admitted requests | 1.301129 / 1.803867 / 1.956208 s |
| CPU2 global median / p95 / maximum, all 50 legal requests | 1.316707 / 1.916303 / 2.589370 s |
| Negative independently audited admitted/published solid margins | 0 |
| Minimum admitted global source / raw-point solid margin | 0.005710 / 0.006174 m (CD12) |
| Minimum published local source / raw-point solid margin | +0.15 / +0.15 m (reporting cap) |

Cold initialization is recorded separately per case and excluded from these
solve timings. Timed native calls finished before independent audits began.
The host is shared; CPU2 limits do not imply an exclusive-host measurement.

CS01 retains its `pct_no_route` failure. CS02 and CE01 reject their initial GPMP
curves for SupportGap and subsequently pass through the existing graph fallback.
Those first-pass failures are retained, not promoted into first-pass success.
All ten fixed physical cases individually pass offline admission.

## Start protocol and comparison boundary

Every legal start was screened against authoritative StaticSupportField and
StaticSolidField with both extra margins >=0.10 m. Eight starts were replaced:
G05, CU04, CU08, CU11, CU12, CU13, CM01, CM02. The other 42 starts, goals,
headings, route strata and three illegal controls remain unchanged. The cohort
contains exactly 50 distinct legal spatial start/goal pairs plus three controls.
Selection used original geometry/connectivity, without reading route scores.

The fixed physical list remains A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03,
CE03. G05 and CM02 use their uniformly certified replacement starts. The prior
v281 cohort is unchanged in its own files. The new98% versus prior96% is not a
paired algorithm-only comparison, because eight requested starts changed.

## Component and recorded-input evidence

All171 inherited native tests pass. A new translated/rotated endpoint test passes
0/12 on frozen v280 and12/12 on v283. A live-free input at a recorded static-wall
witness is incorrectly permitted by the parent local query and rejected by
v283. Missing static readiness resumes after30.475ms when evidence appears;
permanent absence times out at1.50008s under the original1500ms request budget.

The recorded CD12 support failures have clear reconstructed published curves but
0.32–0.36m body displacement and0.43–0.54rad heading discrepancy. At the first
witness, the newest recorded curve is only19.989ms old and already starts far
from the body. v283 therefore binds warm continuation to the measured envelope
within the map's existing half-cell sampling precision, otherwise using the
existing measured-state initializer. Recorded wall-excursion curves are also
clear at the inspected instants; the missing local static query is real, but
does not by itself establish the full physical failure cause.

Recorded-publication reconstruction is not an exact asynchronous controller
replay. Component and offline evidence do not establish absence of physical
tracking, heading, or support excursions. Those remain the ten-attempt gate.

## Evidence

- [Complete 53-case table](../../audits/2026-10-19_v283_navigation_geometry/offline/matrix_table.csv)
- [All per-case results and final gate](../../audits/2026-10-19_v283_navigation_geometry/offline/matrix_summary.json)
- [Once-only native ledger](../../audits/2026-10-19_v283_navigation_geometry/offline/native_ledger.json)
- [Independent audit ledger](../../audits/2026-10-19_v283_navigation_geometry/offline/audit_ledger.json)
- [All50 start decisions and replacements](start_admission.json)
- [Frozen native source and cohort](native_manifest.json)
- [Component review with log hashes](results/component_review.json)
- [Recorded geometry attribution](results/recorded_summary.json)

Remote full numerical evidence:
`gpu5070ti:/home/sun/vla_exec/navigation_geometry_v283/benchmark/`.
Compact results have returned locally. Heavy inputs, builds and raw numerical
artifacts remain on that host. Physical reports and ten MP4 files are delivered separately through RESULTS.md;
this offline result alone does not establish physical acceptance.
