# Latest execution: MPPI adaptation 3, 2026-10-10

Stage: experiment + analysis. v127 starts from v122 / host v125, excluding parked
v126. Independent native validation passes 341 numeric/PVA/epoch +35 real-map
checks, bit-identical curve/proof/stale regressions, controller snapshot/clock/
pose/map-lock regressions, 14-package build and36plugin tests on gpu5070ti.
First physical pair: v122 arrives; v127 fails after observation age0.259857177 s
and subsequent no-progress recovery. No falls; copyback/retention pass. Park
v127 under the declared early stop; retain v122 / host v125. No second pair,
adaptations4–5 or robot actuation. One pair does not establish causality.
See audits/2026-10-10_mppi_step3/REPORT.md. Main in_progress / referencev48 remain.

# Latest execution: MPPI adaptation 2, 2026-10-10

Stage: experiment + analysis. On gpu5070ti, v126 passes the14-package build,
36 plugin tests,12actual-flow fixture cases and real recorded-map curve/stale
regressions. One same-host physical pair: native v122 arrives and holds; v126
ends FAILED after progress, stale-evidence and missing-trajectory aborts. No
fall; copyback and retention pass both. Max round136.189->442.960ms; >60ms7->15.
The declared early stop parks v126; retain native v122 / host v125. No second
pair, adaptations3–5 or robot actuation. v48 reference and main task in_progress
remain. See audits/2026-10-10_mppi_step2/REPORT.md and returned hashed evidence.

The sections below are historical records with their original host boundaries.

# Actual Mac outcome — 2026-10-04

Stage: experiment + analysis. Authorized Newton Mac tests ran actual Building geometry/factory-PD-RL/policy/sensors with exact native v63 (v62 sampled epoch + v63 optimizer failure propagation), original v59 runtime/safety/stop. Host packages v64-v68 are frozen; all source/snapshot identities verified, no GPU access.

Actual route trials: v67_mac_trial01_attempt01 ends31.614254s, successful16.81475wallHz, median11.3037ms/P95102.9532ms/max494.7161ms,13.19696m path. Prepared-cache same-frozen-v68 v68_mac_trial01_attempt02 ends46.506069s, successful18.60555wallHz, median9.5102ms/P9565.7734ms/max836.6828ms,22.74185m path. Both terminate FAILED: heartbeat_stale via original confirmed-hold/quiescence fault flow; state copyback passes. They do not complete90s, reach70s, prove full continuity or30Hz/tail acceptance. Native raw controller remains near30Hz, observer max gaps79.9/122.6ms, while backend last matching heartbeat is at least383.4/306.9ms old at fault start. Backend delivery/executor/filter behavior needs a separate trace; no watchdog is relaxed.

Other preserved failures: v64 receipt-key error; v65 outer manager pre-created-folder admission; v66 final external storage directory; all before physics. v67 retention initially refuses an open native writer, then passes separately verified archive after container removal. v68 attempt01 cold sensor-period check aborts at11.220904s; retry preloads already-compiled cache without source/deadline changes. Full original recorded-corner component qualification remains separately pending.

Report/plots/provenance: audits/2026-10-04_mac_newton/REPORT.md, trial01/, trial02/, acceptance.json, backend_timing_evidence.json, heartbeat_stop_windows.json, storage.json, verification.json. Mac/Linux clock origins are explicitly mapped from converged recorded samples. Raw archives stay at unique private/tmp roots outside repo, with hashes/paths; no unique raw failure data is discarded. All owned runtime containers are absent;63,322,441bytes of temporary native build removed. Rebuilding requires exact source/image plus qualification of fresh installed bytes in a host package; the old repeat wrapper's now-removed workspace locator is historical.

No commit or broad staging. v48 remains the reference. Parent main30Hz/continuity/late-anomaly repair stays in progress; Mac test request has measured failure evidence, not a successful validation. Next: trace raw controller -> matching backend heartbeat on Mac, preserving0.20s gate; finish original corner/GPU qualification when authorized resources are available.

## Requested video delivery

Display-only v69 now renders the latest physical v68_mac_trial01_attempt02 recording through the original managed supervisor/retention, frozen v51 causal stream and v61 close camera on a hidden Mac Cocoa context. Finished review MP4 is output/2026-09-27_lite3_versions/v68_mac_trial01_attempt02_review_v69.mp4,53.866667wallseconds,1280x720/30FPS,3,819,898bytes. Full decode,1,616 original indices/timestamps and direct stair/midpoint/final-stop visual review pass; original source hashes and zero physics steps verified. The failed relative-interpreter preview is preserved; absolute-path retry and full render pass under unchanged frozen v69. Source physics remains FAILED heartbeat_stale; main repair/90s/30Hz acceptance remains pending. See versions/v69/REVIEW_VIDEO.json and RESULTS.md.

## Root-cause investigation and observation-only v70

Dr Sun requested the current heartbeat/planner bottleneck. Verified original identity-bearing raw observations show11/9 matching messages during the old383/307ms backend heartbeat gaps; newest receipts are14.55/7.15ms old at fault-flow start. Original gate replay reproduces timer-before-pending-callback closure and its irreversible fault latch. This confirms backend consumption/delivery delay, not loss of controller publication or changed generation. Exact old DDS/OS/GIL trigger remains unproven; no scheduler-level old trace exists.

Original43.7076s corner round accepts warm seed then fails final collision validation:11 attempts,4 fixed-height retries,3 prefixes, two existing200ms A* search-limit failures ->788.174ms. Actual pre-fault successful local rates21.25/22.02Hz already fail30Hz. Cold rounds4.95% of the second trial consume33.87% of solve time; input/map work also runs before the measured solver timer. Full-state polling serializes up to1.5MB of repeated PCT history; retained-state isolated replay mean30.26ms versus1.04ms with copied history omitted, but no isolated200ms failure.

v70 is frozen diagnostic-only, parentv68/exactnativev63/v59runtime. The initial launch fails when Docker stops before a build receipt/physics. The old temporary raw/cache roots are now unavailable; retained source, final result snapshots, compact analysis and delivered video survive. This task did not delete those old roots. Recompile original CPU scene/raycast cache with0 physics steps; preserve its initial wrong-class import. Attempt02 rebuilds8 packages and passes actual source/install gates, then reaches89.962189s/90,000 integrations,57.081m,RTF.934347 with no heartbeat fault and no pause above1s. Goal remains active at recording bound; no arrival/quiescence acceptance. Frequency23.423Hz, max1316.856ms at78.4885s; tail remains optimizer/seed/cloud recovery. Trace complete,0 drops, matching raw-callback gap max102.149ms, serializer113.011ms, applied-read41.299ms. Long reads spend little CPU and overlap JSON encoding; diagnostics compete with callbacks. A long solver spike alone does not force heartbeat stopping.

Report: audits/2026-10-04_mac_bottleneck/REPORT.md. v70/analysis has full-window metrics and updated plot; v70_trace_summary.json and gate_order_replay.json supply the new evidence. Owned containers absent;63,299,127 regenerable build bytes removed;230,959,487-byte unique raw archive remains outside repo with v70/storage.json. No GPU activity, production fix or commit. Main task remains in progress. Next repairs: compact frequent state responses/append full PCT history once; protect heartbeat reception/dispatch under diagnostics; optimize cold recovery and pre-solve cloud work without v49 timeout, gate relaxation or unsafe trajectory reuse.

Storage closeout: the complete fresh116-file capture (258,819,993 bytes) is now
archived under gpu5070ti:/home/sun/vla_artifacts/2026-10-04_mac_bottleneck/v70_mac_trial01_attempt02.
All remote hashes/sizes and local pre-removal identities pass. Local temporary
capture removed after verification; compact source/results/plots/receipts remain.
No GPU/simulator job is started remotely. v70/storage.json and
remote_archive_verification.json supersede the temporary locator above.

## Requested upstream test and actual video

Dr Sun requested testing the upstream comparison and a video. v71 freezes the
pinned ROS2 planning core (1cf45a1), exact original manager/optimizer/A*/map/
uniform B-spline, existing controller/message/cancel transport and timing-only
FSM wrappers. All65 canonical files/notices match acquisition. Six packages
build and actual native route/cancel smoke passes. The frozen launch fails on
the copied floor publisher's old environment key before navigation; preserve it.
v72 changes only that key and reuses verified installation. Actual Newton ends
15.622684s/15,620 steps with64 unsuccessful planner calls,171 inner collision
restarts,0moving curves,0successfulHz,0.003m stance jitter,49.543ms maximum.
Original backend fails initial_heartbeat_missing and confirms hold/quiescence;
state copyback passes. No later-corner/90s/30Hz or upstream tail superiority claim.
An original ROS1 procedure is not reproduced by this ROS2 integration.

Display-only v73 creates the requested
output/2026-09-27_lite3_versions/v72_upstream_test_review_v73.mp4:4.5s,135frames,
1280x720/30FPS,78,972bytes. Full decode, all original causal frame indices/times,
source hashes and first/middle/final visual review pass;0render-time physics.
Two failed render launch commands are preserved. Allv70-v73 frozen identities
verify.270 closed capture/render files totaling39,410,045bytes are transferred
and SHA-verified under gpu5070ti:/home/sun/vla_artifacts/2026-10-04_upstream_runtime,
storage only, no remote GPU job. Keep compact metrics/plot/report/receipts/video
locally. See audits/2026-10-04_upstream_runtime/REPORT.md and v73/REVIEW_VIDEO.json.
Main task stays in progress; production continuity/30Hz repair and the matched
later-corner comparison remain pending. v48 remains current; no commit or broad
staging, existing unrelated index lock preserved.

Upstream storage closeout: remote SHA/size verification passes270 files/39,410,045bytes; all local pre-removal identities pass. Remove124,096,018bytes from four owned temporary roots (closed captures plus regenerable build/cache/input). Retain the tiny failed child-launch root lacking a process receipt, as well as its verified remote copy. v71-v73/storage.json and audits/2026-10-04_upstream_runtime/local_cleanup.json supply retrieval/rebuild boundaries.

## Requested corner-start comparison and both videos

Stage: experiment + analysis. Dr Sun requested initialization directly beside
the late corner. v74 introduces the explicit pose/profile with exact nativev63/
runtimev59; v75 selects exact upstreamv71 in the same physical condition. Those
attempts' frozen source/compact evidence survive, but temporary raw roots became
unavailable following interruption before durable video closeout. Preserve
that boundary; this task did not issue their deletion. v74 observed19.65m,
16.990Hz,max720.812ms; v75 attempts failed AppliedClient ACK/copyback.

Fresh v76 adds post-run raw archival before rendering; v77 selects upstream and
archives/renders incomplete physical failures without inventing result.json.
Actual corner scenario and factory handoffs are byte-exact between fresh arms.
v76 completes39.990s/40,000steps,20.035m,483/485successfulchains,14.700wallHz,
median8.263ms/P95166.731ms/max1307.535ms. Immediate corner maximum397.826ms;
the11-attempt corner failure takes41.318ms. The overall maximum occurs later
on stairs with4attempts and976.721ms inclusive input processing (7cloud updates,
725.773ms). No fall or pause above1s; one emergency/current-curve-invalid event;
goal active at the bound and copyback passes. No30Hz/full continuity acceptance.

v77 attempt01 preserves an actual native route-admission smoke failure. Unchanged
build retry passes all six native transport/cancel checks. Physical attempt02
records10/1226successfulchains,0.323wallHz,1.130m then stationary,maximum311.138ms
and at most3complete initializations. It fails the original receive/ACK path
and final-state/last-ACK hash verification; original final result absent. Last
saved gate open/no terminal: no heartbeat_stale or completed-stop claim.
The failed/stationary upstream trajectory does not establish a causal speedup
over local v63 or an original ROS1 reproduction.

Both actual review MP4s are delivered: v76_mac_trial01_attempt01_review.mp4
(32.733s/982frames) and v77_mac_trial01_attempt02_review.mp4
(30.700s/921frames, partial-capture label). Full decode, original state/time/
index checks and first/middle/final visual review pass. All288closed raw/render
files225,114,094bytes are SHA/size-verified on5070ti, storage only; no GPU job.
Reverified local identities/install/process closure precede383,897,473bytes
of owned temporary removal; retain empty failed-smoke directory and compact
receipts, plots, frozen source/config and ordinary review MP4s. Exact media
ignores have tracked SHA/storage/regeneration provenance in versions/README.md.

Report: audits/2026-10-04_corner_start/REPORT.md. completion_checks.json verifies
allv74-v77selected current/snapshot/parent identities, actual handoff and videos;
cleanup_preflight.json/local_cleanup.json record storage/rebuild boundaries.
Currentv48, frozen/excludedv49, safety/goal/yaw/PVA/stop stay unchanged. No commit,
broad staging or production fix; existing index lock retained. This requested
comparison/media delivery is complete; the main30Hz/continuity repair remains
in_progress. Next target is repeated input/cloud/map work across cold recovery,
retaining fresh occupancy/support checks and all final gates.


## 2026-10-05 map-processing diagnosis

2026-10-05 map diagnosis: original976.721ms is12synchronous refreshes/7distinct scans,941.490msCPU. Observation-only frozenv78 replays188scans with exact wire poses/config/support payloads;2-package build,3runs/arm and all116source/snapshot checks pass. Six final buffer/history digests identical. Hot work:926950voxel fusions,905074occupancy calls,25175190inflation offset visits,3actualslides/21checks,474416clearedcells. Representative fusion163.691ms,sliding57.719ms,projection49.746ms,traversal37.653ms,decode0.416ms. Idle batch266.600–312.992ms; original live977ms multiplier remains unlocalized (historical native batching/map/cache/planner context and live load not restored). No production fix/physics/GPU job/30Hz claim. Report audits/2026-10-05_map_processing/REPORT.md; main task stays in_progress and currentv48 unchanged.

Unique profile records and exact compiled runtime are retained under gpu5070ti:/home/sun/vla_artifacts/2026-10-05_map_processing/v78_profile_attempt02; original v76 inputs remain in the verified corner capture. Source/config, compact selected data/report/receipts stay local. Temporary selected input/build removal follows remote/current hash verification. Neither the original live977ms delay nor a production optimization is relabeled as reproduced/validated. Next: per-refresh/per-cloud live counters, actual shifts and cache clear size/time to separate the remaining multiplier. Preserve all newest occupancy/support, goal/yaw/PVA/dynamics and stop gates. No commit or broad staging.

## 2026-10-05 authorized repair and failed integrated acceptance

Stage: experiment + analysis. The four requested repairs are implemented in
order as v79 compact polling, v80 equivalent map arithmetic, v81 immutable async
snapshots and v82 strict fixed-point duplicate reduction under genuine backlog.
Eight native packages, 23 Python/HTTP/backend tests, the original safety suites,
26 snapshot checks and 20 backlog checks pass. Every recorded map state matches
the synchronous reference; 188 distinct moving scans are all preserved.
Encoder mean falls 42.428 to 0.307 ms; median seven-scan map work falls 320.599
to 213.193 ms. These are component measurements, not full-route acceptance.

Two actual 89.962 s Mac corner runs preserve heartbeat with the original
watchdog, but fail continuity and steady 30 Hz: 11.114/10.959 useful wall Hz,
491.143/312.939 ms maximum solve, 23.787/31.283 s longest pauses and 850
emergency transitions each. The mapper does not consistently complete within
the unchanged 250 ms source validity interval; repeated stale-map decisions
cause safety holds. No distinct frames are discarded despite queue depth six.
Neither run records arrival. Keep v82 frozen as failed and v48 runnable;
do not relax source ages, change stop semantics or introduce a v49 deadline.

The actual failed trial01 has a display-only v83 MP4 (90.233 s, 2,707 causal
frames), fully decoded and visually checked. Report and plots:
audits/2026-10-05_safe_mapping_repair/REPORT.md. All 343 evidence files /
590,903,005 bytes are remotely SHA-verified under
gpu5070ti:/home/sun/vla_artifacts/2026-10-05_safe_mapping_repair; storage only.
All 41,402 source/snapshot pairs pass after removal of 1,028,377,799 owned
temporary bytes. Keep compact reports/provenance/source/config and the review
MP4 locally. Main task stays in_progress; changes are uncommitted because of
the pre-existing index lock and other Git activity. Review map throughput and
snapshot handover before adoption. The prior reference and failed versions
remain unchanged.
