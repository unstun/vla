# v268 — Closed-solid containment and open source surfaces

Independent geometry repair, not yet adopted by a planner. The original asset
is not a closed oriented surface: the v267 exact audit found1,414 unbalanced
edges. The v266 global oriented-ray fill can therefore create fictitious filled
air beneath an open roof. Preserve that model and its original arithmetic tests
as controls; do not promote their tested-domain qualification to this asset.

Reuse installed Trimesh5.1.0 face adjacency, SciPy graph connectivity and
Trimesh's watertightness/winding/volume checks. Only certified closed positive
volumes receive an interior. Other triangles remain finite two-sided surfaces.
Normalize face winding only on closed inputs; never move vertices, merge by a
distance tolerance, fill holes or change connectivity. These are collision
geometry objects, not route-connectivity rules or endpoint cases.

Retain finite near-floor cap material, all actual poses,0.35m/0.18m geometry,
step/height gates, RL and0.1s scanner. Add open-roof/open-wall counterexamples,
inverted closed-volume and strict0.26m controls. Independently check original
PCD/source surfaces and keep old52/clean50 scores untouched. Native integration
and physical runs remain later gates.
