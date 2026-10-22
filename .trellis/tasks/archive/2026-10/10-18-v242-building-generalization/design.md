# Design: evaluate frozen navigation through case-owned adapters

## Baseline and version ownership

The installed v240 native implementation is the treatment; v241 is the already
completed original-route control, not a new experiment to rerun. v232/v233
remains the selected baseline. Do not edit frozen v238–v241.

Planned v242 owns the offline matrix, C++ probe and sensor-fixture/evidence
adapter. Planned v243 owns the per-case physical execution binding built from
v241. These are evaluation versions, not claimed new planner repairs. A later
algorithm change would require a separate version/task and fresh comparison.

## Case construction and freezing

Read pinned Building geometry, canonical support lattice and ENV225 first.
Identify flat, physically supported spawn regions and actual upstairs rooms,
corridors and corners. Floors come from the map, not hardcoded z=0/z=1.

The matrix has the following semantic strata (see matrix_plan.csv):

| Cases | Count | Coverage |
|---|---:|---|
| A01–A04 | 4 | Different downstairs spawn positions and headings into stairs |
| G05–G07 | 3 | New upstairs room/corridor/corner destinations |
| B08–B09 | 2 | Obstacle-edge destinations and native neighborhood recovery |
| R10–R12 | 3 | Reverse upstairs-to-downstairs routes |

Each pair differs from the historical pair. Include multiple spatially
distinct spawn and destination regions, not twelve slices of the old route.
Where geometry permits, target at least 1 m separation between representative
region anchors. Heading offsets include oblique and initially transverse
approaches. Preserve actual geometric coordinates if a region cannot meet
that spacing; document it rather than shifting endpoints into a wall.

Construction may screen spawn support and identify goal-boundary strata, but
must preserve its candidate ledger. Freeze requested poses and case IDs before
scored planner calls. No replacement of failures after seeing scored results.
Boundary requested goals may legitimately fail admission. Preserve their
denominator and reason. Never force a native branch to manufacture coverage.
The B stratum must include at least one observed neighborhood-search call;
preserve fixture-discovery queries and their typed obstacle/unknown/freshness
context. Failure to reach this branch is an explicit unmet coverage item,
not a successful substitute based only on geometric proximity to a wall.

## Native offline flow

1. Verify the v240 317-file composition, installed inventory, ENV225/raw-map
   hashes, effective parameters, loaded PCT plugin/route library/core, ldd and
   old/new GridMap ABI. Do not compile old planner source into the probe.
2. For each of five fresh instances per case, load its own start pose/yaw and
   native goal contract. Invoke actual PCTPlanner::createPlan through pluginlib,
   with the original native static CheckTraversability service.
3. Capture each GPMP attempt's path and static verdict, eventual admitted
   route, retries and graph fallback. The third-attempt A* fallback is not
   counted as first-attempt GPMP success. Record requested/canonical endpoint
   and generated terminal heading.
4. Sample accepted reference paths using existing translation/rotation rules.
   Assess ENV225 and original Building raw-cloud oracle margins, retaining
   floor-known flags, rejected samples and the 0.15 m saturation flag.
5. Build each case's local map from its own paired body/sensor/geometric-LiDAR
   captures using original callbacks. Use zero-physics static-pose captures
   for this component fixture and label them as such. Keep original cadence,
   evidence stamps/age and unknown space; do not translate/restamp v237/v241
   scans or equate the global static cloud with locally observed free space.
6. Feed that case's PCT route and measured-case initial execution state to the
   actual SCAN FSM with no historical accepted spline or warm binding.
   Observe route admission, cold first plan, original retries/connectors,
   full-curve/dynamic/epoch checks and actual normal spline publication.
   Record the final-goal neighborhood branch separately from forward-frontier
   reuse, warm connector and complete-plan failure.

Use separate fresh processes/instances per call, or a proven complete reset
of map/session/repair/feedback/warm/frontier state. The default is fresh
processes. Report cold initialization separately from createPlan and native
stage durations; report all five calls plus median and maximum. Repetition
exposes call/scheduling variation; it is not five independent learned policies.

## Margin and admission meanings

- Static support PASS is floor/height/edge/gap evidence, not live obstacles.
- ENV edge margin and the original raw-cloud oracle are capped at target.
  Report a saturated value as >=0.15 m, not an exact physical distance.
- Original Building raw-cloud oracle and current-case LiDAR are different
  source columns. LiDAR margin is only meaningful in observed local space.
  Include observed coverage and unknown/unobserved sample counts; N/A is not
  a pass, infinity or large clearance. Local first-curve coverage must satisfy
  the original native unknown-space gate.
- Keep per-stage rates and end-to-end rates. Missing input and early rejection
  remain explicit in end-to-end denominators, not silently omitted.

## Physical selection and execution

Predeclare one oblique-entry ascent (A stratum), one different upstairs
room/corner ascent (G stratum), and one descent (R stratum). Within each stratum
use fixed preference sequences A02/A03/A04, G07/G05/G06 and R11/R10/R12;
select the first eligible case with valid spawn, all native gates and a
usable case sensor fixture; preserve all excluded candidates and their reasons.
Do not rank by fastest solve or select only the largest-clearance cases.
If the R stratum has no admitted route, record that generalization failure
and execute the two admitted ascent representatives. If fewer than two total
eligible cases exist, stop at the measured offline failure and report it;
there is no permission to weaken admission to obtain two runs.

The new physical binding reads only frozen case scenarios with case-specific
run/container/ledger identities. Reuse v241's actual overlay, v237 scanner,
v216 activation and v232 driver. Expand the new profile's cross-floor map
binding so backend.map.pct_layer=None remains explicit. Preserve the original
factory spawn height, PD startup, RL handoff and inferred terminal heading.

Each selected case receives one attempt. Serial execution preserves the
original fixed ports and v241 resource controls (native 6 CPUs/6 GiB, CPU
physics), existing 600 s simulation and 900 s supervision bounds. Own-container
cleanup only; retain all failures. No further historical_full run.

## Verification and outputs

Generalize the original route verifier by replacing only its expected frozen
scenario identity/profile. Keep initial-frame/zero-step/spawn-yaw, continuous
state, no-fall, actual requested goal, shared-state, native FINISHED, endpoint
errors and measured FIXED_STAND/PD rules. Compare numerical rule values to the
original frozen files rather than entering new tolerances in the adapter.

For new routes locate stairs by geometry/floor transition and approach by
route progress/goal floor. Also retain requested raw fixed-time windows where
reached. Use 20 ms measured horizontal speed for >=0.5 s and >=1.0 s counts,
cumulative/split pauses, with startup and valid goal hold separately labelled.
Keep command/curve coverage separate from measured motion. Descending motion
has no prior physical validation; frozen-RL failure remains a result.

Return per-case JSON/CSV, source/install/config hashes, per-stage native logs,
frozen scenarios, all call outcomes, per-run physical metrics and complete
source-verified videos. Bulk point clouds/maps/build cache remain remotely.
Use the existing renderer/causal checker with per-case identities; no state
interpolation, hidden pauses, fabricated holds or future trajectory overlays.

## Approved repair follow-up —2026-10-18

Dr Sun's attachment explicitly authorizes a separate native repair treatment
(v244), directed graph diagnosis, the unchanged12x5matrix and three physical
representatives after offline admission. This supersedes the original
evaluation-only scope for the follow-up; immutable v242 remains the negative
control and v243 remains unfrozen blocked preparation. Preserve all12requests.

Diagnosis confirms the1232-state region existed before v135 (1337cells
pre-mask), and R11/R12 reached layer0but their goals belong to the isolated
region. Raw terrain/inflation cost already exceeded20at A01/A03/B08/B09;
ENV225 shared cost is separate. Do not claim a downward-gateway fix without
a demonstrated downward defect.

The v244 proposal graph has opt-in, exact original-PCD/gap-geometry checked
connections, bounded endpoint anchors and unchanged requested endpoints.
Native selected-surface/final-reference and SCAN publication remain mandatory.
Original static geometry is an extra veto, not live observation or foot proof.
Local source is authoritative; compile/test in private gpu5070ti execution
copy and return compact evidence/full actual physical videos locally.

## User-directed simplification — 2026-10-18 (supersedes v244 treatment)

Dr Sun explicitly rejects extending the v244 endpoint-anchor/component approach.
Preserve frozen v242/v244/v245/v246 evidence but do not adopt or extend v244.
The next treatment starts from frozen v240 and owns a new integer version.

1. Remove v135's all-heading 0.53 m cost=50 preprocessing; measure actual
   installed C++ Search on all unchanged12 requests before/after removal.
2. Separate hard physical standability (original0.35 m oriented double-cylinder
   static support, legal floor/height transitions) from ENV225 soft clearance.
   Do not convert soft terrain/inflation cost into a hard dead zone.
3. Diagnose actual upward/downward transition symmetry. Use generic adjacent
   supported surfaces if a transition fix is justified; no Building-coordinate,
   component-label, multi-anchor or scenario-specific exception. Endpoint
   tolerance, if needed at a true physical boundary, must be minimal and bounded.
4. Re-evaluate unchanged12x5 native chains plus the historical route control.
   Only after qualification execute three new representative physical routes
   and return every actual trial's complete video locally. Keep RL,0.35 m,
   0.1 s sensor/deadline and all final live/dynamic/epoch/PD gates unchanged.

Status correction: v246 A02_attempt01 finished case_failed/nav2_goal_rejected;
no complete route and no G07/R11 attempt. Diagnose graph readiness separately
from algorithm changes. Preserve this failed physical prefix and its receipts.


## Approved generic mechanism repair follow-up — 2026-10-18

Dr Sun authorizes implementation, not only review: (1)restore first-attempt
GPMP smooth physical-mode output by diagnosing optimizer/layer versus support
projection failures, (2)reproduce and repair G07near-end seed/connection on its
saved original cloud/body/route history with first rejected edge/sample/yaw/
typed verdict and the two global rejected poses, (3)verify A02post-PDgap against
original mesh/PCD and repair a mask representation defect only if established.
No scene/endpoint snap exceptions; keepRL/.35m/.1s/requests. No new full-route
physical attempts or commits are authorized in this follow-up.

Main session implements and checks inline. Read-only source research is
parallelized. Work owns new versions beginningv249and a dated diagnosis audit;
frozenv247/v248and all original recordings stay intact. Each independently
frozen logical repair gets its next integer. Expected production boundaries:
PCT map query/layer association and support projection; native seed edge
collision diagnosis and its proven physical mismatch; SupportGapMask/generator
only if exact source geometry establishes a representation error. No broad
refactor, new recovery state machine, anchors or component branches.

First reproduce with actual installed C++, record ranked hypotheses, capture
raw GPMP/layer/projection witnesses, preserve G07timestamps/twist/latest route,
and explain ordered-prefix versus unavailable asynchronous-memory state.
Then lock regressions at the actual seam, repair the confirmed mechanism,
rerun native/static/dynamic/freshness gates and unchanged12x5plusH00component
controls. Report first GPMP admission independently from fallback and any
remaining failings. A02genuine gap remains refused with original radius.


## v253 continuous endpoint contract

See `versions/v253/PLAN.md`: two transient real-coordinate graph nodes and ordinary one-cell connections; unchanged swept support and shared cost, actual GPMP boundary coordinates. No endpoint substitution or scene rule.
