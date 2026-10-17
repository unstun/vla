# v204 provenance

Parent: frozen v203, manifest SHA-256
`293d9f60c3a9e5f90af807c69b446ea49353a3faabe0ff8c8c24e30800ac33ef`.
Behavior reference: frozen v196 mission bridge and navigation tree. The oracle
imports and executes the original methods; it does not translate their expected
outputs into a second hand-written reference algorithm.

The existing Docker image is `vla-newton-foxy:v149`, ARM64 digest
`sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e`.
Execution copy: `/private/tmp/vla_navigation_refactor_20261014/workspaces/v204`.
Read-only execution underlay:
`/private/tmp/vla_navigation_refactor_20261014/underlay/recovery_v196`.
Only source, compact test reports and provenance return to this repository.

Owned package bases: `lite3_nav2_plugins`, `lite3_nav2_bridge`, and
`scan_nav2_controller` from v203; `nav2_controller` from v200;
`lite3_nav2_interfaces` from v198. PCT's algorithm, SCAN planning and map source,
Tracker equations, terrain payloads, locomotion and physical bridge are inherited.
The new C++ route policy migrates only the old terminal-pose/cache decisions.
The PCT wrapper separates existing failure categories so the original three
fallback reasons remain distinguishable.

Foxy FollowPath has no error-reason field. ControllerServer records the typed
terminal-settle exception against the actual accepted FollowPath UUID before
zeroing/aborting. The BT queries that UUID only on abort. Ordinary errors keep
the original RecoveryNode budget and Wait; the terminal exception does not retry.
The inherited stock Wait has its own unused `/cmd_vel` output; it is not remapped
to the robot's `/quad_0/cmd_vel`. That actuator topic remains ControllerServer-owned.

RouteSession is task lifecycle metadata, not a replacement planning service.
It conveys optional-heading presence and task identity once before dispatch;
matching END releases the navigation-owned cache. C++ computes every plan locally.
The HTTP adapter has no planner object, PlanRoute endpoint, canonical pose or
path cache. Its status schema remains the simplified v201 schema; v196's cached
path/status fields are not reintroduced into HTTP responses. Direct unmanaged
GlobalPlanner callers retain v201 behavior; restored legacy mission rules apply
to the managed HTTP/Nav2 task path. No VLA implementation is claimed.

`verification/protected_before.json` and `protected_after.json` cover 1,116
previous source/evidence files. `previous_html/` preserves the pre-v204 page and
source/validation records. v196 physical acceptance and v197 display selection
remain unchanged; v204 is a source/component version only.
