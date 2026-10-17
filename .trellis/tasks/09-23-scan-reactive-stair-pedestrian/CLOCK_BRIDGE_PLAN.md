# Clock-domain seam and local closed-loop continuation

2026-09-26, experiment + analysis; implementation/checks inline.
Dr Sun authorized continuation after the upstream-first survey.

Gap: native Mac simulation and Linux ROS use different monotonic origins.
The archived command watchdog and applied-evidence reader assume equal origins.
Keep those original modules, the sensor/body wire format, physics policy and
all planner/watchdog parameters unchanged.

Implement only in the local Newton stair experiment:

- `clock_sync.py`: a narrow Python port of MAVROS `sys_time.cpp` at
  `a5979a5299775d9dd9ce1d57f9cfa1542c5259b9`, selected BSD license. Preserve
  initial/final alpha/beta,500-sample convergence,10ms RTT/deviation rejection
  and reset behavior. A separate local clock channel exchanges the same three
  timestamp roles; it is not a new sensor protocol or a MAVLink binary port.
  Echo request identity and pin one responder instance per run. Reject missing,
  unconverged, old or abnormal sync evidence before accepting motion.
- `probe_clock.py` and a generated C++ reference: compare the Python filter
  with functions extracted verbatim from the pinned C++ source, then exercise
  actual Mac/Linux transport, stale/future command rejection, delayed sync,
  loss and watchdog zeroing. Do not assume a constant boot offset.
- `native_graph.py` / bounded launcher: start the original PCT, SCAN,
  controller, tracker, ROS bridge and backend from their unchanged local
  snapshots. Only paths, run IDs and network endpoints may change.
- `newton_episode.py`: publish actual same-step pose/twist and geometric
  returns using the original binary bridge, apply only admitted commands to
  the qualified locomotion policy, and write actual state/command evidence.
  Original actor truth stays in the separate scoring stream.

Clock adaptations beyond the MAVROS filter are explicit: require a fresh
accepted sample within200ms; use an uncertainty allowance comprising half the
measured RTT, filter residual and the upstream10ms deviation limit. Map source
times to the earliest plausible receiver-domain time, so uncertainty increases
age rather than making a command/snapshot look newer. A clock failure stops
admission instead of falling back to receipt-only freshness. These bounds are
simulation-adapter checks, not certified synchronization guarantees.

Checks precede motion. Then run a bounded original-scene episode, at most35s
physics and600s wall per attempt, with measured stop and actual video. Frozen
35s backend command timeout may expire earlier on a slow CPU; report that
outcome rather than stretching it. Preserve every attempt and its source bytes.
Newton success would not silently close the separate original Isaac A4 gate.

## Measured platform refinements

- The original HTTP configuration requires loopback. Run the original archived
  `pilot_driver.py` unchanged inside Linux; preserve its5s-plus-stability gate,
  observation deadline and measured stop. No HTTP forwarding workaround.
- Independent observation received150 body poses, while the multi-threaded
  backend handled2. The explicit single-threaded comparison handled149 and
  passed freshness. Adopt the standard `SingleThreadedExecutor` at the entrypoint,
  following ros2/rclpy issues1223/1452. Original backend core/callbacks unchanged.
- `stair_native_walk_v1` produced a native moving spline, then the original
  evidence gate stopped on invalid JSON. The isolated atomic-replacement probe
  captures truncated JSON with both overlapping and disjoint Mac bind mounts,
  consistent with the failure class in docker/for-mac7494 (not proof of the same
  Docker-version bug). Do not retry/ignore parsing errors in the safety gate.
- Use pinned PyZMQ26.4.0 (`b273c0915abd45003dc6378a3c6e8750d39a34c0`)
  standard REQ/REP complete-message transport for the existing JSON snapshot.
  Validate with the original schema/run/sequence/age checks, atomically store
  the exact bytes inside Linux tmpfs, and acknowledge sequence+SHA-256. Keep
  the original reader and driver paths by mounting only their transient state
  directory on tmpfs. Copy it back before container cleanup; host sent payloads
  and per-message acknowledgments remain archived. Return the original finish
  request through that same acknowledged channel. No receipt-time restamping.

## Completed bounded continuation

`clock_reference_v1`, `clock_live_v1`, the single-executor probe and
`native_bridge_zmq_probe_v2` provide component evidence. The full
`stair_native_walk_v2` run records28.056physics seconds, two moving curves,
797nonzero command updates and approximately0.375m forward displacement.
It fails navigation on the unchanged35wall-second command timeout, then
completes a measured stop. No reader error follows the first snapshot.
Use `docker exec tar` for tmpfs return: earlier `docker cp` probe receipts
returned underlying host bytes and are not copyback proof. The full run's final
SHA matches its last positive ACK. Clock-related zeroing/reconnects persist.

Video and results are in the experiment's `RESULTS.md` and validation files.
The next gate is source-backed diagnosis of seed retiming (1.6s→34.250s in the
second curve), followed by separate consideration of simulation progress and
transport clocks. No timeout/bound change has been adopted. A4 remains open.
