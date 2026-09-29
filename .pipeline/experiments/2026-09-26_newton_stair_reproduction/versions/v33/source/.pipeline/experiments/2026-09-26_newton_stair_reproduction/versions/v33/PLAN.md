# v33: judge body-pose freshness by simulation time in the simulator, with a 2.0 s wall-time backstop

## Decision and basis

- **Decisions (Dr Sun, 2026-09-29, after the v32 trials):**
  - Order: the simulation-time pose gate first (v33), then the corridor entry's wrong-height cell (v34).
  - Scope: the change applies in the simulator only; the real-robot wall-time gate is unchanged.
  - Trials run with the other session's `machine-dog` git load paused.
  - Wall-time backstop: 2.0 s.
  - After independent review round 1: the 2.0 s backstop stays, although it is also the only catch for a stalled
    pose path while physics keeps running (see "What the simulation base means"). The case is documented here,
    and the trial's analysis flags any pose gap in which simulated time advanced more than 0.25 s.
- **Why:** mechanism B (host CPU starvation) ended every recent run through the backend's `odom_stale` check.
  That check compares **wall** time between body-pose receipts with 0.25 s
  (`runtime_sources/backend_adapter/backend_adapter/control_gate.py:138`, fed by `time.monotonic()` in
  `runtime_sources/backend_ros/p2b_backend_ros/node.py:226`).
  - **L1:** the bridge held a pose for 254.5 ms.
  - **L2:** the worker published nothing for 320 ms.
  - **Earlier:** v28, v30 and v31 ended the same way.

  In the recorded runs, these stalls also stopped, or nearly stopped, simulated time, so the robot moved little on
  stale information. Across all 128 pose gaps over 0.25 s (17 of 48 runs), simulated time advanced at most
  0.08 s, counting the burst of poses delivered right after each gap. Measured apart from the pose path, from
  the worker's per-step applied reports, physics advanced at most 0.06 s in the 122 gaps with those reports
  (`evidence/clock_lead_survey.json`). That is a property of the recorded stalls, not a guarantee. A stall in
  the pose path alone, with physics running, looks the same to the backend (see "What the simulation base
  means").
- **Evidence** (`evidence/pose_gap_survey.py` → `evidence/pose_gap_survey.json`): 48 runs, 380,795 body-pose
  callbacks.
  - **Wall time:** the longest wall gap between consecutive callbacks was 0.660 s, and 17 runs had wall gaps over
    0.25 s.
  - **Simulated time:** across those gaps, the stamps of consecutive delivered poses advanced at most 0.035 s
    (0.08 s counting the burst after the gap, above). The longest simulation-time gap between consecutive poses
    in any run was 0.065 s.
  - **So:** a 0.25 s simulation-time limit would have tripped in none of the recorded runs, including every
    recorded `odom_stale` end.
- **The simulation clock the backend can use:**
  - **Where `/clock` comes from:** the bridge publishes it (`foxy_bridge_node.py`, `_publish_complete_state`)
    from the same state sample as each body pose, and just before it. Sensor frames advance it too, with their
    capture stamps.
  - **One time base:** the Newton worker stamps poses and scans from the same `physics_time()`
    (`scripts/newton_episode.py`: `round(physics_time()*1e9)` for poses, the step's `physics_time_s` for
    scans). So the pose stamps and `/clock` share one time base. MuJoCo-Warp's float32 drift against
    steps × 1 ms (up to 1.78 s at 390 s) is common to both and cancels in the age.
  - **Consequence:** if the simulator stops, `/clock` stops too, so a pure simulation-time gate would never
    trip. The wall-time backstop covers that case, and so does, first, the unchanged applied-evidence check
    (review round 2, N1; see "What the simulation base means"). The backstop is also the only catch when the
    pose path stalls while physics keeps running, because `/clock` travels with the poses (review round 1, B2).

## The change

Five files change: the three gate files that the backend imports from `runtime_sources/`, the simulator's launch
graph, and the import record `setup/runtime_sources.json`. `materialize.py` makes the edits, `changes.patch`
records them, and the preimages are in `parent_source/`.

**Provenance (corrected after review round 1, B1).** `node.py` has been in every version manifest since v11; v11
and v14 changed it and updated its record in `setup/runtime_sources.json`, as v26 did for `config.py`.
`contracts.py` and `control_gate.py` have not been changed since their import and are not in v32's manifest.
The import record pins them, and it is in v32's manifest. `scripts/run_local_episode.py` re-hashes every record
before physics and refuses a run on any mismatch, so the record is a changed file of this version.

1. **`runtime_sources/backend_adapter/backend_adapter/contracts.py`**
   - `GateConfig` gains `odom_time_base` and `odom_wall_backstop_s`.
     - `odom_time_base` is `"wall"` (the default) or `"simulation"`; any other value is rejected.
     - `odom_wall_backstop_s` defaults to 2.0. It must be non-negative. Under the simulation base it must also be
       at least `odom_stale_s`; that rule does not apply under the wall base, which accepts every configuration
       v32 accepted (review round 1, N3).
   - `MeasuredState` gains an optional `stamp_s`, the pose's header stamp in simulation seconds. It must be
     finite when present.
2. **`runtime_sources/backend_adapter/backend_adapter/control_gate.py`**
   - `CommandGate` takes an optional `sim_clock`, a callable that returns the newest `/clock` in seconds or
     `None`.
   - A new method `measurement_stale(measurement, now)` holds the freshness rule, and `_blocking_reason` calls
     it in place of the old expression, at the same place in the check order and with the same reason
     `odom_stale`.
     - **Wall base:** `measurement is None or now − measurement.monotonic_s > odom_stale_s`. This is exactly
       the old expression.
     - **Simulation base:** the pose is stale if any of these holds:
       - there is no measurement, no stamp, no simulation clock, or the clock has not yet reported;
       - its simulation-time age `max(0, sim_now − stamp_s)` exceeds `odom_stale_s` (0.25 s);
       - its wall-time age `now − monotonic_s` exceeds `odom_wall_backstop_s` (2.0 s).

       A missing input fails closed.
3. **`runtime_sources/backend_ros/p2b_backend_ros/node.py`** (`RosScanPort`)
   - **Subscription, simulation base only:** it subscribes to `/clock` (`rosgraph_msgs/Clock`; topic
     `topics.clock_topic`, default `/clock`) with the bridge's QoS: reliable, depth 1, volatile, keep last.
     - It keeps the newest value and ignores and counts a backward value, as the bridge does.
     - It hands `sim_now()` to the gate.
     - Node timers keep wall time: the node does not use `use_sim_time`.
   - **Pose stamps:** `_on_body_pose` records the already-validated header stamp as `stamp_s`.
   - **Route start:** `measurement_provider()` applies the same freshness rule under the simulation base; the
     wall branch is unchanged.
   - **Status fields:** `snapshot()` adds `odom_time_base`, `sim_clock_s`, `sim_clock_backward_events` and
     `last_body_pose_sim_age_s`.
4. **`scripts/native_graph.py`**, which writes every simulator run's `backend_config.json`: it sets
   `gate.odom_time_base = "simulation"` and `gate.odom_wall_backstop_s = 2.0`. The archived backend config
   (`config_archived/p2b_backend_ros.two_goal.json`) is not edited.
5. **`setup/runtime_sources.json`**, the import record: the three runtime files' rows get their new `sha256` and
   `bytes`, the import hash kept as `archived_sha256` (node.py's, from before v11, unchanged) and a
   `local_modification` note. No other row or field changes.

**Unchanged:**
- **Other gates:** the heartbeat check (`heartbeat_stale_s` 0.20 s of wall time between SCAN commands), the
  initial-heartbeat grace, the applied-evidence check (a wall-time age limit of 2.0 s, the worker's
  `max_reader_age_s`) and the still window.
- **Other components:** the bridge, the Newton worker, SCAN, the planner and controller YAMLs, and the native
  build (`scan64`, as v31 and v32).
- **Other entry points:** the adapter's own `ros_node.py` and `run_adapter.py` keep the default wall base, as
  does any other configuration, the real robot's included.

**What the simulation base means** (corrected after review round 1, B2):
- **What is judged:** the pose is judged against the simulated time the backend receives on `/clock`. `/clock`
  comes from the same bridge callback as the poses (`foxy_bridge_node.py`, `_publish_complete_state`) and takes
  the same DDS path. So the backend cannot tell a stopped simulator from a stalled pose path: both freeze the
  pose and `/clock` together.
- **A host stall that also stops physics** (every recorded stall): the pose stays fresh, and the run goes on while
  the stall lasts under 2.0 s. A stall of 2.0 s or more ends it on `applied_evidence_stale`, as a stopped simulator
  does (below; review round 3, N5).
  This is the case v33 is meant to tolerate.
- **Losing poses while physics runs and `/clock` keeps advancing:** the gate trips once `/clock` is 0.25 s past
  the newest pose. The trip is quantized by what advances `/clock`. If only sensor frames do (one every 0.1 s of
  simulated time), it comes at the first frame past +0.25 s, up to about 0.35 s after the newest pose (review
  round 1, N7). While poses flow, the trial's asynchronous scan stamps lag the newest pose and the bridge drops
  them as backward.
- **A stopped simulator:** `/clock` freezes with the pose. In this integration, the unchanged applied-evidence
  check catches it first (review round 2, N1).
  - **Why first:** the worker sends one applied snapshot per control step, stamped at the step's start and sent
    after its physics. The backend checks the snapshot's 2.0 s age (`max_reader_age_s`) before the gate, in its
    20 ms watchdog and in its raw-command path (`node.py`, `_watchdog_tick` and `_on_raw_command`).
  - **The margin:** when stepping stops, the newest pose is the last step's step-end pose, and it reaches the
    backend after that step's snapshot stamp. Across 119,056 steps in 46 recorded runs, the margin was at least
    15.6 ms, and at least 45.0 ms in `v32_historical_full01` (`evidence/clock_lead_survey.json`).
  - **So:** the gate closes with `applied_evidence_stale` about 2.0 s after the last step started, just before
    the backstop would. Outside this integration, with no applied-evidence reader, the backstop catches it.
- **A stalled pose path while physics runs:** `/clock` freezes with the pose, while the applied snapshots stay
  fresh, so only the 2.0 s wall backstop trips. v32's wall rule tripped at 0.25 s. An `odom_stale` end through
  the backstop with no `applied_evidence_stale` therefore means that physics was running (review round 2, N1).
  What holds commands in the meantime depends on where the pose path stalls:
  - **Inside the bridge's ROS thread** (L1's recorded case, a 288.5 ms publish callback): the same thread
    receives the backend's commands (`_on_twist`), so the bridge's command thread sends zero once its newest
    command is 0.25 s old (`source_command_timeout_seconds`). If that thread is stalled too, the Mac side zeroes
    after 250 ms without commands (`command_state.py`). Commands from a frozen pose reach physics for at most
    about 0.25 s, as under v32.
  - **Before that thread, or on delivery to the backend** (the Mac worker's telemetry sender, the TCP link, the
    bridge's telemetry thread, DDS delivery): the command path keeps running.
    - SCAN's controller keeps publishing commands from its newest pose on a 10 ms wall timer; it checks only
      that a trajectory and a pose have been received (`closed_loop_controller.cpp`, `cmdCallback`).
    - In this profile the bridge does not zero commands on a stalled-feedback verdict
      (`require_fresh_simulation_feedback: false` in `config_archived/bridge.yaml`).
    - The Mac side's 250 ms rule zeroes only commands that stop arriving.
    - The heartbeat stays fresh, because SCAN's commands keep reaching the backend.

    Commands computed from a frozen pose can then reach running physics for up to 2.0 s of wall time, about
    0.7–0.8 s of simulated time at this Mac's usual 0.35–0.4× speed.
  - **Recorded bound:** in none of the 128 recorded pose gaps over 0.25 s did simulated time advance more than
    0.08 s, counting the burst after the gap. The in-container observer's `/clock` never ran more than 0.08 s
    ahead of the backend's newest pose over 1,890,389 samples (`evidence/clock_lead_survey.json`). No recorded
    gap was of this kind.
  - **Dr Sun's decision (after review round 1):** keep the 2.0 s backstop, document this case, and flag it in
    the trial's analysis. Any pose gap in which simulated time advanced more than 0.25 s is flagged, and the run's
    claims are qualified by it. The flag shows that physics ran while the backend's pose was frozen, not what
    physics received. The commands it received are reported separately for each flagged gap (review round 2,
    N4; `PHYSICAL_RUN_PLAN.md`).
- **What is lost in the simulator:**
  - **Within 2.0 s of wall time,** the gate no longer catches a delay that leaves the backend's `/clock` frozen.
    That covers the host stall v33 means to tolerate, and the rarer stalled pose path above.
  - **Losing poses while physics runs and `/clock` advances** (review round 2, N8): v33 trips after 0.25–0.35 s
    of simulated time. v32's 0.25 s of wall time was about 0.09–0.10 s of simulated time at 0.35–0.4× speed. So
    commands from a stale pose can act about 2.5–4 times longer in physics terms (0.25–0.35 s against
    0.0875–0.10 s; review round 3, N6).
  - **A new load on the backend's executor:** the `/clock` subscription adds about as many callbacks as the
    poses, about 60 a second (the v32 trial had 44,028 pose callbacks in 721 s of wall time). They share the
    single-threaded executor with the raw-command path that feeds the heartbeat. This load is not measured
    separately; the trial records the heartbeat's own events.

## Checks before the freeze

| Check | Pass condition |
|---|---|
| K1 byte-exact | each of the four source files equals its v32 bytes plus exactly the edits in `materialize.py`, and reversing them restores the v32 SHA-256; the record equals `materialize.update_record` applied to its v32 bytes, and restoring the three rows gives the v32 bytes; every other v32 manifest file is unchanged |
| K1b record check (added after review round 1, B1) | `record_check.py`: `run_local_episode.py`'s pre-physics record check, executed from its own lines, passes on the v33 bytes, and so does the review's `source_identity` comparison; the v32 record against the v33 files finds exactly the three changed runtime files (negative control) |
| K2 scope | each source file compiles; an AST comparison with its v32 preimage shows changes only in the definitions listed above (`GateConfig`, `MeasuredState`; `CommandGate.__init__`, `CommandGate._blocking_reason`, new `CommandGate.measurement_stale`; `RosScanPort.__init__`, `measurement_provider`, `snapshot`, `_on_body_pose`, new `sim_now`, `_on_sim_clock`; `native_graph.main`) and nowhere else; in the record, only the three rows change, only in `sha256`, `bytes`, `archived_sha256` and `local_modification`, and the new hashes and sizes are the current files' |
| K3 gate contract | `gate_contract.py`, run in the pinned container's Python and on the Mac; see below |
| K4 counterfactual replay | `replay_gate.py` over every surveyed run; see below |
| K5 ROS smoke | `ros_smoke.py`, a real `rclpy` node in the pinned image; see below |
| K6 independent review | the first round that passes with no blocking finding |

**K3, the gate contract.** It uses the v32 gate and contracts from `parent_source/` (red) and the v33 ones
(green). Every case states its expected red and green result.

- **C1 wall equivalence:** both gates get 20,000 random event sequences, each with 200 events. The events are
  admission, heartbeats, poses with and without stamps, ticks at random wall times, transport loss, cancel and
  hold. The default configuration must give identical `(allowed, command, reason, closed_reason)` after every
  event, in both red and green. The expected result is identical.
- **C2 host stall:** simulation base. Poses and `/clock` freeze together for 1.5 s of wall time while the
  heartbeat stays fresh.
  - Red: the wall base trips `odom_stale` after 0.25 s.
  - Green: it does not trip.
- **C3 lost poses:** simulation base. `/clock` advances 0.24 s past the newest pose and then 0.26 s past it,
  within 0.3 s of wall time.
  - Green: fresh at 0.24 s, `odom_stale` at 0.26 s.
- **C4 stopped simulator:** simulation base. Nothing arrives.
  - Green: fresh at 1.99 s of wall time, `odom_stale` at 2.01 s.
- **C5 fail closed:** simulation base with `sim_clock` absent, `sim_clock` returning `None`, or a pose without
  a stamp. Each gives `odom_stale`.
- **C6 clock behind the pose:** `/clock` 5 ms behind the newest pose stamp counts as age 0, so the pose is
  fresh.
- **C7 configuration:**
  - The default is `wall` with a 2.0 s backstop.
  - An unknown base, a negative backstop and a NaN stamp are rejected.
  - Under the simulation base, a backstop below `odom_stale_s` is rejected (also an `odom_stale_s` of 2.5 s with
    the default backstop), and one equal to it is accepted.
  - Under the wall base, a configuration v32 accepted is still accepted: `odom_stale_s` 2.5 s is accepted by red
    and green. Green also accepts a backstop below `odom_stale_s` under the wall base, where it is unused; red has
    no backstop field. These cases were added after review round 1 (N3).
  - `native_graph.py`'s generated gate section builds a valid `GateConfig` with the simulation base.
- **C8 check order:** with both the heartbeat and the pose stale, the reason is still `heartbeat_stale`
  under both bases.

**K4, counterfactual replay.** For every run in the survey, the recorded pose receipts drive the gate. Each
receipt supplies `entered_ns` as wall time and `stamp_ns` as the stamp.

- **Evaluation:** the gate is evaluated on a 20 ms wall grid and at every receipt, with the heartbeat held
  fresh.
- **Simulation clock:** three models are used (the third, and the wording of the other two, after review round 1,
  N1).
  - **M1, newest pose received:** `/clock` never runs ahead of the poses. The simulation age is then always 0,
    so M1 tests only the 2.0 s backstop against the recorded wall gaps.
  - **M2, next pose's stamp throughout a gap.**
  - **M3, the newest stamp delivered within 50 ms after the gap, throughout it.**

  M2 and M3 are approximations, not bounds. The backend's single-threaded executor takes one pose per wait cycle
  from a depth-5 queue while the depth-1 `/clock` jumps to the newest value. The direct measurement is the
  in-container observer's `/clock` against the backend's newest pose, in `evidence/clock_lead_survey.json`: at
  most 0.08 s over 1,890,389 samples, and at most 0.0403 s outside `v12_building_route01`.
- **Pass:**
  - The wall base (v32 behaviour) trips wherever a recorded wall gap exceeds 0.25 s and the replay evaluates inside
    the stale window. This validates the replay against the historical `odom_stale` ends. It reproduces 10 of the 12
    recorded ends, each by an episode in the gap its stop flow followed (`evidence/k4_end_match.py`). It misses
    `v5_building_route01`'s and `empty_long_route02`'s: those gaps exceeded 0.25 s by 10.4 and 3.2 ms, no
    evaluation point of the replay fell inside them, and the backend's own watchdog caught them.
    `empty_long_route02`'s one replay episode is in a later gap, after the stop flow. (Corrected after review
    rounds 3 and 4: the text first said every recorded end was reproduced, then 11 of 12.)
  - The simulation base trips in no run under any of the three models.
  - A synthetic loss, dropping 0.30 s of simulation time of poses from each run while `/clock` keeps
    advancing, trips it every time.

**K5, ROS smoke** (`ros_smoke.py` in the pinned image `sha256:f7363cc3…`, with v33's `runtime_sources` on
`PYTHONPATH`, as `native_inside.sh` sets it):

- **Two variants** (`ros_smoke.py <variant> <attempt>`, via `run_ros_smoke.sh`; each attempt writes its own
  `ros_smoke_<variant>_attemptNN.json` and `_stdout.log`, never overwritten):
  - **`trial`, the pass criterion:** the trial's path. The backend config is the archived
    `p2b_backend_ros.two_goal.json` with the gate update read from `native_graph.py`'s own source. It is loaded
    with `load_runtime_config` and built with `build_runtime`, as `scripts/native_backend_entry.py` does, and the
    backend node spins alone on a `SingleThreadedExecutor`, as with the trial's `--backend-executor single`. A
    thread keeps the applied-evidence file fresh, as the Mac worker's applied channel does, so that check stays
    open and the pose rule is what the checks read.
  - **`multi`, the round-1 harness, reported:** `RosScanPort` and `CommandGate` from a hand-built gate section,
    spun together with the publisher node on one `MultiThreadedExecutor(num_threads=2)`.
- **Setup, both:** a second node publishes, as the bridge does:
  - `/clock` with the bridge's own `CLOCK_QOS`;
  - `/quad_0/body_pose` with sensor-data QoS, 5 ms of simulation time apart;
  - the admitted owner's raw commands, at 50 Hz, as SCAN does.

  The node's own watchdog and raw-command paths evaluate the gate, and the checks read their decisions.
- **Pass, all five:**
  1. `/clock` and poses are received, and `snapshot()` reports a simulation age of at most 0.02 s; in `trial`, the
     loaded gate configuration is simulation, 2.0 s and 0.25 s.
  2. With both streams frozen for 1.0 s of wall time, `measurement_provider()` still returns the pose, and the
     gate stays open with block reason `ok`.
  3. With `/clock` advancing 0.30 s of simulation time and no pose, `measurement_provider()` raises
     `body_pose_stale`, and the gate closes with `odom_stale`.
  4. After fresh streaming and a new admission, the pose is still fresh at 1.9 s of wall time with nothing
     arriving. At 2.1 s both report stale (`odom_stale`).
  5. A backward `/clock` sample is ignored and counted.
- **Not pre-registered: the criteria were changed after failures** (all attempts are in `COMPONENT_RESULTS.md`).
  - **Round 1, after attempt 2 failed:** the harness gained the command stream, read the node's decisions
    instead of calling `tick()` directly, and bounded its streams by simulation time. This text was revised after
    the passing third attempt, not before it.
  - **Round 2, after review N2:** the `trial` variant was added. Check 4 now streams fresh poses before the new
    admission, after `trial` attempt 01 re-admitted while check 3's pose was 0.30 s stale. That is a harness
    fault: the gate rightly closed at once.
  - **Round 2, the criterion moved to `trial`:** `multi` attempts 02 and 03 failed checks on the unchanged
    heartbeat. The harness's own command receipts had gaps of 0.57–0.64 s under emulation (measured in attempt
    03). The cause is not established: GIL contention among the harness's threads is a hypothesis, and the
    publisher node has no callbacks for the executor to serve (review round 2, N6). The pose rule's decisions
    were as expected throughout.
  - **Harness records (review round 2, N6):** `k5_harness/` keeps the harness each round-2 attempt ran,
    rebuilt by reversing the recorded edits and checked by replaying them forward. From now on,
    `run_ros_smoke.sh` copies the harness before each run and checks it afterwards. It also refuses to start
    when any output of the attempt exists: round 2's guard did not stop a run whose log existed, although no log
    was overwritten.

## Live run after the freeze

- **Run:** `v33_historical_full01`, with exactly `v32_historical_full01`'s flags. Only the integration version
  (v33) and the planner-YAML copy path change.
- **Wrapper:** `scripts/run_bounded.py` with a 1800 s deadline.
- **Quiet host:**
  - Before the run, `docker ps` lists no container and no other project process runs.
  - Dr Sun is asked to pause the other session's `machine-dog` git activity first.
  - `host_sampler.py` records the host.
- **Acceptance:** the unchanged Building review for the historical profile.
- **Recorded separately** (the rules are in `PHYSICAL_RUN_PLAN.md`):
  - the exposure: pose wall gaps over 0.25 s while an owner was admitted. Without any, the run says nothing
    about the gate's tolerance (review round 1, N4);
  - the stalled-pose-path flag: any pose gap in which simulated time advanced more than 0.25 s (Dr Sun's decision
    after review round 1);
  - whether `odom_stale` occurs and its cause. The lag is measured from the start of the pose gap in which the
    stop flow started, or which ended at most 0.1 s before it: the runtime's monitor polls the gate every 50 ms, so
    the flow normally starts within about 50 ms of the closure. Recorded flows started 4–76 ms after the earliest
    possible trip (`evidence/k4_end_match.json`; review round 4, N2). The backstop if and only if that lag is at
    least 2.0 s, otherwise the simulation age (review rounds 2 and 3, N3 and N1). With no qualifying gap, the cause
    is reported as unattributed, with the observer cross-check (round 4, N2). The observer's `/clock` is the proxy
    for the backend's, whose receipts are not logged. A backstop end without `applied_evidence_stale` is read as a
    stalled pose path with physics running (round 2, N1);
  - the backend's simulation-age and wall-gap distributions;
  - any `heartbeat_stale` (watched, unchanged);
  - clock reconnects;
  - host load;
  - where the robot stops.
- **Expected, not a criterion:** with the wrong-height cell unfixed (v34), the robot is likely to stand at the
  corridor entry until the 600 s physics bound or the 1500 s goal wall budget ends the run. Such a run tests the
  gate over a long exposure, not navigation.

## Claim boundary

- **Version status:** a version increment is not acceptance. v3 remains the last accepted navigation condition.
- **What K3–K5 can show:** the gate's logic and its ROS plumbing, not navigation.
- **What the trial can show:** one run without `odom_stale` shows that the gate tolerated that run's stalls, and
  only if the run had any. It does not show that B is harmless to control: during a stall, commands are still
  delayed, and the Mac side still zeroes stale commands.
- **A stalled pose path:** v33 lets commands computed from a frozen pose reach running physics for up to 2.0 s
  of wall time in that case, against 0.25 s under v32. It has not occurred in any recorded gap. A trial in which
  it is flagged is qualified by it.
- **The heartbeat:** `heartbeat_stale` (0.20 s of wall time) is unchanged and could become the next thing that
  ends runs. It fires when the backend itself stalls: its timers run before its subscriptions, so it resumes
  seeing an old raw command.
  - **Measured over the recorded runs** (`evidence/clock_lead_survey.json`): 2 of the 17 runs with pose gaps had
    such a stall of at least 0.2 s inside a pose gap, measured by the observer's gated-command gaps while raw
    commands kept flowing. They were `v12_building_route01` (0.439 s inside a 0.483 s pose gap) and
    `empty_long_route03` (0.231 s inside 0.359 s). `empty_long_route03` did end on `heartbeat_stale`, under the
    wall base (its `result.json`). Under v33, `v12_building_route01`'s stall would most likely have ended on
    `heartbeat_stale` too (inferred).
  - **In the historical_full trials** v25, v28, v30, v31 and v32, those gaps were at most 0.05 s.
  - **Reading:** a `heartbeat_stale` end is read as a backend-side stall, not as a v33 regression. It is watched,
    and not changed without Dr Sun.
- **The real robot:** its configuration keeps the wall base, and under the wall base the gate's decisions are
  unchanged (K3 C1).
  - **What does change under the wall base:** the port's status gains four keys (`odom_time_base` is `wall`, the
    others `None` or 0), and `MeasuredState` carries the pose stamp.
  - **What does not:** the `/clock` subscription and the simulation-time rule exist only under the simulation
    base, which only `native_graph.py` selects.
