# Corner-start planner comparison — 2026-10-04

Stage: experiment + analysis. Dr Sun requested starting beside the late corner
instead of repeating the route prefix. Both fresh tests use that starting
condition. The current planner crosses the corner and climbs onward, but still
misses 30 Hz. The upstream integration moves briefly and then remains stationary;
its smaller observed maximum is not a demonstrated performance improvement.

## Starting condition

The fixture comes from the measured approach to the v70 event at native
78.488495 s. Spawn ground XYZ is (6.538910, -6.003162, 3.041690) m, with yaw
-1.425451 rad, about 1.1 m before that event. The original final goal stays
(1.954685, -2.986811, 4.533031) m. The full Building geometry/map, geometric
LiDAR, factory-PD-RL startup, policy, controller and backend remain in use.
Both actual factory handoffs are identical at native 11.020823 s; source/config
and scenario identity are checked in [initial_conditions_verified.json](initial_conditions_verified.json).

The prefix traversal is omitted. Policy, local map and planner state start
fresh; no historical remaining trajectory or recurrent state is restored.
This is a local-scene test, not an exact replay of the historical planner state.
The scenario SHA-256 is
`d2bd7294f45f3819c2d4155711ae3639e1ee812feed6631abf87883a4d22d5d0`.
The five-point triangle-ray spawn screen spans 19.2 mm; this screen alone does
not establish native support admission or dynamics acceptance.

## Fresh physical results

Both use the same Mac CPU physics and cached amd64 Humble planner image. The
requested total recording bound is 40 simulated seconds, including factory
startup. Frequencies count successful completed plans over the actual recorded
navigation wall interval, including waits and failures.

| Measure | Current planner: v76 / native v63 | Upstream integration: v77 / native v71 |
|---|---:|---:|
| Last recorded physics time | 39.990 s | 37.751 s video; 37.771 s pacing |
| Recorded navigation wall interval | 32.857 s | 30.941 s |
| Real-time factor | 0.882 | 0.865 |
| Successful / completed planning chains | 483 / 485 | 10 / 1,226 |
| Successful local planning frequency | **14.70 Hz** | **0.323 Hz** |
| Median solve latency | 8.263 ms | 13.422 ms |
| P95 solve latency | 166.731 ms | 43.218 ms |
| Maximum solve latency, whole recording | **1,307.535 ms** | **311.138 ms** |
| Measured body path | **20.04 m** | **1.13 m**, then stationary |
| Outcome | Bounded capture; goal still active | Failed, incomplete capture |

v76 has 442 accepted warm initializations, 30 rounds at least 100 ms and two
rounds at least one second. Its raw native controller still publishes at
30.0004 wall Hz. The robot does not fall; no measured pause exceeds one second
(longest 0.900 s). One original emergency transition and one current-curve
invalid event remain. This is not continuous-trajectory or arrival acceptance.
Its final state copyback verifies.

v77 fails on the original AppliedClient receive/ACK path (`zmq.error.Again`),
followed by a final-state/last-ACK hash mismatch. The original final result file
is absent and copyback fails. Its last saved backend snapshot has an open gate
and no terminal result; this run does not establish a `heartbeat_stale` terminal
or successful final stop. The analysis uses the actual retained observations
and does not synthesize a result file. Archival/video success does not change
the physical failure status.

## What the corner and long spike show

The corner region is a 1.5 m XY disk around the historical event body position
(7.392298, -6.706414) m. Round positions use the nearest actual saved sensor pose
to their native start timestamp. In v76, 149 completed rounds occupy this
region at native 12.471–18.636 s: median 6.155 ms, P95 43.981 ms and maximum
**397.826 ms**. That maximum is the first cold initialization at the new spawn.

The expanded local recovery chain still reaches **11 attempts** in this region.
That round starts at native 14.457 s, includes two prefix proposals and five
fixed-height attempts, fails, and takes **41.318 ms**. Thus the attempt count
alone does not explain a 1.3-second stall. See
[corner measurements](v76_corner_region.json) and
[11-attempt round](v76_max_attempts.json).

The new **1,307.535 ms** maximum occurs later, at native 29.236 s and body
(8.621, 3.468, 4.513) m, outside the targeted corner. It has four complete
rebound attempts, two prefix proposals and one fixed-height attempt. The warm
connector is rejected and a native A* terminal-recovery search hits its existing
200 ms limit. The measured scopes are:

| Scope | Inclusive wall time | Calls |
|---|---:|---:|
| Input processing | **976.721 ms** | 12 |
| Point-cloud processing, inside input processing | **725.773 ms** | 7 |
| Sliding-map work, inside input processing | 245.565 ms | 21 |
| Seed construction | 304.131 ms | 4 |
| Optimization | 191.404 ms | 3 |
| Target selection | 0.576 ms | 1 |
| Final-goal search | 0.237 ms | 1 |
| Final curve check | 2.095 ms | 1 |

These nested scopes overlap and must not be summed. Input processing spends
941.490 ms of CPU time: most of this spike is real map/input computation, not
just a sleeping optimizer or final-goal-neighborhood search. The next profiling
target is the repeated input/cloud/map work across recovery, while retaining
fresh occupancy/support validation and all final gates. The data does not yet
prove which updates are safely redundant. See [maximum-round evidence](v76_maximum.json).

The upstream run reaches at most **three complete initialization attempts** per
observed chain. It still has 2,828 optimizer collision restarts across the
recording and exceeds 33.3 ms; these inner restarts are not 2,828 full planner
calls. Its failed/stationary trajectory does not visit the later location of
the v76 maximum. No ratio between the two maxima is a causal speedup result.

## Upstream and acceptance boundary

The executable upstream arm is the acquired
`yagami-light7/PCT-SCAN-ROS2@1cf45a1c12ca785ce533293302be09d51daf0ccb` core.
The planner manager, optimizer, A*, map and uniform B-spline are byte-exact
upstream. Six adapted transport/FSM/controller/message paths and their diff
are recorded in [v71 identity](../../versions/v71/upstream_identity.json).
This is not a reproduced original ROS1 SCAN demo. Native terrain/dynamics
acceptance and event/distance scheduling differ from local v63; common external
controller/backend rules are unchanged. The upstream arm has no added 30 Hz
periodic scheduler or whole-round 33.3 ms guarantee.

Current native v63 builds eight packages; upstream builds six. Source/install
gates and the current Mac component subset pass. The upstream retry passes all
six actual native transport/cancel checks. Its first startup-smoke failure
(`No actual native FSM admission`) is preserved; no source or admission threshold
is changed for the successful smoke retry. Full original corner/safety
qualification remains separate from this bounded Mac observation.

No production planner, goal, yaw, PVA/dynamics, safety or stop rule changes in
this comparison. v49 remains excluded. v48 stays the runnable reference.
**30 Hz, tail elimination and full-route acceptance remain unmet.**

## Videos, plots and durable data

The videos replay actual recorded states on the causal wall timeline with zero
render-time physics. Full decode, all original frame indices/times and direct
first/middle/final visual review pass. The upstream video is explicitly labeled
as a partial capture.

- Current: `output/2026-09-27_lite3_versions/v76_mac_trial01_attempt01_review.mp4`,
  982 frames / 32.733 s / 1280×720 / 30 FPS, 3,445,706 bytes,
  SHA-256 `25d638aa3f556f9a3297e0a2d35d26dfce0015c257a855665b1cd19d5f9c907a`.
- Upstream: `output/2026-09-27_lite3_versions/v77_mac_trial01_attempt02_review.mp4`,
  921 frames / 30.700 s / 1280×720 / 30 FPS, 941,069 bytes,
  SHA-256 `ca83ed2a4303d3dd40ac88a5898b35ca590203baccaeda60b6e1852b74b58382`.
- [Current time-series plot](../../versions/v76/mac_trials/attempt01/v76_mac_trial01_attempt01/analysis/time_series.png)
  and its compact frequency/latency CSVs retain the failed rounds and waits.
  The rolling frequency uses a wall-second window on a simulation-time axis.

All 288 closed physical/render files (225,114,094 bytes) are archived and
SHA/size-verified at
`gpu5070ti:/home/sun/vla_artifacts/2026-10-04_corner_start/`, in the four
run-specific directories. Physical data is transferred before rendering.
This is storage-only access; no remote GPU/simulator task starts. File lists,
hashes and verification receipts are returned in each version's `mac_trials/`.
Local source/config, compact reports/plots/receipts, three samples per video and
the MP4s are retained. [Local storage closeout](local_cleanup.json) records any
verified temporary removal and remote retrieval instructions.

Storage closeout removes 383,897,473 logical bytes from five owned temporary
build/cache/capture roots after current file/install identities and writer
closure verify. The empty failed-smoke run directory is retained. Both local
MP4s remain ordinary files, with exact path-specific ignores and SHA/storage/
regeneration provenance in the tracked version index. No unique failed-run
evidence is discarded.

The earlier v74 current test reached 19.65 m, 16.99 Hz and 720.812 ms maximum;
v75 attempts failed. Their frozen source and compact evidence survive, but
their temporary raw roots became unavailable following interruption. They are
not relabeled as archived/video-backed results. Fresh v76/v77 supersede that
missing media with remotely durable raw captures and verified videos.

## Reanalysis

Retrieve a remote run with `rsync -a gpu5070ti:<run-directory>/ <new-local-root>/`
and verify its `storage_manifest.json` before reading or regenerating media.
For v76, run `audits/2026-10-04_mac_newton/analyze.py --run-root <root> --output
<new-analysis-directory>` with the recorded plotting environment. For the
incomplete upstream capture, use `analyze_partial_upstream.py` with those same
arguments. Video display contracts record the source/member hashes and the
frozen v51/v61 renderer; use a new uniquely named display run. The saved physical
failure and frame/clock boundaries must remain visible.
