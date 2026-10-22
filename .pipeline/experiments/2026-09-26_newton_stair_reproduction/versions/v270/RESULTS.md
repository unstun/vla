# v270 independent source conformance passed

All 512 predeclared scene queries agree between standalone C++ and the
independent finite-clipping/GEOS reference: zero collision-sign differences,
zero margin differences above 1e-8 m, maximum error 1.1102230246251565e-16 m.
The C++ query batch took 0.0251833 s on CPU2; this is not global planning time.
All 14 physical counterexamples pass, including strict step-height contact,
open/inverted source objects, near-vertical faces and tiny upward surfaces.

The shared-boundary defect was in reference broad-phase candidate recall.
Bounding-box recall precedes the unchanged finite 3-D clipping. A second
reference performance defect cut a ceiling face against hundreds of caps
entirely below it, making over 10,000 redundant fragments. Strict cap-maximum
height rejection and exact duplicate-piece removal avoid that work. No pose,
radius, triangle coordinate, step band or clipping tolerance changed. All 452
completed attempt03 queries still agree with attempt04 (max 7.77e-16 m).
The interrupted attempts and bounded diagnostic remain in `results/`.

Frozen manifest: `750ecc2f0daa62135614ef4524677928c7420bfa5313757b42e6491f8c22a18a`.
All 26 returned files were verified locally with zero SHA-256 mismatches.
Inherited closed/open physical qualification is recorded in v268; v267/v269
negative controls remain intact. Native PCT/SCAN integration belongs to v271.
This component performed zero planning calls and zero physics steps. The
selected physical/display baseline remains v232/v233.
