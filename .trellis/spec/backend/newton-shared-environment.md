# Shared floor diagnostics and environmental costs

## 1. Scope / trigger

The v223-v228 overlays extend the imported PCT/SCAN navigation experiment.
They share native geometric evidence and a static soft scorer. They do not
change RL, selected-surface predicates, live evidence freshness or command gates.
The version reports, not this spec, determine physical-run acceptance.

## 2. Signatures

- `GridMap::physicalSupportDiagnostic(body)` associates an existing physical
  floor for explanation only.
- `reactive_stair::Verdict::EdgeClearance = 12` is appended; values 0–11 stay
  stable. `reactive_collision.h` owns the enum.
- `EnvironmentalField(path, fnv64)` loads one immutable `ENV225` export;
  `assess(body, yaw)` returns edge/solid margin in metres, normalized penalties,
  terrain difficulty and `floor_known`. `cost(body, yaw)` returns the shared
  scalar score.
- `costGradient(body, yaw, Vector4d&)` returns analytic world XYZ/yaw
  derivatives; `GridMap::environmentalCostGradient` feeds the SCAN chain.
- `PCTRoutePlanner::setEnvironmentalField(shared_ptr<const EnvironmentalField>)`
  installs the same evaluator in search and both GPMP orders. Null clears it.
- `GridMap::environmentalCost(body, yaw)` feeds SCAN's
  `BsplineOptimizer::calcEnvironmentalCost(control_points, gradient)`.
- Bridge `write_profile(..., environmental_manifest=None)` binds both consumers
  to the same field identity. Launch argument: `environmental_manifest`.

## 3. Contracts

Physical-floor association is separate from `selectedSurface`. Only the exact
evidence-fill guard witness may relabel a missing selected floor as
`EdgeClearance`. Preserve the original binary rejection. A physical floor or
an offline torso intersection result cannot grant future foot support.

The environmental manifest carries `format`, relative `file`, `sha256`,
`fnv64`, `terrain_manifest_sha256` and `static_pcd_sha256`. Profiles pass
`grid_map.environmental_path/environmental_fnv64` to SCAN and
`PCT.environmental_path/environmental_fnv64` to PCT. Native shape and body
clearance must match the export. Missing optional manifest retains legacy mode.
`optimization.lambda_environment` is zero by default and 1.0 in the candidate.

The v224 candidate retains radius 0.35, offset 0.18 and vertical inflation
up/down 0.55/0.35 m. Its target extra margin is 0.15 m. With
`p(m)=clamp((target-m)/target,0,1)`, shared cost is
`p(edge)^2 + p(solid)^2 + 0.25*terrain^2`. It saturates at zero above the target;
it does not reward increasing distance indefinitely or enforce road-centering.
Native inflation offsets `[-down,+up]` imply obstacle-source offsets
`[-up,+down]` around the query, not the reverse.

Floor edge distances use native physical-floor drop evidence; terrain uses the
pinned ETH adaptation. Static solid points come from the declared original PCD
and native return classification. Below-floor annotations affect this static
soft view only. Exclude a voxel for a queried level only when **all** retained
points associate with that level; mixed/unassociated points remain. Other-floor
evidence remains. No simulator mesh or FCL result enters planner decisions.

PCT adds the nonnegative graph term after legacy `<5` truncation. Its GPMP
factors retain the legacy residual and add a second independent residual,
including interpolated factors, bypassing legacy `<=15`. SCAN scores actual
cubic-curve samples and propagates position/lookahead-heading derivatives to
control points in rebound and refinement. At zero squared hinge cost its exact
gradient is zero; avoid redundant finite-difference geometry calls there.
Full final-reference/connector and final-curve hard validators remain required.

From v225, static solids use an offline single-cylinder XYZ float32 atlas,
trilinearly sampled at both continuously oriented centers at unchanged body Z.
The original height-selected edge/terrain channels remain bilinear. No runtime
KD-tree or finite-difference cost queries. This is an explicit approximation:
raw material-exclusion events in Z are discontinuous, and large errors occur
near some events. Report ordinary percentiles and worst switch-band errors;
analytic derivative parity is not raw-geometry parity. The atlas is soft only.

From v226, configured shared-mode legacy terrain-cost interpolation is anchored
at integer PCT cells. The inherited `floor(x-.5)` patch with integer weights
extrapolates and jumps at half-cell boundaries. Preserve its arithmetic when
the environmental callback is absent. Do not hide this discontinuity by larger
weights or weaker termination. Heading remains coupled to current velocity;
its derivative is required. A frozen-seed-heading diagnostic must also freeze
the residual value while retaining endpoint-velocity effects through GP position.

Support cell identity requires the original SHA-bound PCT header lattice, not
the float32 cloud's minimum point. v227's physical-origin-only attempt fixes old
witnesses but creates equivalent corner failures; it is a preserved failure.
v228 `TerrainBundle.native_parameters()` binds `support_lattice_enabled` and
the nominal origin `center-(size//2+.5)*resolution`. Only qualified matching
navigation/scored/physical sources with near-integer offsets use this lattice.
Normalize double-arithmetic ULPs at integer boundaries, then use half-open cells.
Pass the explicit cell to `CollisionDecision::supportVerdict/decide` for body,
associated-floor and footprint/final checks, and the same diagnostic lookup.
Do not change source point coordinates, raw/scored heights, classifier grids,
ETH adjacency, selected labels, height tolerances or evidence-fill drop guards.
Unconfigured sources keep original indexing. Interior proxy-height mismatches
still reject; never select a convenient supported neighboring cell.

## 4. Validation / error matrix

| Condition | Required behavior |
|---|---|
| Existing floor fails 0.35 m evidence-fill guard | Report EdgeClearance; keep rejection |
| Unknown physical floor, explicit gap or another native rejection | Preserve that independent reason |
| Field/terrain hash mismatch or incompatible native shape | Refuse configuration |
| No optional environmental manifest | Preserve legacy planning mode |
| Margin at or beyond target | Zero clearance penalty and zero gradient |
| Same XY, different floor or heading | Evaluate the associated level and oriented body |
| Smoothed route fails native check | Repair within existing budget or truthful no-route; never publish it |

## 5. Good / base / bad cases

- Good: identical pose/yaw and field bytes give identical PCT/SCAN components;
  an active soft term changes actual search and optimization in controlled tests.
- Base: v217 48.10519028 s associates floor 1.5580306959 m but retains the
  0.2828427125 < 0.35 m rejection. This square-gap measure is not foot margin.
- Bad: A* gains clearance, GPMP loses it, and only graph output is reported as a
  successful integrated route. Report both stages and final admission separately.

## 6. Required tests and evidence

Require exact floor guard/native verdict tests; fixed-input binary parity;
SHA-bound nominal lattice, half-open/ULP boundary and mismatched-source tests;
heading/layer/saturation checks; both GPMP orders and interpolants below old
thresholds; one-Jacobian optional calls; actual SCAN gradient/L-BFGS displacement;
actual PCT corridor selection; profile identity/tamper checks; unchanged hard
admission/cache/freshness/terminal regressions. Measure real-map latency too.

Reject counts need explicit query denominators. Edge guard, historical 1/0/1
occupancy and extra cylinder-versus-torso intersections overlap: report their
intersections and a separate mutually exclusive first-reason ledger. A torso-only
substitution count must hold every support/unknown predicate fixed. It is not
an executable route or full-leg collision result. Independent FCL/score oracles
are test dependencies only. Return compact receipts and exact source hashes
locally; retain heavy exports remotely with SHA-256 and regeneration commands.

## 7. Wrong vs correct

Wrong: erase the edge rejection to recover a floor; add the three overlapping
cause counts; claim a smoothed/admitted route from A* improvements alone.

Correct: recover the physical association for diagnostics while retaining hard
admission, preserve separate causes, inspect search/smoothing/final admission,
and distinguish component validation from a new physical run.

Sources: version-owned `v223/RESULTS.md`, `v224/PLAN.md`, `v224/RESULTS.md`,
`v225/RESULTS.md`, `v226/RESULTS.md`, `v227/RESULTS.md`, `v228/RESULTS.md` and
the corresponding frozen source/inventory receipts under
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/`.
