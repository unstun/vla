# v267 — Native finite-surface component port

Unqualified experimental component. Parent geometry is independently tested
v266, not the old occupied-voxel domain. Preserve v261 source/install and both
fixed benchmark ledgers. No production planner or physical execution change
until native geometry parity and timing are measured.

Reuse Boost.Geometry's immutable R-tree for conservative finite triangle
broad phase. Narrow phase clips original triangles to the actual finite body
interval, subtracts only actual finite near-floor cap volumes, and evaluates
radial clearance to surviving projections. An oriented-source-ray check covers
closed-solid containment, where a hollow triangle collision test alone fails.
Keep continuous source heights; no endpoint movement or coordinate rules.

Require independent v266 Python/FCL parity on original source endpoints,
synthetic CAD primitives and seeded original-scene queries. Benchmark actual
CPU2 cost before connecting this component to StaticSolidField. Existing
support/unknown gates retain authority; source-solid freedom cannot waive them.
RL, 0.35m radius, 0.18m offset, vertical interval, step/height thresholds and
0.1s scan/deadline remain unchanged. No formal route attempt in this component.
