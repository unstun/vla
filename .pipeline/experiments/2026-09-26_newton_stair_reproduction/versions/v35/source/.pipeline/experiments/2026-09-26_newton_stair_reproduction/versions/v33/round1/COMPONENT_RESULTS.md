# v33 component results (before the freeze)

The change, as `materialize.py` made it from the v32-verified parents and `changes.patch` records it:

| File | Lines added | Change |
|---|---|---|
| `runtime_sources/backend_adapter/backend_adapter/contracts.py` | 13 | `GateConfig.odom_time_base` (`wall` or `simulation`, default `wall`) and `odom_wall_backstop_s` (default 2.0, at least `odom_stale_s`); `MeasuredState.stamp_s` (optional, finite) |
| `runtime_sources/backend_adapter/backend_adapter/control_gate.py` | 23 | optional `sim_clock`; `measurement_stale()` holds the freshness rule; `_blocking_reason` calls it in place of the old expression |
| `runtime_sources/backend_ros/p2b_backend_ros/node.py` | 32 | simulation base only: `/clock` subscription (the bridge's QoS), `sim_now()`, stamps into `MeasuredState`, the route-start check, four status fields |
| `scripts/native_graph.py` | 3 | the simulator's backend config sets the simulation base and the 2.0 s backstop |

The three runtime files had not changed since their import (`setup/runtime_sources.json`), and none had been in
a version manifest before. `materialize.py` checked them against their import hashes.

## K1 and K2 (`check_change.py` → `check_change.json`): passed

- **K1, byte-exact:** for each file, the recorded edits rebuild it from its preimage and reversing them
  restores the preimage. The hashes match `prepared.json`. The other 2,971 files of v32's manifest are
  unchanged.
- **K2, scope:** every file compiles. The changed definitions are exactly `GateConfig` and `MeasuredState` (with
  their `__post_init__`), `CommandGate.__init__`, `_blocking_reason` and the new `measurement_stale`,
  `RosScanPort.__init__`, `measurement_provider`, `snapshot`, `_on_body_pose` and the new `sim_now` and
  `_on_sim_clock`, and `native_graph.main`. All other module statements are identical.
- **First run failed (recorded):** my allow-list named the two dataclasses but not their `__post_init__`
  methods. The plan's scope ("`GateConfig`, `MeasuredState`") covers them; the list was corrected. No code
  changed.

## K3, the gate contract (`gate_contract.py`): passed on the Mac (Python 3.12.13) and in the pinned image (3.10.12)

`gate_contract_mac.json` and `gate_contract_container.json` give identical case results.

| Case | Red (v32) | Green (v33) |
|---|---|---|
| C1 wall equivalence | — | 20,000 sequences × 200 events: identical outputs and state after every event |
| C2 host stall | `odom_stale` at 0.26 s | open throughout 1.5 s |
| C3 lost poses | — | `odom_stale` at 0.26 s of simulation age; age probe 0.24 s fresh, 0.26 s stale |
| C4 stopped simulator | — | fresh at 1.99 s of wall time, `odom_stale` at 2.01 s |
| C5 fail closed | — | no clock, a clock not yet reported, or a pose without stamp: `odom_stale` |
| C6 clock 5 ms behind the pose | — | fresh |
| C7 configuration | — | default `wall`/2.0; unknown base, a backstop below 0.25 s or negative, and a NaN stamp rejected; `native_graph.py`'s gate section gives `simulation`/2.0 |
| C8 check order | `heartbeat_stale` | `heartbeat_stale` under both bases |

C1's gate outputs reached the pose rule both ways:
- **Trips:** 7,824 evaluations ended in `odom_stale`.
- **Passes:** 1,686 ended in `ok` and 1,150 in `measured_map_mismatch`, a check that follows the pose rule.

## K4, counterfactual replay (`replay_gate.py` → `replay_gate.json`): passed

The replay covers all 48 surveyed runs, with 380,795 recorded pose receipts.

- **Wall base (v32 rule):** 84 stale episodes in 16 runs. They include every recorded `odom_stale` end: v17,
  v25, v28, v30, v31, v32, `diag_v31_clock03/04` and `diag_v32_clock01`. The 17th run with a gap over 0.25 s,
  `v5_building_route01`, exceeded the limit by about 10 ms, between two evaluation points.
- **Simulation base:** 0 stale evaluations in every run, under both clock models (newest pose received, and the
  next stamp throughout each gap).
- **Synthetic loss:** dropping 0.30 s of simulation time of poses, while `/clock` keeps following the record,
  trips the simulation base in all 48 runs.

## K5, ROS smoke (`ros_smoke.py` via `run_ros_smoke.sh` → `ros_smoke.json`, `ros_smoke_stdout.log`): passed

The smoke ran a real `rclpy` backend port in the pinned image, with the native build's overlay.

| Check | Result |
|---|---|
| 1 streaming | simulation base; `/clock` received; simulation age 0.0 s; route start fresh |
| 2 host stall (1.06 s of wall time, streams frozen) | the wall rule would be stale; route start fresh; gate open, block reason `ok` |
| 3 lost poses (`/clock` +0.30 s) | route start `body_pose_stale`; gate closed `odom_stale` |
| 4 stopped simulator | fresh and open at 1.9 s; `body_pose_stale` and `odom_stale` at 2.1 s |
| 5 backward `/clock` | ignored, counted once |

**Earlier attempts (recorded; the change under test did not change):**
- **Attempt 1:** did not start. ROS domain 233 is above the maximum of 232, so it was changed to 219.
- **Attempt 2:** passed checks 1, 2 and 5 and failed 3 and 4 on the harness.
  - The wall-bounded clock stream advanced only 0.23 s of simulation time under emulation.
  - With no SCAN commands, the node's watchdog closed the admitted gate with `initial_heartbeat_missing`.
- **The fix:** the harness now bounds streams by simulation time, publishes the owner's raw commands at 50 Hz,
  and reads the node's own decisions. `PLAN.md` K5 was revised to match before the passing run.

## Not yet done

- K6 independent review.
- The freeze.
- The live run.
