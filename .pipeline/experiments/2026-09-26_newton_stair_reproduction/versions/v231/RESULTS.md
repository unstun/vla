# v231: one failed physical execution of frozen v230 navigation

Execution package only; navigation is frozen v230 (`e9f8bec0`), including v229
height alignment (`420a0ff9`). Original v219 route and gates, unchanged RL and
0.35 m collision/support guards. The single authorized attempt failed when
controller_server exited with SIGABRT (-6) near 46.7 s. Recording continued to
its original 600000-step bound without arrival or a terminal finish request.

The frozen manifest records the pre-run state, not the eventual outcome.
See [full results and comparison](../../audits/2026-10-17_v230_physical_comparison/RESULTS.md).
Physical acceptance remains v219/v220. No physics retry was performed.
