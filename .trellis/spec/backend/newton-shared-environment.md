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
  `assess(body, yaw, gap=nullptr)` returns edge/solid margin in metres, normalized penalties,
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

## 8. Support-aligned GPMP Z (v229)

GPMP's legacy height smoother and truncated XY lookup can disagree with native
canonical support cells. In configured shared mode, use matched optimizer
layers, canonical PCT cell, original ENV225 surface height, valid proxy/ceiling
and both original native height-tolerance bands. Prefer surface+reference height
inside their intersection, with a quantization inset. Nominal body clearance is
not an invented hard minimum: that disconnects native-feasible steps. Preserve
XY polyline and original endpoint Z; densify collinearly and bound neighboring
height transitions. Missing/ambiguous/empty association rejects, and the final
native reference checker remains mandatory. This does not prove Z dynamics.

## 9. Persistent local obstruction feedback (v230)

LIVE feedback must preserve the original reactiveOccupancy binary query and
return its exact typed reason through CheckTraversability STATIC_AND_LIVE. A
binary 1 includes unknown/stale/outside and cannot be called a solid obstacle.
Use an immutable snapshot, unchanged freshness checks, stable native source IDs,
observation time and map revision. Rebuild interfaces/provider/client together
when the service schema changes.

Pull current managed reference evidence when createPlan runs; the existing
Header/BT chain only wakes planning. Bind retained witnesses to mission/epoch
and stable source, independently of Path timestamps. Only fresh typed solids
become directional, height-associated constraints. Unknown never clears them;
a strictly newer exact-pose/yaw Free or bounded steady-clock expiry permits
reconsideration. Keep witness positions fixed while deduplicating neighbors.
Reuse the existing derived A*/GPMP map and final connector/rotation sampler;
check persistent constraints on every return, including terminal/error cache.
Per-call static repairs use the current authoritative native final verdict,
not an old expanded search mask. Explicitly query graph headings if needed;
do not infer every heading blocked from one oriented footprint.

Require actual installed PCT blocked/unknown/cleared/new-mission routes, blocked
terminal cache rejection, native typed/binary and stable-source recorded parity,
and the unchanged full-goal Building route. Component wire fixtures and recorded
native replay are separate from a live NativeWorker/closed-loop sensor run.
See v229/RESULTS.md and v230/RESULTS.md for exact gates and remaining latency.

## 10. Frozen endpoint matrix and physical selection (v242)

For same-map generalization, freeze requested ground XYZ, start yaw and source
identities before scored calls. Keep candidate discovery and scored calls in
separate ledgers. Physical floor/ENV support is not PCT graph reachability;
an early `pct_no_route` has not exercised GPMP, shared static review or SCAN.
Retain that failure in overall denominators and report later stages as N/A.

`versions/v242/native_probe.cpp` uses the installed plugin and STATIC_ONLY
native service, explicit0.3m reference height, and managed RouteSession with
`infer_heading=true`. Its global stage has no case-live feedback yet; that
optional query returns unavailable. The local stage applies each case's own
paired original-ray body/sensor/cloud, then public setReferencePath and the
first original FSM round. A target proposal is not a valid spline publication.
Fresh processes prevent warm/session/repair leakage. Fixed ROS capture epochs
measure geometric admission; wall durations do not establish live scheduling.

Preserve source ages and typed native unknown-space gates. Report raw cylinder
center observed/unknown/outside counts separately from native live admission;
do not convert a native measured-body allowance into100% observed coverage.
Original-PCD oracle and case non-terrain returns are distinct margin sources.
Keep the0.15m positive cap explicit and missing later-stage margins as N/A.

| Condition | Evaluation behavior |
|---|---|
| Global search fails before static query | Global failure; GPMP/SCAN untested |
| Goal cost exceeds native threshold | Preserve requested goal and early rejection |
| Boundary group never reaches neighborhood search | Required branch coverage unmet |
| Fewer than two eligible physical cases | No physical launch; no new video claim |
| First curve passes but raw centers contain unknowns | Retain both facts; do not widen original permission |

Use original rebuilt admission-probe byte parity and positive/stale native
controls before source freeze. v242 records12x5fresh calls, with only A02
passing5/5; this is a measured failed coverage gate, not evidence of RL failure
or generalized physical validation. v243 remains unfrozen preparation.
`V243_CASE_ID` and selection.json cannot bypass
`physical_admission_passed=false` in case_binding.py.

For endpoint attribution use actual poseToIndex/Search and raw source records.
The inherited Astar::GetNeighbors method is an empty stub; search expands its
own kNeighbors loop. Its zero return is not evidence of zero reachable neighbors.
Wrong: select replacements after observing failures or call five repeat passes
five independent physical successes. Correct: preserve the matrix and separate
conditional first-SCAN success from the full60-call denominator and physics.

## 11. Rejected endpoint treatment and retained graph diagnosis (v244)

**2026-10-18 decision:** Dr Sun rejected this architecture. Preserve the
frozen experiment and evaluator corrections as evidence; do not adopt or
extend its anchor enumeration, component exceptions or extra geometry veto.
The next treatment returns to v240 and separates native physical admission
from ENV225 soft clearance. The following describes historical behavior only.

### Scope and signatures

Triggered by the frozen v24212x5endpoint matrix, followed by Dr Sun's explicit
repair authorization. Implementation lives in version-owned
`lite3_nav2_plugins/pct_route_planner.{hpp,cpp}`and`pct_planner.cpp`.
`plan(start,goal,smooth,start_yaw)`retains the original request. Optional
`enableEndpointRecovery(body_geometry,support_gap,EndpointCheck)`requires an
exact-PCD veto, the unchanged gap mask and native STATIC_ONLY service callback.
PCT parameters: `endpoint_recovery`(defaultfalse),`static_body_path`,
`static_body_fnv64`,`support_gap_path`,`support_gap_fnv64`.

### Contracts

Try the original map/search first. Recover only after`pct_no_route`; retain the
original raw map. A derived proposal graph may cross original costs>20when
physical height/ceiling/floor association is available. Recovered transitions
require actual continuously oriented cylinder/gap checks. Floor/atlas evidence
is a proposal filter; it cannot replace final native selected-surface review.
Anchor candidates stay on the requested physical level within1.2mEuclidean
radius, original cost<=20, with deterministic distance ordering and at most8
admitted candidates per endpoint. Check the actual connector at2.5cm/0.05rad,
including measured start heading, then preserve exact requested positions.
Final native whole-reference, feedback and SCAN curve/dynamic/epoch checks
remain mandatory. Geometry failure may consume original GPMP retries and use
the existing third graph attempt; report that fallback instead of calling it
first-GPMP success. No new downward gateway rule is justified by this dataset.

`StaticBodyGeometry`uses the original ENV224Bsolid point/material association,
0.35mradius,0.18moffset,+.55/-.35native source offsets and original conservative
voxel-representative padding. It is an extra static veto, not live observed
free space, a future foot-contact proof or a mesh-contact oracle. Preserve this
padding in raw-PCD margin reports; distinguish conservative voxel intersection
from proof of physical body contact. ENV225remains the shared soft atlas.

### Validation and errors

| Condition | Required result |
|---|---|
| Recovery absent | Original planner behavior |
| Recovery enabled without native checker | Configuration error |
| Geometry/gap identity or declared shape differs | Configuration error |
| No bounded geometry/native-approved connector | `pct_endpoint_no_safe_anchor:start/goal` |
| Candidate pair not connected | `pct_endpoint_recovery_disconnected` |
| Smoothed candidate fails exact geometry | Ordinary rejected attempt; no publication |
| Final native static or SCAN fails | Retain rejection; never accept on soft evidence |

### Good, base and bad examples

Good: compare actual Search, directed layer transitions, original pre-mask
costs and exact connector witnesses before selecting a repair. Base: A04/G07
exhaust1232states; the region existed as1337cells before v135. R11/R12reach
layer0but their goals are in that region; actual original-library paired
up/down searches both succeed to a connected downstairs point. Bad: infer a
0.53mwall-inflation cut or downward-gateway defect solely from a floor picture.
v135's0.53mmask is negative-support coverage, while ENV225cost is separate
from the raw node-cost threshold. Stored-slice SCCcounts and A*'s shared
(height_bin,x,y)closed keys have different denominators; label both.

### Required tests and receipts

Require original-PCD cylinder equivalence (v244:2000random queries), finite and
identity failures, actual native refusal of an available start connector,
unchanged default-mode tests and all original fixed cases/fresh processes.
Require route XYZ, typed native requests, exact real goal, observed/unknown
coverage, original source/install/model/sensor hashes and first-GPMP versus
third-attempt graph counts. Retain every scored call and failure. Native
component success is distinct from the later case-owned physical run.

### Wrong versus correct evaluation

Wrong: require the first returned polyline row to equal the measured body,
then label the unchanged v242A02route a native failure. Correct: verify the
original native sampler includes the real measured-start connector and verify
the real goal; preserve both as-scored wrapper flags and the independently
checked approved-protocol ledger. v245's extra row flag reports50/60; original
native protocol reports55/60with byte-identical A02routes. Do not rewrite
frozen source to repair an evaluator. Preserve v244's pre-call syntax failure;
use a new evaluation entry and keep all correction receipts. Physical
representative admission does not imply every matrix case or boundary branch
passed. `GoalSearch`function-call counts alone do not prove an obstacle-driven
neighborhood traversal; retain actual source/reason/branch context.

Sources: v244source/manifest/tests, v245matrix adapter, and
`audits/2026-10-18_v244_endpoint_connectivity`diagnostic/protocol ledgers.


## 12. Generic native physical support treatment (v247/v248)

This is an experimental treatment, not the selected baseline. It starts from
frozen v240 and replaces the rejected v244 anchor/component treatment.

- Restore the original PCT bundle; remove v135's all-heading0.53m cost=50
  preprocessing from the active path. Strict ablation shows removal alone does
  not reconnect the1232-state region (1337after removal), and original high
  costs still cause legal-endpoint refusals. Do not describe mask removal alone
  as a connectivity repair.
- `static_support.h` owns a pure helper shared by GridMap and PCT. Its immutable
  `SUPPORT247` snapshot exports native raw/scored support with SHA/FNV binding,
  original gap mask,0.35m radius,0.18m offsets, nearest-layer semantics and
  original0.26m step limit. It supplies static support only, not live obstacle
  freedom, full body-mesh clearance or future foot coverage.
- PCT associates tomogram proxy slices to physical support before expansion;
  equivalent physical-floor slices share an observed upper bound. Its opt-in
  physical mode uses symmetric supported-neighbor enumeration, bypasses raw
  cost admission and DecideLayer/gateway veto, and uses ENV225as the clearance/
  terrain soft objective. The legacy raw-cost GPMP residual is disabled in this
  mode. Default mode remains covered by the original tests.
- Project height against the hard support snapshot, not ENV's margin-dependent
  floor availability. Typed GPMP optimization failure consumes the original
  two smooth attempts then the existing third graph attempt. Report fallback
  honestly: all55admitted v247calls use graph fallback; GPMP first passes0/60.
- Static-only/full-reference admission, cold/live SCAN collision/dynamics/epoch
  checks and original PD/RL/sensor limits retain their original authority.
  A55/60component result is not55whole-route body-clearance proofs: B08has a
  negative independent voxel-solid reference margin. Unknown coverage and the
  ENV+0.15m cap must remain visible.
- The frozen12x5matrix and H00fresh six-ray fixture use actual installed C++
  components, no physics. Native helper parity10855queries has zero typed or
  exported-admission mismatches;97native regression cases and6PCT CTest targets
  pass. Preserve failed development ledgers and final source/install identities.

v248's four-node lifecycle ACTIVE check uses existing GetState clients before
real goal-session dispatch, with the original5s dispatch budget and ordinary
failure closure. Zero-physics process preflight cannot prove ACTIVE while TF
is unavailable. Never inject fake TF/clock or use a fixed sleep as evidence.
Require installed bridge SHA parity and actual ROS readiness tests (25passed).

Physical analysis uses the measured goal-request boundary through the first
real `arrived=true` driver-journal observation; planning wait remains included.
Clip staircase/body-Z intervals to that navigation window, particularly for
upstairs factory starts. Final PD uses the measured FIXED_STAND suffix with
policy ownership false. ENV soft margin and native StaticSupportField verdict
are separate report fields. Return complete failed prefixes as failed videos,
never as completed routes. Measure actual post-PD start drift before attributing
a live no-route result to the frozen nominal-start matrix.


### v248 measured outcome and diagnostic limits

The three single physical attempts are1/3full-route passes (R11), with A02/G07
retained failures. R11arrives and closes measured PD but has4whole-navigation
>=1spauses, including2in the full floor transition. Do not promote nominal
55/60component admission into physical generalization or select a new baseline.

Post-PD body drift must be checked separately from nominal zero-physics scan
fixtures. A02's measured pose is native SupportGap even though ENV/raw margins
are positive. Do not bypass a hard support refusal using soft fields or a
connector. Actual body support Free and a candidate endpoint occ=0also do not
prove the swept connection or planning yaw is free: G07's last seed round
fails before optimization and later shared global review refuses two poses.

`reactive_collision_blocked`is a shared one-second-throttled query log. A
future-route UnknownObstacle sample is not evidence it was selected as the
actual local target or caused the final failure. Inspect the subsequent target
and seed sequence; report the first refused edge/typed sample as missing when
it was not captured. Do not apply the old long-search starvation diagnosis to
a1.905msseed failure. Preserve source timestamps/revisions in future targeted
replay rather than add an unproven target-selection rule.

## 13. Continuous support and smooth physical-mode optimization (v249–v251)

- The native raw/scored floor snapshot is the physical-floor authority. A
  missing PCT slice alias (`planning_ground=-100` or `ground_valid=0`) does not
  prove the native floor is absent. Associate the actual continuous XY and
  immutable reference height using the existing legal height band. Use the
  canonical grid convention in GPMP and projection, and reject ambiguity or
  actual missing support. LM trial evaluation must not mutate height hints.
- Physical mode recomputes output heights from associated native floors and
  skips the legacy unconstrained height smoother. Final dense projection and
  original oriented static support remain mandatory; optimization completion
  is not admission. Preserve the requested endpoints and explicitly review the
  measured-start-to-optimized-first-point connection.
- `SupportGapMask` retains original uncertain source squares but uses bins
  only as a broad phase. Test each continuous cylinder center against the
  original source square at radius0.35m and height band0.26m. Do not inflate
  target cells a second time. Keep true gaps and source-cell conservatism.
  A02's old post-PD verdict is a verified target-cell false positive: the
  original mesh has0.378376919m rear-disc clearance, above the same0.35m.
- GPMP feasibility and final checks use the same oriented gap geometry.
  Legal support has zero feasibility residual; violated support contributes
  the existing feasibility residual with position/yaw derivatives. Include the
  velocity-to-yaw chain in node and interpolated WNOJ/WNOA factors. Check
  nonfinite states before indexing, and test zero-speed and optional Jacobians.
- ENV225 remains the sole clearance soft objective. Its existing edge channel
  takes the minimum of original floor-edge margin and signed clearance to the
  same uncertain gap sources, at both oriented centers. Preserve0.15m target,
  weights and atlas bytes. Pass the same mask to PCT search, GPMP, SCAN and
  current metrics; do not use positive soft clearance as a hard gate. A larger
  candidate-bin reach must not alter the binary hard domain. The C++ API change
  requires rebuilding all consumers, including separate evaluation probes.
- Bind source, installed files, actual fixture bytes and evaluator binaries
  before scoring. Keep source/build receipts separate from qualification.
  Check native97, physical-factor tests,10855typed/export parity queries,
  unchanged12x5matrix and independent historical H00/endpoints. Counts, failed
  attempts and first-GPMP admission are explicit; B09no-route stays in the
  denominator. Never overwrite frozen versions for a later repair.
- A saved published-cloud-prefix replay preserves original times, stamps,
  body/twist and route but does not recreate unavailable asynchronous mapper
  memory. An unlogged global service request cannot be identified uniquely by
  its rejection count. Label body-window candidates as reconstructed, and
  recheck the same candidate poses after repair rather than claiming exact
  historical request identity. No new physical success follows from replay.
- Clear cached CMake dependency paths when composing a new native overlay:
  a new plan_env build alone does not replace a cached parent plan_env_DIR.
  Verify actual includes/linkage and freeze the installed inventory.

## 14. Physical binding and measured-start coverage (v252)

### Scope / trigger

Use a separate execution version when physically evaluating frozen native
repairs. v252 binds native v251 and the unchanged frozen v248 bridge; it owns
run identity and case evidence destinations, not another planner treatment.

### Signatures

`V252_CASE_ID={A02,G07,R11} python3 versions/v252/preflight_runner.py` performs
zero-step checks. After freeze, the same key with `launch.py` starts one
formal attempt. `V252_RENDER_ID=03` selects only a new recorded-state display
root. `measured_start/run.py` performs independent offline native queries.

### Contracts

Bind source/install/fixture/evaluator inventories and the inherited bridge.
Verify actual lifecycle ACTIVE before goal and actual loaded native libraries.
Keep original scenario bytes, RL, 0.35 m and 0.1 s period/deadline. Formal
launch-once ledgers must reject an existing attempt. A display retry cannot
invoke physics, alter the source capture or overwrite its recording.

### Validation and error matrix

| Condition | Required result |
|---|---|
| Continuous measured pose Free, PCT search no-route | Report both; support alone does not establish connectivity |
| Missing raw time window | N/A, not zero pauses |
| Ordinary Nav2 failure | FAILED closure, retain full failed prefix |
| Display manifest paths differ by predecessor format | Verify using that pinned format/root, preserve failed display logs |
| Goal/PD pass but achieved planner frequency below 30 Hz | Scenario pass; sustained-30-Hz remains unvalidated |
| Existing formal ledger or changed frozen bytes | Refuse another launch |

### Good / base / bad cases

v252 G07/R11 pass route/PD with zero mid-cross-floor long pauses; startup wait
and terminal settling remain included in whole-navigation counts. A02 has
64/64 continuous Free samples but its rounded start searches only 18 unique
grid nodes and fails before GPMP. Its two initially valid unique neighbor
states must not be inflated by counting stored aliases as independent exits.

### Tests and assertion points

Require the original route verifier, unchanged endpoint/PD tolerances,
period/deadline scan counts, whole and geometry-relative pause denominators,
gap-aware native/body margins and independent raw-cloud comparison. Check
every causal rendered frame, complete first/last recording states, local full
decode/hash/frame counts and representative visual samples. Keep the physical
attempt count independent from the number of display passes or internal replans.

### Wrong versus correct

Wrong: promote nominal-start admission or a continuous Free verdict into a
claim that the post-PD grid-start route is reachable. Correct: retain the exact
measured request, native verdict, canonical grid center and a fresh native
search result, while leaving the failed formal attempt and source unchanged.

## 15. Continuous mission endpoints and grid attachment (v253 / v254)

- Physical-mode requests retain actual continuous start/goal XYZ. A rounded
  index supplies a one-cell candidate neighbourhood only; the index centre is
  never substituted for the requested endpoint. Native floor association uses
  actual XY/height and the original legal step band, independently of a missing
  stored slice alias. Transient endpoint nodes do not occupy rounded closed-set
  identities. Ordinary grid expansion and legacy mode remain separate.
- Every start/goal connector uses those coordinates through dense swept
  `transitionAllowed`, the same planning heading and gap-aware ENV225 scoring.
  Include both endpoints in the cost integral. No unsupported endpoint may
  borrow a neighbouring supported centre; no real cliff may be bridged.
- Search output contains actual endpoints. Both GPMP orders initialize priors
  from them and impose exact boundary positions before GP interpolation;
  dense native floor projection retains the requested endpoint heights within
  the unchanged tolerance. The full static reference/SCAN checks still admit
  or reject the result. A two-endpoint same-cell request is not an empty path.
- Preserve floating-point edge lengths in legacy mode: cast integer index
  deltas before norm. Eigen integer norm truncates a diagonal sqrt(2) to 1;
  an accumulated-search-score regression detects this even when route shape
  tests pass. Physical endpoint distances use fractional positions/true height.
- Copying sources with preserved old mtimes can retain a stale test object
  after an initial build. Verify test-case names against actual source, not
  just CTest target count. Rebuild a stale target from identical frozen bytes,
  preserve its original receipt, and return the complete rerun separately.
- Freeze source, installed files, fixtures and evaluator binaries before the
  scored 12x5 protocol. Saved A02 coordinates must pass first GPMP/static
  review with zero endpoint error; H00 and every previous unit/native gate
  remain required. Single physical validation has its own execution binding
  and launch-once ledger; retained predecessor videos do not become new runs.

## 16. Exact geometry acceleration and continuous endpoint heading (v259–v261)

### Scope and trigger

Apply when accelerating the shared static collision/support queries or changing
PCT physical endpoint connections. The selected experiment baseline is a
separate decision. Geometry existence, source-solid freedom, cold local
publication and physical execution are separate gates.

### Signatures

- `StaticSolidField::collides(body, yaw, StaticSolidQueryCache&)` uses a
  caller-owned request cache; `assess(body,yaw)` retains exact margin,
  gradient and witness evaluation.
- `EnvironmentalField::cost(body,yaw,gap)` may omit derivative work, while
  `assess` and `costGradient` preserve their full outputs.
- `PCTRoutePlanner::plan(start,goal,smooth,start_yaw,goal_yaw)` preserves actual
  continuous endpoints. `plannedYaws()` supplies the checked reference headings.
- `poseDistanceLowerBounds(grid,goal,resolution,necessary)` is a relaxed
  distance bound, never an admission result. `SetPoseAngularLowerBound` must
  receive a nonnegative lower coefficient of the actual edge objective.

### Contracts

Broad-phase bounds may prove freedom or decline to prove it; uncertainty must
fall back to the original query. Keep source records, floor exemptions,
conservative voxel padding, comparison ordering, radius and vertical intervals.
Do not turn an occupied coarse bin into a collision mask. Cache bins select
anchors only: actual query coordinates are never rounded. Shared geometry is
immutable; request caches retain their source owner and reset per request.
Cross-height reuse requires unchanged relevant source-floor classifications.

Dense support/gap indices must preserve record order and exact original source
squares. Finite original-mesh floor augmentation may restore physical floor
presence without declaring the swept body free. A floor underneath an overhead
stair structure does not prove a complete route through that structure.

Actual start/goal yaw belongs in the same swept hard-support/solid and ENV225
connection evaluation as XYZ. Keep distinct heading states near boundaries;
merge only after proving all-heading freedom and retain/check every emitted
turn. Keep headings through GPMP projection and RoutePolicy. Exact equal-height
floor aliases may be quotiented only in the relaxed XYZ-only graph. No claim
of global pose-turn objective optimality follows from open-heading merging.

Scalar ENV specialization must preserve value arithmetic and the original
1e-12 selection guards. Skipping unused gradients cannot change a cost or
admission decision. Preserve nonfinite-query errors and callback containment.

### Validation and errors

| Condition | Required behavior |
|---|---|
| Coarse bound or cache class uncertain | Original exact scalar query |
| Source owner changes | Reset request cache |
| Invalid finite-domain query | Original typed/exception behavior |
| Requested endpoint pose or swept turn invalid | Ordinary no-route/rejected attempt |
| Smoothed heading/support/solid check fails | Original safe retry/fallback or refusal |
| Old publisher metadata disagrees with frozen augmented clouds | New execution metadata binding; do not modify frozen geometry |
| Clean coverage/timing gate fails | Preserve scores; no conditional physical launch |

### Good, base and bad cases

Good: v259 keeps 70,928 full solid query outputs and 5,000 sampled edges
identical to the isolated v256 oracle; its old 52-case median falls from
16.4555 to 1.4689 seconds on CPU2. Base: v260 restores the six eastern support
connections, while the declared body still meets real source-solid barriers.
Bad: count the floor-only paths as six fully traversable routes or blend the
unchanged old positive labels with the new certified-positive denominator.

### Required tests and assertion points

Require binary, capped margin, gradient and witness equality; support typed,
gap, height and gradient equality; scalar ENV equality with and without the
actual gap field; finite-cylinder boundary/floor-switch tests; rotated free/core
proof checks; exact-height alias metamorphic distance equality; exact XYZ/yaw
endpoints and dense connections; both GPMP orders and unchanged native tests.
Run H00 and the saved measured A02 pose without moving requests. Record cold
initialization separately from global planning. Freeze source/install/fixtures/
evaluators before each scored once-per-case matrix. Report all refusals and
first GPMP separately from a safe graph fallback.

### Wrong versus correct

Wrong: retain an expensive precheck because it is named an optimization, or
keep adding an auxiliary heuristic that barely changes expansions. Correct:
measure its total cost and remove it when exact scalar queries are faster.
Wrong: rotate a position-only route after search. Correct: search/check the
requested continuous heading transition and preserve it through final review.

## 17. Finite source geometry and equivalent acceleration (v270–v272)

### Representation boundary

`SURFACE271B` is an explicitly authorized alternative to the retained
`SOLID256B` voxel field. Its descriptor pins triangle and closed-volume
metadata bytes with separate FNV identities. Both PCT and SCAN must load the
same descriptor/profile. Keep the legacy parser, query arithmetic and failure
ledgers; source radial margins and padded voxel SDF values are different
quantities and must be reported separately.

The current profile is radius0.35, offset0.18, body clearance0.30 and the
unchanged vertical interval `[bodyZ-0.55, bodyZ+0.35]`. Source clearance is a
capped radial distance to material intersecting that interval, not a 3-D SDF.
Physical floor presence/support/height transitions remain independent hard
gates. Source-solid freedom cannot waive UnknownSupport or SupportGap.

### Source topology and material

Keep original vertices and triangle connectivity. Existing Trimesh topology
checks may normalize face winding only in certified closed positive volumes.
Open or non-volume components remain two-sided finite surfaces; never infer
filled interior from a global winding sum over the whole open asset. Do not
fill holes or round ray-hit heights to decimal bands.

Terrain subtraction uses finite upward caps and their actual affine height,
with the unchanged strict0.26m band. Cap eligibility and projected-distance
geometry are separate: a tiny polygon can be ineligible as a floor cap while
its interior still obstructs the body. Closed-object terrain shortcuts require
complete eligible upward-cap coverage. Preserve low/high ceiling, reversed
closed object, open roof/wall, tiny face and exact step-contact controls.

Use bounding boxes to recall cap candidates, followed by finite3Dclipping.
An exact2Dintersection prefilter can lose interpolated shared edges. A fragment
wholly above a cap's maximum Z cannot intersect the removed volume and may be
excluded without repeatedly partitioning it into unchanged fragments.

### Immutable kernel and query cache

Keep source geometry in a private compilation unit. Adding a large inlined
kernel to legacy arithmetic changed a few libm-dependent outputs at about
1e-16; separate compilation restored the required bitwise legacy equality.
Do not silently relax the equality gate.

Precompute triangle Z ranges, projected areas, complete cap planes and stable
volume pointers. Reuse a full cap only when the whole triangle strictly fits
the original height band; retain the original clipping path for partial caps.
Keep candidate ordering and witness tie behavior. All geometry is immutable
once constructed and safe for concurrent readers.

A Boolean query may return at its first fully material-clipped collision
witness. Full assessment must still return the original margin, XYZ/yaw
gradient and actual3Dwitness. A private early-negative value is a collision
witness distance, not a promised nearest signed distance.

Source memoization is caller-owned and resets with the source owner/request.
Actual height bits identify the fixed clipped obstacle set. XY bins select
nearby anchors only; never replace a query or requested endpoint with a bin
center. At identical real height, triangle inequalities establish two bounds:

- Positive complete clearance minus XY displacement may prove freedom.
- A fixed collision witness remains inside the cylinder when displacement is
  smaller than its radial intrusion, proving collision.

Numerical guards only decline a cached proof; uncertain queries use exact
geometry. Do not import voxel3DSDF or cross-height continuity assumptions.
Retain newly computed anchors and preserve owner lifetime. Test both signs,
neighbor-bin reuse, exact wall tangencies, height changes and owner changes.

### Required evidence and evaluator contract

The implemented seams are the v271 StaticSolidField dispatch and the v272
private `source_surface_geometry.cpp`; v272's isolated v271 reference checks
90,477 complete outputs bit-for-bit. Require source cache/swept parity, actual
witness/gradient checks, independent physical controls, old70,928-value and
5,000-edge equality, and inherited native/endpoint regressions.

Local curve audits must use the actual
`GridMap::collision_heading_lookahead_s` (currently0.8s), including zero-speed
endpoint fallback. This is separate from the unchanged0.1s LiDAR period and
freshness rules. Preserve old0.1s-heading as-scored results and label any
protocol-corrected derived result separately.

Keep source radial, unvoxelized raw-point, old voxel, ENV and live-observation
margins distinct. A raw-point floor association recall bound cannot move raw
points, body poses or thresholds. Pin external audit dependencies as well as
native libraries. Complete timed native requests before parallel CPU audits.
Freeze every cohort and keep all requested cases/labels and failed outcomes.
Component qualification does not establish the50-case gate or physical
success. Physical execution requires the declared coverage/smoothing/timing
and resource gates; preserve other users' active IsaacLab work.

### Scope, signatures and binding fields

Apply this section when loading source triangles, accelerating shared hard
geometry, or scoring a source-model native installation. Public
`StaticSolidField(path, fnv)`, `assess(body,yaw)`,
`collides(body,yaw,StaticSolidQueryCache&)`, `coreCollision(body)` and
`certifiesFreeRotation(body)` retain their call signatures. Private
`source_surface::Field::circleMargin(x,y,ground,radius)` may return an early
nonpositive witness value; `Field::assess` retains the complete value/witness.

The source descriptor contains:

```text
SURFACE271B radius offset up down clearance target
"triangle_path" triangle_fnv64
"volume_metadata_path" metadata_fnv64
```

Bind `PCT.static_solid_path`/`PCT.static_solid_fnv64` and
`grid_map.static_solid_path`/`grid_map.static_solid_fnv64` to those same bytes.
The native evaluator obtains both from `RAW_FIELD`/`RAW_FNV`; support and
`ENVIRONMENT_INPUT`/`ENVIRONMENT_FNV` remain independently pinned.

### Validation and error matrix

| Condition | Required behavior |
|---|---|
| Root/dependency identity, volume bounds or fixed profile mismatch | Reject construction; no silent voxel fallback |
| Nonfinite query | Preserve exception/typed-failure containment |
| Open or uncertified object | Two-sided surfaces only; no inferred interior |
| Source obstacle free but support unknown or insufficient | Retain support refusal |
| Different real height | Reuse only a proven v279 positive height envelope covering this actual height; otherwise exact query |
| Different source owner | Reset the request cache; no reuse of the former certificate |
| Cached bounds inconclusive | Exact source query |
| Full benchmark timing or coverage fails | Preserve the ledger; no conditional physical launch |

### Good, base and bad cases

Good: v272 precomputes cap data while preserving every component of90,477
queries against frozen v271. Base: v271 admits the six development controls
but does not establish the full clean benchmark gate. Bad: label an open
roof's entire lower half-space solid, waive CM01 support because its source
solid margin is positive, or treat the old padded margin as the new radial
margin's numerical oracle.

Wrong: use the source field as a3DSDF across changing height, or suppress a
failed old benchmark after improving its evaluator. Correct: prove each
fixed-height certificate geometrically, retain exact fallback and old scores,
and record a separately frozen once-per-case cohort before physical use.

### v279 height-envelope proofs and v280 endpoint constraints

The exact-height certificates above remain valid. A v279 positive envelope may
also cover a 0.01 m ground interval: use the union of body vertical ranges,
intersection of strict terrain-cap eligibility bands, and only material volumes
eligible at both height extrema. A positive conservative envelope plus the XY
triangle inequality certifies freedom. A nonpositive envelope is inconclusive;
query the actual height exactly. Never cache an envelope collision as a collision
at every height. Negative witnesses remain bound to exact height. Full assess
values and gradients retain the original exact kernel.

Qualification requires 114,477 complete source outputs bit-identical to v272,
24,000 height-boundary checks, legacy/support/ENV parity, and existing native
tests. Timing must be measured on unchanged full cohorts, separately from cold
initialization; development timing alone does not establish the full gate.

v280 anchors the complete initialized GPMP endpoint state with GTSAM
NonlinearEquality in both optimizer orders. Use the installed default elimination
dispatch, which chooses QR for constrained factors; do not force all factors to
QR. This fixes boundary drift, not arbitrary intermediate collisions. Reuse the
existing solid-query cache for GPMP physical residuals: a certified free sample
has zero residual; collisions and uncertain cases use exact values/gradients.
The six endpoint assertions fail on frozen v272 and pass on v280. Preserve
remaining first-pass failures and report both admitted-case and all-positive
denominators (v281: 44/48 and 44/50 respectively).

The retained ENV edge proxy can differ from the physical support field. At the
v281 CE03/E03 witnesses, ENV is negative while actual 0.35 m hard support is
Free with +0.15 m capped physical gap margin. Report both quantities under their
own names; never substitute one for the other or change the frozen cohort.

### Physical evaluation does not collapse arrival and geometry into one flag

Keep recorded FINISHED, requested-goal/terminal-PD acceptance, and measured
support/solid clearance separate. In v282, four routes reach the goal with PD,
but D07/CD12 still show negative measured solid-envelope margins and CD12 has
four SupportGap samples. Only S04/CM07 combine arrival/PD with a clear sampled
geometry screen. Report every case in the original ten-case denominator.
Ten-hertz measured body checks do not certify continuous motion or foot contact.
Keep failed terminal prefixes and full videos, and retain resource overlap.

`pct_endpoint_pose_rejected` calls `poseFree`, which includes repair/live-feedback
constraints as well as static support/solid geometry. It is not a typed support
failure. Positive recorded geometry with that exception requires replaying the
actual request and feedback witnesses; do not introduce a support waiver based
on the exception string. The frozen cohort remains unchanged during diagnosis.


### v287 local-cost correction

v287 supersedes the v286 exact-source rebound/unknown-air query additions. First-stage local scoring uses only the existing ENV225 atlas; the quadratic one-sided penalty and gradient remain active at nonpositive margins. There are no new mesh searches or local publication vetoes. Refinement keeps no environmental term. See newton-local-search-phase.md section11 for native derivative controls, original occupancy provenance, full-round versus optimizer timing, and actual fatal-signal evidence. Native qualification and complete53-case admission do not certify a physical repair.
