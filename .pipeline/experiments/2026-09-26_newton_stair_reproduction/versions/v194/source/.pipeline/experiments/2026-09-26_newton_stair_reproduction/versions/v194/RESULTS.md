# v194 component and graph qualification

Stage: experiment + analysis. Version parent: **v193**. Navigation source
parent: **v192**. Native source/build: **v194**. Native binary underlay: **v176**.

The local version directory owns the source and returned evidence. The execution
copy is `/private/tmp/vla_stop_audit_20261012/recovery_v194`.

## Implemented behavior

1. An explicit 5.0 s spline-wait watchdog survives same-goal plan refreshes and
   repeated emergency stops. A new active-to-wait transition starts a fresh
   budget. Invalid sampled commands fail immediately. Both failures publish zero
   through `stop()` without recursively locking the state mutex. Clearing a
   trajectory also clears the tracker's terminal position latch.
2. The stock six-retry RecoveryNode uses a positive integer `Wait` duration of
   1 s. No MeasuredProgressRecovery node was introduced.
3. Every mission locks its entire terminal Pose on its first accepted PCT plan.
   Explicit yaw includes 0.0; unspecified yaw comes from the last horizontal
   segment longer than 1e-6 m. Later routes reuse the exact position and quaternion,
   with a finite final connector no longer than 2.0 m in 3D. The cache stores a
   deep copy of the last accepted path. `pct_no_route` remains a rejected plan;
   cached replay is disabled, since endpoint consistency does not justify
   treating failed replanning as a successful fresh route.
4. The controller and tracker enter final-yaw braking at 0.125 rad, while the
   external checker retains 0.25 rad. Braking remains latched inside the outer
   yaw and position bands; leaving either band resumes alignment. The checker
   verifies the live query, goal state, and measured stopped velocity.

The pinned ControllerServer calls `setPlan(path)`, takes `path.poses.back()` as
its endpoint, and then calls `GoalChecker::reset()`
(`recovery_v176/src/nav2_controller/src/nav2_controller.cpp:340-353`, inspected
read-only). v194 therefore keeps the braking latch separately from the checker
result. The regression exercises `setPlan -> reset -> compute` while yaw drifts
from 0.11 to 0.16 rad during braking.

## Direct verification

| Check | Result |
|---|---|
| ARM64/Foxy build | 11 packages rebuilt; 14 native packages available |
| colcon | 45 entries; 0 errors, failures or skipped entries |
| Controller package | 22 unique GTests: 20 controller, 1 parity, 1 shutdown |
| Bridge | 9 pytest cases; deterministic PCT fixture, real loopback ROS/HTTP |
| Generated profiles | 2 tests pass; stock recovery and integer Wait checked |
| Native probes | V176_TERMINAL_CAPTURE_PASS and V194_CORNER_LOOKAHEAD_PASS |
| Mac host suite | 24 tests; 0 failures, errors or skips |
| Live graph | Four lifecycle nodes active; actual v194 controller/native libraries loaded |
| Applied-state transport | Bidirectional shared mount verified |
| Native source identity | 272 execution files match exact SHA-256 inventory |
| Protected inventory | All eight trees unchanged, including additions/removals and symlinks |

The first native run compiled all packages but failed two controller test cases:
the existing `plan()` helper returned after observing an old route instead of
waiting for the newly published route. The helper was corrected, and the final
build/test run passed. The first run's logs, XML, source inventory, build request
and controller review patch are retained as `verification/attempt01_failed_*`.
The final successful evidence is separately named.

The graph preflight uses a static identity world-to-base TF, sends no navigation
goal and advances no physics. `run_mac_full.py` was not executed. This qualifies
components and graph wiring only: no new route arrival, full-navigation,
physical-braking, reliability, collision-clearance or real-robot acceptance is
claimed. The prior v192 physical trial remains failed and untouched.

See `quality.json` for evidence hashes, `verification/` for returned records,
`native_sources.json` for source identity, `changes.patch` for the v192 delta,
and `manifest.json` for the frozen source/snapshot bindings. The requested
workflow ends at `freeze_host.py freeze`, `freeze_host.py verify` and the version
index update; a physical trial remains a separate authorization boundary.
