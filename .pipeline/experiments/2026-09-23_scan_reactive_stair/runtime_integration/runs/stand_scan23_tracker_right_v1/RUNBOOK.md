# P2B two-goal pilot prepared package

Run id: `stand_scan23_tracker_right_v1`
Remote run root: `/home/sun/vla_exec/2026-09-26_stair_video/stand_scan23_tracker_right_v1`

This package is prepared for the actual P2B two-goal diagnostic pilot. It is not a completed run and it is not navigation evidence until executed after lead approval.

Claim boundary if later executed and accepted: known-map + truth-pose diagnostic integration of patched Isaac runner, native V12 policy, real Foxy bridge, real Humble PCT worker, real Foxy SCAN/controller, backend_adapter and backend_ros. It does not include an actual LLM, Cortex planner, SLAM, or physical robot interface.

Runtime sequence encoded by `remote_worker.py`:

1. Start device-wide GPU sampling (`artifacts/gpu_samples.jsonl`, every 1 s). Verify package, frozen inputs, patched bridge, local PCT runtime files, V12 runtime and checkpoint hashes, then hash the mounted SCAN workspace `src/` and `install/` trees against the accepted build identity (`artifacts/scan_workspace_gate.json`) and refuse on any difference.
2. Confirm localhost ports are free and owned container names are absent.
3. Start the Foxy bridge only.
4. Start one Isaac runner with `--case flat_nominal` and `--external-goal-mode`.
5. Read fresh `current_command.json` to capture the runner `run_epoch_ns`.
6. Start the Humble PCT worker.
7. Start SCAN, controller and backend_ros using that `run_epoch_ns`; it does not start a second bridge.
8. Run `pilot_driver.py`: POST goal-a attempt 1, cancel after at least 0.4 m measured displacement, require explicit cancelled plus post-cancel stop proof, POST goal-a attempt 2 and require arrived, POST goal-b and require arrived, then write the valid finish request.
9. After cleanup, re-hash the SCAN workspace (`artifacts/scan_workspace_gate_after.json`) and record the GPU peak and remote wall time in `artifacts/result.json`.

HTTP contract used by the driver:

- `GET /state`
- `POST /goal` with `request_id`, `goal_id`, `target_ground_xyz`, `frame`, `map_epoch`, `map_revision`
- `POST /cancel` with a new `request_id` and, for the planned cancel, `target_request_id`

Owner `None` alone is logged but never treated as success. The finish request is written as `FINISHED` only after explicit terminal records for one cancel and two arrivals. Failure paths attempt cancel/hold, write a `FAILED` finish request, preserve logs and return nonzero.

Stance hold (`--stance-hold auto`): the patched runner hands the joints from the V12 policy to a PD stand hold (Kp 60 / Kd 1) after an exactly zero command with a quiet, loaded and balanced four-foot stance, and blends back over 0.25 s when a command arrives (`isaac_runner/stance_hold.py`). The runner writes `runner_output/stance_hold_setup.json`, per-step `stance_*` fields in `metrics.jsonl` and a `stance_hold` summary block. `isaac_runner/analyze_stance_hold.py` reports the AC5 transition checks; the 41 review checks are unchanged.

Entry variant: `--stance-entry-kd xfade1s` (`stance_hold.py` `STANCE_ENTRY_KD_MODES`; recorded in `run_request.json` and the runner summary `stance_hold.entry_kd`).
