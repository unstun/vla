# v29 physical trial pre-registration

Written after the freeze and before any physics. This file is intentionally
outside the frozen manifest.

- **Run ID:** `v29_historical_full01`, through the local bounded supervisor
  `scripts/run_bounded.py` with a 1800 s deadline. All paths are absolute.
- **Profile:** exactly `v28_historical_full01`'s flags:
  - single executor, ZMQ applied transport, geometry obstacles;
  - `building_full` with the `historical_full` route;
  - goal wall budget 1500 s, `factory_pd` startup, stance hold.
- **What changes from v28:** only the native build (`scan61_sensor_column_v29`),
  the planner YAML path (byte-identical copy) and the integration version.
- **Local simulation only:** no robot, no remote host, no training.

## Expected signals

- The integration-version, native-identity and reviewed-candidate gates pass
  before physics.
- The PCT route matches v26-v28: the historical profile, about 73.41 m, and the
  correct goal level.
- The walking start no longer ends in the permanent hold that v28 entered at
  12.691 s. Replans from the lowered walking pose keep producing moving curves,
  so there is more than one moving curve and route progress beyond v28's
  4.3 cm.

## Acceptance

Acceptance is the unchanged Building review for the historical profile:

- native and driver arrival;
- goal XY and floor checks;
- the final PD hold of at least 2 s;
- no fall and continuous physics.

Anything less is recorded as a failure with its first failing gate.

## Known risk

v29 does not touch the wall-clock freshness chain that ended v28 at 15.56 s:
clock-sample rejection, then a command reconnect stall, then the 0.25 s
`odom_stale` gate. The run may end the same way. That is recorded as a failure
of this trial, separately from whether the start thrash is gone.

## Failure signals

- A native crash or exit.
- No moving curves, or only one.
- Native replan exhaustion.
- `odom_stale`, `heartbeat_stale` or `command_timeout`.
- A fall, a wrong floor, or no progress.

## Diagnostic stop rule

Unchanged from v28. Stop early only if the robot stays standing with less than
0.10 m net XY change for at least 60 simulated seconds after startup. The stop
goes through the driver's SIGINT cancel and failed-finish flow, as in
`v26_historical_full02`. Such a stop is recorded as a failure, never as
acceptance. Otherwise the run continues to its own bounds.

## After the run

1. Run the local and Building reviews.
2. Render a recorded video whatever the outcome, labelled with the actual
   outcome.
3. Record `RESULTS.md` without changing any frozen file.
