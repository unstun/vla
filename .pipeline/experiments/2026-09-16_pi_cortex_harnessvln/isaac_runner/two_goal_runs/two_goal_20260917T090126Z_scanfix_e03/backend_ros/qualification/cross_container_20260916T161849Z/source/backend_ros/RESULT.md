# P2B Backend ROS Result

Status: implemented local source for the runnable Foxy rclpy/HTTP binding. Local CPU verification passed, and bounded actual Foxy CPU startup/HTTP/ROS smoke passed in the lead-provided image. No PCT worker, Isaac process, V12 policy, accepted C++ motion pilot, GPU run or physical robot was launched by this slice.

Owned path: `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/**`.

Current implementation:

- `p2b_backend_ros.node`: rclpy node with localhost HTTP `/goal`, `/cancel` and `/state`, typed P2BRoute/P2BCancel/P2BAdmission/P2BStampedTwist wiring, raw SCAN command gate and independent watchdog.
- `p2b_backend_ros.runtime`: pure-Python HTTP runtime, goal payload decoding, terminal result ledger, requested-target arrival checks and PCT ground-start transform.
- `p2b_backend_ros.config`: schema normalization for this package and sibling `backend_adapter` v2 config.
- `launch/p2b_backend.launch.py`: explicit launch entry for `scan_planner`, controller, bridge and backend runtime with absolute config/run arguments.
- `config/p2b_backend_ros.example.json`: local example config matching the frozen P2B pilot topics and thresholds.
- `qualify_foxy_cpu.py`: bounded remote Foxy CPU qualification harness that syncs whitelisted source, runs actual `rclpy` node startup and returns raw logs/hash evidence under `backend_ros/qualification/**`.

Key runtime behavior now covered by source tests:

- `cancel()` does not call the synchronous P2A `cancel_active()` path; it starts one background stop flow, uses `backend_adapter.stop()` once, then polls `backend_adapter.poll_stop()` without resetting dwell.
- Explicit cancel wins over simultaneous arrival.
- Arrival uses immutable HTTP requested target plus nominal body height, and rechecks geometry after stop before recording `arrived`.
- Gate fault and command timeout start stop flow before arrival geometry, so a fault away from the goal does not leave ownership accepted forever.
- The monitor ignores only the expected gate closure caused by the active pending stop flow itself, such as `arrived_hold` while waiting for delayed controller hold. Different faults during that pending stop still promote the flow to failed.
- Raw callbacks zero and stay alive for malformed identity, valid idle identity, stale/mismatched identity and non-finite matching command.
- Body pose must have the configured frame, monotonic ROS stamp and fresh wall age before goal planning or arrival decisions.
- The `/quad_0/body_pose` subscriber uses ROS sensor-data QoS to receive the frozen bridge's BEST_EFFORT `Odometry`; this fixes the actual3 no-odom full-sim failure where the previous default RELIABLE subscription stayed at `_last_measurement == null`.
- Applied snapshot readiness checks configured run id and run epoch.
- Configured `map.pct_layer` is injected into actual PCT requests by the ROS-owned `LayeredPctClient`, and `/state["pct"]["plan_history"]` records the forwarded request and returned route.

Latest local verification:

```text
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/verify.py
# ok: true
# 23 unittest cases passed
# rendered p2b_backend_ros_wire_contract_v1
# latest record: checks/latest_verify.json
```

Latest local verification artifact:

```text
.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/checks/verify_20260916T161254Z.json
```

Latest bounded actual Foxy CPU qualification:

```text
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/qualify_foxy_cpu.py
# ok: true
# local:  .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/qualification/ros_binding_20260916T161258Z
# remote: /home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/ros_binding_qualification/ros_binding_20260916T161258Z
# image:  e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8
# scan_02 install mounted read-only as /workspace
```

Foxy smoke checks recorded in `qualification/ros_binding_20260916T161258Z/result/summary.json`:

```text
initial_state_missing_body_and_snapshot
invalid_goal_structured_refusal
valid_goal_fails_explicitly_without_body_or_pct
best_effort_body_pose_qos_observed_in_state
invalid_raw_identity_zero_output_and_node_alive
valid_idle_raw_identity_zero_output_and_node_alive
```

`qualification/ros_binding_20260916T161258Z/result/state_after_best_effort_odom.json` shows `readiness.body_pose_ready: true`, `measurement_body_pose.position_world_m: [0.1, 0.2, 0.35]`, and `scan_port.last_body_pose_age_s` below the 0.25 second stale threshold after a BEST_EFFORT `Odometry` publisher wrote `/quad_0/body_pose`.

Returned evidence:

```text
qualification/ros_binding_20260916T161258Z/qualification_report.json
qualification/ros_binding_20260916T161258Z/source_sha256.json
qualification/ros_binding_20260916T161258Z/remote_source_sha256.json
qualification/ros_binding_20260916T161258Z/sync_verdict.json  # ok: true, ignoring runtime __pycache__
qualification/ros_binding_20260916T161258Z/result/node.stderr.log
qualification/ros_binding_20260916T161258Z/result/node.stdout.log
qualification/ros_binding_20260916T161258Z/result/state_initial.json
qualification/ros_binding_20260916T161258Z/result/state_after_valid_goal_without_body.json
qualification/ros_binding_20260916T161258Z/result/state_after_best_effort_odom.json
qualification/ros_binding_20260916T161258Z/result/cmd_vel_zero_probe.json
```
