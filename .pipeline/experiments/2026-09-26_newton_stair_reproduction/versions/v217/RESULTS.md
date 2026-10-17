# v217: supported stop passes; route recovery remains unsuccessful

Three packages built on gpu5070ti; 121 distinct cases passed (137 includes
16 CTest wrappers). v216 adds 14 supported-transfer cases. The new expired-curve
regression failed against the old implementation, then passed. An intermediate
check exposed a fixture clock mismatch and a missing static-map environment
variable; these were corrected without changing navigation behavior.

One original-start historical_full attempt ended FAILED after 84.665 s.
No physical fall was recorded. Final stance was FIXED_STAND with forces
[69.236328125, 29.462242126464844, 16.935720443725586, 14.661380767822266] N and continuous final PD for
24.806 s, at the staircase, not the destination.
The original full-route gate failed. Do not promote over v210.

The 0.75 s timeout was observed at 0.769577 s. A new global route arrived at
48.095 s, but the local planner continued failing. Six ordinary retries then
exhausted; each new initial admission retained the original 5 s budget.
The request mechanism worked but was insufficient to recover the route.

45-55 s: 2/181 completed local rounds succeeded; maximum tilt 28.142 deg.
No PD transfer was admitted in that interval. The first later transfer at
57.840 s had all four feet above 10 N and completed without the v212 fall.
Walking unloaded feet are not failures; entry support is checked separately.

Diagnosis: a usable reference remained present while local replanning failed;
waiting until the expired-curve brake then aborting FollowPath loses the chance
to refresh while the last trajectory is still executable. v219 separately
adds a route-bound request from consecutive native planning failures and keeps
the usable trajectory. It does not modify the geometric planner.

Source/runtime provenance: manifest.json, verification/remote/receipt.json,
results/outcome.json and results/staircase_comparison.json. Full real-state
video is version v218; all v210/v212/v216 evidence remains preserved.
