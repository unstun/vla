# v202 LocalMotion component results

The SCAN worker and Tracker are now owned by LocalMotion. Routes and trajectory-
scoped freeze feedback enter one immutable input snapshot; completed splines
cross a direct callback into one output slot. Neither slot grows with traffic.
Route changes and cancellation reject late results. Cancellation also clears a
pending native target when the worker next consumes the input.

LocalMotion does not subscribe to route, spline or execution-freeze topics.
Those publishers remain available for observation. External body, map/sensor,
clock and physical execution feedback retain their ROS interfaces. The Nav2
adapter retains task completion; ControllerServer remains the sole Twist outlet.

## Verification

- Seven related ROS packages built with the pinned ARM64 Foxy image.
- 77 unique component cases passed with no failures or skips, across nine XML reports.
  Colcon reports 86 because it also counts the nine enclosing CTest runners.
- 300 fixed tracking samples match the original tracker exactly in command and phase.
- Real plugin tests reject ROS spline/route/freeze injection; direct snapshots
  supply a moving command. Cancel and a new goal reject the previous generation.
- The real SCAN output function feeds Tracker and retains byte-equivalent ROS
  message fields, including the original start time. Emergency output clears
  Tracker. Old-trajectory freeze feedback cannot freeze a replacement.
- The native worker receives direct routes through three activate/deactivate
  cycles. Without sensor/odometry fixtures these routes remain pending; this is
  receipt/lifecycle evidence, not successful local planning.
- Native cancellation clears the pending reference and trajectory state.
  Concurrent exchange, bounded replacement, malformed input, terminal hold,
  progress exemption, single command publisher and actual no-retry BT checks pass.
- All 287 composed source files match the owning local overlays; all
  927 protected files under v196-v201 are unchanged.

The first build exposed missing explicit includes in the new LocalMotion header.
They were added; the failed log is retained as `verification/build_attempt01.log`.
The final build and complete targeted regression passed. Existing compiler/PCL
warnings remain; no algorithm tuning or warning suppression was added.

No new full-route experiment, physics step, training, or hardware command was
executed. PCT's v201 fixed-input results remain prior evidence; PCT code is
inherited unchanged and was rebuilt, not rerun as another route experiment.
The physical/display pointers remain v196/v197. Steps 4 and 5 remain pending.

See BUILD.md for reproduction, PROVENANCE.md for source lineage and
`verification/summary.json`, raw logs, XML and `changes.patch` for evidence.
