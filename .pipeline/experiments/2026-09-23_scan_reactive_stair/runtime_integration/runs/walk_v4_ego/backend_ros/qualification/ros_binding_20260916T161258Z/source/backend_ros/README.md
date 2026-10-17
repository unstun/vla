# P2B Backend ROS Runtime

This directory owns the runnable Foxy ROS/HTTP binding for the P2B pilot. It reuses the canonical `backend_adapter` library for PCT IPC, P2A lifecycle, typed SCAN contracts, command gating and applied-stop evidence. It does not edit `backend_adapter`, `navigation_service`, frozen upstream source or sibling repositories.

## Runtime contract

Start the native PCT worker separately in the Humble/PCT runtime, then run this package in the Foxy overlay that contains the current generated `scan_planner` and `scan_planner_msgs` packages.

Default loopback HTTP endpoints:

| Endpoint | Behavior |
|---|---|
| `POST /goal` | Accepts `{request_id, goal_id, target_ground_xyz, frame, map_epoch, map_revision}` and starts bounded planning in a worker thread. |
| `POST /cancel` | Cancels the current owner. Release requires `P2BAdmission.consumer == "controller"` plus post-cancel applied evidence dwell. |
| `GET /state` | Reports readiness, measured body pose, PCT ground-start pose, current owner, jobs, gate state and per-request terminal result records. |

`target_ground_xyz` is the PCT input target. PCT start is the measured body pose from `/quad_0/body_pose` minus `nominal_body_height_m`. Native PCT output route Z remains body-reference Z for routing/debug. Arrival is checked against the immutable HTTP requested target converted to body height (`target_ground_xyz + nominal_body_height_m` in Z), not the final native PCT waypoint. Arrival within `0.25 m` XY and `0.20 m` Z only triggers stop; success is recorded after quiescence, controller hold, applied-zero dwell and a second requested-target geometry check.

The command path is:

```text
POST /goal
  -> backend_adapter P2A lifecycle
  -> native PCT TCP worker
  -> /p2b/route P2BRoute(nav_msgs/Path)
  -> /p2b/scan_admission consumer=fsm accepted
  -> /quad_0/raw_scan_cmd_vel P2BStampedTwist
  -> backend_ros gate
  -> /quad_0/cmd_vel
```

The watchdog publishes zero before the first same-generation raw command heartbeat and waits for a bounded initial grace. It does not pre-fault a newly admitted generation by calling `CommandGate.tick()` before the controller has had a chance to echo the new identity. After the first same-generation heartbeat, stale odometry, stale heartbeat or stale runner applied-command evidence closes the gate and publishes zero.

`GET /state` also exposes `pct.configured_pct_layer` and bounded `pct.plan_history`. Each entry records the actual forwarded PCT request after layer injection, including measured `start_xyz_m`, requested `target_xyz_m`, layer, map identity, returned `route_id`, returned waypoints, timing and any planner error. This is intended for lead-side correlation of cancel/resubmit replanning from the measured post-cancel body pose.

## Launch

The launch file takes absolute config paths and run artifact paths:

```bash
ros2 launch p2b_backend_ros p2b_backend.launch.py \
  backend_config:=/abs/path/backend_ros/config/p2b_backend_ros.example.json \
  planner_config:=/abs/path/p2b_execution/baseline_config/planner.yaml \
  controller_config:=/abs/path/p2b_execution/baseline_config/controller.yaml \
  bridge_config:=/abs/path/p2b_execution/baseline_config/bridge.yaml \
  run_id:=p2b-two-goal-001 \
  run_epoch_ns:=1234567890 \
  applied_snapshot:=/abs/run/current_command.json \
  finish_request:=/abs/run/finish_request.json \
  pct_port:=47631 \
  http_port:=8765
```

The launch starts `scan_planner_node`, `closed_loop_controller`, `lite3_sim_bridge.foxy_bridge_node` and `p2b_backend_ros`. It never launches the legacy `reference_path_publisher`.

The controller `body_pose` input is explicitly remapped to `/quad_0/body_pose`. The bridge is launched through `python3 -c 'from lite3_sim_bridge.foxy_bridge_node import main; main()'` because the frozen bridge module defines `main()` but has no module `if __name__ == "__main__"` entrypoint.

Direct module entrypoint, useful when the bridge is launched by the parent driver:

```bash
PYTHONPATH=/abs/path/backend_ros:/abs/path/backend_adapter:${PYTHONPATH} \
python3 -m p2b_backend_ros.node \
  --config /abs/path/backend_ros/config/p2b_backend_ros.example.json \
  --run-id p2b-two-goal-001 \
  --run-epoch-ns 1234567890 \
  --applied-snapshot /abs/run/current_command.json \
  --finish-request /abs/run/finish_request.json \
  --pct-port 47631 \
  --http-port 8765
```

Render the schema without starting ROS:

```bash
PYTHONPATH=/abs/path/backend_ros:/abs/path/backend_adapter:${PYTHONPATH} \
python3 -m p2b_backend_ros.node \
  --config /abs/path/backend_ros/config/p2b_backend_ros.example.json \
  --print-contract
```

## Verification

Local CPU verification:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/verify.py
```

This compiles the package, runs unit tests for config/schema/terminal-state helpers and renders the wire contract. It is not ROS graph, native PCT, Isaac or physical robot evidence. Parent/lead owns the real Foxy compile, controller probe and Isaac two-goal pilot.

Bounded Foxy CPU qualification:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_ros/qualify_foxy_cpu.py
```

This syncs whitelisted `backend_ros`, `backend_adapter` and accepted `navigation_service/core.py` sources to `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/ros_binding_qualification/<run_id>`, mounts the read-only `scan_02` install workspace as `/workspace`, and runs the node inside Foxy image `e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8`. The smoke covers actual `rclpy` startup with launch-style ROS remap args, localhost HTTP `/state`, missing body/snapshot readiness, invalid goal refusal, valid goal failure before PCT when body pose is absent, and zero output for invalid and valid-idle raw commands. It does not launch PCT, Isaac, GPU, accepted C++ motion or hardware.
