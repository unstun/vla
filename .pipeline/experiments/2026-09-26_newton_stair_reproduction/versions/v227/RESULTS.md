# v227 failed physical-origin alignment attempt

Status: component-validated, full-route gate failed. Do not promote this profile.
Parent v226 and all failed probes remain frozen. No new physics or actuation.

Nine packages and 166 colcon records (146 distinct cases, 20 wrappers) pass.
The explicit support-cell API reaches body, floor association, both footprint
centers, final static/live checks and the diagnostic. Heights, scored labels,
source clouds and classifier indices are unchanged.

Three exact previous final WrongHeight points become Free under native static
support checking. However, actual installed PCT final admission still fails in
both modes, each on one new raw-graph corner:

- Legacy: (6.8046852111816412,5.4631887435913091,4.88125).
- Shared: (6.5046852111816413,0.76318874359130873,3.410546875).

Their current canonical cells select navigation heights 4.455177/2.956061 m;
the same physical cells have 4.533031/3.060884 m floors. Native body-height
residuals 0.126073/0.154486 m exceed the unchanged 0.12 m tolerance. The local
physical four quadrants are flat; only the northwest navigation proxy is low.

The physical origin itself comes from float32 minimum points. Relative to the
original PCT header lattice it is displaced by (2.0000019073,2) cells rather
than exact (2,2), approximately 0.19 micrometres in X. Aligning other grids to
this origin merely changes the corner's selected quadrant. It does not define
a consistent nominal half-open lattice. v228 binds the original SHA-verified
PCT header origin instead. No neighbor search, height adjustment or threshold
relaxation is justified by this failure.

Original v217 replay: all 126,324 original queries and three exact planning
queries preserve binary decisions against v223. Each independent occupancy
predicate (including historical 1/0/1, torso and unknown) has zero changes.
The 48.105 s floor remains associated at 1.558030696 m, edge-guarded and
rejected. See `results/replay_comparison.json`. Heavy CSVs remain remote at
`gpu5070ti:/data/sun/vla_mppi_20261009/environment_support_v227/replay_output01/`;
the compact comparison records their SHA-256, sizes and regeneration inputs.

Soft route geometry/score is identical to v226; the shared smoothed route
still has 26 WrongHeight samples. The observed 0.644 s planning time and
0.0367 ms SCAN environmental evaluation are offline component measurements.
Actual plugin no-route times are 0.230/1.018 s; no admitted route is claimed.
