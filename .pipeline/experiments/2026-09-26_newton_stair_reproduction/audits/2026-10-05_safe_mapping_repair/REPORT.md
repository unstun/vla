# Compact polling and mapping repair: review required

Stage: experiment + analysis, 2026-10-05. **v79–v82 are implemented and component
tested, but the integrated v82 candidate fails physical continuity and steady
30 Hz acceptance. Keep v48 as the runnable reference.** v49 stays frozen and
excluded. No new solve deadline, retry circuit breaker, stop reason, watchdog
threshold, inflation envelope or goal/yaw/PVA/dynamic/support rule was introduced.

## Implementation in the requested order

| Version | Change | Direct checks |
|---|---|---|
| v79 | Compact default `/state` route summaries; full records written once to a run-owned JSONL; explicit full-history access | 23 Python/real-HTTP/backend tests; unchanged control/stop ASTs; actual ROS callbacks under 360 compact polls at 30 Hz |
| v80 | Unordered global-voxel semantic membership and row-based inflation address arithmetic; original offsets/counts/masks retained | Eight native packages build; 188 scans per arm, three runs per arm, every scan's map/history digest equal; 14 synthetic sliding phases equal |
| v81 | Single mutable mapper, immutable revisions, shared immutable support tables, writer-side retirement, newest-map validation/publication lease | Eight packages; 26 snapshot/pairing/freshness/support/worker/shutdown/curve-rejection checks; 188-scan sync/async equality; original native and recorded suites |
| v82 | Guarded reduction of spatially identical fixed-point queued scans; newest frame fully processed | Eight packages; ten backlog cases/20 checks; exact map/history/timestamp equality; all 188 moving recorded scans preserved; all original suites rebuilt against final layout |

The backlog policy is deliberately narrow. A genuine queue of two or more
frames is necessary but insufficient: distinct geometry, changed poses/support,
unpaired frames and unsaturated probability updates retain full processing. No
distinct observation is discarded. Actual physical runs report **zero reduced
frames**, despite queues reaching six clouds. This policy cannot resolve their
processing overload by losing obstacle evidence.

## Component performance and safety

The encoder comparison uses the exact retained trial02 final backend state,
not a fabricated pre-fault snapshot. The cached ROS Python runtime measured:

| Measurement | Original full polling | Compact polling |
|---|---:|---:|
| Response bytes | 1,516,647 | 35,792 |
| Mean encoding | 42.428 ms | 0.307 ms |
| Maximum encoding | 83.505 ms | 0.833 ms |

This run overlapped compilation; it establishes encoder overhead reduction, not
an idle-host absolute bound or the sole cause of historical heartbeat faults.
The actual ROS callback test passes 360 polls at 30 Hz with a **38.875 ms maximum
raw callback gap** and an open gate. Disabling the input still triggers the
original 200 ms `heartbeat_stale`; resumed messages cannot reopen the latched
fault. The first test incorrectly admitted raw commands before body readiness
and correctly latched `odom_stale`; the corrected test follows production's
body-ready-before-admission contract. Its failure evidence is retained.

The map replay's median seven-scan batch falls **320.599 → 213.193 ms**; observed
per-scan maxima across three runs are **136.686 → 113.716 ms**. Every recorded
state matches, including occupancy, inflation counts, ray buffers, ring origin
and sorted semantic memberships. These are component tests, not a reproduction
of the full historical 976.721 ms input scope. Snapshot support sharing reduces
typical fixture copy time from about 20–22 ms to 5–6 ms. Planner enqueue timing
is separate from mapper throughput and complete planning latency.

Final v82 repeats the original 35 native checks, 64 cache checks, 10 endpoint
checks with 3,000 sampled footprints, 15 controller epoch/emergency/cancellation
checks, and 98 checks on each of two original recorded maps, including 47 warm
checks per map. It additionally passes 26 snapshot checks and 20 backlog checks.
Newly mapped occupied evidence rejects an older complete curve through the
original full-cubic collision checker. No parameter or acceptance threshold was
relaxed to pass these tests. Fixture path/controller-config/startup failures are
retained separately from qualified attempts.

## Two actual Mac corner runs

Both independent runs use the unchanged v76 Building corner fixture, historical
final goal, actual geometric LiDAR, original factory/PD/RL behavior and a 6-CPU
amd64 ROS execution copy. Each records **89.962 simulation seconds**. These are
Mac measurements; gpu5070ti was used only for verified artifact storage.

| Measurement | v82 trial01 | v82 trial02 |
|---|---:|---:|
| Successful local planning, full navigation wall exposure | 11.114 Hz | 10.959 Hz |
| Attempt frequency | 24.671 Hz | 22.729 Hz |
| Maximum complete solve | 491.143 ms | 312.939 ms |
| P99 complete solve | 120.744 ms | 122.139 ms |
| Rounds >=100 ms / >=1000 ms | 34 / 0 | 35 / 0 |
| Measured path | 20.251 m | 24.591 m |
| Longest measured low-speed pause | 23.787 s | 31.283 s |
| Emergency transitions | 850 | 850 |
| Final backend gate / stop flow | open / none | open / none |
| Actual RTF | 0.873 | 0.914 |
| Maximum queued clouds / discarded distinct frames | 6 / 0 | 6 / 0 |

No `heartbeat_stale` was recorded. The prior v76 corner run observed
1,307.535 ms maximum and 14.700 successful Hz over a shorter recording. The
new observed maxima are lower, but trajectories and exposure differ: **do not
claim a matched-input causal speedup, or acceptance from the lower maximum.**
The robot pauses severely and neither run records arrival. Emergency holding
does not constitute formal terminal stop completion. Minimum observed base-up
components are 0.896/0.872; these telemetry values do not establish a full
contact/collision acceptance verdict. The absence of a `fallen` result field
must not be relabeled as a verified no-fall result.

## Root cause of the failed integration

The writer does not consistently deliver a completed map inside the original
250 ms scan validity interval. Mean background work per published batch is
97.406/106.781 ms, with maxima 816.134/1,062.101 ms; snapshot copies add further
work. These inclusive batch times are not individual-cloud or planner-thread
solve times. Queues reach six genuine, different observations, so duplicate-only
reduction correctly does not discard them.

The first trial's first emergency follows input checks reporting **0.2848 s
cloud age**, repeated target rejection and `Obstacle discovered; emergency stop`.
The unchanged collision/freshness contract rejects stale input; a fast planner
loop over an older completed snapshot can therefore repeatedly enter the old
emergency state even while the mapper is progressing. The original synchronous
input application instead waited for mapping work before making that decision.
Healthy backend heartbeat service does not make stale mapping acceptable.
See `trial01_first_emergency.log`, `trial02_first_emergency.log` and
`freshness_failure.json`; all traces are bound to the closed raw archives.

The next repair must establish sufficient mapping throughput and a valid
snapshot handover under live load. Review whether to retain synchronous mapping
while optimizing further, or synchronize decisions with pending completed input
without weakening source ages or cancellation. Do not silently broaden dropping
to distinct scans, extend the age limit, restamp an old map, mask emergency
events, or reintroduce a v49 deadline. **v82 is frozen as failed acceptance.**

## Review artifacts and preservation

- `versions/v82/analysis/trial01/` and `trial02/`: complete metrics, rolling
  one-wall-second frequency against simulation time, solve-latency plots and
  measured path, including failed and paused intervals.
- `versions/v79–v82/`: frozen source/configuration, exact materializers and
  component qualification. v83 is display-only review of the actual failed run.
- `storage/`: per-file SHA-256 manifests and remote verification receipts for
  full captures, all failed/qualified checks and the exact installed runtime.

Bulk storage is `gpu5070ti:/home/sun/vla_artifacts/2026-10-05_safe_mapping_repair`.
Restore a named directory with rsync and verify its `storage_manifest.json`
before reanalysis. Restore the recorded physical source path or create a new
path-bound display contract preserving all input hashes. Regenerate native
source with the frozen v81/v82 materializers, build inside the pinned image and
verify source/install receipts. The original scan prefix is regenerable from
the prior v76 remote capture using the frozen v78 extraction/preparation tools.
Keep only source/configuration, compact reports/plots/provenance and the review
MP4 locally. Cleanup requires closed processes and current remote byte identity.

The [comparison plot](time_series_comparison.png) shows both complete recordings.
The actual failed trial01 [review video receipt](../../versions/v83/REVIEW_VIDEO.json)
points to the local MP4; its display-only source is v83. Five archives contain
343 files / 590,903,005 bytes, all remotely SHA-verified and checked again against
the current local bytes before cleanup. The [cleanup receipt](local_cleanup.json)
records removal of 1,028,377,799 owned temporary bytes, including regenerable
build and cache copies. A failed first render invocation survives as compact
evidence under `versions/v83/failures/render_attempt01/`.

Changes remain uncommitted for review. A pre-existing `.git/index.lock` and
other Git activity were observed; neither the lock nor another session's work
was altered. The main Trellis task remains in progress because continuity and
30 Hz acceptance failed.
