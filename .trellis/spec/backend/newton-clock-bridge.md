# Newton Mac/Linux clock and applied-state bridge

## 1. Scope

Only the local2026-09-26 Newton stair experiment. macOS physics and Docker Linux
ROS have different monotonic origins and a shared-filesystem consistency seam.
These contracts qualify bounded integration, not completed stair navigation.

## 2. Signatures

- `ClockClient(host, port, log_path).estimate() -> ClockEstimate`, or
  `ClockUnavailable`. Clock channel port46202,50Hz request/reply with echoed
  sequence/timestamp and one pinned responder UUID.
- `DomainCommandState.current(now_ns) -> (snapshot, remote_source, wire_command)`.
- `AppliedClient.publish(original_snapshot) -> ack` through PyZMQ REQ/REP on
  host-loopback46203; timeout100ms, linger0. A failed acknowledgment ends the run.
- `run_local_episode.py --backend-executor single --applied-transport zmq` via
  `run_bounded.py`, with a new immutable run ID and `NEWTON_RUN_DIR`.

## 3. Contracts

MAVROS filter parameters remain500 convergence samples,10ms RTT/deviation
rejection and original alpha/beta schedule. Local adapter requires an accepted
sync sample at most200ms old. Uncertainty is half RTT plus filter residual plus
10ms. Map source timestamps to their earliest plausible receiver-domain value;
never substitute receipt time. Original250ms command watchdog,25ms future
tolerance and2s snapshot age remain. Restarted responder identity fails closed.

Applied JSON retains original run/epoch, state and command sequences, actual
applied command, measured body motion and source times. Linux validates the
original schema, identity, increasing state sequence and age, atomically writes
the exact message bytes into its tmpfs, and reads with the original
`AppliedEvidenceReader`. ACK contains SHA-256, sequence, original-reader
sequence and receive age; finish requests keep the original driver schema.
Only this transient state directory uses tmpfs. Linux-to-host return must use
`docker exec tar` before cleanup and match the last positive ACK hash.

The single-threaded backend entrypoint retains original callbacks. Diagnostic
callback/error traces observe scheduling without modifying return values or
swallowing exceptions. Startup missing-state observations are distinct from
errors after the first accepted snapshot.

## 4. Validation and errors

| Condition | Required result |
| --- | --- |
| Unconverged, rejected or stale sync / changed responder | Reject admission; zero actual command |
| Old/future source command | Preserve original rejection and watchdog behavior |
| Stale/future/foreign/duplicate applied snapshot | Negative ACK; do not replace current Linux state |
| Mismatched ACK hash or sequence / message timeout | Raise; preserve all artifacts |
| Applied JSON parsing failure | Original reader raises; never retry it into a fresh state |
| Copyback differs from last ACK | Fail copyback qualification, even if decoded JSON values match |
| Driver says FINISHED but backend says failed | Report recording completed and navigation failed separately |

## 5. Good, base and bad cases

Good:1,398 byte-matched positive ACKs, no reader errors after startup and a
verified measured stop in `stair_native_walk_v2`. Base: zero-motion3s probe
qualifies only bridge readiness. Bad: Mac atomic replacement produces truncated
Linux JSON; overlapping/disjoint mount probes both preserve counterexamples.
Clock-related zeroing and reconnects remain visible in the full run.

## 6. Required evidence

- Extracted original MAVROS C++ comparison:1,124 samples, matching state changes
  and at most0.109375ns observed numerical difference in `clock_reference_v1`.
- Actual cross-OS convergence, loss, stale/future and250ms watchdog controls.
- Independent stale/future/foreign/duplicate channel tests: advance sequence
  for nonduplicate tests so duplicate rejection cannot confound them.
- Full-rate policy/applied trace, ACK hashes/age, source/config hashes, paired
  cloud stamps, original native curve messages and terminal cause.
- `review_local_episode.py` audits the saved run; `stair_video_review.json`
  separately proves frame/source integrity, decode and visual inspection.

## 7. Common mistakes and upstream references

Do not use a guessed boot offset or stamp state on receipt. Use the pinned
MAVROS filter plus explicit uncertainty/freshness checks. Do not use `docker cp`
for mounted tmpfs: it can copy the underlying directory. Docker's documented
`exec tar` reads the mounted contents. Do not call a stopped recording successful
navigation. Exact upstream pins/licenses and rclpy/Docker issue comparisons are
in `.pipeline/survey/2026-09-26_newton_lidar_bridge_upstream_survey.md`.

## Backend heartbeat timing diagnosis (v70, 2026-10-04)

1. **Scope:** Mac identity-bearing raw-command consumption and Python backend
   scheduling, independently of native planner solve time. v70 is a frozen
   observation package, not a production repair or new watchdog rule.

2. **Signatures:** `backend_timing_trace.install(RosScanPort,
   AppliedEvidenceReader)` delegates original methods once; `Trace.start(path)`
   periodically drains a bounded byte buffer and `Trace.save()` closes it.
   Output events carry `DEBUG-mac70`, stage, entry/finish ns, per-thread CPU ns,
   thread name and relevant identity/heartbeat/gate metadata.
3. **Contracts:** heartbeat freshness remains200ms and updates only when the
   matching original raw callback executes. All message, return, exception,
   cancellation and closed-gate behavior stays unchanged. Distinguish an
   independent DDS receipt from backend callback execution. A later heartbeat
   cannot reopen the original latched fault. Keep full PCT history evidence;
   its repeated serialization in frequent state replies is measured CPU/GIL
   work, even when closed logs are subsequently zipped.
4. **Errors:** changed identity does not qualify as a heartbeat; dropped trace
   records or incomplete closure invalidate a full trace claim. A delayed
   callback with valid independently received commands does not establish the
   exact DDS/OS/GIL cause. Missing original raw data must be reported; retained
   final snapshots can replay serializer cost but are not pre-fault captures.
5. **Cases:** original faults have11/9 matching independent receipts during
   accepted-heartbeat gaps. Original-gate replay fails when the timer runs before
   consumption and passes with pending matching consumption first. Fresh v70
   reaches90,000 integrations with no heartbeat fault despite a1316.856ms native
   solve; long solve time alone does not force heartbeat failure.
6. **Checks:** actual original raw gate/identity-error/reader-error/JSON-output
   seam test; immutable source/build gate; full identity-bearing timestamp
   timeline; wall versus thread-CPU spans and nested-scope overlap; trace
   completion/drop count; full-window achieved Hz. Large read wall times with
   small reader CPU can overlap another thread's JSON encoder; do not label
   these as expensive disk parsing without further evidence.
7. **Wrong vs correct:** do not raise the watchdog, synthesize fresh source
   stamps, reopen a fault, or infer backend delivery from a30Hz observer. Keep
   original thresholds and inspect the actual receive/dispatch path. Separate
   confirmed gate mechanism, measured competing work and uncaptured historical
   scheduler cause. Evidence is in audits/2026-10-04_mac_bottleneck/REPORT.md.

## Upstream comparison admission (v71-v73)

An upstream planner without P2B envelopes requires an explicit recorded
identity/admission/cancel adapter before it can share the original backend.
Preserve the current controller and measured-stop protocol; test the actual
native route, both cancellation consumers, emergency-curve identity and late
cancelled-generation rejection. An accepted route does not establish a moving
curve or a first controller heartbeat. v72 admits the historical PCT route,
but64 original planner calls all fail, so the backend correctly returns
`initial_heartbeat_missing`; this differs from delayed consumption of previously
valid heartbeats. Keep the original timing thresholds. An early zero-motion
upstream failure cannot demonstrate superior latency at a later corner.

Copied host publishers can retain an earlier version's environment key even
when launch helpers are renamed. v71's build/cancel tests pass but its physical
graph fails on V70_PHYSICAL_FLOOR; preserve it and fix only that binding in a new
version. v72 reuses the same installed planner bytes. Source-only and small
transport smoke checks cannot replace the physical launch seam.
