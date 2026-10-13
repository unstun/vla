# SCAN controller plugins for ROS 2 Foxy

This package exports real `nav2_core::Controller` and `nav2_core::GoalChecker`
plugins. The controller owns SCAN's native planner on a separate executor and
reuses the original spline tracker under Nav2's control scheduling. The original
standalone controller is not launched. Native 3D occupancy, support, PVA,
optimization and collision checks remain in the pinned SCAN implementation.

The target is Ubuntu 20.04 / ROS 2 Foxy / ARM64. The component build and tests
use an ARM64 Linux container on Mac; they do not establish Jetson driver,
localization, locomotion or full-route readiness.

## Build and launch

Use the complete v86 workspace sources and the version-owned Nav2 0.4.7
`nav2_controller` package. Stock Foxy strips the P2B identity from velocity
messages and does not notify controller plugins when an action is cancelled.
The small pinned server adaptation calls `CommandOutput` at the real publish
and stop boundary. Without its output-owner handshake, this plugin rejects
control requests. Other Nav2 controller plugins keep the original output path.

For v87, overlay its `plan_env` source before rebuilding all dependent packages;
changing only a runtime library path is insufficient because some native
dependencies are static libraries. Exact build commands and dependency receipts
are retained in the corresponding version directories.

After sourcing the resulting Foxy workspace:

```bash
ros2 launch scan_nav2_controller scan_nav2.launch.py \
  native_planner_config:=/absolute/path/to/the/versioned/planner.yaml \
  use_sim_time:=false
```

The launch file starts ControllerServer and its lifecycle manager. It starts no
actuator, locomotion bridge or fabricated stop-evidence producer. A valid TF
chain is required for activation. Simulator and robot clocks require separate
profiles. The native parameter loader accepts `/scan_planner_node` or the exact
`/quad_0/scan_planner_node` section, preserving its values and explicitly matching
`use_sim_time` to the controller. The qualified section takes precedence when
both are present. Relative sensor pose input is remapped to `/quad_0/lidar_pose`.

## Runtime contract

| Interface | Producer and requirement |
| --- | --- |
| `/nav2_scan/route_binding`, `P2BRoute` | Existing authorized mission/backend; full identity, exact Path, original goal XYZ/yaw |
| `/nav2_scan/binding_ready`, `P2BRoute` | Plugin echoes the exact validated binding; client waits for equality before sending the action |
| `/follow_path`, Foxy `FollowPath` action | Same client; exact bound Path and `controller_id=SCAN` |
| `/p2b/route` | Plugin forwards only an admitted binding to its native SCAN worker |
| `/quad_0/planning/bspline` | Native planner; timed spline and complete matching identity |
| `/quad_0/planning/execution_safety`, `P2BExecutionSafety` | Native full remaining-curve check; original observation stamp, checked time and trajectory binding |
| `/quad_0/raw_scan_cmd_vel`, `P2BStampedTwist` | Nav2's output boundary through the plugin; existing backend remains the sole effective command gate |
| `/p2b/scan_cancel` | Nav2/plugin or existing owner supervisor; matching identity and explicit reason |
| `/nav2_scan/stop_evidence`, `P2BStopEvidence` | Authoritative stop supervisor after original applied/hold/stillness checks |

The client waits for an exact `binding_ready` echo before sending `FollowPath`;
a fixed sleep is not a delivery guarantee. The echo confirms buffered input,
not motion permission or physical-stop completion. Its Path, including headers,
must match exactly and be fresh. The plugin does not invent identity or use the
snapped route endpoint as the requested goal. A periodic update with the same
full identity and requested goal can update the native route; a different owner
requires confirmed stop before admission. Run generations cannot be reused in
one controller instance. The stock `NavigateToPose` request does not carry this
metadata; the mission/backend client must supply it. PCT/BT client migration is
not silently completed by installing this package.

The velocity boundary consumes one exact computed ticket. It rejects delayed,
modified or replayed commands and rechecks evidence at publication. Body age is
at most 100 ms; original observation age is at most 250 ms. The new native safety
validation lease is at most 100 ms and bound to the accepted trajectory. An
unstarted trajectory may wait up to the explicit 2 s startup bound, producing
only zero commands; the existing downstream watchdogs remain authoritative.

Cancellation, safety failure and deactivation latch stop and revoke the old
trajectory. An ordinary cancellation response or zero command never proves
physical stillness. The goal checker requires the original goal XYZ/yaw plus a
matching, fresh supervisor proof with controller hold and measured stillness.
The retained stop owner cannot be replaced merely because Nav2 finished an
action. A new route requires a new generation after stop confirmation.

`native_worker_enabled=false` is an explicit external-planner test seam. The
default is true. The protocol probe uses false and supplies labelled synthetic
planner/TF/stop evidence; this probe must not be treated as real-robot evidence.

## Evidence and limits

The tests load plugins with actual Foxy pluginlib, compare tracking math against
the original v82 code over 300 samples, exercise the real native-worker lifecycle,
and run the actual patched ControllerServer through start/cancel/goal transitions.
Those server tests use synthetic planning and physical-stop evidence. Native map
replays are separate and use original recorded observations.

For v87, the map uses a periodic update worker and a Nav2-style observation
window. Zero retention means latest-only; positive retention keeps a recent
window. SCAN fuses selected observations once instead of repeatedly marking
every retained observation as a 2D costmap does. Dropped observations are counted;
occupied evidence can be lost. Do not call this all-frame equivalence or a
validated continuous-navigation repair. See the version reports before promotion.

Original parent code and tracking extraction are identified by
`tracking_provenance.json`; the Nav2 patch retains the original per-file notices.
