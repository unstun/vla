# Frozen-v240 Building endpoint coverage requirements

## Goal

Evaluate whether the terminal-continuity repair works beyond a single fixed
Building route. Measure native global/local admission and physical outcomes
across different start positions, start headings, destination regions and
travel directions. A failure is an evaluation result, not permission to tune
the policy or relax guards.

## Confirmed facts

- The requested original-route control is already complete: commits b709a7d6
  and e5f640ba contain v238–v240 source/evidence; execution v241 passes one
  historical_full physical route at 121.424896 s with 4.357605 s measured PD.
  Its full and v237 comparison videos are delivered. Reuse that control.
- The local repository is authoritative. Frozen v240 native source/install,
  v232 graph/driver, v237 scanner repair and v216 RL/stance remain available.
- Installed PCT plugin admission includes search, GPMP, height alignment and
  native static support review. Static support does not establish live LiDAR
  collision clearance. SCAN has a distinct first-plan/publication gate.
- Existing physics already accepts scenario spawn XYZ/yaw and target XYZ;
  the experiment launcher, layer selection and historical verifier are the
  restrictions that need an evaluation adapter.
- User approved creating this task and entering planning on 2026-10-18.
  Final implementation and per-route full-video return approved on 2026-10-18.

## Scope and invariants

1. At least 12 distinct start/goal pairs in Building, covering four entry
   positions/headings, three upstairs destination types, two obstacle-edge
   goal/neighborhood-search cases, and three reverse cross-floor cases.
2. Use actual installed C++ PCT + ENV225 + GPMP + native static review and
   actual SCAN cold first-plan/local connector/full-curve publication paths.
   Do not substitute Python planner approximations or count a soft-cost query
   or target proposal alone as successful planning.
3. Freeze every case's world-frame ground XYZ, selected floor and start yaw
   before the scored batch. Requests, canonical native goals and local targets
   remain separate records. Requested physical goals must not be moved to make
   a run pass. Goal heading retains the existing route-terminal-tangent rule.
4. Preserve RL bytes, ENV225, 0.35 m collision/support, 0.1 s scans, v237
   deadline handling, original freshness/dynamics/epoch/publication/stop/PD
   rules. Do not modify frozen versions or inherited repositories.
5. Report five fresh-instance calls per case (at least 60 calls), with
   per-stage numerators/denominators, typed reasons, retries/fallbacks and
   cold/steady timing. Five calls are not a reliability confidence claim.
6. Report capped extra edge margin, original Building point-cloud oracle
   margin, and separately the observed local margin/coverage from that case's
   own paired geometric LiDAR scans. Unknown/unobserved is not free space.
7. Select three representative new cross-floor cases by the predeclared
   strata/ranking rule, normally two ascent and one descent. If no reverse
   case passes native admission, retain that failure and execute two eligible
   ascent cases; do not alter guards to fill the third slot.
8. One physical attempt per selected case, at most three new attempts. Report
   every outcome, including failure/timeout/fall. No automatic success-seeking
   physical retry. No additional historical_full control is required.
9. Return full videos and metrics for new physical cases: successful local
   planning, >=0.5 s / >=1.0 s pauses, cumulative/split low time, edge margin,
   actual endpoint errors, native FINISHED and measured terminal PD closure.
   Use route-relative stair/approach regions as well as raw fixed-time windows.

## Acceptance

- Publish frozen case manifests and map/ENV/native/policy identities, keeping
  the 12 requested cases and every scored call in the denominator.
- Each case reports first-attempt GPMP/static admission, eventual admission,
  graph fallback count, SCAN first valid published curve, connector outcomes,
  required coverage, margin saturation/unknown state and stage/total timing.
- At least one boundary case must record an actual native neighborhood-search
  invocation with obstacle/floor/freshness context. If frozen gates prevent
  reaching it, preserve the early rejection and mark required branch coverage
  unmet; do not force the branch or claim the requested coverage passed.
- Capture and retain each selected physical trial from its own factory spawn
  through terminal/failure closure. Verify original rule values against the
  frozen baseline, with case-specific initial/goal coordinates only.
- Fully decode returned videos, verify source-frame/causal-event/hash linkage,
  inspect representative images, and keep raw clouds/caches on gpu5070ti.
- Separate original-route validation, same-map endpoint coverage, component
  admission and physical outcome. No claim of new-map generalization,
  statistical reliability, sustained 30 Hz or baseline adoption.

## Out of scope

Planner/RL tuning or retraining; a new collision model; changing terminal yaw
policy; bypassing unknown-space or support gates; new recovery protocols;
robot hardware; unrelated harness changes; changing selected v232/v233.

## Planning status

Implementation approved and v242 completed:12 frozen cases x5 fresh calls,
only A02 passes5/5 global and first-SCAN chains.55 calls fail PCT search.
Physical support screening does not establish PCT connectivity. Requested
boundary branch coverage is unmet. Only one eligible representative triggers
the approved fewer-than-two stop rule, so v243 remains unfrozen preparation;
zero new physical attempts/videos. Compact source/evidence is returned locally.
Physical acceptance remains pending review of the failed offline coverage gate.

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

## Authorized physical follow-up after v251 qualification — 2026-10-18

Dr Sun explicitly authorizes one new formal physical attempt each for A02,
G07 and R11 on gpu5070ti, based on frozen v251. Preserve the exact original
case scenarios, RL, 0.35 m hard radius and 0.1 s scanning/deadline. This
supersedes the preceding offline-only restriction for these three attempts.
No success-seeking retries or planner modifications. Return every complete
recorded attempt, including failed prefixes, to the new audit's delivered/.
v252 owns execution binding only; native v251 and bridge v248 remain frozen.

## Approved expansion: static solids and full-space coverage

The latest user instruction supersedes twelve cases repeated five times: require at least fifty distinct spatial start-goal pairs with explicit start/goal headings, one scored call per case. Repair B08 negative original-cloud solid clearance through a shared 0.35 m hard domain before scoring. Conditional authorization covers eight to ten distinct hardest Newton routes after offline qualification, one formal attempt each, videos returned locally. Preserve v254/v255 results and original fixed-policy, sensor and geometry contracts. See versions/v256/PLAN.md for prospective gates and strata.


## v256 / v257 outcome — expanded gate failed

Frozen native v256 repairs B08 solid-body admission, with 148 distinct tests and 10,928 zero-mismatch independent geometry checks. Frozen v257 scores all 52 different spatial requests once each: 34/49 predeclared positives pass full global/static/cold SCAN, all 34 first-GPMP; all three illegal controls refuse. Zero admitted negative independent global/local solid margins. The prospective >=90% positive requirement fails. Fifteen failures and original labels remain, including five separately diagnosed wall-disconnected ground endpoints; remaining unknown-support and approach-yaw failures need general mechanism diagnosis. No runtime component rules, endpoint snap, radius/step waiver or scored substitution.

Conditional v258 is preparation only, unfrozen and never executed; zero new physical attempts/videos. Full original table, compact logs/witnesses, hashes and next boundary are in `.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v256_static_solids_and_space_coverage/RESULTS.md`. No commit, archive or selected-baseline promotion.


## Approved v259+ follow-up

Restore ~1s global median using exact-equivalent static-solid acceleration; prove frozen-v256 query parity. Diagnose/fix original ground coverage for U11/U12/D09/D10/D11/D13 without accepting unknown. Incorporate unchanged requested start/goal yaw in search/connection/smoothing physical feasibility rather than post-hoc rotation. Keep original52 ledger, add original3D-mesh-certified50 physically reachable positives plus illegal controls, one scored call each. Only after >=90% full-chain and recovered timing execute8–10distinct hard physical routes on one frozen native treatment, one formal try each, return every video.


## Approved independent source-surface treatment — 2026-10-18

Dr Sun explicitly permits an independent source-surface model after the
immutable v262 benchmark found seven endpoint hard refusals and an 81-curve
protocol audit proved the separate0.1/0.8s yaw-sampling mismatch. The model
may change old geometric query outcomes; keep v259/v261 exact-equivalence
controls, original52 and v26250+3 ledgers intact. Preserve0.35m, original
requests, RL and0.1s scanner. Validate finite source surfaces, material/floor
association and real-wall/column controls independently before native full
chain and conditional physics. Never simply waive unknown support or remove
source uncertainty without a surface-based geometric justification.
