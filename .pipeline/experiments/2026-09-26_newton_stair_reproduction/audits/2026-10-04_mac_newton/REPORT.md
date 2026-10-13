# Newton Mac validation of the repaired planner

Stage: experiment + analysis, 2026-10-04. Dr Sun explicitly authorized Newton testing on Mac while gpu5070ti was busy. The two measured route trials ran the exact frozen v63 native planner (v62 epoch correction plus v63 optimizer failure propagation), original v59 Newton physics/policy/backend and unchanged production configurations. Host integration packages are v67/v68. No gpu5070ti access or workload was used.

**Actual Newton runs confirm stair motion, but neither completes the requested90-second endpoint or meets30Hz. Both measured route trials stop through the original heartbeat fault flow.** The Mac native planner runs as linux/amd64 code under Docker emulation, while Newton physics uses the Mac ARM64 CPU; these are not matched hardware measurements against gpu5070ti.

| Actual Mac result | Route trial01 | Route trial02 (prepared cache) |
|---|---:|---:|
| Run ID | v67_mac_trial01_attempt01 | v68_mac_trial01_attempt02 |
| Actual native end time | 31.614254 s | 46.506069 s |
| Physics integrations | 31,620 | 46,520 |
| Navigation wall RTF | 0.695328 | 0.655633 |
| Successful planning / full navigation wall window | **16.81475 Hz** | **18.60555 Hz** |
| Median complete planning round | 11.3037 ms | 9.5102 ms |
| P95 complete planning round | 102.9532 ms | 65.7734 ms |
| Maximum complete planning round | **494.7161 ms** | **836.6828 ms** |
| Rounds >=100 ms / >=1000 ms | 27 / 0 | 26 / 0 |
| Measured3D path | 13.19696 m | 22.74185 m |
| Longest measured low-speed interval | 1.79901 s | 2.39868 s |
| Terminal status | FAILED: heartbeat_stale | FAILED: heartbeat_stale |

Zero observed >=1000ms rounds in these shortened trajectories does not demonstrate extreme-tail elimination. Neither reaches the post70-second anomaly. The two originally requested complete90-second validations remain outstanding; the runs were not prolonged by weakening safety checks. The frozen v63 optimizer regression still establishes3 failed repair searches ->1, but these independent Mac trajectories do not isolate its live latency effect. The latest original gpu5070ti v59 full run remains26.42581 successfulHz and1236.709246ms max; it is historical context, not a valid matched-host reduction denominator.

## Stop evidence

The original backend requires a matching-generation heartbeat within0.20wallseconds. Immediately before the recorded fault-flow start, the last recorded matching heartbeat is older by at least0.383362s in trial01 and0.306918s in trial02. The existing flow cancels, confirms controller hold and completes the fault stop. The final goal is not attained; both Linux state copybacks match the last acknowledged applied bytes. No watchdog threshold, goal/yaw, stop/cancel protocol or native collision/stair/PVA/dynamics rule was changed.

The independent raw-command observer still reports about30Hz; its largest receipt gaps are0.079901s and0.122599s, both below0.20s. Therefore a total loss of raw-controller publication does not explain the backend fault. Backend delivery/executor/filter behavior under this Mac host setup needs a separate trace; the available observer omits message identity and cannot distinguish queueing/drop from identity-filter rejection. Body callback computation maxima are16.366ms and1.509ms and do not alone explain the gap. These are boundaries for the next diagnosis, not a confirmed scheduling root cause. [Recorded heartbeat windows](heartbeat_stop_windows.json), [callback/observer evidence](backend_timing_evidence.json).

## Source, startup and preserved failures

All native source and installed bytes are checked at launch against the frozen v63 source and cached ROS image. Newton initializes the original Building robot, original factory/PD/RL startup, geometric sensing and CPU solver graph. The physical-floor payload is regenerated from existing pinned maps and matches its original SHA-25620acd5cf1ef156c5bd336b12651efe9a18e9959816905b05178ed44b1a181c96. Host entry tests reject changed/failed builds, old run data and nonempty applied-storage directories. Full original recorded-corner component qualification remains separately pending; this user-authorized experimental run does not promote the existing Mac subset to full qualification.

v64 fails before physics on the qualification key; v65/v66 fail before physics on two successive temporary-folder admission boundaries. Their frozen sources and evidence remain preserved. A correction raced the v64 freeze; its alternate bytes were saved and the current paths restored from the untouched frozen snapshots. v67 fixes the final episode-folder admission and produces the first measured route. Its first retention attempt refuses a still-open native log writer; after the owned container is removed, a separately recorded closed-retention retry losslessly archives the original bytes. v68 restores complete runtime-container teardown before retention. Its first physical attempt aborts at11.220904 native seconds when the first scan misses the unchanged sensor-period check. Repeating the same frozen v68 with the existing compiled kernel cache prepared before launch yields the second measured route above. The sensor deadline and physics algorithm are unchanged. All these failures remain separately recorded.

## Measurements and artifacts

Hz is the count of successful completions divided by the complete navigation wall window, including waits and the fault stop. The figure uses a trailing1wallsecond window mapped onto actual simulation time. Mac and Docker monotonic clocks have different origins: the analyzer maps their original converged clock samples before selecting a window or placing events on the plot. Factory/native time is not relabeled as simulation zero. Complete-round latency includes every prefix/fixed-height/warm/native recovery attempt.

[Trial01 metrics](trial01/metrics.json), [trial01 time series](trial01/time_series.png), [trial02 metrics](trial02/metrics.json), [trial02 time series](trial02/time_series.png). Each directory contains exact provenance, per-round latency CSV, rolling frequency CSV, maximum-round details and PDF. [Raw data/storage locators](storage.json) bind source/run/host/hash/path and reproduction commands; bulk is temporarily outside the repository. Native build products are removed after validation. No full PNG frame sequence was retained. Following Dr Sun's video request, display-only v69 renders the latest trial into a [53.87-second review MP4](../../../../../output/2026-09-27_lite3_versions/v68_mac_trial01_attempt02_review_v69.mp4), preserving actual wall timing and the final FAILED heartbeat_stale stop. Full decode, source-state identity and visual review pass; [video provenance](../../versions/v69/REVIEW_VIDEO.json) records the3,819,898-byte return. No broad staging or commit was performed.

v48 remains the runnable reference. Full-route continuity,90-second completion, max-tail elimination and30Hz remain unvalidated.

Subsequent investigation: [current bottleneck report](../2026-10-04_mac_bottleneck/REPORT.md)
matches the original raw identities and reproduces the gate dispatch-order
failure mechanism. A fresh observation-only v70 run reaches the90s bound without
heartbeat failure but still records23.423Hz and1316.856ms maximum solve. This
does not establish an optimization or explain the exact earlier OS/DDS delay.
The original temporary raw roots listed in this report are now unavailable;
retained compact analysis, original final result snapshots and review video are
preserved. Fresh v70 raw/storage provenance is in versions/v70/storage.json.
