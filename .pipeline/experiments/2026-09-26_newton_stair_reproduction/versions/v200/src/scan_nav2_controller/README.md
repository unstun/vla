# SCAN controller plugins for ROS 2 Foxy

The Nav2 controller publishes standard `nav_msgs/msg/Path` routes on `/pct_path`,
receives `scan_planner_msgs/msg/Bspline` on `/quad_0/planning/bspline`, and returns
`geometry_msgs/msg/TwistStamped` to ControllerServer. Only that server publishes
`geometry_msgs/msg/Twist` on `/quad_0/cmd_vel`. The native SCAN worker
runs in-process on its own executor; `initial_path` is remapped to the configured
route topic. Its route input uses reliable, transient-local QoS.

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
available. `native_worker_enabled=false` allows an external spline producer.

The full navigation launch is:

```bash
ros2 launch lite3_nav2_bridge navigation.launch.py \
  native_planner_config:=/absolute/native.yaml \
  backend_config:=/absolute/backend_config.json \
  pct_map:=/absolute/map.pickle \
  generated_params:=/absolute/new-profile.yaml \
  odom_topic:=/quad_0/body_pose
```

The mission bridge serves HTTP goals/cancellation/state, sends Nav2 goals, and
plans PCT paths in-process. Tests cover plugin loading, direct route/curve/output
interfaces, goal checking, malformed inputs, lifecycle, route-heading corner
cases and 300 samples of tracking parity. These are component tests, not a
simulation or hardware navigation trial.

The v200 tree has no generic outer recovery: FollowPath failure ends the task.
Movement progress checking resumes when the controller leaves terminal waiting.
Source the v198 interface (included in this component build) and run the v198
bridge/producer for typed physical execution feedback. The v196 bridge cannot
produce that new message.
