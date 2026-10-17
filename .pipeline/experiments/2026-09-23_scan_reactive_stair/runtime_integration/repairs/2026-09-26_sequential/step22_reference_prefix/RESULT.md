---
origin: ai_only
reviewed: false
date: 2026-09-26
---

# Reference target proposals and stopping-prefix candidate

scan33 changes only the FSM source/header from scan32. In REFERENCE_PATH mode,
the occupied-goal scan supplies a refreshed free-point frontier while retaining
the admitted global goal and full duration. Target selection stays within that
bound, and commits the actual adjusted route time only after full manager
success. Failure cannot advance the accepted-window marker.

After a failed primary attempt, at most three forward route-time halvings are
considered, sharing a budget across the original outer initialization modes.
Blocked or invalid endpoint proposals also consume this budget. Prefixes keep
start PVA, request zero terminal velocity and use the complete native planner.
The sequence is primary1, prefixes, primary2, primary3; primary relative order
is preserved. Existing partial-expiry logic keeps the complete global goal.
Non-reference behavior and every collision/dynamics/solver limit remain.

Final native source-method fixture has 15 cases. Old scan32 local v3 shows the
declared 12 failures and three positives. scan33 local v3 and pinned Foxy v1
pass all15; source hashes match the built candidate. Cases cover goal/duration,
actual adjusted commit, all-failure rollback, shared budget including rejected
endpoints, original target heading, invalid-before-map, frontier refresh,
near-goal rejection, route reset and partial expiry. Manager, route and ROS are
doubles. Early fixture v1 expected 5.75 for adjusted target; actual old search
chooses nearer backward4.5. Corrected v2/v3 preserve the true commit failure.
All prior attempt files remain available.

Independent authorized read-only review closed the finite-before-query issue
and requested budget/heading tests; no remaining code/call-contract blocker.
Deterministic regeneration matches all93 source files. Full Foxy compilation
passed in80.644s with source hashes matching before and after.

Two subsequent install-identity captures failed with SSH exit255 before login.
Their logs and result JSON are preserved under `builds/scan_33/`
`install_identity_failed_v1/` and `install_identity_failed_v2/`. Dr Sun then
reported the server shutdown and requested archival. All connection retries
stopped. No scan33 install identity, real-optimizer replay, accepted curve or
live simulation exists. The next remote step after continuation is identity
capture, then paired fresh/old recorded-input replay, not rebuilding scan33.

The frontier does not prove prefix reachability, the unit verdict does not prove
optimizer acceptance, and planned zero terminal velocity does not prove physical
stopping. Rolling start state is still predicted from the previous spline.
Native tests/build are complete; runtime qualification remains pending.
