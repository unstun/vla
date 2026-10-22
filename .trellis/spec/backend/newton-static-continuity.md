# Static mission continuity and source-wall soft costs

## 1. Scope / trigger

v284 supersedes the v283 local source veto and forced measured-seed reset for
the user-authorized static-building experiment. Preserve frozen parents. Source,
component, offline and physical results are separate claims; consult the version
report for acceptance. This is not an adopted navigation baseline.

## 2. Signatures

- `RoutePolicy::retainedStatic(start, goal)` returns an optional admitted cached
  route, trims passed prefix and retains the original epoch and at least two poses.
- `PlanOnGoalChange` retains SUCCESS across status/timestamp refreshes; full goal
  change or explicit halt releases ownership. No local replan subscription.
- `StaticSolidField::repulsionCost(body,yaw,gradient,cache)` supplies one shared
  soft cost. Optional cache is the existing request-owned `StaticSolidQueryCache`.
- `GridMap::sourceSolidCostGradient` connects that evaluator to SCAN.
- `environmentalCurveCost(..., measured_yaw, spatial_step=.025,
  minimum_samples=10)` retains the original defaults; source-wall quadrature
  uses map resolution and two minimum samples per cubic span.

## 3. Contracts

PCT with pinned static support retains its first admitted same-mission route;
moving-start heights and local hint events cannot destroy that route. Initial
global support/solid checks remain unchanged. Mission epoch change prevents a
retained result from publishing as the previous owner. Goal change/cancel
releases the cache through the existing route-session owner.

Local `getInflateOccupancy(pos,yaw)` uses the existing live/support query without
v283's added source-field veto. WrongHeight alone can associate to the nearest
selected raw/scored floor at the same XY inside the existing0.26m stair bound;
raw/scored heights must match. Check real support gaps at that floor. Do not
move body/obstacle XYZ, waive UnknownSupport or change initial static admission.
Warm continuation uses the preceding behavior, without the half-cell measured
envelope reset added in v283.

Source-wall soft cost is `0.1*max(0,(0.07-margin)/0.07)^2`, where margin is the
exact extra radial source-solid distance beyond0.35m. Source gradients are
horizontal XY/yaw at actual height, with zero Z derivative; this is not a3DESDF.
Reuse the closest source point. Cache may prove only exact zero beyond the soft
band using positive same-height/conservative-interval certificates; otherwise
query the actual source field. Hard assess/collides behavior stays unchanged.
Global GPMP and local spline use the same scalar evaluator. Legacy local atlas
quadrature and all hard validators keep their original density and semantics.

Tracking keeps translation and yaw coupled with advancing spline phase during
travel. Pure-yaw final alignment is confined to the existing XY/Z goal capture
region. Expired nonterminal braking does not add a pure-yaw command. Preserve
the existing slew limits, emergency/cancel owners, policy, PD and goal tolerances.

## 4. Validation and error matrix

| Input or transition | Required result |
|---|---|
| Same goal/status/timestamp refresh | Keep admitted static route and epoch |
| New destination, cancel or new route session | Release old owner |
| Illegal initial endpoint | Existing support/solid refusal |
| WrongHeight with same-XY selected step layer | Local association and real gap/live checks |
| True SupportGap or live obstacle | Retain its refusal |
| Source wall absent from live cloud | Positive soft cost/gradient; no added local source veto |
| Soft-cache zero proof unavailable | Exact actual-pose cost query |
| Large travel heading error | Nonzero translation where curve requests it, phase advances |
| Terminal XY/Z capture | Existing final-yaw convergence |

## 5. Good / base / bad cases

Good: one initial global solve survives100same-goal refreshes and moving-start
height fluctuation. Base: preserve parent0/4 versus candidate4/4 translated/
rotated travel-heading contrast. Bad: call a zero command a measured stop,
confuse WrongHeight with SupportGap, or assume a soft cost guarantees physical
clearance. Source-wall repulsion cannot move a fixed low-margin requested goal.

## 6. Required tests and evidence

Require actual BT/RoutePolicy lifecycle checks, native command tests, source
soft-band/value/derivative and cached/full parity, recorded A04 height contrast,
real gap/obstacle controls and inherited native regressions. Bind source/install
and evaluator executable hashes before the complete53scored calls. Reuse frozen
v283 endpoints/captured scans and report all50starts; no score-based resampling.
Only a passing complete offline gate permits the fixed ten single Newton
attempts. Keep all failures, support/source/raw geometry, stalls, applied pure yaw,
scanner deadlines and full videos. Video repair adds zero physics.

## 7. Wrong vs correct

Wrong: hard-reject a supported transient height, restart global search from that
moving pose, then wait on a route the same feedback excludes. Correct: retain
the admitted static reference and let live local planning follow it continuously.

Wrong: increase hard radius/deadline or claim that a soft penalty prevents every
physical collision. Correct: keep0.35m and0.1s exact, audit the actual recorded
body independently and report any remaining failure without a success retry.

## Recorded v284 validation boundary

The complete v284 cohort retains one global epoch/original reference on all ten
physical attempts and has no endpoint/shared-no-route rejection. Nevertheless,
only 3/10 arrive with PD and 1/10 also pass measured geometry. S04/CS03 first solid
excursions occur with zero applied commands in STAND_SETTLING while measured
horizontal speeds remain about 0.310/0.275 m/s. Sampled corresponding published
curves have positive source margins; their nominal windows have expired.
A safe reference/curve and a zero command do not establish stationary-body
clearance or successful execution. Preserve the distinction without adding a
new publication veto. See the v284 audit's RESULTS.md and OBSERVATIONS.md for
exact witnesses, raw-point confirmation and reconstruction limits. This is an
unaccepted frozen candidate; no source overwrite or actual retry may relabel it.
