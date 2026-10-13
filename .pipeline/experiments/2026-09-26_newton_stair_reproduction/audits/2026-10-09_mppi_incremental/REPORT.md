# Step 1 and gpu5070ti execution

Stage: experiment + analysis. **Keep step 1 as diagnostic instrumentation.**
Its declared benefit is accurate failure-stage reporting. It is not a navigation
speed optimization. Steps 2–5 remain pending; the navigation reference remains v48.

Compilation, component tests, actual Newton trials and full-data analysis ran on
gpu5070ti. Local work was limited to source/configuration, source identity checks
and compact reports. Bulk is at `/data/sun/vla_mppi_20261009` on its data disk.
The same original CPU physics solver was retained; no CUDA acceleration or
Jetson performance claim is made.

## Same-host comparison

Both variants used the frozen v125 Linux host entry, the same Foxy x86_64 image,
original Building corner fixture, original policy/factory startup, geometric
sensing and unchanged safety gates. Each variant had one independently initialized
physical trial. Both original navigation backends recorded `FINISHED` with
`native arrival and measured PD hold`; state copyback and closed-output retention
passed. Neither trial recorded a fall. This is a bounded smoke comparison, not a
reliable success-rate estimate or full navigation qualification.

| Metric | Baseline native v114 | Diagnostic native v122 |
|---|---:|---:|
| Trial | v125_baseline_attempt01 | v125_candidate_attempt02 |
| Planning rounds | 957 | 1055 |
| Successful / failed rounds | 951 / 6 | 1052 / 3 |
| Mean solve time | 4.031 ms | 3.075 ms |
| P95 solve time | 8.049 ms | 6.862 ms |
| Maximum solve time | 263.284 ms | 172.769 ms |
| Rounds above 60 ms | 7: 5 successful, 2 failed | 7: 6 successful, 1 failed |
| Measured path | 26.392 m | 26.355 m |
| Actual physics end | 60.798 s | 55.721 s |
| Actual real-time factor | 0.99939 | 0.99969 |
| Longest measured pause | 9.695 s | 4.298 s |
| Full-window successful planning frequency | 19.093 Hz | 23.527 Hz |

These independently evolving trajectories are not identical planner inputs.
Do not attribute the observed timing or mission-duration difference to diagnostic
logging. Full-window frequency includes waits/stopping and is distinct from the
active planner rate; sustained 30 Hz remains unvalidated.

## Diagnostic acceptance

- All 1055 completed ordinary rounds have exactly one diagnostic record, and
  every success flag agrees with the original planner result.
- All three failed rounds have reasons. Last rejections were dynamics/refinement
  (12.595 ms), optimizer (172.769 ms), and dynamics/refinement (20.853 ms).
- The three last-rejection contexts recorded fresh LiDAR observations. This does
  not prove every earlier query or every other safety input was fresh.
- Target candidates rejected inside a successful round are not failed rounds.
  Per-stage counts count branch rejections, not independent planning attempts.
- Decision-token parity and compiled outcome semantics passed on Linux; real
  native epoch/no-translation/unknown-map branches passed.
- The original native publication fixture was restored from the SHA-verified
  archive (85 file hashes checked). With identical recorded scans, a fixed clock,
  fixed RNG seed and ordered mapping, both native builds produced bit-identical
  33 control-point values, 15 knots and trajectory duration. Both passed the
  original successful-publication and stale-input rejection assertions; candidate
  diagnostics were active. See `curve_results/result.json` and the hash-bound
  logs. This component fixture does not replace the asynchronous physical pair.
- Each native variant built all 14 packages and passed 36 component tests.
  The 1000-emission native diagnostic probe measured mean 2.91 us / P95 3.81 us,
  below the predeclared 200/500 us limits. This isolated emission cost is not a
  bound on total planning latency.

## Host migration evidence and retained failures

v123 preserves the output-directory ownership failure before physics. v124
preserves a real factory stand followed by the Foxy log-directory creation race
before navigation. The race was reproduced with 12 concurrent initializations:
3 failed without the directory and 0 failed with it pre-created.
v125 pre-creates log directories, runs native outputs under the host UID/GID and
verifies both host and container open-writer detection. Its actual 10-child ROS
graph preflight passed. v125 candidate attempt01 failed the socket-bind preflight
before container creation/physics; later all five ports were verified free and
attempt02 ran. The first failure did not identify the specific occupied port.

All earlier attempts remain on the server. The old Mac v116 attempt03 is not a
completed comparison, and its temporary root is unavailable. v122's Mac trial
has compact results but unavailable temporary raw data; it is not used for this
keep decision or for cross-host timing claims.

Fixed-input probe attempts 1 and 2 also remain: the first did not apply ordered
mapping, and the second stopped on the comparison script's mistaken assumption
that the control matrix had N rows instead of 3 rows. Attempt 3 passed after
those test-harness corrections; native binaries and physical-run data were not
changed. The actual 3D matrix values, not their printed layout, were compared.

## Reanalysis and retained data

Run `analyze_remote_pair.py` from this directory with the server Newton Python.
It uses frozen v125 analysis, verifies captured ZIP members, checks execution and
retention, joins original round boundaries and writes `results/comparison`.
`remote_results/comparison.json` contains exact metrics; per-variant CSV files
contain the complete measured timing curves. `remote_artifacts.json` records
every retained run/evidence file hash and absolute server root. The two retained
trials total 182,892,663 and 164,340,370 bytes. The compact comparison return is
253,621 bytes. Full build logs, images, binaries and raw captures stay remotely.

Step 2 was subsequently implemented as v126 and parked after its first paired
physical trial failed navigation. Keep the step-1 native v122 / host v125. See
[step-2 evidence](../2026-10-10_mppi_step2/REPORT.md); steps 3–5 remain pending.
