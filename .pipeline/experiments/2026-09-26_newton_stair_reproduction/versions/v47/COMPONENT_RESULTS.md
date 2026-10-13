# v47 component results

The final source is frozen with 6,297 selected source/configuration files,
98 native source files and 516 installed files verified by SHA-256. The parent
v44/v45/v46 source identities are unchanged. Only the FSM implementation/header
change in the native tree; the other 96 files match v44.

The actual gpu5070ti build passed (`build_evidence_retry03`). The final native
build has 34 goal/timing/stop assertions and 48 cache assertions passing in
`tests/attempt06`; attempt 7 explicitly binds these checks to its identical
native source manifest. Both final recorded cold geometry outputs exactly match
v36's frozen v32/v33 oracle. Cold replay plan costs are 12.989 and 11.737 ms;
these do not establish full-scene planning frequency.

The final window tests pass 24 assertions for v33 and 25 for v32. They cover
accepted-window storage, current-map reuse, exact goal preservation, growth from
measured odometry, no growth from planned progress alone, accumulated growth,
identity/goal/map changes, backwards or large planned/measured projection jumps,
clock regression/expiration, stale scan, bounds, zero span, shorter nominal
selection, emergency stop and route regeneration.

The v32 fixture additionally accepts a 95% window through the complete native
planner and exercises its consumption by getLocalTarget. No shorter zero-terminal-
velocity window passes the bounded v33 stopped-state fixture set; the test records
that skipped coverage and requires the original nominal fallback. Rejected
curves remain rejected. The full live run is required to assess actual motion.

All earlier attempts, including a zero-span bug, fixture assumptions, rejected
shorter curves and the floating-point growth-threshold stimulus, are retained.
Build 3 is the final native source; the final threshold retest changes only the
test input to 1e-6 route-seconds beyond half-span.

The v45 representative live categories are selected from its original log in
`analysis/v45_representative_log_cases.json`. They are not paired executable
replays of identical complete live map/route/spline state. No independent agent
review was performed in this inline session. See INLINE_REVIEW.md for scope.

Final goal/yaw/tolerances, collision and stair rules, planner manager, optimizer,
controller, policy, physics, sensing and real-time pacing retain the parent
implementation/configuration. Window target selection changes and is evaluated
separately in the bounded full-stack trial.
