# v194: bounded spline waiting and a stable terminal goal

Stage: experiment + analysis. Version parent: v193. Navigation source parent:
v192. Native version: v194. Mac binary underlay: archived v176.

The local v194 directory is the source of truth. The only new native execution
copy is `/private/tmp/vla_stop_audit_20261012/recovery_v194`. Step 0 recorded all
recursive SHA-256/byte counts, symlink targets, directories and special entries
for v189-v193 and recovery_v176/recovery_v189/recovery_v191 before any edit.
Those eight trees admit no changes. Docker mounts the parent execution copies
read-only; only the v194 workspace and task evidence are writable during build.

## Behavior and ownership

- Controller waiting starts for a new goal or loss of an active spline. Repeated
  same-goal refreshes and emergency stops preserve the first waiting timestamp.
  Missing splines fail after 5.0 seconds; invalid samples fail immediately.
  Stop/deactivate/cleanup reset both waiting and terminal timeout state.
- The tracker clears its terminal position latch with a cleared trajectory.
- The stock six-retry RecoveryNode remains. Foxy Wait uses integer `1` second.
- Each mission locks the complete terminal Pose on its first accepted PCT route.
  Explicit yaw includes zero. Otherwise the final nondegenerate horizontal
  segment (length greater than 1e-6 m) determines yaw once. Later PCT routes reuse
  that exact pose. The final connector must be finite and at most 2.0 m in 3D.
  This is a connectivity bound, not a collision-clearance claim.
- A deep-copied accepted path remains on its job for inspection. `pct_no_route`
  remains a rejected plan; cached route replay is deliberately not introduced.
  The service carries no mission ID, so attribution uses the active job and its
  requested/canonical goal coordinates; owner changes during planning reject.
- Inner yaw capture uses half the configured external tolerance (0.125/0.25 rad).
  Once captured, zero-command braking remains latched within the outer yaw and
  position tolerances. A live query and measured stopped velocity are required
  by GoalChecker. Same-goal setPlan preserves this braking latch in a controller-owned field,
  including the following GoalChecker.reset() performed by ControllerServer.

## Qualification and stop boundary

Run build_mac.py, run_host_tests.py, test_overlay_runtime.py, verify_protected.py,
qualify_mac.py, then freeze_host.py freeze and verify. Bind source inventories,
11 rebuilt packages, 45 colcon entries, 22 unique controller-package GTests
(20 controller + parity + shutdown), 2 profile tests, host tests, and the actual
loaded controller/native libraries into local qualification evidence.

The graph preflight activates four lifecycle nodes using a static identity TF.
It sends no navigation goal and advances no physics. Update current.json and the
version index only after successful freeze verification. Do not invoke
run_mac_full.py. No full-route, physical stopping, arrival or robot acceptance
is claimed by this qualification.

Changes are confined to v194 source, tests and qualification scripts plus the
requested version indexes and task-root v194 artifacts. Prior results remain
historical evidence. No commit or unrelated worktree cleanup is part of this task.
