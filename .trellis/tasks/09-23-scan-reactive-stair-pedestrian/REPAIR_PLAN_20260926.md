# Sequential repair plan after the cause review

Dr Sun explicitly authorized sequential repairs and asked the agent to select
the most reasonable method without optimizing for elapsed time. This continues
the active experiment/analysis task. Existing source snapshots, original runs,
frozen collision thresholds and sibling repositories remain unchanged.

## Step 1: native search bookkeeping

The gap is at native A* discovery and open-queue handling: an occupancy-rejected
neighbor is marked explored without entering the queue; mutable pointer scores
also invalidate priority ordering, and initial infinite cost is zero. Repair
these together in an isolated scan_20 candidate derived from hash-pinned scan_19.
Change only `path_searching/dyn_a_star.{h,cpp}` plus task-owned materializer,
native regression fixtures and execution evidence. Do not add heading state,
alter occupancy calls, change the heuristic, relax any collision threshold,
or move map/actor input in this step. The 0.2 s search bound includes discarded
obsolete queue records.

Use a native test that compiles the actual source against an injected collision
fixture: blocked-first/free-later, decrease-key queue order and stale entries,
reuse across search rounds, no-path, and vertical movement. Demonstrate the
original failure before the candidate pass. Then build in the pinned Foxy
container and replay the same captured inputs. Report graph search, seed edge
validation and moving spline generation separately. A successful graph search
does not certify a collision-free accepted trajectory.

### Step 1 result and next search/seed boundary

scan_20 passes six native regression groups including 256 Dijkstra-oracle maps.
The old implementation fails the three targeted bookkeeping cases. A mutation
that removes the real improved-cost enqueue is caught by the new integrated
test. The complete Foxy build and source/install gates pass. On the exact
diagnostic input prefix, 179 graph-search failures become zero graph failures
and 179 seed-edge rejections. No moving spline is yet produced.

Before changing the independent tracker, address this newly isolated boundary
in scan_21: search must reject edges that fail the same half-cell sampling and
heading rule already enforced by seed validation. Place the shared segment
checker in the native map/collision layer and call it from both A* and seed
verification. Keep the same occupancy rule, sample spacing, thresholds and
unknown blocking. Verify a thin obstacle between free endpoints and a detour,
then rerun the identical captured-input prefix. This order follows observed
failures rather than combining the fix with tracker input changes.

## Step 2: tracker ground coverage

After step 1 is tested and recorded, separate physical ground coverage from the
robot-traversability cost mask. Preserve sensor-derived observations and exclude
actor truth from runtime input. Define the meaning of incomplete coverage and
complete-empty observations before changing the producer/consumer contract.
Replay both original and right-side recordings and test missing/stale support,
wall/ground clusters and stationary scenes, not just the known actor position.

### Selected perception contract after offline probes

Do not adopt full-ground plus 3D Euclidean clustering: it produces 23/22 track
IDs and no complete actor tracks in the original/right full sequences. Use the
published static Building PCD as an explicitly pinned **tracking-only** prior,
then keep the existing XY shape clustering and current-observation association.
The PCD is imported under
`references/upstream/2026-09-26_pct_building_static_background/`, pinned to
Robot-Nav/legbot_3D_Nav commit f60606a and SHA-256 8721efeb…1f2eae, in raw frame.
The offline threshold is frozen at 0.10 m nearest-static-point distance, 5 m
current sensing range, and at least 80% background alignment. Full-record
probe results: both placements yield 189 complete actor frames, one ID,
no pre-motion tracks, no outside-actor tracks, and no missing foreground ground.
Truth is used only for posthoc scoring. These are feasibility results, not ROS
or live timing acceptance.

Implementation boundary for scan_22:

- Add a strict pinned-PCD loader/current-cloud foreground selector and a thin
  fail-closed wrapper around the unchanged tracker core. Missing/wrong map,
  invalid pose/cloud, poor static alignment, unsupported foreground, stale
  inputs and unresolved/lost tracks must not produce a complete clearing batch.
- Keep every raw sensor point supplied to SCAN. Static subtraction applies
  only to tracker candidate extraction, never navigation occupancy.
- Publish full finite PCT ground on independent `/tracker_ground`; preserve
  `/pct_tomogram` bytes and its robot-traversability filter. The tracker decoder
  explicitly accepts at most 200,000 ground records (current map 149,504), while
  the raw cloud bound remains 100,000. Ground height lookup has no cost mask in
  this mode and retains separate provenance.
- Emit a new source ID, `sensor_lidar_static_background_cluster_v3`, and stage
  the verified prior from VLA into each runtime package. No sibling runtime
  dependency, simulator actor positions, motion prediction, or velocity prior.
- Verify pure negative cases and full-record wrapper replay, then real ROS
  decoding/topic/stamp/source integration before a bounded live scene.

## Step 3: remaining stair and episode boundaries

Step 2 recorded-input component acceptance is complete in scan_22: all 562
captured frames match local, frozen Foxy and installed ROS processing; each
placement has 189 complete actor frames, one ID and no pre-motion/building
false tracks. Nineteen unit tests and the independently reviewed same-byte
schema negative case pass. Live V3 input wiring is prepared separately.

The next isolated candidate, scan_23, bounds both native terrain layer
associations by the existing 0.26 m step capability. Missing/ambiguous compatible
layers propagate Unknown across the entire scoring window. This intentionally
does not make a blocked route free. Native before/after fixtures establish the
old false six-meter step; all 86,775 real selected-ground records are compared.
No new traversable record appears, and 15 prior traversable records become
Unknown. The old high-box and wall cases retain final collision rejection.

After the identical-input replay, inspect the first native search component in
a separate logging-only copy. Record existing collision verdicts, checked edges
and popped nodes without extra collision calls; defer log output until search
returns and retain its original 0.2 s bound. This is diagnostic evidence with
instrumentation overhead, not a timing benchmark or an accepted live candidate.

Inspect same-level support association, candidate height/heading consistency,
continuous seed/spline collision validation and settled goal dispatch one at a
time. Add targeted diagnostics only when the previous result identifies the
next blocker. Keep unknown/out-of-map blocked. Use bounded live simulation
only when source, sensing and native trajectory gates are meaningful; return
real video and contact/fall/timing records. No formal training or physical actuation.

Each completed step records source hashes, exact commands, tests, result and
remaining limitations before the next step begins. No baseline or prior verdict
is silently rewritten; no partial planner result is called validated avoidance.

## Subsequent evidence and repair order

The scan_23 first-search observer found only eight reachable grid states and
0.15 m forward progress; no time-cap hit or dropped query was involved. Front
queries become WrongHeight, while raising the body makes rear queries Unknown.
A single-call 0.158 m short-prefix probe passed graph/seed validation but failed
the original spline optimizer. It is not adopted for execution. A separate
1 mm endpoint-height sweep of the next edge found zero accepted values among
121 probes; this does not support changing Z discretization to force a pass.

The review also found that initial spline safety checks cover only the first
two thirds. scan_24 adds complete final/remaining interval sampling after final
optimization and dynamics checks, with explicit endpoints, valid relative-time
and spline-layout checks, unchanged heading, and half-voxel translation bounds.
Native actual-UniformBspline fixtures, full Foxy build and identical recorded
replay pass their declared gates. The replay still has no moving spline, so
real GridMap cost on an accepted moving curve is not yet measured. Sampling is
not a continuous rotating-footprint proof.

The next evidence-backed repair is height semantics. Actual fixed V12 sources
on the execution host match the local immutable reference: reward root-height
target is 0.30 m, while initial root position is 0.35 m. Two hundred stable
standing samples have median base-minus-ground height 0.296544 m. The launcher
had used the spawn value as SCAN/PCT/backend planning reference as well. Split
these explicitly in new packages: preserve spawn 0.35, V12 and all tolerances,
use the pinned reference 0.30 in SCAN, native PCT, backend ground/arrival
conversion and runner goal-height metrics. Validate both loaded registry values
and source hashes at runtime. Regenerate native PCT routes for paired CPU
comparisons; never vertically shift a previous route and label it native output.

The new prepared package is `walk_scan24_height030_right_v1`. It has not yet
been executed. Its source/config tests pass; independent review and native
PCT/SCAN comparisons precede any live navigation claim.

The paired comparisons completed: the native-PCT 0.35 control has 180 seed
search failures; the corrected 0.30 reference has zero search failures but
179 seed-edge rejections. Both have zero moving splines. Counts are callbacks,
not performance evidence. See `step6_body_reference/PAIRED_RESULT.json`.

## Step 7: exact endpoint consistency

The manager currently overwrites the last lattice node after search, changing
the last segment's heading. An actual-C++ controlled fixture reproduces an
originally clear edge becoming blocked at sample 0 after this change. The
Building log's edge 74 still requires path-size and original-geometry evidence.
`scan24_endpoint_trace` is a logging-only package for that question.

`scan_25` is locally prepared directly from scan_24: strict seed endpoint mode
checks an explicit terminal edge from popped lattice nodes within two cells
in 3D, continues after failed connectors, returns the exact goal, clears old
path state on every call, and includes terminal checks in the existing .2 s
budget. The manager stops overwriting endpoints and retains all edge checks.
Default optimizer search behavior and every collision/Unknown threshold remain.
Eight final endpoint fixtures and eight existing native search/segment cases
pass locally; the old build fails the five declared endpoint-contract cases.
Independent source review found no blocker. Full ROS/runtime evidence is pending.

Automatic approval review rejected the diagnostic remote build before execution
because explicit source-transfer authorization to gpu5070ti was not recognized.
Dr Sun subsequently replied “授权”, approving this destination and the bounded
build/replay/simulation scope. Execution resumes under that explicit approval. See
`step7_exact_endpoint/LOCAL_RESULT.md` and `REMOTE_APPROVAL_BLOCK.json`.


## Steps 8–9: preserve the safe seed through resampling

Actual step7 diagnostics confirm last-edge replacement changes yaw by9.10deg;
scan25 removes all seed-edge failures (162 checked seeds), but optimization
still fails. Both full Foxy build and eight Foxy endpoint regressions pass.

The first-replan scan25 observer proves that the old 76→24 point resampling
already creates a blocked chord before fitting. It increases maximum point
spacing from.0866m to.3247m and deviates up to.0527m from the original polyline
in sampled geometry comparisons. Initial and optimized cubics fail independently.
See step8_spline_seed/RESULT.md, GEOMETRY_TRACE.json and the source-backed plot.

scan26 preserves all nonzero seed edges and corners with half-voxel subdivisions,
keeps total initial duration and records bounded quintic time-allocation error.
Exact duplicates retain raw-edge/vertex attribution; all output edges are checked
again using actual unchanged heading and collision rules. Its native five-case
suite (including real76points) and full Foxy build/install pass. All39 generated
chains in the same-input replay pass, with no resample rejection; all39 optimizer
calls still fail and no moving spline appears.

The scan26 first-replan observer has1622 records, zero drops and23 search calls.
The fitted curve first hits WrongHeight at2.33s and has a native derivative-control
acceleration bound142.61m/s^2; the optimized curve still hits WrongHeight at1.44s.
The optimizer returns after21 rebound cancellations, including repeated one-node
repair routes. Next repair is the empty-rebound/constraint-validity contract:
no new valid constraint must not trigger a new rebound; per-control-point
intersection validity must not reuse a previous index or uninitialized point.
The latter is a static defect, not yet attributed to this recorded failure.
All collider/Unknown/height/dynamic limits remain unchanged. No live walking
candidate has been accepted; right-side standing tracker video remains the latest
valid live integration artifact. User explicitly authorized gpu5070ti execution.

## Steps 10–12: rebound validity and execution-consistent curve timing

scan27 now commits only finite current-point rebound constraints and terminates
when a collision produces no new valid constraint. Ten actual-code Foxy cases
pass; the old source fails seven negative cases while retaining three positive
controls. Full build and same-input replay pass their declared gates: the first
21 rebound cancellations become one explicit final failure, with 77 checked
seed chains, 77 optimizer failures and no moving spline. This repairs failure
handling; it does not establish successful curve optimization.

The step11 post-failure observer directly isolates heading: at the first
rejected curve point, changing only preview yaw to nearest seed-edge yaw makes
the unchanged point clear; projection alone does not. Body and clock stamps
match. All-knots scaling derived from the native derivative bound preserves
centerline geometry and passes all 9,324 sampled checks, but changes PVA and
duration to 93.223 seconds. This is a diagnostic, never a published fallback.
The final gate and controller both use 0.8-second preview; changing only the
checker to seed yaw would contradict execution. See step11 RESULT.json/.md.

scan28 therefore isolates timing initialization, with the original end velocity
and limits. Fix first/last three controls from the supplied PVA and fit only
interior controls. Permit at most eight refits with an interval increase derived
from the unchanged native feasibility check, retaining original PVA each time.
Then run the original rebound optimizer and all final gates. Add a numerical
boundary residual gate before publication because the existing later native
soft refit can otherwise undo PVA. Do not silently scale terminal velocity,
change collision headings, relax Unknown or publish an unoptimized fallback.
An impossible boundary or exhausted iteration budget fails closed.

The actual native spline fixture reproduces the old soft-boundary drift and
infeasible recorded initialization before implementation. Native candidate
tests, independent source review, full Foxy build, identity and same-input CPU
replay precede any live candidate. Physical yaw tracking, rolling-state PVA,
timing deadlines and actual stair walking remain separate unclosed gates.

## Steps 13–14: correct replay frames and isolate the live input gap

scan28 completed eight native cases, full build, identity and original-optimizer
replay with one published moving cubic. Independent output verification found
that the historical replay mislabeled recorded world twist as base twist. Step13
restores direct body twists from the identical physics rows; original poses,
world twists, clouds, ground, tracks, route and config remain unchanged. New
paired replays confirm scan27 still fails and scan28 still succeeds. The latter
preserves recorded world start velocity within5.04e-11m/s; zero acceleration is
the original requested initial condition, not a measured quantity. Its duration
remains93.223s and all9,324 collision samples pass. Keep legacy frame evidence
explicitly labelled and preserve its bytes.

The new live scan28 trial is complete and recorded, but75 graph searches fail
before any seed validation or time initialization. No motion command is admitted.
The35s-cap trial ends after29.08s, following driver cancellation at27s, with
no nonfoot contact or reset. The inherited run_request45s field is stale metadata;
the actual argv/scope/pilot cap is35s. All49 artifacts returned with matching hashes.
The video was delivered and fully decoded. Do not label this as a walking result.

A fresh6.2s recorded input prefix reproduces search failure in CPU replay. Step14
therefore inspects exact first-search edges and existing occupancy verdicts,
without changing inputs, thresholds or Unknown treatment. A specific difference
is the voxel containing the sensor origin: reverse ray traversal excludes that
terminal voxel, so observed history can matter. This is a hypothesis until the
new first-search trace and per-cell update evidence identify a decisive blocker.

## Step 15: checked terminal recovery after strict search exhaustion

Step14 now has a same-map witness: the fresh first search reaches1,315 nodes
but only two are within the existing0.10m exact-goal radius; both connectors
fail. Post-failure probes find a fully checked0.154980m connection at rank14,
with body/clock both5.56999988s. This is not a curve or live-motion result.
The separate live sensor-origin Unknown cell is known in this full-history CPU
replay, so it is not a sufficient explanation for the fresh replay failure.

Predeclare one isolated repair: retain all normal strict search behavior and
default optimizer AStar; only after strict queue exhaustion, stable-sort longer
connections from current popped nodes by gScore*step_size+terminal_distance.
Use the same complete collisionFreeSegment and exact endpoint. Sorting, each
predicate and path construction share the original0.2s total budget; expired
success must be rejected. Calls are not preemptible, so this is not a hard
wall-clock guarantee. No support, Unknown, dynamic or final-curve gate changes.

Four new actual-native-source fixtures cover long clear/cost-ordered connection,
Unknown interior, total-budget overrun and repeated strict/default state reuse,
beside the existing eight strict cases. scan28 reproduces exactly the three
predeclared positive/recovery exercise failures; nine other cases pass.
scan29 is being tested locally before remote native/full-build/replay gates.
Keep failed test packages and all earlier runs. Do not commit or stage.


Step15 completed native12/12 local+Foxy, independent review, full build and
462-file install identity. Fresh identical-input replay now has63 fully checked
seed chains but zero moving splines: full final collision gate rejects the
first79.1561s curve at46.3477s. Old accepted input still passes and yields exactly
the same control points/knots as scan28. Terminal recovery is therefore qualified
for the captured graph failure, not accepted for live walking.

Step16 investigates the first rejected curve after the original rejection:
compare timed initialization with final optimization, record complete curves,
seed projection/heading and actual support verdicts on the same timestamp.
The optimizer initial-guidance pool error also exists in the old successful
case; it is not sufficient cause attribution. Its coarse prefix collision check
misses a failure caught by the complete final gate. No threshold or production
optimizer changes until the paired geometric evidence is returned.


Step16 complete: at the same5.56999988 map/body time, timed-initial first
collision51.07748s is only44.674micrometres from the seed, but16.672965deg preview
heading difference moves the front footprint onto WrongHeight. Same position
with seed yaw clears; projection alone does not. Final first collision46.3477s
is1.048976mm from the seed; either seed yaw or projection clears this point,
whose rear footprint is UnknownSupport. Full geometry, exact paired results,
hashes and independent spline-position reconstruction are archived in step16.
These point substitutions are diagnostic, not permission to change execution yaw.

Step17 scan30 therefore unifies both optimizer terminal checks with the existing
complete sampled curve helper, preserving all existing map predicates, .8s
heading, sample budget, original retries and manager final gate. This first
corrects success semantics. Observe actual paired finite constraint counts at
retry; no count alone proves a useful correction. Old seven-fixture suite has
six expected negative failures and one positive pass; candidate passes seven
fixtures on both native methods locally and in Foxy. Independent review passes;
full build and paired real-optimizer replay are in progress. The solver/map in
unit fixtures are doubles; do not call them full optimization validation.


Step17 full build/462-file identity and paired real-optimizer replays completed.
Fresh input:56 checked seeds,168 complete optimizer checks,168 bounded retries,
all stored valid-constraint counts remain0→0;zero moving publication. First three
checks retain identical first collision time and control squared norm; do not
claim byte identity from a norm. Old accepted input still publishes the exact
same controls/knots as scan28. The consistency defect is repaired without
claiming geometry repair or live acceptance.

Step18 captures initial and first retry guidance failure endpoints within the
same planning attempt, including actual control snapshots and indices. After
the original optimizer returns false only, an independent100³ AStar pool tests
same-endpoint strict search and rechecks any returned edges. Preserve original
false and never publish diagnostic paths. Source and body/clock stamps must
match; extra pool allocation/search is not production performance evidence.


Step18 completed: retry snapshot CP250/252 matches the component values of
final controls (max component delta0), same body/clock5.56999988s. Default
endpoint adjustment returns INIT_ERR; strict same-endpoint search finds a
three-node route, both edges clear and zero endpoint errors. Initial proxy
CP131/133 still fails strict search and differs from final controls, so do not
conflate its geometry with the full-curve retry. Original optimizer false is
preserved. This establishes a missed checked guidance route, not valid rebound
constraints or an accepted cubic.

Step19 scan31 changes only the two actual repair call modes:
initControlPoints(false) uses exact endpoints; its true first-init mode stays
unchanged. check_collision_and_rebound also uses exact endpoints, including
merged-segment retries. Existing control-polygon segmentation, assignments,
weights, limits, source maps and final curve checks remain. Native caller tests
now extract the full init method as well as full rebound detector, exercise
first/retry/callback/merge/failure/reuse modes, and verify unchanged endpoint
columns/control positions. The old source reproduces five expected mode
failures beside eleven positive cases. Candidate tests/review precede runtime.


Step19 complete: 16 native cases pass locally and in Foxy; source review,
full build and 462-file identity pass. Fresh input now generates paired
constraints (0→3→6) and executes 14 rebound cancellations before a no-valid-new-
direction stop, with 45 checked seeds and no moving curve. Old accepted input
continues to publish exactly the same controls/knots as scan28. Endpoint repair
is therefore exercised; overall navigation remains unaccepted.

Step20 observes the actual returned trial after original optimizer false, with
no change to STOP_FOR_ERROR. At the zero-pair branch it records controls,
flags/pair counts, final segments and paths; manager later checks the full
returned curve and compares geometry/heading. Verify snapshot equality before
attribution. LBFGS internally rolls q back on cancellation, whereas this wrapper
returns cps_ from the last cost callback; never call that returned trial a
solver-accepted solution. Neither a clear diagnostic trial nor valid stored
pairs alone establishes a publishable trajectory. The diagnostic log does not
include explicit per-path totals; validate observable indices and closing
markers, and avoid claiming unobserved segment completeness if ambiguous.


Step20 completed: all 428 stop controls match actual returned trial values.
The returned curve still collides at 45.837742 s and passes native dynamic
limits with the original configured feasibility tolerance; this is not a false
proxy stop on a clear curve. The observed CP249→CP257 segment has seven interior
controls, but its same-endpoint route has only two points. Each local normal
plane has both route endpoints on the same side; complete segment enumeration
also finds no crossing. Do not fix the midpoint walk: no geometric crossing
exists. The controls have folded away from the short checked repair route.

Step21 scan32 is a bounded geometric fallback candidate for precisely that
case, only in check_collision_and_rebound. If an entire segment has no finite
plane intersection and the exact-endpoint route/controls are finite, project
each internal control onto the route. Query that candidate with its own control
heading, then reuse the original base-point ray and guarded paired write.
No propagation to unqueried controls. Existing plane cases, zero-direction
rules, clearance/objective/weights/limits and full acceptance remain unchanged.
Nearest points are mostly the route's start endpoint in this recorded fold;
they are correction candidates, not along-route progress or safe final output.
Recorded/native fixture and heading/invalid-route/math counterexamples precede
real-map replay. Old case is red; candidate native checks/review are in progress.


Step21 completed: 21 native groups, review, full build and 462-file identity pass.
Fresh real-map replay creates six clear projection anchors/pairs but still reaches
the original 21 rebound cancellations; 40 checked seeds, zero moving curves.
The old accepted corrected-input curve retains identical controls and knots.
The geometric repair is exercised but does not solve this complete segment.

Step22 is an explicit REFERENCE_PATH planning-policy experiment. Keep the
admitted global route, goal and full duration; occupied-goal scan becomes a
refreshed point-free frontier only. A selected target time remains a proposal
until complete manager success; commit its actual adjusted time, including a
shorter accepted endpoint. After primary failure consider three halved-time
route prefixes with zero terminal velocity and the same start PVA, original
0.2 m separation/own-target-heading prefilter and all native acceptance gates.
Share the three-proposal budget across the existing outer initialization
modes, including blocked proposals. Actual order is primary1 -> prefixes ->
primary2 -> primary3, preserving primary relative order. Partial expiry uses
the unchanged replan branch and cannot replace the global goal.

Native fixture includes complete production methods and exact expiry block;
manager verdict, route and ROS are doubles. Corrected old fixture has twelve
declared failures and three positives; candidate scan33 passes all fifteen
locally, including finite-input-before-map, rejected-prefix budget and target
heading. Old fixture v1 incorrectly expected forward 5.75 rather than nearer
backward 4.5; v2/v3 correct this expectation and retain the original artifact.
Generator regeneration matches all93 candidate source files; only FSM source
and header differ from scan32. Real optimizer replay and actual motion are
still required; a planned zero terminal velocity does not prove physical stop.


Step22 stopping point: all15 final native cases pass on local clang and fixed
Foxy g++; independent review closed. Full scan33 build passed in80.644s with
matching before/after source hashes. Install identity capture then failed
twice at SSH handshake, records preserved as install_identity_failed_v1/v2.
Dr Sun reported server shutdown and requested archival. No further remote
retry, scan33 optimizer replay, live run or accepted curve. Resume at install
identity capture after continuation. Main-session archive only under current
inline instruction; no commit or task completion. Handoff: .pipeline/handoffs/
2026-09-26_scan_stair_handoff.md. Local M5/32GB can run native tests; an adapted
MuJoCo path remains a proposal, not an executed replacement of Isaac RTX.
