# v278 Conservative source-surface free-space index

Parent: frozen v272, with identical exact geometry and all full assessments.
Rasterize conservative XY AABBs of every relevant non-excluded source surface
and closed-volume interior for each entire ground-height interval. Exclude only
complete terrain volumes or complete upward faces whose original strict band
holds throughout that interval. Compute a Euclidean distance lower bound with
both cell extents and arithmetic padding subtracted. Return the existing capped
0.15 m circle margin only when that lower bound proves at least radius + target.
All other queries use the unchanged exact clipping kernel. No cell rejects a
pose, no requested pose is quantized, and no radius/support rule changes.

Full 8-value source/reference parity, cached Boolean and swept-edge parity,
rotation implications, legacy/support/ENV parity, 171 existing tests, H00/A02,
fixed controls and timing are required before freezing. Constructor time and
memory are reported separately. A performance miss remains a failed candidate.

Development01 passed geometric parity but had no useful timing gain. Its index
was consulted only after associative-cache misses. Development02 queries the
sufficient-free bound before that cache and uses the Boolean-only radius bound;
full margin results remain unchanged. Preserve both timing and source revisions.
