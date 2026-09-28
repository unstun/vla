# v15: Classify measured risers within connected mapped ground

Parent: v14. Native candidate: `scan52_riser_ground_v15`.

The recorded blocking hits at the first riser are 5–11 cm below the PCT
surface in their own XY cell. The symmetric 5 cm endpoint band marks these
hits as nonterrain forever, even though an adjacent lower tread bounds them.
Retain the existing positive endpoint classification, and additionally accept
returns below a selected surface only between it and an associated lower
neighbor within the existing ETH step capability. Reuse `nearestSurface` and
the existing 0.26 m capability; do not change collision dimensions or clear
historical obstacle labels.

Source review: CMU ground_based_autonomy_basic commit
`7ae94b72206430a399ae012f49715cf51fadb0e0`, `terrainAnalysis.cpp` lines 512–522
uses signed height relative to ground. Its surveyed terrain package has no
license file; no CMU code is copied or linked. The local change reuses the
already pinned BSD-3-Clause ETH surface association. This is a local adaptation,
not upstream reproduction.

Acceptance: captured riser endpoints and native continuation; flat-ground
boxes, walls, people, posts, occlusion and blocked-corridor regressions; absent
central support, another floor, excessive step height and a slab underside
remain unclassified. Then execute physical stairs using the frozen version.
