# v241 — one physical validation of frozen v240 passed

The sole authorized original-route run on gpu5070ti finishes at121.424896s,
passes original arrival/terminal gates and holds measured PD for4.357605s.
Final XY error0.115871m, yaw error0.068466rad, height error0.008771m; no fall.
All1104 scans meet the unchanged100ms deadline, maximum30.465ms.

109–115s:168/169 successful rounds, zero emergency and >=0.5s measured pauses.
Actual approach108.851807–114.668610s has zero cumulative low speed or active
curve gap. The raw fixed window includes0.271423s normal near-goal settling.
45–55s:273/274 rounds, zero emergency/pause/gap;100/100 known-floor samples,
minimum extra edge margin0.129810m,95% at the capped0.15m target, no negative
margin. v237 had100% at that target; the smaller minimum remains reported.

Frozen v240 native install, original v232 graph/driver and v237 scanner repair
are bound by source/install/actual-prefix/profile checks before and after the
run. RL, endpoints, ENV225,0.35m hard guards and0.1s captures are unchanged.
No physical retry or baseline promotion. Original full_qualification=false
and lack of repeated reliability/sustained30Hz evidence remain in force.

See the [full audit and four videos](../../audits/2026-10-18_v240_gpu5070ti_physical/RESULTS.md).
The frozen manifest records pre-physics readiness; this separate result binds
the subsequent physical pass without rewriting the source snapshot.
