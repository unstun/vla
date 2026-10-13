# Compact polling and asynchronous Newton mapping

## 1. Scope and trigger

Applies to the v79–v82 repair in the Newton experiment. The runnable reference
remains v48 until full acceptance; v49 stays frozen and excluded. Compact polling
and mapping concurrency do not authorize changed watchdog, stop, goal/yaw/PVA,
dynamic, occupancy, support, stair or inflation parameters.

## 2. Signatures

- v79 `NavigationHttpRuntime.state(include_history=False)` and
  `LayeredPctClient.snapshot(include_history=False)` produce compact route
  summaries. `GET /state?include_history=1` explicitly returns retained full
  history. Normal control callers use `GET /state`.
- `diagnostics.pct_history_path` names a new run-owned JSONL artifact. The v82
  backend entry sets it to `pct_plan_history.jsonl` beside `backend_config.json`.
- `GridMap::startAsyncMapping()`, `stopAsyncMapping()`, `mapRevision()` and
  `beginPublication()` manage the writer, immutable revisions and publication
  lease. Runtime YAML uses `grid_map.asynchronous_mapping: true`.
- v82 enables `grid_map.drop_backlogged_lidar: true`; this is a guarded duplicate
  reduction policy, not general newest-frame loss.

## 3. Contracts

Normal state polls keep owner/gate/measurement/jobs/terminal/navigation fields.
`pct.plan_history` contains summaries without request bodies or waypoint arrays,
with `history_seq`, `waypoint_count`, status/identity/timing and `plan_count`.
Full records, including failures, are appended once by PCT workers. A write
failure is explicit in `history_evidence.error` and does not change route results.
Never append a new run into an existing history artifact.

The mapper owns mutable map buffers and semantic sets. Completed snapshots hold
immutable state; support tables are shared read-only and copied on mutation.
Planner adoption clears borrowed terrain/raw caches before releasing the old
state. Large old states retire on the writer. Sensor/body source timestamps and
support identities remain original; snapshot publication never refreshes them.
Live body pose remains on the planner thread for the original 0.1 s body waiver.

Final complete-curve validation adopts the newest completed snapshot under a
publication lease. The manager retains that lease through actual FSM Bspline
publication, then releases it. No half-updated map reaches queries. Writer failure
keeps the last completed bytes but cannot grant collision/endpoint safety. The
existing failure/stop protocol handles rejection; no new timeout reason exists.

Backlog reduction requires 2–254 complete queued clouds with strictly increasing
stamps, identical layout/data/frame and sensor/body geometry, unchanged origin
and support pointer, and a previously applied full fusion with no net occupancy
changes. Advance skipped ray generations and process the newest frame fully.
Distinct data, unpaired/malformed poses, changed support and unsaturated maps
retain full processing. Exact final buffers, semantic sets and timestamps must
match processing every frame. Do not infer that arbitrary older scans are safe
to discard from this duplicate-only policy.

## 4. Validation and error matrix

| Input/state | Required behavior |
|---|---|
| Default state poll | Compact summaries; control fields unchanged |
| Explicit full poll | Full retained records; lossless run evidence still available |
| History path already exists | Refuse to overwrite/reuse |
| New scan without exact pose | Retain until paired; do not transform with another pose |
| Mapper delayed, stale or future source timestamp | Original freshness checks reject |
| Support replaced | New coherent revision; old cache pointers cannot survive adoption |
| Map computed during final publication | Wait until validation/publish lease ends |
| Worker exception | No partial publication; collision/endpoint grants blocked |
| One queued scan or distinct observations | Full processing |
| Identical observations before occupancy saturation | Full processing |
| Fixed-point duplicate backlog | Guarded reduction; exact terminal state equality |
| Full ray-generation cycle in backlog | Full processing |

## 5. Good, base and bad cases

Good: compact polls with full evidence recorded once, coherent map revisions and
fresh full-curve checks. Base: one incoming frame or moving robot uses every
observation. Bad: a background writer edits the planner's buffers, a large mutex
holds through mapping, source ages are restamped, or distinct scans are dropped
to improve frequency.

## 6. Required tests and evidence

v79 tests real HTTP default/full routing, lossless records/failures, races and
unchanged control/stop ASTs. The offline ROS load probe must establish body
readiness before admission, as production does: admitting raw commands first
correctly latches `odom_stale`. Validate 30 Hz compact polling, actual matching
callbacks, original missing-heartbeat rejection and latched faults.

v80 compares every recorded-scan buffer/history digest and positive/negative/
multiaxis/full-grid slides against the original archive. v81/v82 test immutable
retained views, exact pairing, newest-map full-curve rejection, stale/future
clocks, support replacement, worker failure and joined shutdown. Rebuild original
native/cache/endpoint/controller and recorded warm/PVA/goal suites against the
actual layout; supply both original planner and controller YAMLs.

v82 tests single/duplicate/unsaturated/changed-pose/changed-body/changed-obstacle/
support-change/unpaired/ray-wrap/full-generation cases against full processing.
Recorded moving scans must remain identical and report actual reduction counts.
Bind physical trials to exact source/install/configuration, keep bulk remotely,
and distinguish enqueue, map, round-solve and successful-plan frequency metrics.
Component equality or callback cadence is not physical steady 30 Hz acceptance.

## 8. Admission replay and separated-lane evidence (2026-10-08)

v84 compares FIFO, timer/latest-slot and latest-slot admission using exact
recorded clouds, paired poses, support and the same v82 native mapper. It is a
scheduling adaptation, not a ROG-Map algorithm reproduction. Controlled worker
blackouts must be labelled; native-service-driven event time is not historical
DDS/physics scheduling. Compare full map state and obstacle retention before
claiming equivalent behavior. In the durable attempt, latest skips 12 frames and
loses 173 occupied cells; timer skips 16 and loses 252. The native transient
negative confirms that a skipped observation can be the only obstacle evidence.

Report both source age at completion and the age of the previous map held until
the next completion. Fresh output after a stall cannot erase the stale interval
during it. No distinct-frame dropping is enabled in navigation from these tests.

v85 is a three-thread component prototype only. The sensor path can veto but
cannot grant map freshness/support, clear a pending unprocessed hazard with a
later timestamp, or revive a cancelled owner. Clearing a hazard requires an
actually contiguous applied-observation bound plus original clear-map evidence.
The 250 ms rule remains. The current measured-body footprint veto and numeric
epoch surrogate are not the production full trajectory/identity/stop protocol.
Bind those original interfaces and qualify moving/braking/stair geometry before
runtime adoption. A nominal 30 Hz decision poll is not planner/controller 30 Hz.

Tests: v84 native recorded admission and transient probe; v85 26 source/identity/
veto checks and the actual three-thread 188-frame replay. During each injected
650 ms map stall, six sensor callbacks and nineteen execution decisions survive,
with zero checked stale-map allowances. Final map digest matches original FIFO.

## 7. Wrong versus correct

Wrong: claim that removing 1.5 MB history responses proves every heartbeat fault
fixed, or that asynchronous enqueue timing is the complete planner solve latency.
Correct: report the encoder and actual callback tests separately, then validate
the unchanged physical route and measure completed successful planning rounds.
