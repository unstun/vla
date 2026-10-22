# v268 independent topology qualification

The original asset is not one closed solid. The verified extractor retains all
16,448 source triangles and exact vertex coordinates, identifies 344 closed
volumes (13,004 faces), and treats the remaining 3,444 faces as two-sided source
surfaces. Six face windings are reversed within certified closed objects;
vertices, face connectivity and holes are unchanged.

The independently run checks pass: 14 inherited physical controls, six open
roof/wall and reversed-winding counterexamples, three strict step-boundary
controls, and 4,000 filled-cylinder/FCL comparisons with zero mismatches.
The seven disputed endpoints are source-solid-free; B08 remains refused.
These are component results. In particular CM01 still has an independent native
UnknownSupport refusal; source-solid freedom does not establish route admission.

Frozen manifest: b1322ff8cdf8512045910403b27d03f9869d6f73d7c82f428fe497f5e2121d00.
The returned ten-file inventory was checked locally with zero hash mismatches.
Bulk normalized geometry remains on gpu5070ti, identified in
`results/geometry_export.json`.

A subsequent v269 scene comparison exposed a reference candidate-recall defect:
exact projected intersection could lose a shared boundary before finite 3-D
clipping. v270 owns its correction and renewed C++ conformance checks. Preserve
this version's declared component results; do not treat it as native PCT/SCAN
integration or a physical-run success. No new physics or selected-baseline change.
