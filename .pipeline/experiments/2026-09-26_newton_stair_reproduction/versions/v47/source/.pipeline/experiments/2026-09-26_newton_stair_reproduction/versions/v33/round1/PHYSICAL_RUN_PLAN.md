# v33 live run: pre-registration

Written before the freeze and before any v33 physics. `PLAN.md` states the change, the checks and the claim
boundary. This file fixes how the single trial is executed.

## The run

- **Run:** `v33_historical_full01`, through `scripts/run_bounded.py --run-id v33_historical_full01 --deadline 1800`
  around `scripts/run_local_episode.py`.
- **Flags:** exactly `v32_historical_full01`'s, except the integration version and the planner-YAML copy:
  - `--backend-executor single`, `--applied-transport zmq`, `--geometry-obstacles`;
  - `--native-build runtime/scan64_input_refresh_v31` (unchanged);
  - `--scene building_full`, `--building-route historical_full`, `--goal-wall-budget 1500`;
  - `--startup-mode factory_pd`, `--stance-hold`;
  - `--planner-config versions/v33/building_planner.yaml`, a byte-identical copy of v32's;
  - `--integration-version v33`.
- **Version gate:** `run_local_episode.py` checks every file in v33's manifest before physics, the three gate
  files included.
- **Local simulation only:** no robot, no remote host, no training.

## A quiet host

- **Before the run:**
  - `docker ps` lists no container, and no analysis, render or build from this project runs.
  - Dr Sun is asked to pause the other Claude session's activity in `machine-dog`. Its session-diff refreshes run
    `git diff --numstat` there, up to six processes at once, during v32's trial.
  - The run starts only after he confirms.
- **During the run:** `audits/2026-09-29_wall_clock_chain/host_sampler.py` records the host once a second, to
  `versions/v33/host/v33_historical_full01_host.jsonl`.
- **If git activity in `machine-dog` still appears,** it is recorded, not acted on. The run is not restarted.

## What is recorded

- **Acceptance:** the unchanged Building review for the historical profile, and the local review.
- **The gate:**
  - whether `odom_stale` occurs;
  - if it does, whether the simulation age or the backstop tripped it, from the backend's status fields
    (`odom_time_base`, `sim_clock_s`, `last_body_pose_sim_age_s`, `last_body_pose_age_s` in
    `backend_states.jsonl`) and the fault record;
  - the distributions of simulation age and wall age in the status samples;
  - the wall and simulation gaps between body-pose callbacks (`backend_body_callbacks.jsonl`, the survey's
    method).
- **Watched, unchanged:**
  - any `heartbeat_stale`, `initial_heartbeat_missing` or `applied_evidence_stale`;
  - clock-sync rejections, TTL windows and reconnects;
  - the bridge's stall counters.
- **Navigation:**
  - where the robot stops;
  - SCAN's signatures (`versions/v31/trial_signatures.py`);
  - the corridor-entry check (`versions/v32/corridor_entry_curves.py`).
- **Videos:** the standard view and the heading-follow view, as for v32.

## Expected, not criteria

- **Where the robot stops:** with the wrong-height cell unfixed until v34, it is likely to stand at the upper
  corridor entry.
- **How the run ends:** by the 600 s physics limit, the 1500 s goal wall budget or the 1800 s deadline. It ends
  on `odom_stale` only if a pose stream truly stops, or the simulator stops for more than 2.0 s of wall time.
- **Commands during stalls:** stalls still delay commands, and the Mac side's own command-staleness rule still
  zeroes a stale command.

## Stop rule

- **One run, not repeated for a better outcome.**
- **An `odom_stale` from the backstop or the simulation age** is recorded with its cause and investigated from
  the saved records before anything else changes.
