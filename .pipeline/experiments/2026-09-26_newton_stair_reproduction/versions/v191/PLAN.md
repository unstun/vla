# v191: Option B direct Nav2 + SCAN

Stage: experiment + analysis. Version parent: **v190**. This candidate replaces
the P2B route/command gateway with direct ROS interfaces. The archived Mac
ARM64 **v176** workspace remains the native binary underlay; that dependency
is distinct from the frozen version parent. The local VLA repository is the
source of truth. `/private/tmp/vla_stop_audit_20261012/recovery_v191` is its
explicitly authorized Mac execution copy.

## Behavior and source boundary

The HTTP mission bridge requests the internal Nav2 `NavigateToPose` action and
provides the PCT `PlanRoute` service. Nav2 computes a `nav_msgs/msg/Path`, then
`FollowPath` supplies it to the SCAN controller. The controller publishes the
path on `/pct_path`; its embedded native SCAN worker publishes the native
`scan_planner_msgs/msg/Bspline` trajectory. The controller publishes standard
`geometry_msgs/msg/Twist` directly on `/quad_0/cmd_vel`.

The v191 source physically removes the six `P2B*.msg` files, their identity
fields from `Bspline.msg`, `BindRoute.srv`, the BindRoute BT implementation,
`gateway.py`, `control_gate.py`, the legacy HTTP adapter, the gateway executable,
and inherited backend/service packages. There is no gateway velocity gate,
P2B transport or `current_command.json` polling in the candidate source. The
historical underlay receipts and frozen source ancestry still reference earlier
P2B implementations; those records are provenance, not active v191 interfaces.

The native inventory contains **272 source files**, **37 changed/new files**
and **33 deleted source paths** relative to the recorded v176 source inventory.
`native_sources.json`, `prepare_native.py`, and `test_source_inventory.py` bind
the local package snapshots to a clean reconstructable execution tree.

The 0.5 m global-route heading lookahead and 0.02 m local endpoint capture remain
enabled. The direct BT has six finite retries and a 0.1 s built-in Wait action.
This Wait is only a delay: the removed P2B measured-stop/owner-admission protocol
is not claimed to survive Option B. Full-route, stop-handoff and physical safety
acceptance require separate tests of the new architecture.

## Graph qualification repairs

The resumed preflight exposed two prepared-harness defects. The BT's Wait node
had no launched action server and used a relative endpoint inside the internal
Nav2 namespace. The launch now starts a wait-only Foxy `recoveries_server`,
manages its lifecycle, and binds the tree to `/wait`. The existing profile test
checks that endpoint. No spin or backup recovery is enabled.

The process inspection previously required a standalone `scan_planner_node`.
The actual controller starts `NativeWorker` in-process on activation. The check
now verifies both the v191 controller and `libscan_native_core.so` in the actual
ControllerServer memory map, the embedded `/quad_0/scan_planner_node`, direct
Path/Bspline/Twist topic types, absence of P2B topic types and gateway node, and
all four managed lifecycle nodes in the active state. Exact mission-bridge
executable matching prevents the inspector's own command text being mistaken
for a bridge process. The bridge must load the pinned v174 PCT library.

A synthetic static identity `world -> base` TF fixture lets costmaps activate
without a simulator. There are **no physics steps, navigation goals or synthetic
odometry/clock ticks**. This checks graph readiness, not navigation behavior.
The preflight has a bounded activation deadline, refuses to overwrite an earlier
trial directory, removes stale pass receipts before a retry, and removes its
own container on exit. Earlier interrupted/failed logs remain preserved.

## Qualification and freeze procedure

Use the existing Newton Mac virtual environment with
`PYTHONDONTWRITEBYTECODE=1` and Docker context `desktop-linux`.

1. After the graph launch repair, synchronize the four changed bridge files to
   `recovery_v191`, update both source inventories, rebuild the eleven overlay
   packages, and regenerate the native receipt. Verify all native tests, two
   profile tests, `V176_TERMINAL_CAPTURE_PASS` and `V191_CORNER_LOOKAHEAD_PASS`.
2. Run the host suite and `test_overlay_runtime.py --task-root
   /private/tmp/vla_stop_audit_20261012`. Save stdout/stderr to
   `evidence/v191_graph_preflight.log`; require both overlay and graph receipts.
3. Run `qualify_mac.py --task-root /private/tmp/vla_stop_audit_20261012`. It writes
   `quality.json` and copies compact native/host/graph evidence to `verification/`,
   with SHA-256 bindings. Graph launch logs, generated profiles, process maps,
   source identity, and the earlier failure evidence are retained locally.
4. Run `freeze_host.py freeze`, then `freeze_host.py verify`. The immutable
   manifest pins v190, the quality receipt, and inherited/new source snapshots.
   Set `versions/current.json` to v191 only after verification succeeds.
5. Compare every file hash and symlink in v189, v190, `recovery_v176`, and
   `recovery_v189` with the pre-existing protected baseline. Keep the comparison
   report with v191 verification evidence; no protected path may change.

## Acceptance boundary

The required component result is 45 colcon test entries with zero failures,
errors or skips: 20 controller GTests, one tracking-parity GTest, one executor
shutdown GTest, eight plugin GTests and nine bridge pytest cases; colcon's total
also includes CTest wrappers. Two generated-profile tests and 25 Mac host tests
are separate. The final machine-readable outcomes are in `quality.json` and
`verification/`; a version freeze alone is not acceptance.

This task qualifies components and the live Mac ARM64 graph only.
`full_navigation_accepted` remains **false**. v189's failed held-yaw result and
v190's display-only result are unchanged. No new physical route, repeated-run
reliability, sustained 30 Hz result, remote training, or real-robot actuation is
part of this qualification.
