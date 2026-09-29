# v33 live run: pre-registration

Written before the freeze and before any v33 physics. It was revised after independent review rounds 1 to 4, all
still before any v33 physics. `PLAN.md` states the change, the checks and the claim boundary. This file fixes
how the single trial is executed and analysed.

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
- **Gates before physics:**
  - `run_local_episode.py` checks every file in v33's manifest. That includes the three gate files and, from
    review round 2 (N9), the seven files of `config_archived/`. The trial loads three of them: `bridge.yaml`,
    `controller.yaml` and `p2b_backend_ros.two_goal.json`. Its planner configuration is the v33 copy passed by
    `--planner-config`.
  - It then re-hashes every record of `setup/runtime_sources.json` and refuses the run on a mismatch. v33
    updates that record for its three runtime files, and `record_check.py` shows the check passing on the v33
    bytes.
  - The native-identity and reviewed-candidate gates are unchanged.
- **Local simulation only:** no robot, no remote host, no training.

## A quiet host

- **Before the run:**
  - `docker ps` lists no container, and no analysis, render or build from this project runs.
  - Dr Sun is asked to pause the other Claude session's activity in `machine-dog`. Its session-diff refreshes ran
    `git diff --numstat` there, up to six processes at once, during v32's trial.
  - The run starts only after he confirms.
- **During the run:** `audits/2026-09-29_wall_clock_chain/host_sampler.py` records the host once a second, to
  `versions/v33/host/v33_historical_full01_host.jsonl`.
- **If git activity in `machine-dog` still appears,** it is recorded, not acted on. The run is not restarted.

## What is recorded

The status samples in `backend_states.jsonl` are written every 5 control steps. That is 10 Hz of simulated time;
in `v32_historical_full01` the median wall interval was 0.22 s, about 4.6 Hz (review round 2, N7). Every pose
wall gap below means an interval over 0.25 s between consecutive callbacks in `backend_body_callbacks.jsonl`.

- **Acceptance:** the unchanged Building review for the historical profile, and the local review.
- **Exposure** (review round 1, N4; tightened in round 2, N2): the pose wall gaps during which the gate was
  evaluating the pose rule. A gap counts when all three conditions hold:
  1. **Admitted and open:** the newest status sample whose `data.gate.last_measurement.monotonic_s` (the
     backend's clock, as `entered_ns`) is at or before the gap's start is at most 0.5 s older than the gap's
     start, and it shows `data.gate.owner` set and `data.gate.closed_reason` `open`. With no such sample within
     0.5 s, the gap is "unknown".
  2. **No stop flow before it:** no sample shows a `data.stop_flow.started_monotonic_s` at or before the gap's
     start.
  3. **Heartbeat fresh and the backend evaluating** (tightened in round 3, N2): the observer's `raw_command`
     stream (SCAN's output) and its `gated_command` stream (the backend's) both have no interval over 0.20 s
     overlapping the gap. `artifacts/reactive_observations.jsonl` holds both streams.

  Counts are reported as exposed, not exposed and unknown. A gap that fails condition 2 or 3 is not exposed, even
  when condition 1 is unknown. A gap that meets 2 and 3 with condition 1 unknown is unknown. With no exposed gap,
  the run says nothing about the gate's tolerance of stalls, whatever its outcome.
- **The stalled-pose-path flag** (Dr Sun's decision after review round 1; refined in round 2, N4):
  - **Measure 1, pose path:** for every pose wall gap, the simulated-time advance from the pose before the gap to
    the newest pose delivered within 50 ms after it (`evidence/clock_lead_survey.py`'s method).
  - **Measure 2, independent of the pose path:** the physics-time advance over the gap from `applied_sent.jsonl`.
    That is the physics time of the newest step started by the gap's end, minus that of the newest step started
    by its start, with a resolution of one control step (0.02 s).
  - **A terminal gap** (no pose after it, for example when the run ends inside the stall) is measured by
    measure 2 up to the stop flow's start or the last step, whichever is first.
  - **The flag:** a gap is flagged when either measure exceeds 0.25 s. That shows physics ran while the backend's
    pose was frozen, not what physics received.
  - **For each flagged gap:** the commands physics received are reported, from `telemetry.jsonl` (`command`,
    `command_reason`) and from the observer's `gated_command` stream. The run's claims are qualified by any
    flagged gap. The other advances are reported as distributions.
- **The gate:**
  - whether `odom_stale`, `applied_evidence_stale` or `heartbeat_stale` occurs, from `data.stop_flow.reason` and
    the terminal results;
  - **the cause of an `odom_stale` end** (review round 2, N3; corrected in round 3, N1):
    - **The trip lag:** `data.stop_flow.started_monotonic_s` minus the start of the newest pose gap over 0.25 s
      that contains it or ended at most 0.1 s before it. The runtime's monitor thread polls the gate every
      50 ms, so a stop flow can start just after the gap ends; recorded ones started up to 41 ms after.
    - **The classification:** a lag of at least 2.0 s is the backstop, a shorter one the simulation age. The
      backstop trips only after 2.0 s, and the stop flow can only follow the trip.
    - **Cross-check:** the observer's `clock_ns` at the stop flow's start, minus the stamp of the pose before the
      gap. It is the proxy for the backend's `/clock`, whose receipts are not logged (`native_backend_entry.py`
      wraps only the pose callback);
    - **No qualifying gap** (review round 4, N2): if no pose gap over 0.25 s contains the stop flow's start or
      ended at most 0.1 s before it, the cause is reported as unattributed, with the observer cross-check;
  - **a backstop end:** without `applied_evidence_stale`, it is read as a stalled pose path with physics running
    (round 2, N1), and it is checked with measure 2;
  - the status fields `odom_time_base`, `sim_clock_s`, `last_body_pose_sim_age_s` and `last_body_pose_age_s`
    (`data.scan_port`);
  - the distributions of simulation age and wall age in those samples. Negative simulation ages (the clock a step
    behind the pose) are clamped at 0, as the gate does; the raw minimum is reported (review round 1, N8);
  - the wall and simulation gaps between body-pose callbacks (the survey's method).
- **Watched, unchanged:**
  - any `heartbeat_stale`, `initial_heartbeat_missing` or `applied_evidence_stale`. A `heartbeat_stale` end is
    read as a backend-side stall and checked against the observer's `gated_command` and `raw_command` gaps
    (`PLAN.md`, claim boundary). The `/clock` subscription adds load to the backend's executor, and the
    heartbeat is what would show it;
  - clock-sync rejections, TTL windows and reconnects;
  - the bridge's stall counters.
- **Navigation:**
  - where the robot stops;
  - SCAN's signatures (`versions/v31/trial_signatures.py`);
  - the corridor-entry check (`versions/v32/corridor_entry_curves.py`).
- **Videos:** the standard view and the heading-follow view, as for v32.
- **A known inaccuracy, not a deviation:** `run_local_episode.py` writes the fixed text "original sensor/command
  freshness watchdogs" into every `episode_request.json` (line 230). For v33 runs the body-pose watchdog is the
  simulation base. RESULTS notes it; the script is not changed (review round 1, N6).

## How the analysis writes its outputs (review round 2, N5)

- **Where outputs go:** every post-trial tool runs from a copy in the session scratch directory, or with its
  output path redirected, and writes run-named outputs under `runs/v33_historical_full01/` or
  `versions/v33/analysis/`. None rewrites a file in v33's manifest or a committed output. Known fixed-name
  writers:
  - `ttl_windows.py` writes `audits/2026-09-29_wall_clock_chain/ttl_windows.json`, which is pinned; it is
    redirected as for v32;
  - `versions/v32/corridor_entry_curves.py` writes the committed `corridor_entry_curves.json`;
  - `evidence/clock_lead_survey.py`, `evidence/pose_gap_survey.py` and `replay_gate.py` write inside `versions/v33`.
- **After the analysis,** v33's manifest is re-verified against disk, and 0 mismatches are expected.

## Expected, not criteria

- **Where the robot stops:** with the wrong-height cell unfixed until v34, it is likely to stand at the upper
  corridor entry.
- **How the run ends:** by the 600 s physics limit, the 1500 s goal wall budget or the 1800 s deadline. Other
  possible ends:
  - **`odom_stale` by the simulation age:** poses stop reaching the backend while `/clock` keeps advancing past
    them by 0.25 s of simulated time.
  - **`applied_evidence_stale`:** the worker's applied snapshots stop refreshing for 2.0 s. That happens when the
    simulator stops (it comes just before the backstop; `PLAN.md`), during a clock-sync outage of that length, or
    when the applied channel stalls.
  - **`odom_stale` by the backstop:** the backend's pose and `/clock` stay frozen for 2.0 s while the applied
    snapshots stay fresh, which is a stalled pose path with physics running.
  - **`heartbeat_stale`:** the backend itself stalls for more than 0.20 s.
- **Commands during stalls:**
  - Stalls still delay commands.
  - The Mac side's command-staleness rule zeroes a command that stops arriving, and the bridge zeroes its command
    0.25 s after the newest one it received.
  - In a stalled pose path before the bridge's ROS thread, commands from a frozen pose keep flowing until the
    backstop, for up to 2.0 s of wall time (`PLAN.md`, "What the simulation base means").

## Stop rule

- **One run, not repeated for a better outcome.**
- **Investigated from the saved records before anything else changes:** an `odom_stale` from the backstop or the
  simulation age, or a flagged gap, is recorded with its cause.
