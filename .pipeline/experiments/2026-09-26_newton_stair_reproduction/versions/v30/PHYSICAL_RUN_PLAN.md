# v30 physical trial pre-registration

Written after the freeze and before any physics. This file is intentionally
outside the frozen manifest.

- **Run ID:** `v30_historical_full01`, through the local bounded supervisor
  `scripts/run_bounded.py` with a 1800 s deadline. All paths are absolute.
- **Profile:** exactly `v29_historical_full01`'s flags:
  - single executor, ZMQ applied transport, geometry obstacles;
  - `building_full` with the `historical_full` route;
  - goal wall budget 1500 s, `factory_pd` startup, stance hold.
- **What changes from v29:** only the native build
  (`scan62_support_evidence_v30`), the planner YAML path (a byte-identical
  copy) and the integration version.
- **Local simulation only:** no robot, no remote host, no training.

## Expected signals

- The integration-version, native-identity and reviewed-candidate gates pass
  before physics.
- The PCT route matches v26–v29: the historical profile, about 73.4 m, and the
  correct goal level.
- The start behaves as in v29: few start replans, moving within seconds of the
  RL handoff.
- The frozen-state replays predict that the reference frontier passes 8.6446 s
  on the upper landing. The robot should move past its v29 stop at
  (−5.00, −2.45, body z 1.70), into the corridor towards +x.

## Acceptance

Acceptance is the unchanged Building review for the historical profile:

- native and driver arrival;
- goal XY and floor checks;
- the final PD hold of at least 2 s;
- no fall and continuous physics.

Anything less is recorded as a failure with its first failing gate. Progress
past the v29 stop is recorded separately; it is not acceptance.

## Known risks

v30 does not touch the wall-clock freshness chain that ended v28 (`odom_stale`),
the emergency-hold feedback or the 13 cm protrusion choice. It changes 7,873
support labels across the Building. Each of these can end the run, and any
later stall is diagnosed separately.

From `PLAN.md`'s risks widened after the independent review:

- **No drop test.** Under v30 the Building has no Unknown or Unsupported
  navigation layer, so this trial cannot test drop handling. Walkway edges
  rely on PCT's selection margin and on LiDAR occupancy. Passing it says
  nothing about drops.
- **Different planning from v29.** A* candidates, seeds and optimizer attempts
  differ from v29 even where the saved-state results are identical. Replan
  counts and latency may differ.
- **Startup rescoring.** The evidence arrives once and triggers one full-map
  rescoring on the planner's executor, about 72 ms in the pinned image on this
  Mac.

## Failure signals

- A native crash or exit.
- No progress past the v29 landing stop.
- Native replan exhaustion.
- `odom_stale`, `heartbeat_stale` or `command_timeout`.
- A fall, a wrong floor, or any footprint placed off the walkway.

## Diagnostic stop rule

Unchanged from v29. Stop early only if the robot stays standing with less than
0.10 m net XY change for at least 60 simulated seconds after startup. The stop
goes through the driver's SIGINT cancel and failed-finish flow. Such a stop is
recorded as a failure, never as acceptance. Otherwise the run continues to its
own bounds.

## After the run

1. Run the local and Building reviews.
2. Render a recorded video whatever the outcome, labelled with the actual
   outcome.
3. Record `RESULTS.md` without changing any frozen file.
