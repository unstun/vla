# v266 — Independent finite source-surface validation

Status: experimental model, not adopted by either planner or a physical run.
Dr Sun explicitly authorized this model-domain change on 2026-10-18. Frozen
v259/v261 equivalence results and both scored ledgers remain unchanged.

Use the original Newton Building triangles, with finite surface extents and
source normals, instead of treating a sampled occupied voxel as a solid ball
or box. Preserve the exact requested poses, 0.35 m cylinder radius, 0.18 m
offset, vertical interval, step/height gates, RL and 0.1 s scanner. Do not
silently classify a source floor, short wall, underside or riser as free.

First inspect all seven refused endpoints and B08 against original triangles,
actual point-cloud source records and vertical surface intersections. Independently
test finite walls, columns, slabs, risers, ceilings, ramps and stacked floors.
Separate source support presence, body collision and step material association.
Unknown actual support stays refused; a floor at a neighbouring virtual cell
is not evidence for the real query point.

Only after independent geometry validation may a new native integration and
frozen once-per-case full-chain evaluation be prepared. The fixed original52
and clean50+3 request sets must not be filtered or substituted. Physical
execution remains conditional on the existing coverage and timing gates.

Local repository is the source of truth. Execution directory:
`gpu5070ti:/data/sun/vla_mppi_20261009/source_surface_v266/`.
Return compact source identities, exact witness records, test output and
comparison summaries. Original clouds, triangle arrays and build caches stay
remote, with hashes and regeneration commands recorded locally.
