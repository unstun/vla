# v192 Mac attempt 01: shared-state transport passed; navigation failed

Stage: experiment + analysis. Execution date: 2026-10-14. **The authorized full
Mac Building attempt ran, but did not complete the route.** The driver reports
`route_arrived=false` (no arrival field was produced), `execution_completed=false`,
and terminal status `FAILED` with `nav2_failed` / action status 6.
The frozen v192 harness reuses native_version=v191; recovery_v191 was not rebuilt.

The pre-run gates passed: 24 Mac host tests, bidirectional Docker bind-mount
exchange, all four active Nav2 lifecycle nodes, actual v191 loaded libraries,
protected-path checks, and freeze/verify of 4,610 source/snapshot pairs and 618
runtime inputs. The native receipt retains its already-qualified 45 colcon
entries with zero errors/failures/skips. All 137 copied native snapshot files
match v191. The sole predecessor edit removes the explicitly authorized trailing
forward-reference paragraph from v191/RESULTS.md.

| Measurement | Observed result |
|---|---:|
| Route arrival / terminal | False / FAILED |
| Recorded physics end, including factory startup | 118.886292 s |
| Navigation interval, simulation / wall | 107.865468 / 117.584898 s |
| Navigation RTF | 0.917341 |
| Recorded body path (sensor samples) | 72.572289 m |
| Last recorded XY distance to original goal | 4.832352 m |
| Last recorded yaw error to requested goal | 0.525200 rad |
| Final held-pose acceptance | Unavailable; no arrival/terminal PD hold |
| Falls / dropped physics steps | 0 / 0 |
| Successful local planning / direct command rate | 26.066273 / 29.984195 Hz |
| Completed / successful planning rounds | 3124 / 3065 |
| Maximum planning-round time | 774.569792 ms |
| PCT route / B-spline publications | 13 / 3096 |
| Direct-command stop transitions / subsequent restarts | 13 / 12 |
| Observed zero-command duration after those transitions | 6.120389 wall s |
| Measured low-speed intervals at least 1 s | 2; 3.398132 s and 1.799011 s |
| Shared-state closure / retained-byte verification | Passed |

The original nav2.log records **seven** `Native SCAN did not publish a trajectory
before timeout` errors and **six** completed Wait recoveries. Before the final
abort, SCAN repeatedly reports an occupied target with no collision-free point
on the global trajectory. These are observed failure conditions; the underlying
geometry/planner cause is not established by this run. No source repair or retry
was performed after freezing v192.

The applied-state ZMQ client, receiver, port and tmpfs shadow were absent from
the v192 runtime graph. Current command state was written atomically through the
existing asynchronous writer; finish status was read from the shared directory.
Closed host/container files match byte for byte and the analyzer rechecked the
retained originals. This establishes the recorded shared-state closure, not
continuous per-step visibility or general VirtioFS reliability. The driver did
not abort with a fresh-snapshot timeout.

v189 recorded **20 replacement stops and 34.225422 wall s** of cancel-to-proof
waiting (the requested 34.22 s reference), plus 2.290349 s from proof to the new
route. v192 has no P2B measured-stop protocol, so its corresponding proof count
and wait are **not applicable**, rather than zero. Its 13 observed cmd_vel
nonzero-to-zero transitions and 6.120389 s zero-command exposure use different
criteria and cover an incomplete route. Initial zeros are excluded; the last
unrestarted zero ends at the last recorded command. They do not establish a
full-route stop reduction, successful recovery, or sustained physical holding.
v189 traversed the route but failed its final held-yaw gate; v192 never arrived.

The launcher/supervisor exited 0 for recording and retention, and retention
explicitly records `explicit_failure=true`. That process status is not navigation
acceptance. The raw ZIP preserves 1,083 files (313,583,153 bytes). Full-route
verification and outcome remain false. `v193` and its review MP4 were **not
created**, because the requested route-arrived/FINISHED condition was not met.
The completion milestone was not emitted.

Evidence: [metrics](results/v192_mac_full_attempt01/metrics.json),
[failure/stop audit](results/v192_mac_full_attempt01/failure_metrics.json),
[terminal log excerpt](results/v192_mac_full_attempt01/terminal_log_excerpt.txt),
[outcome](results/v192_mac_full_attempt01/outcome.json),
[shared-state witness](results/v192_mac_full_attempt01/shared_state.json),
and [reproducible closed-run analyzer](results/v192_mac_full_attempt01/analyze_outcome.py).

The failed capture is durably archived at
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v192_20261014/v192_mac_full_attempt01_failed.tar`
(373,309,440 bytes; SHA-256
`1f8c8c1a9ecc91d0a39a81e2ae0bd8a80a7b562e6fd85321daead2bfad075e17`).
Remote verification checked all 137 TAR files and all 1,083 original raw ZIP
members. See [artifact/restore record](results/v192_mac_full_attempt01/ARTIFACTS.json).
The local temporary trial is retained. This archives failure evidence, not a
completed-route display. Post-run [frozen-source verification](results/v192_mac_full_attempt01/final_freeze_verify.json)
and [protected-path checks](results/v192_mac_full_attempt01/final_protected_check.json)
also passed.
