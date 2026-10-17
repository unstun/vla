# v202 source lineage

Parent: frozen v201; navigation algorithm baseline: v196.
The native SCAN package comes from v201's verified composition. Controller and
Tracker come from frozen v200, which v201 inherited unchanged. The only replaced
packages are `plan_manage` (ROS package `scan_planner`) and `scan_nav2_controller`.
The new LocalMotion module owns native-worker lifecycle, route/spline exchange,
Tracker and freeze feedback. No upstream algorithm or parameter retuning.

Build image: `vla-newton-foxy:v149`, ARM64,
`sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e`.
Execution copy: `/private/tmp/vla_navigation_refactor_20261014/workspaces/v202`.
Underlay: `/private/tmp/vla_navigation_refactor_20261014/underlay`, mounted read-only.
The durable local source of truth is this version directory, not that build copy.

`verification/changes.patch` compares the two packages against the verified v201
composition. `protected_before.json` and `protected_after.json` bind the preceding
v196-v201 sources and records. `source_identity.json` checks the complete composed
build copy against its authoritative sources. Build/test logs and XML are copied
back here; binary build trees remain disposable. No new physics steps, full-route
experiments, policy training, or robot commands are part of this version.
