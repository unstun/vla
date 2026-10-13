# Independent native trajectory validation (v127)

## 1. Scope / trigger

Applies to MPPI adaptation 3, starting from retained native v122 / host v125.
v126 retry reduction remains parked. v127 also remains parked after its first
physical candidate failed; its interface is experimental, not the selected runtime. v127 extracts native checks without changing
sampling, thresholds, optimizer, retries, source clocks, ownership or stopping.
Runtime acceptance is recorded separately in the step-3 report; the interface
alone does not establish navigation reliability or sustained 30 Hz.

## 2. Signatures

`plan_manage/trajectory_validation.h` defines stateless
`scan_planner::NativeTrajectoryValidator`:

- `boundary(UniformBspline &, start, end, derivatives) -> ValidationResult`
- `dynamics(UniformBspline &, velocity_limit, acceleration_limit) -> ValidationResult`
- `collision(UniformBspline &, GridMap &, begin_s) -> reactive_stair::TrajectoryCheck`
- `publicationEpoch(elapsed, duration) -> ValidationResult`

`ValidationFailure` distinguishes None, BoundaryPva, VelocityLimit,
AccelerationLimit and PublicationEpoch. Dynamic reports retain the first failing
sample time, measured norm and original limit. Collision retains the original
native status, first sample time, duration and sample count.

## 3. Contracts

The validator has no mutable state, optimizer, cached permission or clock owner.
The manager retains its original staged order: successful refit/minimum-cruise,
PVA, dynamics, map input refresh, publication lease, whole-curve collision,
publication epoch, then commit exact trajectory and proof. The existing checks
before these stages remain mandatory. Dynamics consumes an already admitted
spline; no new invalid-layout/numerical policy is introduced during extraction.
Epoch consumes elapsed time derived from the checked source epoch and a valid
curve duration. These entry points do not replace input admission.

The controller passes its private snapshot query view and actual tracker phase.
The FSM passes its existing map view and original source-relative phase. Neither
calls candidate PVA checks on an executing remainder. Map support, footprint,
heading, source age, writer health and exact binding remain native contracts.
Collision returns a sampled full-curve check, not a continuous swept-volume proof.
A validation report is not a publication/query lease or authorization to move.

## 4. Validation / error matrix

| Condition | Preserved behavior |
|---|---|
| Boundary differs beyond original 1e-6 tolerance | Reject PVA |
| Sampled speed or acceleration exceeds original limit + tolerance | Reject at original first violating sample |
| Equality at dynamic limit | Preserve original non-rejection |
| Collision, invalid curve/time/resolution or sample-budget failure | Preserve native full-curve status |
| Old pose/observation or unhealthy map | Preserve original snapshot/occupancy/owner rejection |
| Publication elapsed <0 or >= valid duration | Reject without rebasing epoch |
| Earlier refinement fails | Short-circuit original later checks |
| Replan fails while current curve remains valid | Existing FSM/owner policy still decides execution |

## 5. Good / base / bad cases

Good: delegate numerical/geometry checking while keeping original map refresh and
lease timing at the call site. Base: exact parent and candidate checks return the
same verdict, sample metadata and successful control points on fixed inputs.
Bad: move the full checker to a 2D Nav2 costmap, refresh a source timestamp on
receipt, or call a cached clear result a new command permission.

## 6. Required tests

`versions/v127/contract/run_remote.py` compiles a baseline probe against actual
v122 manager/helper code and the candidate probe against v127. Compare 341
PVA/dynamic/epoch checks and 35 real-map collision checks. Check both accepted
and rejected inputs, equality/one-ULP dynamic boundaries, first failure reasons,
curve/map immutability and identical successful native curve values.

Run inherited actual publication/stale-input checks and controller snapshot
regressions: independent clock, future/stale/wrong-frame/nonfinite pose, stale
observation, writer fault, publication pin and subsequent writer progress.
Rebuild all dependent packages and run existing controller/terrain tests. Run
same-host physical comparison after freezing source and exact install receipts.
Component equivalence does not waive failed physical acceptance.

## 7. Wrong versus correct

Wrong: a refactor that silently drops legacy retry calls or evaluates the epoch
before collision work. Correct: preserve v122 retries and the original epoch
check position; source-audit these regions in addition to behavior tests.
Wrong: directly pass an unadmitted invalid spline to the dynamics-only entry
point and assume it replaces every validation stage. Correct: use the original
admission/PVA contract, then dynamics and native collision in their actual order.

## 8. Repeat and diagnostic interpretation

The 2026-10-10 repeat audit ran six fresh trials per unchanged installation;
v122 arrived 0/6 (including one fall), v127 1/6. Actual captured numerical
inputs and reconstructed controller queries agree, but that does not establish
live scheduling equivalence or candidate acceptance. Keep v127 parked.

In the inherited controller, `scan_safety_evidence_stale` is also emitted for
`!safety_->clear`. Classify rejection events using original observation/proof
ages and the native verdict; the label alone is not evidence of expired data.
Keep mission failure, individual solve rejection, long successful solve and
physical fall distinct. Same-input numeric replay may be exact while an ordered
cloud-prefix reconstruction is not the original asynchronous map revision.
Evidence: `audits/2026-10-10_mppi_step3_repeats/REPORT.md` under the Newton
experiment; no collision, freshness or recovery threshold changed in this audit.


### Sampling-density changes require downstream-consumer audit

The recordedv147failure09curve2366is admitted at the full interval but rejected
when the remaining interval begins24.986267mslater on the same reconstructed
map revision. The first native verdict isUnknownObstacle(code6), not support
clearance. Preserve this distinction. v151keeps every legacy sample and adds
four interior samples, retaining the10000sample fail-closed budget. This repairs
the captured miss; it is not a continuous-collision proof.

`SCANPlannerManager::makeWarmStartSeed` also consumes `check.samples-1` as its
initializer division count. A denser checker therefore changes initialization
as well as safety. Do not claim v151is initialization-invariant. v155is an
unbuilt parked draft separating those counts; no equality test or repair claim
is established by that draft. Fixed-clock cold replans in v152find valid
alternates, but do not reproduce warm initialization or live scheduling.
