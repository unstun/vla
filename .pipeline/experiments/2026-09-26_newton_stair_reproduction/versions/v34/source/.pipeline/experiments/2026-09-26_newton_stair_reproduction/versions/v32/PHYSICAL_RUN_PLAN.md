# v32 live runs: pre-registration

Written before the freeze and before any v32 physics, and revised after review rounds 1–3 (only the
attribution wording and the L1 rules changed). `PLAN.md` states the checks and pass criteria. This file fixes
how the two runs are executed.

## Order and profile

- **Order:**
  1. **L1, `diag_v32_clock01`.** This is the diagnostic run. It uses
     `audits/2026-09-29_wall_clock_chain/diag_launch.py` under `scripts/run_bounded.py`, with the same
     worker instrumentation and container-side observation as described in `PLAN.md`.
  2. **L2, `v32_historical_full01`.** This is the trial. It runs `scripts/run_local_episode.py` directly
     under `scripts/run_bounded.py`, with no instrumentation.
- **Profile, identical for both:** exactly v31_historical_full01's flags:
  - single executor, ZMQ applied transport, geometry obstacles;
  - `building_full` with the `historical_full` route;
  - goal wall budget 1500 s, `factory_pd` start-up, stance hold;
  - native build `runtime/scan64_input_refresh_v31` (unchanged);
  - planner YAML `versions/v32/building_planner.yaml`, a byte-identical copy of v31's;
  - `--integration-version v32`.
- **Deadline:** 1800 s for each run.
- **Local simulation only:** no robot, no remote host, no training.
- **A quiet host:**
  - Before each run, `docker ps` must list no container.
  - Nothing else from this project runs during a run: no analysis, render or build.
  - Other applications on the Mac are not controlled, and their load is recorded only in L1's host
    samples.

## What may differ from v31, and what may not

- **Changed:** only `scripts/newton_episode.py` (three insertions) and the integration version.
- **Unchanged:** the physics inputs, the scene, the sensor, the planner, the bridge, the backend and every
  gate.

## Expected signals

- **L1 is judged exactly as `PLAN.md` defines it, by `l1/evaluate_l1.py` (written before L1 ran):**
  - **Exposure:** at least 7,100 control steps, otherwise the run is inconclusive.
  - **Watchdog log:** if the wake-up log does not span the loop, L1 is inconclusive.
  - **In the Mac worker:** within the loop, no automatic full collection and no collection over 20 ms.
  - **Holds:** no process-wide hold by the watchdog rule (*W* − *w* > 110 ms), whether in a step or
    between steps.
  - **Intervals:** every interval is reported with its class. The classes are exhaustive, and the rules
    were checked on synthetic records before L1 (`l1/synthetic_check.json`).

  L1 also records the delivery path from end to end:
  - each telemetry frame's enqueue and send time in the worker;
  - the bridge's receive and delivery time for each body state;
  - the bridge's publish-callback durations;
  - each container Python process's collections.

  `audits/2026-09-29_wall_clock_chain/analyze_pipeline.py` splits each large gap into the pre-registered
  segments and blames each superseded pose by the fixed rule.
- **L2 is judged by the Building review.** Recorded for it:
  - whether and when `odom_stale` occurs;
  - the largest body-pose gaps, with an attribution to A or B that can only be an inference, because L2
    is not instrumented;
  - clock TTL windows, reconnects and peak RSS;
  - the stale-input signatures (`versions/v31/trial_signatures.py`), for comparison with v31.
- **Likely stop:** the known corridor-entry stop, from the wrong-height navigation cell, is likely. Both
  v31-configuration diagnostic runs stood there. Such a stop is not evidence for or against v32, which does
  not touch navigation.

## Stop rule

- **Each run ends by itself:** by `odom_stale`, the 600 s physics limit, the goal wall budget, or the
  supervisor deadline.
- **No repetition:** a run is not repeated to get a better outcome, and a failed L1 is recorded as failed.
- **L2 still runs after a failed L1,** because L2 is the version's trial either way. Its result is then read
  with L1's evidence.
- **Videos:** L2 is rendered like v31 (standard view and heading-follow view). L1 is not rendered.
