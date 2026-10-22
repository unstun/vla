# v279 Equivalent source-height envelope cache

Frozen manifest: `3cc70329470813cfbc19590fcdf4bd11d1eb0d853c6b2a7af8a8e8a9de1b8b8e`.
Parent v272 remains unchanged. Cache entries may now prove positive freedom over
an entire real-height interval, using a union of body heights and intersection
of eligible terrain material. Inconclusive interval queries return to the exact
actual-pose query. Negative certificates remain exact-height only. No requested
position is rounded; no hard collision/support threshold or cost changes.

114,477 full eight-value source assessments are bit-identical, 24,000 interval
boundary cases and all source-cache/swept-edge/rotation implications pass. Legacy
70,928 values and 5,000 edges, 70,928 support values and 70,928 ENV costs have
zero differences. 74 plugin and 97 native tests pass, as do all six hard-route
controls, H00 full offline chain and measured A02 first-GPMP admission.

On CPU2, A04/G05/D07 take 1.721432/1.687751/1.895835 s. This component alone has
not passed the <=1.5 s full-cohort median gate. Development01 (0.05 m proof
interval) and its 1.828/1.789/1.858 s results are retained. Final interval is
0.01 m; only positive proofs skip exact queries. No new matrix/physics claim.
36 frozen source files and all four returned inventories were locally verified.
