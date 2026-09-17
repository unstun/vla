# P2B two-goal pilot prepared package

Run id: `two_goal_20260916T155805Z_p2b_actual1`
Remote run root: `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/two_goal_pilot/two_goal_20260916T155805Z_p2b_actual1`

This package is prepared for the actual P2B two-goal diagnostic pilot. It is not a completed run and it is not navigation evidence until executed after lead approval.

Claim boundary if later executed and accepted: known-map + truth-pose diagnostic integration of patched Isaac runner, native V12 policy, real Foxy bridge, real Humble PCT worker, real Foxy SCAN/controller, backend_adapter and backend_ros. It does not include an actual LLM, Cortex planner, SLAM, or physical robot interface.

Runtime sequence encoded by `remote_worker.py`:

1. Verify package, frozen inputs, patched bridge, local PCT runtime files, V12 runtime and checkpoint hashes.
2. Confirm localhost ports are free and owned container names are absent.
3. Start the Foxy bridge only.
4. Start one Isaac runner with `--case flat_nominal` and `--external-goal-mode`.
5. Read fresh `current_command.json` to capture the runner `run_epoch_ns`.
6. Start the Humble PCT worker.
7. Start SCAN, controller and backend_ros using that `run_epoch_ns`; it does not start a second bridge.
8. Run `pilot_driver.py`: POST goal-a attempt 1, cancel after at least 0.4 m measured displacement, require explicit cancelled plus post-cancel stop proof, POST goal-a attempt 2 and require arrived, POST goal-b and require arrived, then write the valid finish request.

HTTP contract used by the driver:

- `GET /state`
- `POST /goal` with `request_id`, `goal_id`, `target_ground_xyz`, `frame`, `map_epoch`, `map_revision`
- `POST /cancel` with a new `request_id` and, for the planned cancel, `target_request_id`

Owner `None` alone is logged but never treated as success. The finish request is written as `FINISHED` only after explicit terminal records for one cancel and two arrivals. Failure paths attempt cancel/hold, write a `FAILED` finish request, preserve logs and return nonzero.
