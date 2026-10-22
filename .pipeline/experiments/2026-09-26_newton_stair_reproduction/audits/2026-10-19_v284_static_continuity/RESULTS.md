# v284 complete physical execution report

The frozen candidate completed all 53 scored offline requests and the same ten
once-only Newton physical simulation attempts. No physical retry was used.
Goal plus terminal PD: **3/10**. Goal/PD plus
nonnegative sampled physical support-gap and source/raw solid margins:
**1/10**. The stricter retained
static all-Free screen passes 1/10.
Requested physical outcome: **UNMET**.

Benchmark acceptance remains **FAIL**: the native global median is
**1.649325 s**, above the requested approximately 1.3 s and
the original 1.5 s gate. Dr Sun explicitly replied “继续十条，耗时记未达标”.
The separate execution review allowed these ten attempts after every non-timing
criterion passed; the benchmark gate and original selection were not rewritten.

## Main physical finding

The global endpoint/no-route rejection is absent, while all seven failed
recorded prefixes remain measured support/source/raw-clear and terminate with
`Native SCAN has no executable trajectory before timeout`. S04 and CS03 still
cross the solid boundary after the latest curve's nominal expiry. Their first
negative samples have zero applied commands and measured movement in
STAND_SETTLING; S04 reaches its deepest excursion after RL resumes.
Soft wall repulsion does not close that execution gap. See the
[confirmed observations](OBSERVATIONS.md) for exact witnesses and inference limits.

## What changed

- A static mission retains its first admitted global reference. The cache only
  permits trimming a passed prefix; it does not replace the remaining geometry. Same-goal BT status refreshes, transient moving height/yaw
  and local feedback witnesses do not replace that reference. A new goal or
  explicit halt releases it; initial global hard admission remains unchanged.
- SCAN no longer applies v283's source-field publication veto or its forced
  measured-state warm reset. Live map, support and freshness checks remain.
  The narrow local WrongHeight handling uses the existing selected floor and
  physical support coverage; it does not waive SupportGap or move obstacles.
- Nonterminal tracking couples translation and yaw while advancing curve phase.
  Final heading alignment requires the original XY/Z terminal capture region.
- GPMP and SCAN share source-wall soft repulsion over the 0.35–0.42 m radial
  band. Cost is `0.1 * max(0,(0.07-extra_margin)/0.07)^2`, with source XY/yaw
  gradients at actual height and zero soft Z derivative. This is a soft bias,
  not a 0.42 m hard boundary or guaranteed dynamic clearance.

The fixed CD12 and CE03 goals have only +5.710 mm and +19.715 mm static
source-solid margin, respectively. Their exact goals and headings are retained;
soft repulsion cannot guarantee a 3–5 cm margin at an endpoint it cannot move.
The physical table reports the actual achieved arrival-window margins.

Exact 0.35 m hard radius, 0.18 m cylinder offset, vertical profile, 0.1 s scan
period/deadline, locomotion policy, factory PD, goal tolerances and episode
limits are unchanged. Production code has no route-name or coordinate branches.

## Qualification and the complete offline cohort

The parent/candidate tracking probe changes from 0/4 to 4/4 coupled travel
controls. The actual BT same-goal regression plans once across 100 status and
timestamp refreshes, then replans on a new goal or explicit halt. Native checks
pass 172 tests in 20 suite executions, including translated/rotated soft-band
controls, finite differences, 200 cached/full source comparisons, support and
the recorded A04 WrongHeight case. Development failures remain in the logs.

The scored cohort is exactly the frozen v283 50+3, with its captured LiDAR,
headings, goals and three illegal controls. All 50 legal start certificates were
checked; every start has at least 0.10 m static support and source-solid extra
margin. Eight uniform v283 replacements, including G05 and CM02, are retained.
No native scored request or physical attempt was repeated to improve a result.

Offline legal full-chain passes: **48/50 (96%)**;
global admissions 49/50; illegal refusals
3/3. First GPMP: 47/50,
or 47/49 admitted. All admitted
global and published local source/raw margins are nonnegative; all ten selected
cases pass the full offline chain. CD11 local refinement and CS01 global
no-route failures remain. Timing uses CPU quota 2, excludes initialization,
and does not claim an exclusive host. The complete timing table is in the
[offline report](../../versions/v284/OFFLINE_RESULTS.md).

## Ten actual outcomes

| Route | Recorded terminal | Goal + PD | Physical envelope clear | Duration s | Final XY / height error m | Full video |
|---|---|---|---|---:|---:|---|
| A04 | FAILED | False | True | 96.259 | 5.144 / 2.707 | [MP4](delivered/v284_A04_full_attempt01.mp4) |
| G05 | FAILED | False | True | 97.158 | 10.226 / 2.699 | [MP4](delivered/v284_G05_full_attempt01.mp4) |
| CU06 | FAILED | False | True | 97.398 | 7.052 / 2.708 | [MP4](delivered/v284_CU06_full_attempt01.mp4) |
| D07 | FAILED | False | True | 82.206 | 8.670 / 2.995 | [MP4](delivered/v284_D07_full_attempt01.mp4) |
| S04 | FINISHED | True | False | 58.879 | 0.245 / 0.016 | [MP4](delivered/v284_S04_full_attempt01.mp4) |
| CD12 | FAILED | False | True | 76.530 | 6.119 / 4.089 | [MP4](delivered/v284_CD12_full_attempt01.mp4) |
| CM02 | FAILED | False | True | 55.981 | 9.459 / 1.476 | [MP4](delivered/v284_CM02_full_attempt01.mp4) |
| CM07 | FINISHED | True | True | 87.763 | 0.124 / 0.006 | [MP4](delivered/v284_CM07_full_attempt01.mp4) |
| CS03 | FINISHED | True | False | 39.270 | 0.156 / 0.011 | [MP4](delivered/v284_CS03_full_attempt01.mp4) |
| CE03 | FAILED | False | True | 51.044 | 0.759 / 0.021 | [MP4](delivered/v284_CE03_full_attempt01.mp4) |

## Measured geometry

All margins are extra metres beyond the unchanged profile; +0.15 m is a cap.
Navigation windows start at the real goal request and end at first observed
arrival, or the final preterminal observation on failure. They include initial
planning waits and in-place movement; factory startup and final PD are separate.
The source, independent original raw points, hard physical SupportGap and ENV
soft atlas are separate channels. WrongHeight is retained in static verdict
counts and is not relabeled as a collision or a physical support gap.

| Route | Physical support gap min m | Source solid min m | Raw point min m | Static verdict counts | ENV soft edge min m |
|---|---:|---:|---:|---|---:|
| A04 | 0.150000 | 0.150000 | 0.150000 | {"0": 829} | 0.105643 |
| G05 | 0.073152 | 0.150000 | 0.150000 | {"0": 838} | 0.073152 |
| CU06 | 0.150000 | 0.150000 | 0.150000 | {"0": 840} | 0.108438 |
| D07 | 0.128930 | 0.150000 | 0.150000 | {"0": 688} | 0.128930 |
| S04 | 0.150000 | -0.051553 | -0.050974 | {"0": 446} | -0.164493 |
| CD12 | 0.071711 | 0.150000 | 0.150000 | {"0": 631} | 0.071711 |
| CM02 | 0.100701 | 0.150000 | 0.150000 | {"0": 426} | 0.100701 |
| CM07 | 0.093009 | 0.150000 | 0.150000 | {"0": 735} | 0.093009 |
| CS03 | 0.150000 | -0.034650 | -0.034644 | {"0": 250} | -0.143354 |
| CE03 | 0.150000 | 0.150000 | 0.150000 | {"0": 376} | 0.054492 |

These are 10 Hz measured body-pose samples, not continuous-time or foot-contact
certificates. Negative samples remain failures even if the driver reports
arrival. The original static all-Free criterion is retained separately from
physical-envelope clearance, so transient WrongHeight cannot silently disappear.

## Continuity and stops

Recorded global-reference geometry remains the original curve or a suffix on
10/10 routes. Exact route-message
epochs, pose-sequence hashes and suffix checks are retained in every
`command_continuity.json`; this uses actual published paths, not just unit tests.

Mid-route low-speed intervals of at least 60 s after the first translation:
**0**. Endpoint rejection log lines: **0**. Applied
pure-yaw is defined as XY command norm <=0.01 m/s and absolute yaw >0.1 rad/s,
outside the original goal capture region. It is measured from applied telemetry,
not only tracker targets. Sample endpoint durations carry one-sample uncertainty.

| Route | v283 max pause after motion s | v284 max pause after motion s | >=60 s holds | Max nonterminal pure-yaw s | Nonterminal STAND_SETTLING samples | Local success/completed |
|---|---:|---:|---:|---:|---:|---:|
| A04 | 87.950 | 25.026 | 0 | 0.080 | 233 | 987/1641 |
| G05 | 81.103 | 30.363 | 0 | 0.180 | 356 | 821/1635 |
| CU06 | 82.941 | 31.183 | 0 | 0.000 | 126 | 960/1763 |
| D07 | 5.559 | 3.158 | 0 | 0.220 | 755 | 893/947 |
| S04 | 4.338 | 7.176 | 0 | 0.180 | 115 | 225/239 |
| CD12 | 9.095 | 4.318 | 0 | 0.080 | 1083 | 647/708 |
| CM02 | 76.312 | 18.970 | 0 | 0.080 | 156 | 40/221 |
| CM07 | 5.057 | 6.816 | 0 | 0.080 | 455 | 907/992 |
| CS03 | 14.892 | 5.457 | 0 | 0.060 | 47 | 196/206 |
| CE03 | 10.334 | 5.157 | 0 | 0.100 | 562 | 119/287 |

Low-speed durations include permitted final heading alignment before the
first arrived observation; the separate pure-yaw metric excludes terminal capture.
The v283 comparison reuses its unchanged recordings under exactly the new pause
and applied-command definitions; it adds zero physics. STAND_SETTLING counts,
planning-round success and measured pause duration are different quantities.

## Scanner and execution integrity

| Route | Scan jobs | Deadline failures | Maximum scan ms | Native process failure |
|---|---:|---:|---:|---|
| A04 | 852 | 0 | 28.683 | False |
| G05 | 861 | 0 | 50.770 | False |
| CU06 | 864 | 0 | 29.895 | False |
| D07 | 712 | 0 | 27.576 | False |
| S04 | 478 | 0 | 25.307 | False |
| CD12 | 655 | 0 | 28.152 | False |
| CM02 | 449 | 0 | 27.398 | False |
| CM07 | 767 | 0 | 28.765 | False |
| CS03 | 282 | 0 | 25.515 | False |
| CE03 | 400 | 0 | 26.782 | False |

Totals: 6320 scan jobs, 0
deadline failures, 0 native process failures.
The scanner period remains 0.1 s on every attempt.

One A04 zero-step resource preflight was rejected before any physical launch
while an unrelated GPU evaluation occupied the host. Its qualification01 and
graph/deadline logs are retained. Qualification02 continued waiting, then was stopped before physics after the
user authorized sharing based on remaining resources. Qualification03 uses
>=16 GiB available RAM and >=10 GiB output space, records GPU occupancy without
a CPU-execution veto, and completed the ten preflights. This is separate from any actual attempt.
The first continuation monitor also stopped on a transient read of an updating
JSON status file, before any physics. Its receipt/log and original source are
retained; the revised continuation handles that read race. Continuation03 owns the
approved shared-resource execution; earlier waiting processes were stopped
without changing other GPU jobs. Native frozen code is unchanged.
The five earlier v283 disk-gate startup failures remain preserved with their
original correction receipt and hashes; they are not v284 physical attempts.

## Failures and limits

Every terminal error and recovered planner error is retained in the
[terminal bill](results/failure_terminal_bill.json). Full-route completion,
terminal PD, sampled geometry, command continuity and timing are reported
independently. One attempt per route does not establish statistical reliability.
Overall benchmark acceptance remains failed because timing is unmet; no baseline
promotion or source commit is implied by finishing the execution protocol.

## Provenance and delivery

- Native manifest: `660842708af904fad2b5d63f3499c655422d2c1bddacf323e0cb981e185d3e32`.
- Execution manifest: `f21a9d1235fa1ff4347fbb079894ffb10a04ff230f210bd4e907188234760522`.
- Execution review: `070dc22d9e22e0aa2466eb116d15ab5b051fa6f83bd06abc9b8bb952bebb878f`.
- Return inventory: [all compact files and ten real MP4 hashes](physical_return/return_inventory.json).
- Machine-readable outcomes: [summary](physical_summary.json), [table](physical_table.csv).
- All 50 starts: [certificate verification](results/all50_start_verification.json).
- Raw Newton captures stay on gpu5070ti at `/home/sun/vla_exec/physical_runs_v284`.
- Local review videos are regular MP4 files, never symlinks. Every file has full
  decode, state-coverage, exact hash and zero-render-physics proof. Rendering uses
  the same generic close-body FOV 95 camera on all normal full recordings.
- Recreate media from retained recorded states; never rerun physics to repair
  a video. Source/configuration, compact evidence and review videos return here.

## Recorded curve witness review

This query-only reconstruction uses the actual latest published curve at selected
stop/clearance witnesses, with its nominal elapsed phase. It is not exact internal
tracker scheduling, a replayed mission or a causal ablation. Whole-curve source
queries use 10 ms nominal samples and the original 0.8 s heading lookahead.
Expired curves are explicitly counted; degenerate endpoint headings use the
measured yaw and carry no heading-accuracy claim; their endpoint discrepancy does not
prove that a controller was executing that curve. Static support query counts
include WrongHeight, distinct from physical support gaps.

| Route | Witnesses | Max nominal position discrepancy m | Expired witnesses | Selected curve source min m | Static support refused queries |
|---|---:|---:|---:|---:|---:|
| A04 | 3 | 0.062 | 2 | 0.150000 | 0 |
| G05 | 3 | 0.081 | 2 | 0.150000 | 0 |
| CU06 | 3 | 0.089 | 2 | 0.150000 | 0 |
| D07 | 3 | 0.504 | 1 | 0.150000 | 0 |
| S04 | 4 | 0.283 | 4 | 0.150000 | 0 |
| CD12 | 3 | 0.477 | 1 | 0.150000 | 0 |
| CM02 | 3 | 0.050 | 2 | 0.150000 | 0 |
| CM07 | 3 | 0.125 | 1 | 0.150000 | 0 |
| CS03 | 4 | 0.157 | 4 | 0.097871 | 0 |
| CE03 | 3 | 0.026 | 2 | 0.150000 | 0 |

Every selected pose, applied command, stance mode, curve identity and native
verdict is retained in each route's `results/recorded_curve_diagnosis.json`.
Query inputs/full query margins remain remote with a compact hash inventory;
the local script regenerates them from the unchanged recordings with zero physics.
These witnesses narrow remaining failures but do not establish a new fix.
