# v281 — Completed source-surface generalization benchmark

Status: offline qualified for the prospectively selected physical cohort.
Native source is frozen v280. Exactly 105 fresh once-only native calls used the
unchanged original 52 and fixed 50-positive-plus-3-illegal cohorts. RL, endpoints,
headings, 0.35 m hard collision/support and 0.1 s scanning are unchanged.

| Metric | Original 52 | Fixed 50 + 3 |
|---|---:|---:|
| Positive full-chain admissions | 38/49 | 48/50 (96%) |
| First GPMP, among admitted positives | 38/38 | 44/48 (91.67%) |
| First GPMP, among all positives | 38/49 | 44/50 (88%) |
| Illegal controls correctly refused | 3/3 | 3/3 |
| CPU2 median global planning | 1.255811 s | 1.336759 s |
| CPU2 p95 / maximum global planning | 1.809777 / 1.856566 s | 1.840213 / 2.406595 s |
| Admitted global/local curves with negative audited raw margin | 0 | 0 |

Global times exclude initialization, which is reported separately per request.
The fixed-cohort physical gate passes: at least 45/50 full admissions, at least
90% first GPMP **among admitted cases**, median at most 1.5 s, all illegal
controls refused, and no negative independent raw-point margin. The original
cohort remains 38/49; its failed labels and records were not changed.

All 105 audit jobs closed without error. The 86 admitted global/local curve
pairs use the frozen independent v276 source-material audit and unchanged raw
XYZ for distances. Fixed-cohort minimum raw clearance is 0.000986757 m globally
and 0.000986671 m locally (CU13); native source clearance is approximately
0.000850 m. These are narrow positive margins, not a claim of execution robustness.

The retained ENV soft atlas reports negative edge proxies at CE03 (-0.177240 m)
and original E03 (-0.030549 m). A separate actual-native diagnostic finds both
hard support verdicts Free at radius 0.35 m, with physical extra gap margin
+0.15 m (the reporting cap). This is an atlas/physical-support discrepancy;
the soft proxy must not be presented as the hard physical support margin.

Remaining first-pass failures are CU08 (solid collision), CU11 and CS02
(SupportGap), and CE01 (SupportGap, a new first-pass regression versus v273).
They retain admitted later attempts; CE01 uses the third graph fallback.
CM01 remains UnknownSupport at the start; CS01 has valid endpoints but no route.
Original positive refusals U11, U12, U13, D09–D15 and S03 remain in the ledger.

The ten prospectively selected cases are A04, G05, CU06, D07, S04, CD12, CM02,
CM07, CS03 and CE03. All ten passed first GPMP offline. Selection is frozen,
including its use of the existing ENV proxy; no case was replaced after scoring.

Evidence: [complete returned cohort](../../audits/2026-10-19_v280_source_generalization/results/return_inventory.json),
[fixed gate](../../audits/2026-10-19_v280_source_generalization/results/clean50/offline_gate.json),
[original ledger](../../audits/2026-10-19_v280_source_generalization/results/original52/matrix_table.csv).
585 compact files (6,612,013 bytes) returned with zero SHA mismatches; 516 larger
numerical artifacts remain hash-pinned remotely. All legacy models and failed
development/benchmark records remain intact. Physical outcomes are recorded
separately under v282; the selected physical/display baseline remains v232/v233.
