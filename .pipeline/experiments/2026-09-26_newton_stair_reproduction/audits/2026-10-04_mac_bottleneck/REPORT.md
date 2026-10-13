# Current Mac planning and heartbeat bottlenecks

Stage: experiment + analysis, 2026-10-04. Investigation requested by Dr Sun.
The source of truth is the local VLA repository. No gpu5070ti workload was used.

**There are two separate failures: slow synchronous planner recovery, and delayed
heartbeat consumption inside the backend path. Controller publication does not
stop during the historical heartbeat faults. A fresh observation run completes
the90s bound without that fault but still fails steady30Hz and tail acceptance.**
No production planner, goal/yaw/PVA/dynamics/stair/collision rule, watchdog
threshold or stop protocol was changed. v70 is observation only; v48 remains
the runnable reference and v49 remains excluded.

## What the heartbeat error actually means

The original backend updates `last_heartbeat_s` when `_on_raw_command` executes
with the active identity. The20ms watchdog checks this application callback
timestamp against the unchanged200ms threshold. It does not measure the latest
independent DDS subscriber receipt. All backend ROS callbacks share the default
mutually exclusive group and these Mac launches select SingleThreadedExecutor.
The inspected cached Humble executor dispatches ready timers before ready
subscriptions. A delay can therefore make a timer close the gate before a
pending raw-command callback is serviced. Later heartbeats do not reopen an
already closed gate: the original cancel/hold/quiescence fault flow latches the
stop and eventually releases the owner.

| Original captured fault | Mac route trial01 | Mac route trial02 |
|---|---:|---:|
| Last accepted heartbeat to fault-flow start |383.36ms |306.92ms |
| Matching-identity raw messages independently received inside that gap |11 |9 |
| Newest such raw receipt age at fault-flow start |14.55ms |7.15ms |
| Observed backend body-callback dispatch gap overlapping the event |196.19ms |262.30ms |
| Planner round overlapping fault-flow start |57.49ms, warm success |788.17ms, failed recovery |

The identity-bearing original `reactive_observations.jsonl` supplies the missing
evidence that the frequency-only observer could not supply. Run/epoch/request/
goal/route/command/generation/map identity matches the active owner. The backend's
last raw-callback timestamp is also frozen, so this is not explained by a
different generation merely failing heartbeat matching. Complete source hashes,
raw receipt windows and callback records are in [trial01](evidence/trial01.json)
and [trial02](evidence/trial02.json).

[The original-gate replay](gate_order_replay.json) passes10 assertions: leaving
those matching messages unconsumed produces `heartbeat_stale`; consuming the
newest matching message before the timer yields `ok`; consuming it after closure
cannot reopen the gate. This identifies the failure mechanism. **It does not
prove that the earlier delay occurred specifically in DDS ingress, rclpy
dispatch, OS scheduling, applied-file I/O or the Python GIL.** The separate
subscriber cannot prove when the backend's own DDS queue received each message.
An OS/DDS scheduler trace was not captured in the two original runs.

Sources: frozen [backend callbacks](../../versions/v59/backend_ros/p2b_backend_ros/node.py),
[original gate](../../runtime_sources/backend_adapter/backend_adapter/control_gate.py),
[runtime fault flow](../../versions/v59/backend_ros/p2b_backend_ros/runtime.py).

## Why the planner stalls at the43.7s corner

In original Mac trial02, the43.707607s planning round starts from retained PVA
near(6.991,-4.353,1.858), moving about0.823m/s horizontally. Its local target is
near(7.96,-4.01,1.87). The remaining-curve warm guess passes initial validation,
but the optimized/refitted candidate fails the final collision check near its
endpoint. The native graph and fixed-height candidates fail the same final gate.
The recovery chain then tries three shorter reference prefixes, retaining the
original start PVA and zero terminal velocity; they also fail. No failing curve
is published.

The full round makes11 planner attempts, including4 fixed-height attempts and3
shorter-prefix proposals. Later native searches hit the already-existing200ms
A* limit twice. That yields788.174ms before returning failure. In the inclusive
stage profile: seed437.721ms, input refresh317.170ms (cloud291.919ms), target
selection242.587ms, optimizer6.275ms. Goal-neighborhood search is only1.536ms.
These scopes overlap; they are not an additive breakdown. The native CPU times
are close to their wall times, so this round contains substantial real compute,
not just a paused planner process.

A failed candidate also calls `invalidateWarmStart()`. Consequently later
retries report `identity_or_owner` and perform cold initialization. That reason
is not proof that a new command owner appeared: it can be the consequence of
the previous failed candidate clearing the accepted binding. The captured
sequence starts with an accepted warm seed, then a final-check rejection and
`V48_WARM_RESULT accepted=0 graph_fallback=1` before those later messages.

## Why short warm solves do not produce steady30Hz

| Original Mac planning before fault | Trial01 | Trial02 |
|---|---:|---:|
| Successful completions per active wall second |21.25Hz |22.02Hz |
| Successful Hz over complete navigation window |16.81Hz |18.61Hz |
| Warm-accepted round mean |20.16ms |14.87ms |
| Cold/failed round mean |119.70ms |146.33ms |
| Cold/failed fraction of started rounds |7.44% |4.95% |
| Cold/failed share of total solve time |32.32% |33.87% |
| Missed nominal slots before fault |203 |342 |
| Mean gap between solve end and next plan start |19.46ms |24.04ms |

The30Hz clock retains absolute phase and skips missed slots; it does not issue
concurrent solves or catch-up bursts on the same mutable map. The10ms polling
timer is therefore not a hard25Hz cap. A788ms call can lose about24 scheduled
opportunities. More importantly, `execFSMCallback()` drains odometry and runs
`refreshSensorInputs("exec")` **before** starting the measured solve interval.
Cloud/sliding-map work, safety/input callbacks and scheduling therefore also
occupy time outside the displayed solve metric. Median solve latency alone
cannot establish a sustainable30Hz loop. [Comparison](comparison.json).

## Diagnostic state serialization is measurable overhead

`/state` returns up to50 complete PCT route records, including every waypoint,
on each request. Both the native graph and navigation driver poll it. The
original captured response grows from about4–5KB to1.516MB at44s; PCT history
accounts for about1.496MB. This affects runtime CPU/GIL use as well as disk output;
post-run ZIP compression does not remove the repeated runtime serialization.

The retained final snapshot is still available locally with its original result
hash. An isolated replay of the exact unchanged `json.dumps(data, sort_keys=True)
encoder in the same cached amd64 ROS image takes a mean30.26ms, maximum53.63ms
for the1.517MB trial02 final state. Removing only copied route history for a
diagnostic counterfactual reduces it to20.2KB, mean1.04ms, maximum1.29ms. The
Python heartbeat-work thread's largest gap is80.10ms with the full state versus
39.28ms without that history. Neither isolated condition exceeds200ms.

**Serialization is a demonstrated source of overhead, not a proven sole cause
of the original heartbeat fault.** The replay uses the retained final state
after the stop, not a relabeled pre-fault payload. [Replay/provenance](retained_state_replay.json),
[complete measurements](serialization_linux_amd64.json).

## Fresh v70 trace and its limits

v70 branches directly from physical v68 with exact native v63 and v59 runtime.
It wraps the original callbacks/reader/serializer without changing their return
values, exceptions, messages or effects; bounded diagnostic records are drained
by a background writer. The actual original-gate/JSON/error seam test,4 host
entry tests and actual manager/supervisor/retention chain pass. The rebuilt exact
native source finishes all8 packages and the actual source/install gate passes.
Full original remote-corner qualification remains separately pending.

The initial diagnostic launch loses its Docker connection before a build receipt
or physics run; its evidence is preserved. Docker is restarted. The temporary
old raw/cache roots are no longer available following the interrupted turn;
this task did not delete them. Saved compact analysis, retained original result
snapshots and delivered review MP4 remain available. Recompile the same CPU
model/raycast kernels with zero physics steps, preserving the failed initial
cache-helper import, then retry the same not-yet-frozen package and freeze it
before execution.

The successful observation run reaches89.962189 native seconds with90,000
integrations and navigation RTF0.934347. It travels57.081m with no pause above1s,
no emergency transition and no heartbeat fault. The goal is still active at the
recording bound; it is not an arrival or final-quiescence validation.

| Fresh v70 measured outcome | Value |
|---|---:|
| Successful local planning over complete navigation wall window |23.423Hz |
| Median / P95 complete round |5.756 /45.468ms |
| Maximum complete round |**1316.856ms** |
| Rounds >=100ms / >=1000ms |42 /1 |
| Largest matching raw-callback gap |102.149ms |
| Largest backend JSON serialization span |113.011ms |
| Largest applied-read / watchdog span |41.299 /40.627ms |
| Largest body callback / GC span |0.773 /40.033ms |
| Diagnostic trace dropped records |0 |

The longest applied-read spans cost only0.37–0.50ms of reader-thread CPU while
taking37–41ms wall time. They overlap other HTTP threads encoding1.26–1.47MB
states for33–41ms. Thus those apparent slow reads are consistent with waiting
for CPU/GIL during diagnostic serialization, rather than expensive file parsing.
This is direct runtime evidence of competition between diagnostics and control
callbacks, but does not explain an uncaptured historical200ms stall by itself.
[Read/serializer overlap](reader_serializer_overlap.json).

The1316.856ms round starts at78.488495s, rejects the warm target connector and
tries7 planning attempts,3 fixed-height attempts and3 shorter prefixes. Its
inclusive profile is optimizer696.833ms (CPU676.388), seed395.703ms
(CPU380.474), input refresh346.771ms including12 clouds325.943ms
(CPU317.728). Target selection0.513ms and final-goal search0.086ms are small.
It eventually publishes a fully checked shorter prefix. The controller and
backend remain alive through this long round. **A long planner solve does not
by itself force heartbeat failure.** [Detailed trace](v70_trace_summary.json),
[full-window metrics](../../versions/v70/analysis/metrics.json),
[updated time series](../../versions/v70/analysis/time_series.png).

This fresh observational run is not a matched-load speedup experiment. No
specific historical OS/DDS/GIL cause is promoted to confirmed merely because
the fault disappears after runtime restart or trace instrumentation. The
remaining uncertainty is exactly the source of the earlier backend dispatch/
delivery delay; no trace supports blaming stop protocol or identity rejection.

## Durable raw storage

After diagnosis, the closed fresh capture is archived at
`gpu5070ti:/home/sun/vla_artifacts/2026-10-04_mac_bottleneck/v70_mac_trial01_attempt02`.
The reviewed allowlist contains116 files/258,819,993 bytes, including the raw ZIP,
robot/factory states, small logs, configuration and provenance. Every remote
SHA-256 and size passes comparison, and local identities are rechecked before
removing the temporary capture. Only storage transfer/verification runs on the
server; no GPU or simulator job is started. Local source, compact reports,
hashes, plots and review videos remain. The63,299,127 logical bytes of owned
regenerable native build are also removed. [Storage/retrieval record](../../versions/v70/storage.json),
[remote verification](../../versions/v70/remote_archive_verification.json).

## Repairs supported by these findings

1. Make frequent state polling compact and store full PCT history once in
   append-only evidence. Preserve job/owner/terminal/measurement contracts and
   the complete route history for review. Measure callback latency under load.
2. Prevent heartbeat/odometry consumption from competing with large Python
   diagnostic work. Preserve active identity, original source timestamps,
   freshness thresholds, cancellation races and stop latching. Test the actual
   executor/receive path under delayed diagnostics before physical validation.
3. Optimize the cold recovery and cloud/map pipeline identified by the profiles:
   avoid repeating rejected initialization/optimization, preserve a still-valid
   parent binding transactionally, and account for input work before the solve
   timer. Any map snapshot/concurrency change must revalidate against the newest
   occupancy/support before publishing. Do not drop sensor evidence or weaken
   final collision/dynamics checks to improve timing.

These are recommended next repairs, not implemented behavior changes. Do not
increase the watchdog, add a v49-style hard abort, bypass the collision rejection,
or reopen a latched fault to obtain better figures. Main30Hz/tail/continuity
acceptance remains open.
