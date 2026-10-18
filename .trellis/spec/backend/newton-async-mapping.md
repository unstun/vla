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


## 9. Continuing-reference search and evidence age (v238 diagnostic)

The v237 recording shows a clear current curve before a final-goal-neighborhood
search consumes200ms. Planning, safety and sensor subscriptions share a mutually
exclusive work group while the clock continues. DDS-received clouds are not
necessarily enqueued, and enqueued clouds are not completed map snapshots.
The post-search ordered drain/adopt already takes the newest completed map;
it cannot grant freshness to a queued cloud or a half-built writer state.

Do not classify every binary target rejection as geometric occupancy. The
original0.35s scan-age bound can expire inside the search/fallback, making all
candidate points stale and triggering the unchanged safety emergency branch.
Do not freeze time, restamp evidence, extend the bound or suppress the stop.

A continuing admitted route may first propose a free forward reference
frontier and retain original seed/whole-spline/dynamic/publication gates. New
route admission and actual no-progress terminal recovery retain neighborhood
search. Test all three branches, stale evidence and unchanged goal identity.
Preserve overload ABI/class layout when loading an isolated native overlay into
an existing controller binary, and verify the actual linked replacement library.

Ordered-map/fixed-clock replay can establish a removed search call and its
cost, but cannot establish eliminated physical pauses. Record residual cold
solve latency and rejected inputs. v238 retains7 approach calls >100ms and is
only partially qualified; require continuous-clock callback/input replay before
claiming no avoidable emergency interruptions. See the v237 terminal-approach
audit and v238 offline gate. STAND_SETTLING is RL ownership; measured velocity
defines pause duration. Report >=0.5s episodes and cumulative split low time
without counting the motion gap as stopped time.

v239's adopt-and-cancel attempt eliminates emergency messages but expires an
active replacement curve for0.184561s. Check the currently owned curve only:
a shorter new curve retires the old remaining lifetime. Never union historical
lifetimes to claim coverage. Command coverage is also distinct from motion.

v240 polls the original ordered drain inside A* every20ms without adopting a
completed async map. The writer processes actual paired inputs while search
retains its immutable read snapshot. Original caller refresh and publication
lease then adopt/check completed maps. Held evidence still expires under its
original source stamp; queued data cannot renew it. Synchronous revision/
source/origin mutation rejects the search. Do not reenter executor spin from
a planner callback. Test held digest, real worker completion, stale rejection,
normal adoption and a background support/obstacle-change rejection through
the original full-curve/lease primitives. Name component versus full-manager
and fixed-clock versus live-window evidence accurately.

plan_env, path_searching and bspline_opt are static archives here. Rebuild
shared/plugin/test consumers: replacing an archive does not replace embedded
code. Check actual linked core, ABI symbols and source/install inventories.
v240 passes two live approach repeats and a stair control with zero emergency
and zero expiry gap. Body follows the old recording; physical pause elimination
and sustained30Hz remain separate unvalidated claims.

The separately authorized v241 physical execution of frozenv240 passes one
original route.109–115s contains zero emergency and >=0.5s pauses; actual
approach has zero cumulative low speed. The same fixed window now includes
0.271423s normal goal settling after114.668610s. Keep raw fixed-window counts
and add a named route-relative approach window; do not erase low samples
merely because they belong to terminal hold. Preserve original arrival/PD
gates independently.45–55s has zero pauses but only95% of body samples at the
0.15m capped extra-margin target (minimum0.129810m), versus100% forv237.
Do not describe capped scores as uncapped measured clearance, or promote a
single route into repeated reliability/sustained30Hz/baseline adoption.
