# New-endpoint physical adapter seams

Read-only local source inspection, 2026-10-18. No new physical attempt.

## Existing capabilities

- versions/v40/physics/robot_scene_v40.py:44–62 reads spawn_ground_xyz_m
  and spawn_yaw_rad from the per-run scenario. Factory crouch remains ground
  plus 0.14 m; initialization is a new run, not a mid-run teleport/reset.
- versions/v198/newton_episode.py:55–58 passes the scenario to StairRobot.
- versions/v232/long_route_driver.py:47–48,68–75 reads goal_ground_xyz_m.
  Existing measured PD startup, native arrival/health/failure closure and final
  measured PD suffix remain reusable. The driver does not pass target_yaw_rad;
  keep the route-terminal-tangent yaw contract for this evaluation.

## Restrictions to adapt in new owned versions

- v196/run_local_episode.py:52–69,82,165–167 accepts a fixed profile enum
  and binds historical_full to its original scenario SHA. Inject a per-case
  frozen-scenario loader in a new adapter; do not change the historical source.
- v241/launch.py binds version/run/container/task/ledger and historical_full.
  New IDs and exactly-one-per-case ledgers are necessary for the new binding.
- v232/native_graph.py:84–87 clears backend.map.pct_layer only for
  historical_full/corner_start. The new profile must enter this cross-floor
  branch; otherwise it accidentally fixes navigation to one map layer.
- audits/2026-10-18_v240_gpu5070ti_physical/verify_full_route.py:18–27
  hardcodes historical endpoints/profile. Replace the expected scenario
  identity only, retaining initial-state, continuous motion, no-fall, actual
  requested goal, shared-state, endpoint and measured PD checks.

## Preflight, scheduling and uncertainty

v237/probe_scans.py currently uses an old v233 physical state. That is useful
scanner parity evidence but does not establish a new spawn's observed space.
Capture the current case's geometric rays and paired pose with zero physics
steps for its preflight; never translate old point clouds to a new start.
v237 scanner repair retains the absolute 0.1 s wall deadline and source stamps.

Reuse serial v241 resource bounds and fixed ports: 6 CPU/6 GiB native, CPU
Warp physics, one scanner, original 600 s physical/900 s supervisor caps.
Run rendering after physical execution. No other job/container mutation.

Prior direct physical evidence covers ascent on the historical route only.
No reverse cross-floor pass was found in the inspected v216/v219/v220/v232/
v233/v237/v240/v241 records. Downstairs capability is an evaluation question.
Frozen-RL failure must remain visible rather than being repaired by changing
guards, pre-setting routes, moving the robot or repeating until success.

Use geometry/progress to identify new-route stair and approach windows; raw
45–55/109–115 s windows are supplemental when those times are reached, not
definitions of where a new route's stairs or destination actually lie.
