# v280 / v281 / v282 — completed source-model generalization evaluation

All authorized work in this evaluation is delivered: independent source-model
qualification, native PCT/SCAN integration, unchanged original52 and fixed50+3
benchmarks, ten distinct once-only physical attempts, and ten complete local
review videos. The local repository remains authoritative; raw captures,
installations and build caches remain on gpu5070ti.

**Four of ten routes reached the requested goal and completed terminal PD.**
D07 and CD12 nevertheless have negative measured solid-envelope margins; CD12
also has four SupportGap samples. Only S04 and CM07 combine arrival/PD with
no refusal or negative margin in the sampled navigation geometry audit. This
additional 2/10 screen does not replace the original arrival gate or prove
continuous-time/foot-contact safety. The physical generalization result is
insufficient for baseline adoption. Selected baseline stays v232/v233.

## Frozen identity and offline evidence

- Native v280: `b4dd7a47dea57318ffb9671a2c9fedce36e17e064f7657f60c3f143d5d586ac9`.
- Benchmark v281: unchanged original52 and fixed50+3, exactly105 once-only calls.
- Execution v282: `de9fae3524cc29f0f0c0dead632132ee5212ea34c0d5c27d25f55c1e6ca84cd6`.
- RL SHA: `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.
- Requested XYZ/yaw, 0.35 m support/solid radius, 0.18 m offset, vertical profile,
  0.1 s scans and v237 deadline handling are unchanged. All ten process/profile/
  scanner preflights passed; frozen identity returned locally before physics.

Independent component comparisons and native integration passed. v279/v280
preserve all114,477 full source-query outputs,24,000 height-boundary checks and
171 native tests; old voxel models, all failed candidates and old ledgers remain.
B08 remains rejected. [v281 results](../../versions/v281/RESULTS.md) report:

| Cohort | Full positive admission | First GPMP among admitted / all positives | CPU2 median global time |
|---|---:|---:|---:|
| Original52 | 38/49 | 38/38 / 38/49 | 1.255811 s |
| Fixed50+3 | 48/50 | 44/48 / 44/50 | 1.336759 s |

Both cohorts refuse all3 illegal controls. All86 admitted saved global/local
pairs have nonnegative independent raw margins. This is offline evidence;
it does not predict safe tracking under measured physical execution.

## Physical arrival, planning and pauses

Each row is one formal attempt, with no retry. Local success uses completed
native SCAN rounds within the goal-request-to-arrival/preterminal window.
Low speed is measured horizontal speed below0.05m/s; initial planning waits and
in-place turns remain included, while factory startup/final PD are separate.
Cross-floor windows include the actually traversed interval; a failed partial
ascent is not a completed crossing. No interval is reported as a dash, not zero.

| Case | Class | Goal + PD | Local planning success | Pauses >=0.5 / >=1 s | Cross-floor pauses >=0.5 / >=1 s | Goal PD suffix |
|---|---|---|---|---:|---:|---:|
| A04 | ascent | FAIL | 88.29% (1146/1298) | 5 / 3 | 4 / 2 | — |
| G05 | ascent | FAIL | n/a (0 rounds) | 1 / 1 | — | — |
| CU06 | ascent | FAIL | 86.93% (1297/1492) | 5 / 2 | 2 / 1 | — |
| D07 | descent | PASS | 99.30% (2961/2982) | 4 / 3 | 0 / 0 | 4.350 s |
| S04 | same_floor | PASS | 93.25% (235/252) | 4 / 2 | — | 4.318 s |
| CD12 | descent | PASS | 99.50% (3196/3212) | 3 / 3 | 0 / 0 | 4.290 s |
| CM02 | intermediate | FAIL | 96.86% (741/765) | 2 / 2 | — | — |
| CM07 | intermediate | PASS | 98.74% (860/871) | 3 / 2 | 0 / 0 | 4.358 s |
| CS03 | same_floor | FAIL | 90.08% (227/252) | 5 / 3 | — | — |
| CE03 | boundary | FAIL | n/a (0 rounds) | 1 / 1 | — | — |

D07, CD12 and CM07 have zero >=0.5 s pauses during their actual cross-floor
intervals. That does not erase their separate geometric excursions. All6 failed
missions closed through finish_request; no native process crash was recorded.
All6,236 scans completed with zero deadline failures. Maximum observed scan
latency across cases is55.144ms. Policy and timing thresholds were unchanged.

## Measured geometry: distinct from arrival

Margins below are metres beyond the fixed0.35m model; +0.15m is a reporting cap.
These are6,236 measured body poses at10Hz, not foot locations or a swept
continuous-time proof. Actual hard-support verdict and ENV values agree exactly
with the original per-case scorer on every sample. ENV is a soft atlas proxy;
its minimum is reported only where its floor association is known.

| Case | Hard support Free / samples | Physical gap minimum | Source solid minimum | Raw-point solid minimum | ENV edge minimum | Arrival + sampled geometry clear |
|---|---:|---:|---:|---:|---:|---|
| A04 | 1014/1014 | +0.150000 | +0.150000 | +0.150000 | +0.131497 | NO |
| G05 | 0/63 | -0.076893 | +0.150000 | +0.150000 | -0.076893 | NO |
| CU06 | 1064/1064 | +0.142330 | +0.150000 | +0.150000 | +0.079070 | NO |
| D07 | 1154/1154 | +0.106317 | -0.004884 | -0.001371 | +0.106317 | NO |
| S04 | 174/174 | +0.150000 | +0.118948 | +0.119610 | +0.001154 | YES |
| CD12 | 1269/1273 | -0.020260 | -0.183185 | -0.180762 | -0.020260 | NO |
| CM02 | 363/363 | +0.049934 | +0.150000 | +0.150000 | +0.049934 | NO |
| CM07 | 413/413 | +0.085027 | +0.150000 | +0.150000 | +0.085027 | YES |
| CS03 | 301/301 | +0.150000 | -0.145919 | -0.145614 | -0.262842 | NO |
| CE03 | 147/147 | +0.150000 | +0.150000 | +0.150000 | +0.150000 | NO |

D07's source minimum occurs at120.665314s near(5.379927,7.153598,0.348057),
yaw2.046685rad: -4.884mm source / -1.371mm raw, with6 negative source samples.
CD12's source minimum is -0.183185m at132.392166s near
(4.560115,7.822622,0.335945), yaw-0.485625rad; its raw minimum is -0.180762m.
It has106 negative source samples and4 SupportGap samples. The first support
refusal is37.511013s near(7.864249,6.277672,4.839736). CS03 has151 negative
source samples and a -0.145919m minimum. These are planning-envelope violations;
no claim of exact physical body/foot collision is inferred from the envelope.
[Exact witnesses](geometry_excursion_witnesses.json) retain sample coordinates,
yaw, time and all scorer values.

## Remaining failure bill

All six failed routes terminate with pct_endpoint_pose_rejected. That message
combines geometry and repair/live-feedback constraints, so it is not itself a
typed physical-support verdict. [Terminal excerpts](results/failure_terminal_bill.json)
retain the actual logs.

- G05: factory standing shifts Y from8.013188 to about8.109986m. All63 measured
  navigation poses return SupportGap(11), minimum extra gap -0.076893m. No global
  route or local planning round was produced. Source/raw solid margins remain
  positive. Endpoints and radius were not moved to bypass this failure.
- A04 and CU06: stop in the stair/landing region; all sampled navigation body
  poses remain hard-support Free with positive source/raw margins. Repeated live
  feedback precedes endpoint refusals. The saved logs motivate an exact
  request/feedback replay; they do not prove which asynchronous witness caused
  each refusal. A04's longest low-speed interval is53.690s under the current
  navigation-window definition.
- CM02:741/765 local rounds succeed, but arrival fails despite
  positive sampled hard support and solid margins. The final PCT endpoint
  refusal needs request-level attribution, not a geometry waiver.
- CS03: same-floor execution has substantial negative source/raw solid margins
  before terminal refusal; preserve this separate tracking/heading counterexample.
- CE03: no global route/local planning round; measured start geometry remains
  Free, and the logs show live feedback and endpoint refusal. Offline admission
  does not explain the runtime start/goal/feedback difference by itself.

No production repair was made during this fixed-version evaluation. In
particular, no endpoint snapping, coordinate exception, threshold relaxation
or success-seeking rerun was introduced.

## Resource and delivery evidence

The unchanged admission gate waited for20GiB RAM, no GPU compute job and10GiB
free output disk. Captures use the existing larger /home filesystem. A new
IsaacLab process was observed during A04; the60-second probe did not observe
such overlap in the other nine cases, which is not a claim of exclusive host
use. [Resource overlap audit](results/physical_resource_overlap.json) retains
per-case timings. Other jobs were not stopped or modified. Analysis wall times
include resource waiting; they are not planner latency measurements.

Ten real local MP4s total72,466,870 bytes. All pass full remote decode,
first/last recorded-state coverage, causal curve timing and zero-new-physics
verification, and all returned bytes match SHA-256. Twenty frames across all10
videos were visually inspected, including terminal captions and geometry
excursion windows. The compact return is462files /9,426,541bytes, with no build
caches or bulk raw recordings. Failed videos retain the entire recorded prefix.

- [Complete metric table](physical_table.csv) and [machine-readable summary](physical_summary.json).
- [Per-file/video hashes and remote paths](physical_return/return_inventory.json).
- [All videos](delivered/README.md).

The display-only adapter was corrected for the current frozen source/<path>
snapshot layout; actual v280/v282 hash checks pass, with red/green receipts.
The source/native/physics identity was unchanged. The monitoring automation and
owned resource probe are stopped after this delivery. No commit, task archive
or selected-baseline promotion is implied.
