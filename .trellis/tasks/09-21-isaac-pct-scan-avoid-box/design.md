# Design: one walk around the unmapped box

## Architecture

Keep the two-goal process split. Add a separate launcher and a one-goal
driver. Do not change `run_two_goal_pilot.py`’s cancel sequence or
`pilot.json`.

```
Isaac run_pct_scan_building
  --case flat_nominal --external-goal-mode
  --unmapped-box lidar --lidar-pattern-mode livox_mid360
  spawn = pilot.json spawn, box = 2.5 m along spawn yaw
        |  /quad_0/cloud (sensor frame), /quad_0/lidar_pose, /quad_0/body_pose
        v
scan_planner_node  (scan_04, planner.yaml + p2b_mode: true)
  grid from Livox, collision via getInflateOccupancy
        ^
        |  /p2b/route
p2b_backend_ros.node
        ^
        |  TCP plan()
pct_worker on the Building tomogram (box absent)
        ^
        |  POST /goal {goal-b}
one-goal driver
        |
closed_loop_controller → /quad_0/cmd_vel → V12
```

`pathCallback` still drops `/pct_path` in P2B mode. The global path is the
typed route on `/p2b/route`.

## Goal geometry

`goal-b` xyz is
`(2.3894024585958937, -4.45715232978101, 1.5608844757080078)`.
The box center is spawn plus `(2.5 cos yaw, 2.5 sin yaw, 0.4)`, about
`(0.887, -4.399, 1.961)`. The straight corridor from spawn to `goal-b`
crosses that 0.4 m footprint. `goal-a` is not sent.

## Pass measurement

- PCT route: the native route returned for this goal. A segment crosses the
  box xy footprint when the segment’s xy intersects the frozen AABB’s xy.
  That is expected, because the tomogram has no box.
- Body: every telemetry pose goes through `robot_aabb_world` (URDF torso
  plus 0.25 m) and `aabbs_intersect` against the frozen box AABB from
  `unmapped_box_identity`. Any intersection fails AC2.
- Arrival: final body xy within `goal_xy_tolerance_m` 0.25 of `goal-b`.

## Compatibility

- Source `p2b_execution/baseline_config/planner.yaml` is read-only. The run
  copy gets the same `p2b_mode: true` insertion `make_scan_runtime_configs`
  already uses. No other parameter changes.
- SCAN mount is the accepted `scan_04` workspace, checked with the existing
  hash gate before and after the episode.
- Livox CSV and sensor rig are staged the same way
  `qualify_stand_runner.py` stages them.
- Ports stay off the two-goal defaults if a two-goal package is still
  reserved: pick a free telemetry, command, HTTP, and PCT port and record
  them in the run request.

## Rollback

The new launcher and driver are additive. Deleting that run directory
leaves the two-goal pilot and the livox stand probe as they are. No
`planner.yaml` edit to revert.
