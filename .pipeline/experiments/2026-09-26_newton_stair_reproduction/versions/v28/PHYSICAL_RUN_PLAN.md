# v28 physical trial pre-registration

Written after the freeze and before any physics. This file is intentionally
outside the frozen manifest.

- **Run ID:** `v28_historical_full01`, through the local bounded supervisor
  `scripts/run_bounded.py` with a 1800 s deadline. All paths are absolute.
- **Profile:** exactly `v27_historical_full01`'s flags:
  - single executor, ZMQ applied transport, geometry obstacles;
  - `building_full` with the `historical_full` route;
  - goal wall budget 1500 s, `factory_pd` startup, stance hold.
- **What changes from v27:** only the native build (`scan60_constraint_guard_v28`),
  the planner YAML path (byte-identical copy) and the integration version.
- **Local simulation only:** no robot, no remote host, no training.

## Expected signals

- The integration-version, native-identity and reviewed-candidate gates pass
  before physics.
- The native SCAN process survives past v27's 13.24 s crash point, with no
  segmentation fault or abort in `scan.log` and no `native_failure.json` crash.
- The PCT route matches v26 and v27: 631 points, about 73.41 m, correct goal level.

## Acceptance

Acceptance is the unchanged Building review for the historical profile:

- native and driver arrival;
- goal XY and floor checks;
- the final PD hold of at least 2 s;
- no fall and continuous physics.

Anything less is recorded as a failure with its first failing gate.

## Failure signals

- A native crash or exit.
- No moving curves.
- Native replan exhaustion.
- `odom_stale`, `heartbeat_stale` or `command_timeout`.
- A fall, a wrong floor, or no progress.

## Diagnostic stop rule

Stop early only if the robot stays standing with less than 0.10 m net XY change
for at least 60 simulated seconds after startup. The stop goes through the
driver's SIGINT cancel and failed-finish flow, as in `v26_historical_full02`.
Such a stop is recorded as a failure, never as acceptance. Otherwise the run
continues to its own bounds.

## After the run

1. Run the local and Building reviews.
2. Render a recorded video whatever the outcome, labelled with the actual outcome.
3. Record `RESULTS.md` without changing any frozen file.
