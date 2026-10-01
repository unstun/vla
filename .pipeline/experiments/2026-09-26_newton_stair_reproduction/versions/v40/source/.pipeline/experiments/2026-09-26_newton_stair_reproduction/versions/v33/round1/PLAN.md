# v33: judge body-pose freshness by simulation time in the simulator, with a 2.0 s wall-time backstop

## Decision and basis

- **Decisions (Dr Sun, 2026-09-29, after the v32 trials):**
  - Order: the simulation-time pose gate first (v33), then the corridor entry's wrong-height cell (v34).
  - Scope: the change applies in the simulator only; the real-robot wall-time gate is unchanged.
  - Trials run with the other session's `machine-dog` git load paused.
  - Wall-time backstop: 2.0 s.
- **Why:** mechanism B (host CPU starvation) ended every recent run through the backend's `odom_stale` check.
  That check compares **wall** time between body-pose receipts with 0.25 s
  (`runtime_sources/backend_adapter/backend_adapter/control_gate.py:138`, fed by `time.monotonic()` in
  `runtime_sources/backend_ros/p2b_backend_ros/node.py:226`).
  - **L1:** the bridge held a pose for 254.5 ms.
  - **L2:** the worker published nothing for 320 ms.
  - **Earlier:** v28, v30 and v31 ended the same way.

  In a simulator, a host stall also stops simulated time, so the robot has not moved on stale information.
- **Evidence** (`evidence/pose_gap_survey.py` → `evidence/pose_gap_survey.json`): 48 runs, 380,795 body-pose
  callbacks.
  - **Wall time:** the longest wall gap between consecutive callbacks was 0.660 s, and 17 runs had wall gaps over
    0.25 s.
  - **Simulated time:** at every one of those gaps, simulated time advanced at most 0.035 s. The longest
    simulation-time gap in any run was 0.065 s.
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
    trip. The wall-time backstop covers that case.

## The change

Four files change: the three gate files that the backend imports from `runtime_sources/` (put under a version
manifest for the first time here), and the simulator's launch graph. `materialize.py` makes the edits,
`changes.patch` records them, and the preimages are in `parent_source/`.

1. **`runtime_sources/backend_adapter/backend_adapter/contracts.py`**
   - `GateConfig` gains `odom_time_base` and `odom_wall_backstop_s`.
     - `odom_time_base` is `"wall"` (the default) or `"simulation"`; any other value is rejected.
     - `odom_wall_backstop_s` defaults to 2.0. It must be non-negative and at least `odom_stale_s`.
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

**Unchanged:**
- **Other gates:** the heartbeat check (`heartbeat_stale_s` 0.20 s of wall time between SCAN commands), the
  initial-heartbeat grace, the applied-evidence check and the still window.
- **Other components:** the bridge, the Newton worker, SCAN, the planner and controller YAMLs, and the native
  build (`scan64`, as v31 and v32).
- **Other entry points:** the adapter's own `ros_node.py` and `run_adapter.py` keep the default wall base, as
  does any other configuration, the real robot's included.

**What the simulation base means:**
- **What is judged:** the pose is judged against the simulated world it describes. During a host stall,
  simulated time stops with the pose stream, and the pose stays fresh.
- **Losing poses while physics runs:** if poses stop while sensor frames still advance `/clock`, the gate trips
  once `/clock` is 0.25 s past the newest pose.
- **A stopped simulator:** it trips after 2.0 s of wall time.
- **What is lost in the simulator:** the gate no longer catches a wall-time delay shorter than 2.0 s that
  leaves simulated time frozen. That is exactly the host stall v33 means to tolerate. On the Mac side, the
  applied channel's own command-staleness rule still zeroes a command that goes stale.

## Checks before the freeze

| Check | Pass condition |
|---|---|
| K1 byte-exact | each of the four files equals its v32 bytes plus exactly the edits in `materialize.py`; reversing them restores the v32 SHA-256; every other v32 manifest file is unchanged |
| K2 scope | each file compiles; an AST comparison with its v32 preimage shows changes only in the definitions listed above (`GateConfig`, `MeasuredState`; `CommandGate.__init__`, `CommandGate._blocking_reason`, new `CommandGate.measurement_stale`; `RosScanPort.__init__`, `measurement_provider`, `snapshot`, `_on_body_pose`, new `sim_now`, `_on_sim_clock`; `native_graph.main`) and nowhere else |
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
  - An unknown base is rejected, and so is a backstop below `odom_stale_s`.
  - `native_graph.py`'s generated gate section builds a valid `GateConfig` with the simulation base.
- **C8 check order:** with both the heartbeat and the pose stale, the reason is still `heartbeat_stale`
  under both bases.

**K4, counterfactual replay.** For every run in the survey, the recorded pose receipts drive the gate. Each
receipt supplies `entered_ns` as wall time and `stamp_ns` as the stamp.

- **Evaluation:** the gate is evaluated on a 20 ms wall grid and at every receipt, with the heartbeat held
  fresh.
- **Simulation clock:** two models are used.
  - **Newest pose received:** `/clock` never runs ahead of the poses.
  - **Next pose's stamp throughout a gap:** the upper bound from the survey.
- **Pass:**
  - The wall base (v32 behaviour) trips wherever a recorded wall gap exceeds 0.25 s. This reproduces the
    historical `odom_stale` ends and validates the replay.
  - The simulation base trips in no run under either model.
  - A synthetic loss, dropping 0.30 s of simulation time of poses from each run while `/clock` keeps
    advancing, trips it every time.

**K5, ROS smoke** (`ros_smoke.py` in the pinned image `sha256:f7363cc3…`, with v33's `runtime_sources` on
`PYTHONPATH`, as `native_inside.sh` sets it):

- **Setup:** one process builds `RosScanPort` with a real `rclpy` node and the simulation base. A second node in
  the same process publishes, as the bridge does:
  - `/clock` with the bridge's own `CLOCK_QOS`;
  - `/quad_0/body_pose` with sensor-data QoS, 5 ms of simulation time apart;
  - the admitted owner's raw commands, at 50 Hz, as SCAN does.

  The node's own watchdog and raw-command paths evaluate the gate, and the checks read their decisions.
- **Pass, all five:**
  1. `/clock` and poses are received, and `snapshot()` reports a simulation age of at most 0.02 s.
  2. With both streams frozen for 1.0 s of wall time, `measurement_provider()` still returns the pose, and the
     gate stays open with block reason `ok`.
  3. With `/clock` advancing 0.30 s of simulation time and no pose, `measurement_provider()` raises
     `body_pose_stale`, and the gate closes with `odom_stale`.
  4. After fresh streaming, the pose is still fresh at 1.9 s of wall time with nothing arriving. At 2.1 s both
     report stale (`odom_stale`).
  5. A backward `/clock` sample is ignored and counted.
- **Revised before K5 passed:**
  - **What changed:** the command stream and the reading of the node's decisions replaced direct `tick()`
    calls, and streams are bounded by simulation time.
  - **Why:** without SCAN commands, the node's watchdog closes an admitted gate with
    `initial_heartbeat_missing` after 1 s. Under emulation, a wall-bounded stream advanced only 0.23 s of
    simulation time.
  - **What stayed:** the change under test did not change. See `COMPONENT_RESULTS.md`.

## Live run after the freeze

- **Run:** `v33_historical_full01`, with exactly `v32_historical_full01`'s flags. Only the integration version
  (v33) and the planner-YAML copy path change.
- **Wrapper:** `scripts/run_bounded.py` with a 1800 s deadline.
- **Quiet host:**
  - Before the run, `docker ps` lists no container and no other project process runs.
  - Dr Sun is asked to pause the other session's `machine-dog` git activity first.
  - `host_sampler.py` records the host.
- **Acceptance:** the unchanged Building review for the historical profile.
- **Recorded separately:**
  - whether `odom_stale` occurs and its cause (simulation age or backstop);
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
- **What the trial can show:** one run without `odom_stale` shows that the gate tolerated that run's stalls. It
  does not show that B is harmless to control: during a stall, commands are still delayed, and the Mac side
  still zeroes stale commands.
- **The heartbeat:** `heartbeat_stale` (0.20 s of wall time) is unchanged and could become the next thing that
  ends runs. It is watched and not changed without Dr Sun.
- **The real robot:** its configuration keeps the wall base. Nothing in v33 changes a real-robot path.
