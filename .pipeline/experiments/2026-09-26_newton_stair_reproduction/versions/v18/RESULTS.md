# v18 results

All five real receive-loop regressions pass. Three tests failed on the parent:
the original uninterrupted clock trace, ordinary repeated rejection with TTL,
and deviation rejection before the reset threshold. Socket, identity and echo
failure remain fail-closed. No TTL, uncertainty or watchdog limit was widened.

Physical trial `v18_building_route01` has zero command reconnects and zero
protocol errors. It ends after 37.431 s simulated time, with 1.984 m forward
travel and 0.211 m rise. Its explicit terminal cause is
`native_replan_exhausted`, not odometry freshness. The native notice, controller
hold, measured stillness and terminal stop flow complete, and applied-state
copyback verifies. This validates the repaired clock behavior in this trial;
the short stair route and historical complete building remain unsuccessful.

The next exact 189-scan fixture is `audits/2026-09-27_v18_frontier/inputs`.
Its selected ground contains a proven float16 classification flip, documented
separately in `audits/2026-09-27_pct_precision`. The broader raw-cost ground
candidate remains rejected after a mapped low-box counterexample.
