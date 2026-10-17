# v204 — restore mission behavior, retain architecture simplification

Status: 106 unique ROS component cases and one host graph check passed. No full-route experiment or physics run.

The three managed-mission behaviors now follow frozen v196:

| Behavior | v204 behavior | Owner |
|---|---|---|
| Terminal pose | Lock the first successful route's last XYZ. Explicit yaw, including zero, wins; otherwise use the last horizontal segment longer than 1e-6 m. Keep the complete pose across refreshes and the 2 m connector limit. | C++ RoutePolicy in the PCT Nav2 plugin |
| Last valid route | Retain only for the original three failure categories, or the original terminal-approach XY/Z limits. Refresh returned timestamps without changing the stored geometry. Task replacement/cancel invalidates in-flight results and prevents cross-task reuse. | Same navigation-owned policy |
| Ordinary failure recovery | Original Wait 1 s and maximum six retries for planning/tracking failure. Typed terminal-settle timeout bypasses Wait and retry. | Nav2 RecoveryNode and a UUID-scoped failure query |

Global refresh remains 1 Hz. Step 5 is deferred. No PCT cost-map modifications,
dynamic blockage masks, new fallback categories or local-navigation tuning.
C++ PCT direct calls, LocalMotion snapshots, single robot command output, two-second
PD completion, unified static terrain and removal of the redundant 2D maps remain.

Verification executed in the existing ARM64 Foxy image:

- Seven composed packages built; final owned packages rebuilt with clean targets
  to eliminate stale incremental objects.
- 10 fixed traces / 28 planning requests compared to the actually executed frozen
  v196 Python methods. Accepted paths match all seven pose components to 1e-12;
  rejection reasons, solver-call counts and retained counts match. This checks
  omitted versus explicit yaw, snapped terminal position, refresh, fallback,
  terminal approach, cancellation, ownership changes and invalid inputs.
- The actual old and restored RecoveryNode trees agree on ordinary failure and
  eventual-success attempt/wait counts. Terminal timeout produces one attempt,
  zero waits, and does not contaminate the next task's retry state.
- Real ROS session/action fixtures check native PCT metadata, HTTP dispatch,
  cancel/replacement during acknowledgement, exact FollowPath UUID lookup,
  typed-cause persistence after stop, and no stale-cause reuse.
- Stock Wait configures/activates, completes a one-second action and cleans up;
  it does not publish on the robot's command topic.
- Existing LocalMotion, terminal, static terrain, map shell, native support and
  300-sample Tracker equivalence tests are retained. The host launch check uses
  fake children. No full navigation goal or physical robot was run.

The final unique-case count and raw XML files are recorded in
`verification/summary.json`. CTest wrapper entries are not counted twice.

Repair history is retained: the test-only YAML dependency needed Foxy's existing
vendor package; the asynchronous BT test needed time for ROS responses; the new
sixth ControllerServer case exposed a reference cycle in the prior test fixture's
progress-checker setup, now released in teardown. Incremental builds also retained
an old ControllerServer object, so the owned packages were clean-built and checked
again. None of these repairs changes navigation policy. Initial failure reports
remain under `verification/` alongside final evidence.

Limit: these are component and fixed-input behavior checks, not new whole-route
acceptance. HTTP retains the simplified v201 status schema (no cached-path fields).
Previous frozen sources and the previous HTML are preserved. Physical baseline
v196 and display/current v197 remain selected.
