# Safe mapping and compact polling repair

Stage: experiment + analysis. Authorized by Dr Sun on 2026-10-05, in this order:
compact state polling, equivalent map operation optimization, asynchronous
versioned mapping, then conditional LiDAR backlog reduction. Implement/check
inline. Local VLA source is authoritative; frozen predecessors stay immutable.

## Boundary and versions

The behavior gap is synchronous, repeated map work on the planner thread and
repeated serialization of up to 50 full PCT routes on the HTTP thread. Existing
backend identity, watchdog, cancellation, measured hold and stop latching remain
unchanged. Goal/yaw/PVA/dynamics/stair/support/occupancy decision rules remain.
No v49 deadline, new timeout stop reason, freshness extension or artificial
heartbeat is introduced. These changes are experimental until tested.

1. v79: copy the frozen v59 backend package; make normal `/state` polls compact
   at the PCT history producer. Retain full records once in an append-only run
   artifact and provide explicit full-history access for compatibility. Bind
   the new backend to a new entry point; keep the original heartbeat callbacks.
2. v80: copy exact v63 native source, retaining v79 backend. Optimize occupancy,
   inflation address arithmetic and sliding semantic-history maintenance. Keep
   every inflation offset, occupied threshold, transition count and clear mask.
   Prove byte-exact map/history equivalence on recorded inputs and boundary cases.
3. v81: give the mapper sole ownership of mutable state. Publish complete,
   immutable versioned snapshots; planner queries pin a snapshot and adopt newer
   completed revisions at original fresh-input boundaries. Revalidate the full
   candidate against the newest completed map before publication. Support and
   sensor/body identities and original timestamps travel with the snapshot.
   Exceptions publish no partial state. Join the owned worker on shutdown.
4. v82: reduce full ray processing only when multiple complete, correctly paired
   LiDAR frames genuinely accumulate and are spatially identical to a previously
   applied fixed-point scan. Require identical data/layout/frame, sensor/body
   geometry, map origin and support revision, plus unchanged occupancy after the
   last full fusion. Advance only the skipped ray generations, then process the
   newest frame fully. Preserve exact final buffers and semantic history. Keep
   distinct scans, incomplete pairs and unsaturated occupancy updates. Count all
   reductions; this deliberately does not implement general distinct-frame loss.

Native ownership is limited to `plan_env` mapping state/operations/ingress and
the manager/FSM publication boundary if required for snapshot consistency.
Backend ownership is limited to the PCT history producer, HTTP snapshot/endpoint,
run-artifact wiring and their tests. New build/probe/launch tooling belongs to
the four new versions; other source is inherited by verified hash.

## Acceptance and execution

- Compact and explicit full polls retain identical owner/gate/measurement/jobs/
  terminal/navigation fields; full route records, including failed requests,
  survive once in the evidence stream. Serialization benchmark uses identical
  retained input; exercise original heartbeat and stop handlers under polling.
- Build the affected native packages and planner. Compare original/optimized
  recorded map hashes at every scan, including rolling origin, inflation counts,
  ray buffers and semantic sets; test positive/negative/multiaxis/full shifts.
- Async tests exercise snapshot immutability, monotonic revisions, concurrent
  reads, newest-map obstacle rejection, stale/future clocks, delayed writer,
  support replacement, worker failure and clean shutdown. Re-run available
  original goal/yaw/PVA/freshness/warm/cache/controller/backend safety suites.
- Backlog tests cover no backlog, paired accumulation, mismatched/missing poses,
  changed/occluded obstacles, unsaturated maps, support changes and ray-generation
  wrap. Require exact buffers/history against processing every frame. Report the
  limited eligible conditions and actual reduction counts.
- Run bounded Mac native/ROS validation first. Actual Newton corner validation
  uses the existing frozen v76 scene/route/physics/controller; timing is Mac-only.
  Report all failures and do not claim steady 30 Hz from a component benchmark.
- Use a uniquely owned `/private/tmp/vla_safe_mapping_*` build/input/run root.
  Archive bulk on `gpu5070ti:/home/sun/vla_artifacts/2026-10-05_safe_mapping_repair`
  using storage-only access; return compact reports/hash receipts/test summaries
  and a review MP4 if produced. Never start a competing GPU job. Delete temporary
  bytes only after durable byte verification. No repository-wide file ignores.

Freeze each logical change after build/component checks, before runtime trials.
Subsequent repair of a frozen failure requires another integer version. The
runnable reference remains v48; none of these versions inherits v49 mechanics.
