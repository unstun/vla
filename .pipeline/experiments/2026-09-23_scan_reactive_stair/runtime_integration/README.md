# SCAN reactive stair runtime overlay

Stage: experiment and analysis. Status: local preparation only. No simulator,
ROS graph, training, remote process, or robot has been started by this package.
This directory contains a prepare overlay and a bounded driver seam, not a
working ROS launcher. It pins the historical `scan_09` and `first_hit_v2`
identities. `scan_10` is a separate candidate and is not silently selected by
this overlay. The later `first_hit_v3/result.json` also reports `passed: false`
after dynamic mesh translation failed to move ray hits; an independently
passing first-hit and a newly reviewed package are required.

## Prepare and refusal

`prepare_runtime.py` makes a small source/configuration overlay under an explicit
output directory. It checks the frozen P2B input, bridge, and PCT manifests,
uses the existing two-goal launcher's SCAN source/install identity capture and
configuration writers, and copies only runtime files needed by the new seam.
The baseline `planner.yaml` is copied before adding the existing P2B typed-route
parameter; `use_sim_time: true` and `grid_map.cloud_is_world: false` are checked.
The frozen baseline is never edited. The SCAN 09 local source manifest and
remote install identity are recorded separately in `source_manifest.json`.

Prepared review artifact: `prepared/local_review_02/`. It is blocked by
`package_status.json` and `execution_gate.json`. `--execute` fails before any
network command. The single-goal driver also checks these gates before HTTP.
`prepared/local_review_01/` remains an immutable historical snapshot and
contains the earlier incorrect `SAFE_YIELD` label. Use `local_review_02` for
review of the corrected driver semantics; neither snapshot is executable.

The current route proposal starts the robot at `(-5.3, 2.0)` and the person at
`(-5.3, 1.4)`, only 0.60 m apart in XY. Initial conservative clearance is
0.18 m SCAN double-cylinder forward offset + 0.25 m robot radius + 0.30 m
person radius + 0.10 m review margin = 0.83 m. Both preparation and the driver
record or reject the overlap. The proposal has `geometry_reviewed: false`.
The actor source has `APPROVED_ROUTE_SHA256 = None`, and official-mesh first-hit
v2 failed inside Isaac's sensor update. None is an approved substitute.

## Existing launch seam

The reusable reference is
`../../2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py`:

| Reference function / location | Reuse and required change |
| --- | --- |
| `build_scan_workspace_gate`, `scan_workspace_gate` | Reuse exact `scan_09` source and installed-file maps before and after the run. The local installed tree is remote-only, so capture `install_identity.json` and verify both `src/` and `install/` on the host. |
| `make_scan_runtime_configs`, `make_bridge_config`, `make_backend_config` | Reused for runtime copies. A reviewed stair spawn/goal and backend map epoch must replace two-goal pilot inputs; never edit `baseline_config/`. |
| `verify_input_manifest`, `verify_bridge_source`, `verify_pct_runtime_manifest` | Reused at preparation. Recheck package hashes on the host before starting a process. |
| `remote_worker_source` | Cannot execute this episode as written: it launches the two-goal runner/driver and lacks terrain topic and tracker processes. A small reviewed replacement worker is required. |
| `execute`, `verify_returned_artifacts` | Follow the mkdir/sync/run/collect/finally collection pattern. Return all artifact logs, source/install gates and `artifact_hashes.json`; compare local returned SHA-256 values. |

The replacement worker should use a new unique remote directory and bound the
entire run to 1,200 wall seconds and 45 simulation seconds. Check the pinned
Foxy image `e4aa7154...` and Humble image `40f0fa16...` by full image ID.
Use one `ROS_DOMAIN_ID=192`, host network and host IPC for the bridge, SCAN,
backend, tracker, and terrain sidecar. The bridge publishes `/clock`; wait for
advancing positive clock samples. The Humble sidecar publishes one latched
`/pct_tomogram` from the pinned Building pickle. The Foxy
`scan_reactive_tracker moving_cluster_tracker` consumes current paired
`/quad_0/cloud` and `/quad_0/lidar_pose` plus that terrain topic, and publishes
`/tracked_person_snapshot`. The socket `backend_adapter.pct_worker` remains
separate and must not create a second terrain topic publisher. SCAN planner,
controller and backend must use the copied config and the verified `scan_09`
install. Require a fresh health record with live process state, one publisher,
clock/terrain/cloud/pose/track stamps, and paired cloud/pose stamps before
`single_goal_driver.py` posts a goal.

The Isaac source candidate `runner/run_pct_scan_building.py` requires an
official asset root, official retarget cache, reviewed source-pinned actor
route, and `--unfiltered-planner-cloud`. Its actor truth JSONL is scoring only;
no actor pose or velocity is sent to the planner or tracker. An approved
robot spawn and one reviewed ground goal are still required. No velocity
extrapolation, trajectory prediction, or time-indexed search belongs in this
worker. A stale or incomplete track should lead to stop or failed episode,
with the reason retained.

Each started process/container needs a unique owned name/PID and a `finally`
cleanup in reverse order. Never kill by broad process name. Record start and
exit status, stdout/stderr, ROS topic stamps, SCAN correction and 50 ms safety
events, backend request and applied-command snapshots, runner sensor metrics,
official human truth, route completion or measured deadline stop, robot fall and
contact evidence, and before/after source/install hashes. Compare returned
artifact hashes after syncing to the local experiment path even on failure.
Isaac's current official visual has no validated physical human contact; video
or proximity alone cannot be reported as contact validation.

## Claim boundary

The driver contains the one-goal backend request, a wall/simulation deadline,
an explicit cancel on deadline, and a measured stillness dwell. That path is
reported as `DEADLINE_STOPPED`, with a failed finish request. It is not evidence
of pedestrian avoidance. A future `SAFE_YIELD` assessment requires a current
obstacle observation linked to a SCAN correction/stop event by simulation
timestamps and separate outcome review. The driver reads only backend/robot
observations and worker topic health. A complete empty current track snapshot
is valid; whether a person was ever seen belongs in separate scoring over
returned sensor logs. The backend's actual terminal ledger uses lowercase
`arrived`, `cancelled`, `failed`, `stopped`, and `rejected` statuses
(`backend_ros/p2b_backend_ros/runtime.py`); the driver compares lowercase
`arrived` and `cancelled`. It does not score actor separation or contact;
those require an offline outcome evaluator over returned simulator truth and
sensor/SCAN logs. Preparation and local tests establish no SCAN correction,
fall, contact, yield, or route outcome.
