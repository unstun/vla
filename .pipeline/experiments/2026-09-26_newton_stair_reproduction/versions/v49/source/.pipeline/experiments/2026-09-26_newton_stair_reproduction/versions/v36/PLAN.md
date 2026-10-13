# v36 Nav2 navigation timing and goal contract

Stage: experiment + analysis. Parent: frozen v35. Status: preparing, unfrozen.

## Authorized behavior

Dr Sun requested system alignment with Nav2, including goal tolerances and
planning frequencies, on 2026-09-30. He selected local planning / navigation
control at **30 Hz**, and global planning at **1 Hz**. Trellis task creation was
declined for this session. All compilation and executable verification run on
gpu5070ti; the local repository remains the only source of truth.

The 50 Hz locomotion policy and 1000 Hz joint-PD/physics loop retain their pinned
timing. Navigation control produces vx, vy and yaw rate; it is a separate loop.
There is no authorization to train a policy, actuate hardware, or silently
replace PCT/SCAN with a wheeled Nav2 algorithm.

## Verified gaps

* v35 SCAN nominal replanning is 2 Hz on the ROS clock. Its FSM polls on a
  10 ms wall timer and separates trigger and attempt across callbacks.
* The native velocity controller has a hard-coded 10 ms wall timer (100 Hz).
* PCT computes a route for a submitted goal; the accepted goal has no periodic
  global-path refresh.
* HTTP arrival checks use XY 0.25 m and Z 0.20 m, followed by measured quiescence.
  The previous goal wire carries XYZ but no desired yaw. Dr Sun selected
  position and orientation completion: XY 0.25 m, yaw 0.25 rad, with the initial
  global path's last non-degenerate segment as default orientation. An explicit
  target_yaw_rad overrides that default. Keep that goal orientation fixed across
  periodic global-path refreshes, and recheck actual XYZ/yaw after stopped dwell.
* Native local-curve finish_dist (0.15 m), reference-neighborhood search tolerance
  (1.0 m), and whole-goal arrival tolerance (0.25 m) have different owners.
  Changing a search tolerance does not align whole-goal completion.
* A native A* search may run for 0.2 s; several searches and spline optimization
  can occur in one callback. A 30 Hz parameter alone is insufficient evidence.

## Change boundary

1. Derive a new native source tree from v35; keep every v35 byte and artifact.
   Make navigation controller frequency configurable and select 30 Hz.
2. Schedule local nominal attempts at 30 Hz on the monotonic wall clock,
   following the Nav2 controller's WallRate basis; trajectory progress remains
   ROS/simulation time. Schedule without accumulating missed ticks,
   leave wall scheduling independent of ROS-clock pauses/rewinds, and avoid an
   extra FSM-trigger callback. The optional ROS scheduling basis reanchors its
   next deadline after a rollback. Preserve
   collision checks, physical feasibility, accepted-curve PVA and safe stop.
3. Add one asynchronous global PCT refresh at 1 Hz for an active command.
   Compute from the latest measured start, commit only to the same live owner,
   discard results after cancel/replacement and preserve the active local curve.
   Avoid restarting the command lifecycle or accepting stale map identities.
4. Use a version-owned backend overlay and launch entry, preserving frozen shared
   runtime files. One contract identifies frequencies, units, clocks, XY/Z and
   any approved yaw semantics across controller, backend, driver and review.

## Evidence and gates

The execution copy is `/home/sun/vla_exec/vla` on gpu5070ti. Before execution,
SHA-256 verify the exact version-owned sources and pinned shared prerequisites;
after execution, return logs, native source/install identity, results and hashes
to this local version directory. No remote-only edit counts as implementation.

Tests must exercise actual compiled native wall timing, invalid parameters,
the optional ROS scheduler's pause/reset handling, missed periods,
stop/preemption and asynchronous refresh races.
Record actual controller publications, nominal attempts, plan durations and
deadline misses. Use wall time and ROS/simulation time as separate fields.
Replay recorded geometry through the native planner to assess the 33.333 ms
local budget; report any inability to achieve 30 Hz instead of relaxing safety.
The alternate-clock scheduler fixture is not a test of complete trajectory or
command lifecycle recovery after a ROS clock rewind. That recovery is outside
v36's rate/goal component acceptance and remains unvalidated.

Component tests and builds do not imply whole-Building acceptance. The v35
failure and last accepted v3 empty-floor condition remain recorded. A new long
physics/video trial requires a separately authorized run and a frozen v36
manifest. No commit or push is planned.

## Primary reference

Nav2 controller frequency is configurable (default 20 Hz); 30 Hz here is Dr
Sun's selected configuration. The default NavigateToPose behavior tree invokes
ComputePathToPose through a 1 Hz RateController. SimpleGoalChecker defaults are
XY 0.25 m, yaw 0.25 rad, stateful true. Preserve 3D height and measured-stop
requirements as explicit Lite3 additions rather than calling them Nav2 defaults.

* https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/
* https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/controller_server_plugins/simple_goal_checker/
* https://docs.nav2.org/jazzy/getting_started/nav2_behavior_trees/detailed_behavior_tree_walkthrough/detailed_behavior_tree_walkthrough/
* https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_controller/src/controller_server.cpp#L355
