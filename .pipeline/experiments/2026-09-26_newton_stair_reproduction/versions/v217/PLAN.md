# v217: event recovery from local trajectory starvation

Parents: frozen v212 event-planning navigation, v216 supported PD transfer.
The user explicitly requests one full historical-route physics/video validation.

Diagnose captured v212 failures against the v210 route updates. Do not change
PCT/SCAN geometry, maps, speed/heading policy, goal tolerance or retry count.
After the first executable spline, expose a missing or expired braking curve
to ordinary Nav2 recovery after 0.75 s. First map/reference admission keeps its
original 5 s budget (v212 first route at 12.27 s, first local round at 14.59 s). Keep PlanOnGoalChange: initial
goal, changed goal or ordinary recovery; no periodic global planning.
Preserve the existing 1 s recovery Wait and six retries, terminal stand timeout
non-retry semantics, and terminal braking without false starvation.

Owned code: LocalMotion (wait/expired-curve lifecycle and exception), controller
configuration and regression tests. Existing v212 BT remains identical.
Validation: deterministic controller starvation/recovery tests and old tests on
gpu5070ti; verify installed-source hashes; one original-start historical_full
physics trial, report 45-55 s SCAN success, foot forces, tilt, final pose/PD.
Record all failure attempts. Render actual captured states; do not resimulate for
video. Return compact reports/provenance and regular MP4, keep large raw data on
5070Ti. No default promotion without unchanged full-route gate success.
