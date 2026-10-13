# Authorized SCAN plugin and Nav2 observation scheduling

Stage: implementation + component validation. Dr Sun requested actual SCAN
pluginization, then requested Nav2-style mapping backlog handling. This supersedes
the BT-only first increment in the earlier Foxy design.

## Change boundary

- v86: real Foxy `nav2_core::Controller` and goal-checker plugins, retaining SCAN
  spline tracking and a separately scheduled native planner. `setPlan` dispatches
  an explicitly bound P2B route; `computeVelocityCommands` runs tracking, not a
  second standalone command timer. Preserve full route/spline identity and the
  exact requested goal. A narrowly pinned controller-server adaptation is needed
  because stock Foxy strips command identity and has no plugin cancellation hook.
- v87: use Nav2's timed observation-window/update-worker organization for SCAN's
  native 3D map. Keep original point/pose pairing and immutable publication. Make
  retention and skipped-frame counts explicit. It changes observation admission,
  so test obstacle retention and do not claim all-frame equivalence.
- Native source parent: frozen v82; v85 is component reference only. Preserve
  preceding bytes and allocate separate integer versions. Do not overwrite v82.

Owned paths: new version directories, a new version-owned ROS package/native
materialization, selected pinned upstream reference files, minimal Foxy server
adaptation, task/design/spec links and compact validation records. Keep the
existing robot command gate and measured stop authority. No default planar
costmap substitutes for 3D stair/support checking.

## Acceptance

Build/load actual plugins in Foxy; check route binding, actual spline tracking,
one command producer, cancellation, lifecycle shutdown, invalid/old/future input,
goal Z/yaw and stop evidence. Exercise the actual Nav2 server where the build
environment permits; clearly separate plugin API tests from full server tests.
For mapping, test periodic updates, bounded windows, exact timestamp pairing,
stale sensor rejection, transient obstacles, and recorded map-state differences.

These component gates do not establish complete Newton route success or Jetson
driver/robot acceptance. Any build/host blocker must be recorded rather than
relabeling Humble execution as Foxy. No formal training or robot actuation.
Temporary local build products use an owned task root and are archived to
gpu5070ti with hashes before cleanup; all final source and compact results return
to the local VLA repository. The main continuity task remains in progress.
