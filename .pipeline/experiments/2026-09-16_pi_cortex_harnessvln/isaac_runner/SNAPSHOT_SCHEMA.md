# External Episode Snapshot Schema

This is the shared file contract between the patched Isaac runner and the
actual PCT/SCAN backend for the bounded two-goal pilot.

## Runner Output: `current_command.json`

The runner atomically replaces this compact JSON file in `--external-control-dir`
after each completed control step. A backend may read it repeatedly; a partially
written file should never be visible because the writer uses same-directory
temporary files and `os.replace`.

Required top-level fields:

```json
{
  "schema_version": 1,
  "run_id": "p2b-two-goal-001",
  "run_epoch_ns": 1234567890,
  "source": "run_pct_scan_building.py external-goal status snapshot",
  "output_dir": "/immutable/run/output",
  "sim_step": 42,
  "sim_time_s": 2.1,
  "wall_monotonic_s": 5.25,
  "wall_monotonic_ns": 9876543210,
  "sim_time_timestamp_ns": 2100000000,
  "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
  "admitted_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
  "raw_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
  "command_sequence": 17,
  "command_stale": false,
  "command_reason": "accepted",
  "command_source_timestamp_ns": 9876500000,
  "command_watchdog_events": 0,
  "command_sequence_gaps": 0,
  "measured": {
    "base_xyz": [-1.0, -4.0, 1.91],
    "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0],
    "horizontal_speed_mps": 0.01,
    "yaw_rate_radps": 0.01,
    "command_obs_error": 0.0
  },
  "state_epoch": {
    "state_sequence": 42,
    "telemetry_sequence": 100
  },
  "freshness": {
    "writer_monotonic_ns": 9876543210,
    "max_reader_age_s": 2.0,
    "atomic_replace": true
  },
  "clock_domains": {
    "sim_time_s": "Isaac simulation time relative to run_clock.simulation_origin_s",
    "sim_time_timestamp_ns": "Isaac absolute simulation time in ns",
    "wall_monotonic_ns": "same-host Python time.monotonic_ns",
    "command_source_timestamp_ns": "same-host monotonic_ns from command sender when present"
  }
}
```

Backend stop verification should require:

- matching `run_id`;
- fresh `wall_monotonic_ns` under `freshness.max_reader_age_s`;
- matching `run_epoch_ns` carried into the finish request;
- `math.hypot(applied_command.vx, applied_command.vy)` at or below the pilot
  stop command norm, plus `abs(applied_command.wz)` at or below the same norm;
- `measured.horizontal_speed_mps <= 0.10`;
- `abs(measured.yaw_rate_radps) <= 0.15`;
- `measured.base_xyz` and `measured.base_quat_wxyz` as the same-step world
  metric body pose from the physics row, using quaternion order `wxyz`;
- `measured.command_obs_error` to confirm the admitted command entered the
  policy observation at that step;
- command state evidence from `command_sequence`, `command_stale` and
  `command_reason`.

## Backend Output: `finish_request.json`

The backend writes this file after it has finished its goal lifecycle and has
independently confirmed cancellation/hold behavior from `current_command.json`.
The runner accepts and latches the first structurally valid request only when
the run identity and epoch match and the request is fresh on the same host
monotonic clock. The request file does not need to be refreshed during the
runner's local stillness dwell.

```json
{
  "schema_version": 1,
  "run_id": "p2b-two-goal-001",
  "request_id": "backend-unique-id",
  "observed_run_epoch_ns": 1234567890,
  "requested_at_monotonic_ns": 9876543210,
  "backend_terminal_status": "FINISHED"
}
```

`request_id` is a non-empty string. `observed_run_epoch_ns` and
`requested_at_monotonic_ns` are JSON integer numbers, not strings or booleans.
`backend_terminal_status` is either `FINISHED` or `FAILED`. After accepting the
request, the runner still waits locally for zero applied command and measured
stillness for `--external-finish-stillness-seconds` before returning
`EXTERNAL_EPISODE_FINISHED` or `EXTERNAL_EPISODE_FAILED`.

## Pilot Values

The frozen pilot file is:

`.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/inputs/pilot.json`

Relevant stop parameters:

- `stop_command_norm`: `0.01`
- `stop_speed_mps`: `0.10`
- `stop_yaw_rate_radps`: `0.15`
- `stop_dwell_sim_seconds`: `1.0`

The runner CLI remains configurable; the first pilot should pass
`--external-finish-stillness-seconds 1.0`.
