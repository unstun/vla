# v260 — Original finite floors and physical graph association

Frozen offline source/evidence repair, parent v259. Manifest SHA-256:
`938e039f659ce3419fbe335d307f793f9e26722fec44e125faa08d15975e4b94`.

Original upward Newton triangle intersections recover floor heights lost by
vertical tomogram reduction. Old selected input records remain byte-identical.
New physical-presence records and standing candidates have distinct roles:
standing candidates also require actual vertical chassis space. Unchanged native
fill, step score, gap mask and 0.35 m hard solids retain admission authority.
The source geometry is 16,448 original triangles, SHA-256
`f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc`.

PCT now represents selected native floors even if their tomogram aliases were
lost. Physical GPMP height projection no longer treats a slice cut as a physical
ceiling; real overhead obstacles remain enforced by the exact shared solid field.

Validation:

- 62 plugin tests, 97 native regressions (10 overlap), and 4 finite-mesh extraction tests pass.
- Fresh native support export: 125,522 records; FNV64 `15212154834549674106`.
- 12,219 live-vs-shared queries: zero typed/admission differences.
- A04 and G05: first-GPMP global/static admission; 1.5003 s and 1.7394 s at two CPUs.
- U11/U12/D09/D10/D11/D13: all six support-only diagnostic searches now connect; all six full-solid searches correctly remain rejected under the current solid model. Original point/mesh barriers remain. This is not six successful full routes.

The earlier infinite point-plane extension caused a GPMP regression and is
preserved under `development/point_plane_attempt`; it is not the final producer.
A decoder regression briefly failed when fed changed bytes while asserting the
old fixture identity. Its original assertions remain and run on their frozen
fixture; fresh input behavior is covered separately by the 12,219-query parity.

Original 52 labels/results remain intact. No clean50 acceptance, physical run,
video, commit, archive or selected-baseline promotion is claimed. RL, endpoints,
0.35 m hard radius and 0.1 s scanner period remain unchanged.
