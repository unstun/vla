# v86: actual Foxy SCAN controller plugins

Date: 2026-10-08. Stage: implementation + component analysis.

Implemented `scan_nav2_controller/Controller` and `scan_nav2_controller/GoalChecker`
as real pluginlib exports for Nav2 0.4.7. The plugin owns the native SCAN planner
on its own executor; SCAN mapping retains a separate worker. Nav2 schedules the
tracking calculation. The old controller's independent command timer/publisher
is absent from the extracted tracker.

The pinned ControllerServer adaptation preserves full P2B command identity and
notifies the plugin on cancel, failure, invalid preemption, deactivation and
shutdown. A stock server cannot authorize plugin output. Route and stop evidence
interfaces are documented in the [package README](../../runtime/scan_nav2_foxy_v86/src/scan_nav2_controller/README.md).
The original source and modifications are retained in `nav2_controller/` and
`nav2_controller.patch`.

## Direct evidence

- Actual Ubuntu 20.04 / Foxy / ARM64 build: eight packages. Installed Nav2 core,
  controller and costmap packages are 0.4.7-1focal. The installed controller
  interface SHA-256 equals the audited fixed-commit upstream header.
- **18 GoogleTest cases pass**: 17 controller/goal/lifecycle cases plus one
  300-sample tracking comparison. The colcon result counts 20 entries because
  it includes two CTest wrapper entries. All 300 command/trajectory-phase pairs
  equal the original controller under the declared fixture.
- The real patched ControllerServer passes ten protocol checks in
  `results/server08/result.json`: actual FollowPath start, tagged commands,
  cancellation, stop-before-new-owner, original goal rather than snapped path
  endpoint, hold-versus-stillness distinction, and invalid-controller preemption.
  It emits 18 tagged commands and zero plain Twist commands in that test.
- The packaged launch activates the actual native worker with the v87 profile:
  5 Hz map updates and 0.5 s observation persistence. It emits zero commands
  without a route and deactivates/cleans up; see `results/launch03/result.json`.
- The native remaining-curve checker emits correctly identified, source-stamped
  clear evidence for a constant curve at a recorded clear body position, and
  rejects a future-dated curve. See `results/final_build04/native-safety.log`.
- All 135 files in the final composed build source match local source hashes;
  the verification receipt is in v87. Source/snapshot manifests bind the release.

## Boundaries

The server protocol test uses **synthetic planner, TF and physical-stop evidence**.
The launch test uses synthetic TF and sends no route. The native safety fixture
does not move a robot or reproduce a complete navigation episode. This is
component integration evidence, not complete Newton navigation, Jetson runtime,
locomotion integration, or physical stop qualification.

The existing mission/backend must supply an authorized exact route binding and
authoritative stop evidence. PCT/BT mission-client migration is not completed by
this plugin package. Keep the existing command gate. Do not start the legacy
standalone controller alongside the plugin. The v48 reference remains selected.

## Failed development attempts retained

- `build01`: Foxy's older GoogleTest uses `SetUpTestCase`, so the newer hook did
  not initialize ROS. The corrected hook and null-safe teardown pass afterward.
- `server01`: Foxy rejected an untyped empty YAML plugin array. The frame-only
  costmap profile now names an inflation layer; native SCAN remains the collision
  authority.
- `build05`: an unqualified YAML node section did not apply to the namespaced
  native worker. The loader now resolves the named section explicitly with
  Foxy's YAML parser, preserving its values.
- `server03`: the mock-worker command-line override did not replace the file
  setting. The probe now saves one explicit mock profile; the packaged launch
  uses Foxy's `RewrittenYaml`.
- `final_build01`: Foxy could not infer a generic subscription lambda in the
  native safety probe. An explicit message pointer type compiles and runs.
- `launch01` observed one plain zero during shutdown with no selected controller.
  The final server adaptation routes SCAN-only shutdown through the tagged
  boundary; launch03 observes zero messages throughout.

These are development-attempt logs, not additional accepted runtime versions.
No frozen predecessor was edited. No formal training or real-robot actuation.
