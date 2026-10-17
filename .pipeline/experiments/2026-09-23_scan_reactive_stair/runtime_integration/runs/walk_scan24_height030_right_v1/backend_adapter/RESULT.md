# P2B Backend Adapter Result

Status: backend_adapter library/core/PCT/gate/materializer slice is ready for lead's fresh `scan_02` build/probe. This is still not a completed ROS/Isaac pilot.

Implemented within owned `backend_adapter/**`:

- Native PCT JSON-line worker for the frozen Humble/PCT runtime, with serialized native planner calls, bounded socket handling, `optimize=true` enforcement, reference height 0.35 m, native optimizer height extraction, and display-Z delta validation before returning body-reference route Z.
- Foxy-side P2A backend port that uses measured start pose, calls real PCT IPC, submits only correlated routes, opens the gate only after matching SCAN acceptance, and keeps unknown/malformed/mismatched outcomes uncertain rather than fabricating success.
- Command gate for generation-tagged raw SCAN velocity remap with owner identity, heartbeat/odometry freshness, map epoch/revision, cancel/hold and stale old-generation suppression.
- Applied-command evidence verifier for the runner `current_command.json` schema, preserving sim step/time, command source timestamp, base pose and command observation error, and requiring causal post-cancel 1.0 sim-second dwell before stop release.
- Hash-gated SCAN overlay materializer with concrete messages and C++ changes. It adds typed `P2BRoute`, `P2BCancel`, `P2BAdmission.consumer` (`fsm` or `controller`) and `P2BStampedTwist`, propagates command identity route -> spline -> raw velocity, latches cancel tombstones/high-water generations, rejects late cancelled or stale splines/routes without overwriting current active identity, and disables legacy anonymous `/initial_path` in explicit P2B mode.
- Local regressions for malformed inputs, missing PCT worker, identity/mapping validation, causal stop evidence, consumer hold semantics and materializer smoke checks.

Lead-owned `scan_01` evidence showed the previous generated controller failed real Foxy probe checks for controller hold receipt, cancelled-generation resurrection, stale old cancel/spline disturbance and cancel-before-spline tombstone. The current materializer was updated after that evidence; do not use `scan_01` as the current candidate.

## Ready command for fresh lead build/probe

```bash
cd /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter
python3 -m backend_adapter.materialize_overlay \
  --source /Users/sun/tongbu/study/phdproject/vla/references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src \
  --output <fresh-scan-02-root>/src
```

The materializer refuses existing outputs and verifies pinned upstream hashes before copy. The generated source should be compiled/probed by lead-owned Foxy tooling.

## Verification run

Latest owned verification record: `checks/latest_verify.json` (`ok: true`, `owned_files: 20`, timestamp `20260916T152017Z`). It recorded these commands and return codes:

```text
/Users/sun/.openviking-venv/bin/python3 -m compileall -q /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/backend_adapter  # rc=0
/Users/sun/.openviking-venv/bin/python3 -m unittest discover -s /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/tests -v  # rc=0, 17 tests
/Users/sun/.openviking-venv/bin/python3 -m backend_adapter.run_adapter --config /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/config/p2b_adapter.example.json --print-contract  # rc=0
/Users/sun/.openviking-venv/bin/python3 -m backend_adapter.materialize_overlay --source /Users/sun/tongbu/study/phdproject/vla/references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src --output <temp>/src  # rc=0
```

Additional regression after the final materializer update:

```text
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/navigation_service/test_core.py
# 37 tests OK

python3 .trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/test_p2a_adversarial.py
# 21 tests OK
```

Reference hashes captured in `checks/latest_verify.json`:

```text
P2A core.py: 0fe9addf9f2901b38728b21e3e12485a14cf99dded989e6684dd8475397bef96
SCAN scan_replan_fsm.cpp: bb5fa854031ecb9a94fc9b3aeff0a225a48ff3bb81cefdc9f345659afcf285eb
SCAN closed_loop_controller.cpp: 32d3e2c75f3dc2177c496c30bd483d28791ba17685fe7c8a41b6ad909631fcd7
PCT planner_wrapper.py: 4b59fca5c67481edbe7f7040a74dde279d2bf382849773467da3c7b14818c8a8
Bridge run_pct_scan_building.py: 1490dc85146ce7ea71f05c4f5520639da1a342a13e9dfcd8ce0ba04f21c8a76b
Isaac runner SNAPSHOT_SCHEMA.md: bc5a7bdc3aaf82cebf3eed30943bc78ec91a9e334406b0090400121858ac87ae
```

Known remaining gaps:

- Lead still needs to materialize a fresh candidate, compile in real Foxy and rerun `p2b_execution/ros_controller_probe.py` against the current generated C++.
- The real rclpy/HTTP launch implementation has moved to a sibling `backend_ros/**` worker; `backend_adapter/ros_node.py` is retained as a reuse draft but is not the canonical completed runtime deliverable from this slice.
- No native PCT worker, ROS graph, Isaac process, V12 policy, simulator episode or physical interface was launched by this executor.
- Full two-goal persistent navigation acceptance still depends on lead-owned actual PCT worker launch, SCAN/controller probe pass, backend_ros runtime, Isaac runner external mode and raw run evidence.

## Addendum: actual PCT IPC and persistent stop API

A CPU-only PCT IPC qualification passed after the scan_03 materializer fix.

Local artifact directory:

```text
/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/qualification/pct_ipc_20260916T153430Z
```

Remote artifact directory:

```text
/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/backend_adapter_qualification/pct_ipc_20260916T153430Z
```

Results:

- Real `backend_adapter.pct_worker` process plus real `PctIpcClient` RPC ran in the PCT/Humble container `40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555` with `--network=none`.
- `goal-a`: 10 points, route id `pct:goal-a:aa3c91c3923f1df79b09`, endpoint XY error `0.0414953441391397` m.
- `goal-b`: 10 points, route id `pct:goal-b:8c1fa6ab9c37629dbd55`, endpoint XY error `0.045661226200165224` m.
- Worker verified wrapper display Z minus native optimizer height equals `0.5` before returning `lite3_body_reference_no_display_offset` route Z.
- Negative cases passed: `optimize=false` returned `PlannerRejected:pct_worker_requires_optimize_true_for_body_reference_z`; unavailable and timeout returned bounded `PlannerUnavailable:pct_worker_unavailable_or_timeout`.
- Foxy Python 3.8.10 ran owned tests in image `e4aa7154`: 17 tests OK for that qualification run.
- Returned result hashes matched remote hashes; see `sync_verdict.json`.

Persistent stop continuation is now implemented in `P2BBackendAdapter`:

- `stop(command, reason)` sends only the first correlated cancel/hold, records stop state and returns pending when controller hold or applied evidence is incomplete.
- `poll_stop(command)` continues the same stop state without resending cancel or resetting the post-cancel dwell window.
- Full command identity is stored before every submit, including pending/uncertain submissions, so cleanup stop uses the original map metadata even if the gate owner was not opened.
- Owned stop continuation regressions passed locally as part of 20 backend_adapter tests.

Latest verification after these changes:

```text
checks/verify_20260916T153845Z.json
backend_adapter verify: ok, owned_files=21
backend_adapter tests: 20 OK
P2A core tests: 37 OK
lead P2A adversarial tests: 21 OK
```

Source hashes from latest verify:

```text
materialize_overlay.py: 69954316fefce140574b26b54e2b76ad4a2148d01e7ca76c9effa8e10cbf0ce5
qualify_pct_ipc.py: bef45f04cd618ea04e8d3b7d93a3050546dece710b1c1398edbcae9bd4dbb69a
verify.py: fba52be8a662fe322bc69c73026544cbb16aa3f4590938f5b19365969c9fbd0a
```
