# v23 native component results

Native scan56 builds successfully in 66.544 s. The frozen native source has
97 files and is unchanged through the build. `runs/v23_native_regression01`
passes seven actual native stopped-state continuations: original 66/67-frame
cases, v18, v19 twice, and v21 twice. Every accepted curve passes boundary PVA
and the full-curve collision check; no-progress, out-of-map and stale rejection
remain active. The new v21 prefix is 1.256635186 m in both repetitions.

All eight unmapped fixture outputs are exactly equal to v21, including complete
query results, paths, checked edges, unknown and stale handling. No semantic
messages enter these cases. This is a fixture regression result, not a claim
about every obstacle configuration.

Actual ROS source tests reject malformed layouts, missing inputs, wrong frame,
future/expired inputs and invalid delivery order. A changed source removes all
17 old positive voxel grants while retaining nonterrain history. Additional
contract tests establish one source rather than OR, preserve the empty-topic
classification, and retain original scored support. The latter directly tests
the CollisionDecision interface with explicit free obstacle evidence; it is
not labeled a whole-map physical query.

Mapped-protrusion results require a separate acceptance rule. Each row has
489 same-height footprint queries (free / free with object-envelope overlap):

| Mapped fixture | v21 | v23 |
|---|---:|---:|
| 13 cm low box | 387 / 114 | 387 / 114 |
| Low box beside wall | 187 / 46 | 195 / 54 |
| High box | 109 / 0 | 109 / 0 |
| Short wall | 75 / 0 | 75 / 0 |
| Overhead | 10 / 0 | 10 / 0 |

The eight additional near-wall free queries overlap the low protrusion's
navigation envelope. This is an acceptance-domain change, not measured solid
contact. The original baseline already accepts mapped 13 cm terrain; neither
this result nor the eight unmapped cases settles whether independent mapped
low boxes must always be avoided. That user-policy question remains open.
The physical Building trial has no newly added objects and can proceed within
its existing authorized scope. No physical navigation acceptance is recorded
by these component tests.
