# v266 — Finite-surface arithmetic qualified; full model not accepted

Later v267 input-topology audit found1,414oriented boundary edges in the
original asset. Its global oriented-ray filling assumption is invalid for
open surfaces. Do not adopt this model as a physical solid classifier; v268
will distinguish closed solids from open two-sided surfaces. The arithmetic,
endpoint and FCL controls below remain valid within their declared tested
geometry domains.

Frozen manifest SHA-256:
`ef93f05dbb230d4440e0a9dc8abf7f0abfccf4c36cbfd453b8cdab542d563da2`.
All 22 returned files match their manifest. This is independent component
validation, not PCT/SCAN integration, a new benchmark pass or physical acceptance.

The explicitly authorized new model uses original finite Newton triangles.
Near-floor material is removed only under finite upward caps at their actual
affine height. Walls, columns, high steps and low ceilings remain solids.
Continuous ray heights and a containment check avoid both fictitious occupied
slivers and the hollow-mesh failure for a body entirely inside a thick wall.
No requested pose, cylinder radius, RL or scanning parameter changed.

## Independent checks

- 14 declared physical geometry controls pass: floors, walls, columns, finite
  wall ends, steps, ramps, stacked floors, ceilings, containment and floor edges.
- 3,300 finite-surface FCL comparisons: zero differences.
- 4,004 filled convex Box/Cylinder FCL comparisons without shared clipping or
  filling logic: zero differences; includes near-contact and containment.
- 400 height-translation controls and four sloped-cap height-band controls pass.
- Nonfinite queries are rejected normally. Planning calls and physics steps: 0.

| Fixed endpoint | Source-surface radial solid margin |
|---|---:|
| CU08 start / CD12 goal | +0.005710 m |
| CU13 start | +0.000850 m |
| CM01 start | +0.006812 m |
| CS01 goal | +0.003241 m |
| CE01 goal | +0.011273 m |
| CE03 goal | +0.019715 m |
| B08 real-wall control | **-0.133340 m**, refused |

All seven fixed refused endpoints are free in this source-surface diagnostic.
CU13 is geometrically legal but very tight; this is not a dynamic robustness
claim. The old voxel queries remain negative and retain their original ledgers.
CM01 additionally remains UnknownSupport in the unchanged native support map;
source-solid freedom does not waive that independent gate. The cap-union
support diagnostic is not a connected-support or leg-contact certificate.

CE03's source witness has downward normal and lies under the actual 4.533031m
floor; its old proxy floor label differs. CM01's source voxel mixes upward
platform and vertical faces. Five other old sign changes involve occupied-voxel
padding; exact occupied voxel boxes still reject all seven. Finite source
geometry and correct material association are separate from tightening padding.

The first prototype's height-event rounding error and its correction are
retained in `development/attempt01` and `development/attempt02`. The final
model also restricts ramp cap subtraction to the clipped admissible height band.

Dependencies are pinned in [summary.json](results/summary.json): python-fcl
0.7.0.8, Shapely 2.1.2, NumPy 2.5.3 and SciPy 1.18.1. Sources, raw witnesses,
logs and hashes are in [manifest.json](manifest.json). Regenerate remotely with
`inspect_source.py`, `validate_primitive_oracle.py`, `validate_surface.py`, then
`seal.py`. Original arrays/PCD remain on gpu5070ti. Python overlay construction
is diagnostic; native query correctness and total planning latency are separate
v267+ gates. No baseline promotion, commit or new video.
