# Repeated v122 / v127 investigation

Stage: experiment + analysis. Status: repeated experiment and replay complete;
navigation reliability remains unqualified.
Dr Sun explicitly asked to distinguish adaptation-3 regression from original
system instability. This audit supersedes the earlier early-stop rule only for
these repeats. It does not change the frozen source, thresholds or prior record.

## Decision

The retained v122 system is demonstrably unreliable in this scene. Six fresh
unchanged v122 runs produced zero arrivals, five navigation failures and one
fall. Six unchanged v127 runs produced one arrival and five navigation failures.
The original single successful control and failed candidate did not establish
an adaptation-3 regression.

No validation-verdict regression was found on the captured inputs: 28,720
candidate curves, 11,691 publication epochs and nine reconstructed controller
queries agree between the actual installations. This does not prove that v127
has zero effect on asynchronous scheduling or reliability. Its live latency
tails were worse in this small sample. Keep v127 parked and the selected native
v122 / host v125 unchanged; diagnose shared rejection/recovery behavior before
adopting another adaptation. No navigation fix or adaptation 4–5 was performed.

## Fresh experiment results

| Metric | v122 baseline | v127 adaptation 3 |
|---|---:|---:|
| Arrived with measured hold | 0 / 6 | 1 / 6 |
| Nav2 action failed | 5 / 6 | 5 / 6 |
| Fell in physics | 1 / 6 | 0 / 6 |
| Median of run-level P95 solve times | 4.262 ms | 4.589 ms |
| Median of run-level P99 solve times | 14.067 ms | 16.755 ms |
| Median of run-level maximum solve times | 149.340 ms | 289.340 ms |
| Completed planning rounds over 60 ms | 26 / 4,608 | 39 / 5,252 |
| Failed planning rounds | 39 / 4,608 | 54 / 5,252 |
| Median longest low-speed interval | 6.347 s | 10.444 s |

These are whole planning rounds, not isolated validator calls. Different mission
durations, physical states and recovery histories make the live timing comparison
descriptive rather than an identical-input causal estimate. Baseline RTF spans
0.959–1.000 and candidate RTF 0.999–1.000. No other Docker workload was active
at the per-trial preflight, but this is not a controlled OS-scheduler experiment.

Arrival Wilson 95% intervals are 0–39.0% and 3.0–56.4%. The two-sided Fisher test
is p=1.0; it neither establishes equivalence nor proves the candidate better.
Attempt01 is excluded from this balanced comparison. Including that historical
pair gives one arrival in seven for v122 and one in seven for v127, as context
only. All 12 fresh runs have verified state copyback and complete retention.

| Order | Run (prefix `v127_`) | Outcome | Travel |
|---:|---|---|---:|
| 1 | candidate_attempt02 | Navigation failed | 14.989 m |
| 2 | baseline_attempt02 | Navigation failed | 23.210 m |
| 3 | baseline_attempt03 | Navigation failed | 23.513 m |
| 4 | candidate_attempt03 | Navigation failed | 23.477 m |
| 5 | baseline_attempt04 | Navigation failed | 23.250 m |
| 6 | candidate_attempt04 | Arrived and held | 26.542 m |
| 7 | candidate_attempt05 | Navigation failed | 23.612 m |
| 8 | baseline_attempt05 | Fell; no Nav2 terminal result | 16.052 m |
| 9 | candidate_attempt06 | Navigation failed | 23.748 m |
| 10 | baseline_attempt06 | Navigation failed | 15.693 m |
| 11 | baseline_attempt07 | Navigation failed | 15.702 m |
| 12 | candidate_attempt07 | Navigation failed | 22.283 m |

Source: `results/analysis/summary.json`, `trials.csv`, per-run `physical/` outputs
and `results/batch/progress.json`. Preserve failures as part of the comparison.

## What actually fails

The label `scan_safety_evidence_stale` is ambiguous. The unchanged controller
uses it for a negative native verdict **as well as** expired evidence
(`versions/v114/src/scan_nav2_controller/src/controller.cpp:493`). Of nine
detailed controller rejection events in the fresh batch, eight have fresh
recorded proof/observation ages but a negative native verdict; one exceeds the
250 ms observation limit. Do not call all nine a mapping backlog failure.

Specific directly recorded chains:

- Baseline attempt02: no progress; then observation age 254.860 ms with an
  immediate native rejection; after recovery a new trajectory is still missing
  at the unchanged 2 s startup timeout; Nav2 fails.
- Candidate attempt02: an initial missing trajectory consumes a recovery;
  later fresh observation age 119.934 ms, but the curve is rejected at phase
  2.432300 s; a further safety stop is followed by no progress and final failure.
- Baseline attempt03 and candidate attempts03/05/07 both show fresh-data native
  rejection around the same stair/turn region (approximately x=8.0–8.2,
  y=5.8–5.9, z=4.8 m), followed by stalled recovery or a missing trajectory.
  These logged nearest poses are approximate, not exact collision locations.
- Baseline attempts06/07 already log repeated path-search pool-boundary errors
  before the controller rejects the remaining curve. Subsequent native state
  enters WAIT_TARGET, then the mission fails. The logs do not prove which
  individual geometry/support predicate caused the rejection or which stop
  acknowledgement condition ended recovery.
- The successful candidate attempt04 also encounters startup and progress
  failures, but recovers and arrives. An intermediate failure does not itself
  imply mission failure. Baseline attempt05's fall is a separate outcome;
  its physical cause has not been isolated here.

`results/batch/diagnosis.json` preserves ordered error/revocation events and
original line numbers. The nine detailed events cover only controller-query
rejections, not every asynchronous safety callback. The fresh batch also has
asynchronous `scan_safety_rejected` stops, startup timeouts and progress failures.
Sensor computation peaks below 30 ms and sensor publication delay at 40.017 ms,
while background map work peaks at 523.536 ms (baseline) / 429.388 ms (candidate),
with queue depth reaching five in both arms. Those mapping durations are not
planner-thread blocking times; their contribution must be diagnosed per event.

## Same-input replay and timing

The corpus includes all 12 fresh runs and the two historical attempt01 captures.
It contains 28,720 captured candidate-stage curves (including intermediate and
rejected candidates), not 28,720 independent navigation trials. Run order is
A/B/B/A/A/B, three numeric passes per installation. All six output pairs have
identical verdict-file SHA-256 values. All 28,720 boundaries pass; the same
2,418 candidates fail dynamics in each pass. All 11,691 epoch verdicts agree,
and input curve controls/knots remain unchanged.

Median of the three pass-average PVA/dynamics times: baseline 5.889 microseconds,
candidate 5.961 microseconds, a 0.072 microsecond difference. This isolated check
is roughly 0.006 ms per curve; it is not a full controller or physics deadline
test and does not time every collision query. It provides no evidence that the
extracted numerical checker explains 100–300 ms whole-round spikes.

All nine queries on three reconstructed recorded map prefixes match, including
the first failed fresh run from each arm and the historical failed candidate:

- For the baseline attempt02 and historical candidate attempt01 fixtures,
  the same recorded curve/body/map is clear at 249 ms observation age and
  rejected at 251 ms in **both** installations. Their logged-phase queries
  reproduce the original rejection message and first sample.
- For candidate attempt02, both installations reject the fresh-data curve at
  the same future phase, 2.432300 s. Moving the observation age to 249 ms does
  not make it pass. At 251 ms both reject from the first sample.

The three logged-phase replay messages reproduce the corresponding live
first-rejection sample metadata, but ordered prefix reconstruction does not
restore original DDS consumption, asynchronous revisions or exact pose timing.
See `results/replay/result.json`, `input_identity.json`, `map_*/maps.tsv` and
`results/batch/replay_input_manifest.json` for scope and hashes.

Existing runtime profiles locate the live maxima in target search, seed search
and optimizer retries. Examples: baseline attempt03 spends 243.368 ms across
13 attempts (80.623 ms seed / 158.329 ms optimizer); candidate attempt03 spends
300.530 ms across seven attempts (281.262 ms optimizer) and ultimately succeeds
in that round; candidate attempt06 spends 293.588 ms across seven attempts
(287.808 ms seed). Profile categories overlap and must not be summed as if
independent. The candidate tail difference is real in this sample, but captured
states and retry histories differ; a full same-state planner/scheduler experiment
would be needed to attribute it to the refactor.

## Next narrow investigation

Start from retained v122 and one captured fresh-data rejection: determine which
native footprint/support check blocks the remaining curve, then follow the
replacement search, stop acknowledgement and new-target handoff through
recovery. Preserve the existing time limits and collision checks. Compare any
future repair with repeated unchanged controls; another single successful run
will not establish reliability. This is the recommended next task, not work
silently included in this diagnosis.

## Protocol

Six additional runs of unchanged native v122 and six of unchanged native v127
on gpu5070ti, in BAAB/ABBA/BAAB order (B=new). Same frozen v127 host, existing
qualified native installs, original Building corner, CPU Newton and 90 s bound
with early arrival plus measured hold. Run all navigation outcomes; no selection
of successful runs, no concurrent build/replay during physics. Attempt01 from
each arm is historical and excluded from the primary balanced count comparison.

See PLAN.md and run_batch.py. The source/install/image gates run for each trial.
Original v122 is /task/candidate/install; v127 is /task/step3_v127/install.
No navigation code or parameter changes, hardware actuation, training or next
adaptations are part of this investigation. Main task and v48 reference remain.

## Evidence interpretation

Arrival/hold, action failure, fall and incomplete execution are separate outcomes.
Per-round failure or a >60 ms successful solve is not a failed navigation mission.
Compare all runs' rates and tail measures; six runs per arm have broad confidence
intervals. A non-significant exact test does not establish equivalence. Controls
are independent reinitializations with asynchronous timing, not repeated seeds
promoted to deterministic trajectories.

The replay compares actual captured 17-digit candidate curves and original seed
boundaries against both native installations. Controller-query replay uses exact
saved cloud points and poses, processed in a declared ordered prefix; it does
not claim to restore original DDS take batching or live asynchronous map revision.
Logged rejection phase has six decimal digits, and query pose comes from the
last recorded body sample at/before the check. Extra249/251ms queries are explicit
clock counterfactuals on fixed input, with unchanged source timestamps/threshold.

## Storage and reproduction

Remote execution/bulk root: /data/sun/vla_mppi_20261009.
Run metadata/progress: results/step3_repeats; physical trials:
trials/v127_{baseline,candidate}_attempt02..07. Original source remains local.
After the full batch, summarize.py reads closed captures, then replay/prepare.py
exports numeric cases and selected first failures' recorded map prefixes.
replay/run.py --attempt N builds against the two exact installs and alternates
three numeric replay passes per arm before comparing controller query results.
Return compact reports and SHA-256 locators only; preserve raw trials and failed
harness attempts on the remote data disk. Do not remove the existing Git lock.

Final verification: 174 compact evidence files / 3,281,791 bytes returned and
individually SHA-256 checked locally. The 12 retained trial trees total
2,101,080,393 bytes on gpu5070ti and were rehashed against their retention
receipts. All 2,942 replay-input files have byte locators and SHA-256 identities.
Frozen source verification passes locally and remotely (2,840 source pairs,
618 runtime inputs). Baseline 1,235 / candidate 1,236 installed files still
match the original receipts; no native rebuild occurred during comparison.
No experiment containers or trial processes remain. See
`results/closeout_manifest.json` and `return_verification.json`.

Both replay probes built and ran successfully on their first attempt. Initial
report download failed because its local parent directory was absent; creating
that directory and repeating the download resolved it without rerunning or
altering experiments. The pre-existing Git index lock and unrelated dirty
worktree were preserved; no staging, commit or main-task archive was performed.
