# v206 command continuity

This package inherits v204's LocalMotion/Tracker ownership. Only normal command
execution and route revision semantics change. PCT/SCAN geometry is unchanged.

- Same-goal route refresh replaces the bounded input snapshot without invalidating
  an in-flight solve, pending output, or trajectory-bound freeze feedback.
- Heading attenuation and 1.0/0.6 rad turn hysteresis survive spline replacement.
- TrackingNode owns one three-axis slew history; normal Controller goal braking
  calls LocalMotion::brakeCommand and uses that same history. Emergency/cancel
  immediately clear it. New curves do not reset the command timestamp.
- An expired low-speed curve brakes to exact zero and remains stopped until a
  replacement. This is a local execution state, not successful goal completion.
  Active short/reverse corrections remain possible; final pose/PD gates and
  ordinary retries are unchanged.

The new component tests exercise individual command ticks. Existing lifecycle,
heading and goal-contract tests now wait for the production limiter to settle;
no production feature is disabled in tests. The old 300-sample full-command
parity claim belongs to v204; v206 retains only straight-path phase/geometry and
settled-command parity, since heading and ramp behavior intentionally changed.

## Inherited package description

# SCAN controller plugins for ROS 2 Foxy

`LocalMotion` owns the SCAN worker, Tracker and their bounded snapshot exchange.
Nav2 calls `setRoute`, `command` and `cancel`. SCAN alone writes planning state;
the Nav2 control thread alone writes Tracker state. Completed splines cross the
boundary through a direct callback and one immutable output slot. Route changes
and cancellation invalidate late outputs; freeze feedback carries trajectory ID.

`/pct_path`, `/quad_0/planning/bspline` and execution-freeze topics are observation
outputs. LocalMotion has no subscriptions to them. External sensors, localization,
clock and physical execution-state input still use ROS. Standalone SCAN retains
its ROS inputs when initialized without `DirectIO`. Only ControllerServer
publishes `geometry_msgs/msg/Twist` on `/quad_0/cmd_vel`.

`setPlan` validates path coordinates, orientations and frames. A valid cubic
B-spline becomes available to the tracker immediately. While waiting for the
first curve, the controller returns zero velocity and fails after the default
5-second timeout. The goal checker requires goal position and yaw acceptance
plus measured stopped velocity and two seconds of source-stamped FIXED_STAND
with PD ownership from `/quad_0/execution_state`. Missing feedback cannot complete
the task; a separate 10-second terminal deadline aborts it. The tracker retains the original cubic spline
phase/feedback calculation and the v189 corner route-lookahead heading behavior.
Native mapping, optimization and collision checks remain in SCAN.

The `ExecutionControl` hook only clears execution on cancellation or failure.
It does not publish. The server sends the stop command through its own publisher. The standard
Foxy two-argument controller API and an explicit GoalChecker overload are both
available. `native_worker_enabled=false` is only for component fixtures; it does not enable a ROS spline input.

The full navigation launch is:

```bash
ros2 launch lite3_nav2_bridge navigation.launch.py \
  native_planner_config:=/absolute/native.yaml \
  backend_config:=/absolute/backend_config.json \
  terrain_manifest:=/absolute/terrain/terrain.json \
  generated_params:=/absolute/new-profile.yaml \
  odom_topic:=/quad_0/body_pose
```

The mission bridge serves HTTP goals/cancellation/state, sends Nav2 goals, and
keeps no planner loop. PCTPlanner calls the native C++ planner directly (v201). Tests cover plugin loading, direct route/curve/output
interfaces, goal checking, malformed inputs, lifecycle, route-heading corner
cases and 300 samples of tracking parity. These are component tests, not a
simulation or hardware navigation trial.

The v200 tree has no generic outer recovery: FollowPath failure ends the task.
Movement progress checking resumes when the controller leaves terminal waiting.
Source the v198 interface (included in this component build) and run the v198
bridge/producer for typed physical execution feedback. The v196 bridge cannot
produce that new message.

In v203 the 2D terrain-slice publisher and timer are removed. Default Nav2
costmaps have no active layers, one cell, 1 Hz lifecycle updates and no grid publication.
SCAN's 3D occupancy, inflation, geometry and support checks remain unchanged.
The unified terrain manifest binds PCT input and three distinct static cloud
roles; one `static_terrain` process publishes those clouds. See v203/BUILD.md.
