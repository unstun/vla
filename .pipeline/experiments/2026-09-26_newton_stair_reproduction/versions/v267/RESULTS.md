# v267 rejected prototype and independent raw-point audit

The standalone C++ prototype is not adopted. It incorrectly exempted material
at the strict 0.26 m step boundary, and inherited a global inside test invalid
for the asset's open and inconsistently wound faces. Later v268/v270 components
own the topology and strict-boundary corrections.

The full 4,008-query Python comparison did not finish and is not a pass.
Retain its interrupted logs and all counterexamples. No planner installation
or physics was modified.

A separate original 2,000,000-point PCD audit keeps every XYZ unchanged. Finite
source floor association uses at most one float32 nextafter neighbour on each
side for cap recall; no body/query coordinates or distance are moved. Nine
material controls pass, including one-ULP seams, points eight ULPs outside a cap,
and a genuine wall. Seven disputed endpoints have positive raw-point margins;
B08 remains negative (about -0.13330 m). This is sparse point evidence, not a
continuous surface or native-support certificate. The old padded-voxel numbers
remain separate and unchanged.
