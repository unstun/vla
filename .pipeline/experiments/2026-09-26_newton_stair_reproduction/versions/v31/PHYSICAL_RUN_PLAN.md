# v31 physical trial pre-registration

Written after the freeze and before any physics. This file is intentionally
outside the frozen manifest.

- **Run ID:** `v31_historical_full01`, through the local bounded supervisor
  `scripts/run_bounded.py` with a 1800 s deadline. All paths are absolute.
- **Profile:** exactly `v30_historical_full01`'s flags:
  - single executor, ZMQ applied transport, geometry obstacles;
  - `building_full` with the `historical_full` route;
  - goal wall budget 1500 s, `factory_pd` startup, stance hold.
- **What changes from v30:** only the native build
  (`scan64_input_refresh_v31`), the planner YAML path (a byte-identical copy)
  and the integration version.
- **Local simulation only:** no robot, no remote host, no training. No other
  container runs on the Docker VM during the trial.

## Expected signals

- **Before physics:** the integration-version, native-identity and
  reviewed-candidate gates pass.
- **Route:** the PCT route matches v26–v30: the historical profile, about
  73.4 m, and the correct goal level.
- **Up to the upper landing:** the climb and the upper-landing crossing behave
  like v30's.
- **Input refresh:** `scan.log` contains `input_refresh` lines.
  - The four inner sites (`target_check`, `replan_start`, `rebound_round`,
    `final_check`) log every call.
  - At the two timers, the lines that applied a stale input show cloud ages
    falling from above 0.15 s to below 0.12 s, and body-pose ages to below
    0.1 s.
- **Stale-input signatures,** counted with `versions/v31/trial_signatures.py`
  against v30's counts:
  - far fewer conflict stops at 0.000 s (v30: 63);
  - far fewer invalid-curve invalidations of the executing curve (v30: 89) and
    final-curve `InvalidCurve` rejections (v30: 131);
  - far fewer "inside an obstacle" messages followed by a blocked terminal
    point (v30: 48 of 53).
- **Measured, not predicted:**
  - within-step ageing: inner-site before-ages above the gates;
  - inputs stamped ahead of the clock: negative after-ages;
  - failed takes.
- **Not expected to change:** the collision rejections at the wrong-height
  navigation cell (47, 41), which v31 does not touch. The robot may still stop
  in the upper corridor there.

## Acceptance

Acceptance is the unchanged Building review for the historical profile:

- native and driver arrival;
- goal XY and floor checks;
- the final PD hold of at least 2 s;
- no fall and continuous physics.

Anything less is recorded as a failure with its first failing gate. Progress
past v30's final position, (−1.99, −4.25, body z 1.85), and the change in the
stale-input signatures are recorded separately; neither is acceptance.

## Known risks

- **Not addressed by v31:**
  - the wall-clock freshness class that ended v28 and v30 (`odom_stale`: the
    body-pose callbacks paused for more than 0.25 s of wall time);
  - the emergency-hold feedback;
  - the 13 cm protrusion choice;
  - the wrong-height navigation cell.

  Each of these can end the run.
- **Longer timer callbacks:** each safety callback that applies pending scans
  takes longer, in the pinned image on this Mac.
- **Within-step ageing:** several A* searches between two sites can still
  pass the pose gate; only `final_check` always sees the newest inputs.
- **Future stamps:** a body pose applied just before a decision, before the
  clock thread has processed its `/clock`, reads as stale.
- **Timing-dependent planning:** the A* 0.2 s wall-time budget makes planning
  outcomes differ from run to run, as the regression control showed for v30
  and v31 alike. One trial cannot separate v31's effect from this variation.

## Failure signals

- A native crash or exit.
- No progress past v30's corridor-entry pause.
- Native replan exhaustion.
- `odom_stale`, `heartbeat_stale` or `command_timeout`.
- A fall, a wrong floor, or any footprint placed off the walkway.

## Diagnostic stop rule

Unchanged from v30. Stop early only if the robot stays standing with less than
0.10 m net XY change for at least 60 simulated seconds after startup. The stop
goes through the driver's SIGINT cancel and failed-finish flow. Such a stop is
recorded as a failure, never as acceptance. Otherwise the run continues to its
own bounds.

## After the run

1. Run the local and Building reviews.
2. Render a recorded video whatever the outcome, labelled with the actual
   outcome.
3. Count the stale-input signatures with `trial_signatures.py` for v30 and v31.
4. Record `RESULTS.md` without changing any frozen file.
