# P2B Backend Adapter Contract

This directory owns the library/core side of the P2B integration between the accepted P2A lifecycle and the real PCT/SCAN/Isaac stack. It contains the bounded PCT worker, Foxy-side adapter contracts, command gate, applied-runner evidence verifier, and a hash-gated SCAN overlay materializer. It does not claim a completed ROS/Isaac pilot by itself.

## Canonical wire schema

Native PCT must run outside Foxy Python in the existing Humble/PCT runtime. The Foxy adapter talks to it over bounded JSON-line TCP. The worker uses real PCT planning only; missing runtime, timeout, malformed output or native rejection fails explicitly.

```bash
PYTHONPATH=/pct-runtime/python:${PYTHONPATH} \
LD_LIBRARY_PATH=/pct-runtime/lib:${LD_LIBRARY_PATH} \
python3 -m backend_adapter.pct_worker \
  --host 127.0.0.1 \
  --port 47631 \
  --pct-source-root /pct-runtime/python \
  --rsg-root <frozen-rsg-root> \
  --tomogram-path <frozen-map-pickle> \
  --reference-height-m 0.35
```

The worker requires `optimize=true`. It sets native reference height to 0.35 m when supported, reads native optimizer heights, verifies the wrapper route still carries the known display-only `+0.5 m` Z offset, and returns body-reference Z values with `z_semantics=lite3_body_reference_no_display_offset`.

The SCAN overlay materializes these typed ROS messages in `scan_planner_msgs`:

- `P2BRoute`: full command identity plus `nav_msgs/Path path` on `/p2b/route`.
- `P2BCancel`: full command identity plus cancel reason on `/p2b/scan_cancel`.
- `P2BAdmission`: full command identity, `consumer` (`fsm` or `controller`), status, message, hold flags and trajectory id on `/p2b/scan_admission`.
- `P2BStampedTwist`: full command identity plus raw controller twist on `/quad_0/raw_scan_cmd_vel`.

The adapter gates raw commands to `/quad_0/cmd_vel`. Controller hold, not FSM hold, is the required consumer stop receipt for releasing P2A ownership. Final stop also requires post-cancel runner evidence: fresh same run/epoch, causal command source timestamp after the stop request, advancing state/sim time for a continuous 1.0 sim-second dwell, applied command norm <= 0.01, measured horizontal speed <= 0.10 m/s and yaw rate <= 0.15 rad/s. A still cached sample from before cancel is not enough.

In explicit P2B overlay mode, the legacy anonymous `/initial_path` entry is ignored so it cannot bypass typed command identity. The overlay keeps upstream files frozen and writes a fresh generated source tree only.

## Materialize SCAN overlay for lead build/probe

Use a fresh, non-existing output path. The materializer verifies pinned source hashes before copying and refuses source/output ancestor relationships.

```bash
cd /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter
python3 -m backend_adapter.materialize_overlay \
  --source /Users/sun/tongbu/study/phdproject/vla/references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src \
  --output <fresh-build-root>/src
```

The generated launch file uses ROS package name `scan_planner` and the overlay topics above. Parent/lead owns the actual Foxy build and controller probe execution.

## Library/API files

- `backend_adapter/contracts.py`: validated JSON/IPC dataclasses and `ScanAdmission.consumer` schema.
- `backend_adapter/pct_worker.py`: native Humble/PCT worker entrypoint with serialized native planner calls.
- `backend_adapter/pct_ipc.py`: Foxy-side bounded IPC client and route id derivation from actual waypoints.
- `backend_adapter/adapter_core.py`: P2A backend port using PCT route, SCAN admission and stop evidence.
- `backend_adapter/control_gate.py`: raw command gate by command identity, generation, heartbeat, odometry and map freshness.
- `backend_adapter/applied_evidence.py`: canonical runner snapshot decoder and causal dwell stop verifier.
- `backend_adapter/materialize_overlay.py`: hash-gated generated SCAN/C++ overlay.
- `backend_adapter/ros_node.py`: earlier local rclpy/HTTP draft entry retained for reuse; active follow-up ownership for real ROS/HTTP launch moved to sibling `backend_ros/**` per lead direction.

## Verification

Run:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/verify.py
```

The check compiles Python, runs owned tests, renders the v2 config contract, materializes a temporary SCAN overlay, and records owned/reference hashes under `checks/`. Passing this check means the owned adapter/materializer contract is ready for lead's real Foxy compile/probe. It is not ROS graph, Isaac episode, V12 policy or physical robot evidence.

## Persistent stop continuation API for ROS/HTTP binding

`P2BBackendAdapter.stop(command, reason)` starts a stop attempt for the exact stored `CommandIdentity`. It closes the gate and publishes one correlated SCAN cancel/hold request. If controller hold or applied evidence is not complete yet, it returns `BackendOutcome("pending", ...)` and keeps a stop state.

The ROS/HTTP binding must then call:

```python
adapter.poll_stop(command)
```

on a timer or request continuation. `poll_stop` does not publish another cancel and does not reset the applied-evidence dwell window. It accumulates the same controller hold receipt and fresh post-cancel runner evidence until it can return `BackendOutcome("stopped", ...)`. The caller should preserve the P2A owner while this is pending and only report terminal cancellation/arrival after `stopped`.

The adapter records the full `CommandIdentity` before every submit call, including pending or uncertain submissions. A later stop for that command uses the stored identity and original map metadata even when the local gate owner was not opened yet.

## Actual PCT IPC qualification

The CPU-only qualification script is:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/qualify_pct_ipc.py
```

It syncs hashed owned adapter sources plus frozen `p2b_execution/pct_runtime`, pilot and map inputs to `gpu5070ti`, starts `backend_adapter.pct_worker` inside the existing PCT/Humble image `40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555`, drives it through real `PctIpcClient` requests, then runs owned tests under the Foxy Python 3.8 image. This remains CPU-only compute evidence: no ROS graph, Isaac, controller publisher, GPU or physical interface is launched.
