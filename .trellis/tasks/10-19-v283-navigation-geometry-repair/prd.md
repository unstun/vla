# v283: Replanning, local geometry, and spawn admission

## Goal and authorization

Repair v282 feedback-driven endpoint failures and local solid/support violations; uniformly certify starts, evaluate updated 50+3, and run the ten fixed physical routes once each.

Deliver a complete report and ten real local MP4 files, including any failed
attempts. On 2026-10-19 Dr Sun approved task creation and this intended code and
experiment scope after evidence review. Dr Sun subsequently explicitly approved
the final PRD/design/execution plan and directed implementation and execution.
The final planning review gate is satisfied; implementation is now authorized.

## Confirmed evidence

Paths below are relative to
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/`.
Inherited source paths were matched to the frozen v280 source inventory.

| Finding | Evidence |
|---|---|
| Native v280 SHA b4dd7a47dea57318ffb9671a2c9fedce36e17e064f7657f60c3f143d5d586ac9; physical v282 SHA de9fae3524cc29f0f0c0dead632132ee5212ea34c0d5c27d25f55c1e6ca84cd6 | `versions/v282/source_identity.json` |
| A04/CU06/CM02/CE03 have positive sampled geometry but terminate with endpoint rejection; CE03 first lacks static evidence | `audits/2026-10-19_v280_source_generalization/results/failure_terminal_bill.json` |
| Endpoint/connection checks mix physical geometry and live feedback in poseFree | `versions/v280/source/src/lite3_nav2_plugins/src/pct_route_planner.cpp:110,147,197,396` |
| Start expansion already visits neighboring cells and 16 arrival headings | `versions/v261/src/pct_planner/lib/src/a_star/a_star_search.cc:557` |
| SCAN loads StaticSolidField, but its local B-spline collision query bypasses it | `versions/v256/src/plan_env/include/plan_env/grid_map.h:649`; `versions/v256/src/plan_env/include/plan_env/scan_reactive_grid_methods.inc:370,494`; `versions/v232/src/bspline_opt/src/bspline_optimizer.cpp:39,1095` |
| Solid excursions: D07 -0.004884 m, CD12 -0.183185 m, CS03 -0.145919 m | Audit `geometry_excursion_witnesses.json` |
| CD12 has four SupportGap samples, minimum -0.020260 m, first at 37.511013 s | Same witness file and CD12 `results/physical_support_margins.jsonl` |
| G05 factory standing shifts about 0.0968 m; approximately 0.02 m initial margin becomes -0.076893 m | G05 physical diagnostics and offline `results/clean50/G05/summary.json` |
| Generated starts only require positive margins; historical starts bypass selection; at least six other stored generated starts have a margin below 0.10 m | `versions/v262/construct.py:33,88`; `versions/v281/clean50.json` |
| Prior offline result: 48/50 full-chain passes; first GPMP 44/50 or 44/48 admitted; CPU2 median global 1.336759 s excluding initialization | `versions/v281/RESULTS.md` |

The preceding review checked 5,966 navigation-window pose rows, all ten video
hashes, and owned v280/v281/v282 source hashes. It did not replay every original
asynchronous request. Body excursions alone do not distinguish planning from
tracking failure. Four routes arrived with PD; only S04/CM07 also cleared sampled
geometry checks.

## Requirements

### R1. Endpoint validity and mission continuity

Live-feedback hints must not blacklist legal start/goal poses or otherwise safe
endpoint connections. Preserve authoritative support, solid, and current live
obstacle checks. Distinguish unavailable evidence and hint exclusions from hard
physical invalidity. Keep a mission active during initial evidence readiness or
temporary replanning failure when its existing route remains usable from the
current state. Preserve cancellation, existing deadlines, and genuine failure.

Keep every safe departure available to a moving start. Do not discard measured
yaw or bypass swept turn checking. Change heading expansion only if a native
regression demonstrates a missing safe connection.

### R2. Local geometry and CD12 support

Local search, B-spline optimization/refinement, final publication, and active
curve checking must use the same static solid boundary as PCT. Include CD12's
SupportGap in diagnosis and correction. Establish whether planned geometry or
physical tracking first violated support, then fix the responsible shared owner.

### R3. Uniform legal-start admission

Check all 50 legal starts, including inherited starts, against authoritative
support and source solids. Require both extra edge and solid margins >=0.10 m.
Keep qualifying starts unchanged; replace failures with one deterministic
geometry-based rule, preserving goals, headings and route strata. Retain exactly
50 distinct legal spatial start/goal pairs and the three unchanged illegal
controls. Preserve the old cohort. Freeze a new cohort and old/new margin table
before scoring; do not select replacements by planner success. G05 retains its
case lineage with a certified new spawn. The 0.10 m requirement is an admission
rule, not a demonstrated upper bound on all PD startup drift.

### R4. Fixed boundaries

Keep 0.35 m radius, 0.1 s LiDAR period/deadline, original offset/vertical profile,
policy, factory PD, goal tolerances, freshness checks, and source geometry.
No scene-name, route-ID, coordinate, or region-specific production behavior.
Recorded coordinates may appear in diagnostic fixtures only. Do not refactor
unrelated modules, overwrite frozen versions, or promote the selected baseline.

### R5. Ordered evaluation and delivery

Finish all 53 offline cases, then one formal Newton attempt each for A04, G05
replacement, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03. Keep this selection
fixed before scoring. No success-seeking formal retries. Deliver every result
and full recorded video prefix, including failures.

## Acceptance Criteria

- [ ] AC1 / R1: Parent/candidate regressions expose feedback-induced endpoint
  rejection and verify legal departures, actual obstacle/support refusal,
  readiness waiting, safe-route retention, cancellation and timeout behavior.
- [ ] AC2 / R2: Exercise actual SCAN local/final-curve queries with a source wall
  absent from live cloud, and the recorded CD12 support counterexample. Report
  planned-versus-measured differences; no support waiver or heading inflation.
- [x] AC3 / R3: All 50 starts meet both >=0.10 m extra margins, with exactly 50
  distinct spatial pairs and three unchanged illegal controls. Geometry-only
  replacement certificates and endpoint differences are frozen before scoring.
- [x] AC4 / R4: Numerical/profile/hash checks preserve the fixed contracts;
  translated/rotated fixtures exercise generic behavior.
- [x] AC5 / R5: All 53 calls finish; >=48/50 legal full-chain passes and 3/3
  illegal refusals; no admitted/published negative source/support margin;
  CPU2 median global solve <=1.5 s. Report initialization, p95/max, and both
  first-GPMP denominators separately. Retain the inherited >=90% first-GPMP
  among admitted cases gate. Each of the fixed ten routes must pass offline
  admission before the physical batch.
- [ ] AC6 / R1-R5: Exactly ten formal attempts with no hint/readiness endpoint
  mis-aborts and no sampled solid-envelope or SupportGap violations. Report
  arrival, terminal PD, pauses, local success and scanner timing independently.
  A failed attempt remains a failed acceptance result.
- [x] AC7 / R5: Complete local report, machine-readable tables, provenance and
  ten non-symlink MP4s with verified hashes, full decode, recorded-state coverage
  and visual inspection. Heavy raw data/builds stay on gpu5070ti. Sampled checks
  must not be described as continuous-time or foot-contact proof.

## Out of scope

New VLA architecture, policy training, physical robot actuation, scene changes,
threshold relaxation, a new planner framework, old result relabeling, or
automatic baseline adoption.

## Decisions and technical work

User scope and evaluation order are resolved. Request/witness attribution and
CD12 planning-versus-tracking attribution remain technical work within R1/R2.
No user-owned scope decision is outstanding. Final planning approval is recorded
above; implementation and the specified experiment sequence may proceed.


## Final assessment

The full v283 experiment/delivery protocol is complete. Offline acceptance passes;
physical acceptance AC6 fails. Actual goal/PD is5/10 and goal/PD plus sampled
geometry2/10. CD12 SupportGap is removed in this one attempt, but S04 regresses
and D07/CE03 retain solid-envelope violations. Task remains in_progress; do not
claim a completed physical repair or promote the selected baseline. See
versions/v283/RESULTS.md and the linked complete report/videos.
