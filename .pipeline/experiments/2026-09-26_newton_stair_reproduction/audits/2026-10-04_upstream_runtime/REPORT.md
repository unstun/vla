# Actual upstream SCAN test on Mac Newton

Stage: experiment + analysis, 2026-10-04. Dr Sun requested an upstream test and
video. **The upstream ROS2 planning core fails before its first moving curve.
This run does not reach the later corner and cannot establish whether upstream
would have the1.3s latency spike there.** No production planner repair, watchdog
change or v49 timeout is introduced. v48 remains the runnable reference.

## Tested implementation and comparison boundary

The executable base is yagami-light7/PCT-SCAN-ROS2 commit
`1cf45a1c12ca785ce533293302be09d51daf0ccb`. All65 selected canonical files/notices
match the existing acquisition manifest. The manager/header, optimizer, A*,
grid map and uniform B-spline implementation are byte exact to that base.
The FSM retains original target selection, new/reference-path initialization,
distance/event scheduling and retry rules. Wrappers only measure the original
synchronous chains. Existing P2B identity/admission/cancel transport is added;
the current controller and message envelopes are retained so the original
backend goal, freshness, cancellation and measured-stop contracts still work.
[Exact pins and adaptations](../../versions/v71/upstream_identity.json),
[transport diff](../../versions/v71/upstream_adaptations.patch).

The robot, full archived Building, policy/factory startup, sensors, historical
route, planner configuration, controller, backend, clock bridge and6-CPU/6GiB
cached amd64 Humble image match the v70 Mac condition. Upstream's own planning
and terrain predicates remain different: local whole-curve PVA/support checks,
warm binding, shorter prefixes, fixed-height fallback and30Hz scheduler are
absent. This is an integration of the ROS2 port, not reproduction of the
author's original ROS1 demo procedure. Independently evolving physical runs
and an early upstream failure do not form a causal speedup experiment.

## What actually happened

v71 builds all six packages in2min32s and passes an actual native transport
smoke: route admission, FSM/controller cancellation holds, identity-bearing
emergency curve, cancelled-generation rejection, and no false claim of measured
physical stillness. Four negative entry/storage tests and the actual
manager/supervisor/retention chain pass. Its first Newton launch fails after
factory startup because the inherited floor publisher expects the old V70
environment key. v71 and its failure are frozen and retained.

v72 corrects only that host key and reuses the exact native installation. Native
transport and installed-source gates pass again. Actual factory startup reaches
11.020823s. The historical PCT route is admitted with631 input poses reduced to
134 trajectory waypoints. Every original local planning attempt fails. The
initial target is approximately(-5.22,2.40,0.952), from body(-5.57,6.11,0.399).
The log contains repeated optimizer collision restarts and A* errors; no normal
moving B-spline is published. No particular floor cell is promoted to the
confirmed spatial cause without a native occupancy witness.

Because there is no admitted moving trajectory/identity-bearing controller
heartbeat for the active route, the unchanged backend records
`initial_heartbeat_missing`, executes confirmed hold and measured quiescence,
and returns FAILED. This is distinct from the earlier `heartbeat_stale`
delivery stalls. Physics ends at15.622684s, after15,620 actual integration steps;
the requested90s bound is not completed. State copyback matches its last ACK.
Process/retention completion is not navigation success.

| Measured outcome | Upstream v72 | Current v70, historical Mac observation |
|---|---:|---:|
| Actual physics end |15.623s, failed |89.962s, bounded recording |
| Complete planning rounds |64 |1,991 |
| Successful plans |0 |1,979 |
| Successful plans per navigation wall second |0Hz |23.423Hz |
| Median / P95 complete round |10.622 /33.292ms |5.756 /45.468ms |
| Maximum complete round |49.543ms |1,316.856ms |
| Measured path |0.003m, stance jitter |57.081m |
| Later corner evaluated |No |Yes |

All64 upstream rounds are original GEN_NEW_TRAJ calls with one complete manager
attempt each; without a successful prior trajectory, its three-mode reference
replan branch is never exercised. There are171 optimizer collision restarts,
showing inherited inner repetition even in these short failed rounds. No200ms
A* limit is hit and no100ms or1s round is observed in this short window.
This does not prove such spikes are absent on a completed upstream route.
The earlier source comparison still establishes that our11-complete-attempt
expanded recovery path adds layers beyond upstream's ordinary reference chain.
[Verified metrics](../../versions/v72/analysis/metrics.json),
[comparison](comparison.json), [time series](../../versions/v72/analysis/time_series.png).

## Review video and evidence

Display-only v73 reuses the frozen v51 causal renderer and v61 close camera.
It streams the actual recorded v72 states to a4.5s/135-frame MP4 at1280x720,
30FPS. The recording shows a stationary robot and final failed status; no
physics, sensing or planning is rerun to render it. Full decode, frame count,
causal original state indices/times/hashes, and first/middle/final visual review
pass. The original untimed factory prefix is preserved in raw evidence and
omitted from the timed display. Native source ends15.622684s; last displayed
sample is15.582667s under the original causal wall-time grid.

Video: `output/2026-09-27_lite3_versions/v72_upstream_test_review_v73.mp4`.
SHA-256: `5ab4d6dbf51af5d09aa801a58c1e842d9a83a8ee074da6fdd45c28906fa3de48`.
Two failed render launches (relative script path, then omitted interpreter)
remain recorded; the unchanged frozen renderer succeeds with absolute paths.
[Video receipt](../../versions/v73/REVIEW_VIDEO.json).

Raw test/render evidence is transferred to
`gpu5070ti:/home/sun/vla_artifacts/2026-10-04_upstream_runtime/` by storage-only
SSH/rsync. [Transfer manifest](raw_archive_transfer.json) and
[remote verification](remote_archive_verification.json) bind each retained byte.
No GPU job starts. Local files retain source/configuration, compact metrics,
plots, receipts, three representative samples and the requested MP4.

The additional matched corner replay remains pending because this baseline
never acquires the prior valid trajectory needed to exercise that state. A
lower early maximum must not be called tail-latency reduction. The main30Hz
repair and original corner qualification remain in progress.

Storage closeout: all270 remote file hashes/sizes pass (39,410,045bytes). Local pre-removal source/capture/install checks pass; four owned temporary roots totaling124,096,018bytes are removed. The tiny failed render launch without a process receipt remains locally as well as remotely. [Cleanup](local_cleanup.json). Rebuilding requires qualifying fresh installed bytes against the frozen source/image; old installation byte identity is not promised for a fresh build. Existing unrelated Git index lock is retained; no commit or broad staging.
