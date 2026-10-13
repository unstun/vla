# v184: stateful completion of a local curve

Stage: experiment and analysis. Parent: Mac v176, identical native baseline to
Linux v177. User authorization, 2026-10-13: fix the last-centimetres crawl,
keep the RL model unchanged, inspect open-source approaches, then repeat the
complete original-start route. No training or real-robot actuation.

Change only the local tracking completion policy: capture an expired spline
inside 0.03 m rather than 0.02 m, then latch zero for that curve. A newly accepted
curve, changed owner/map identity, goal or cancellation resets this latch.
An identical curve retransmission retains it. Mission goal yaw/XYZ tolerances,
measured stillness, planner collision/PVA/freshness admission, stop proof,
locomotion weights/gains/observations, map, route and start remain unchanged.
The new feature defaults off; the versioned profile explicitly enables it.

This follows Nav2 stateful goal-checking semantics, adapted to local curves.
It does not declare mission success or certify physical stillness. Three cm is
an experimental tolerance: it covers the recorded 2.19 cm plateau yet remains
below the 5 cm recovery prefix. Do not treat it as an RL minimum-speed solution.

Prospective checks:
1. Actual Foxy C++ tracker: retain inward motion at the recorded 4.9246 cm error;
   stop inside 3 cm; suppress later error-induced restart on the same curve;
   allow new curves/owners to move; reject stale/cancelled curves; preserve
   default-off behavior, final-yaw alignment and emergency stop.
2. Rebuild the controller and bridge, rerun controller tests and generated
   profiles; inspect the actual loaded library and profile in the ROS graph.
3. Freeze source before physics. Run the original Building/historical_full
   start and goal, first once locally, then at least five serial full routes on
   gpu5070ti if its existing admission gate permits. If occupied, continue the
   separately labelled Mac cohort. Retain every failure and its original ID.
4. Inspect actual RL inputs and native curves, not only arrival: flag any
   expired-curve correction within 5 cm with nonzero horizontal command below
   0.1 m/s lasting over 2 s. Compare against the old 9.155 s plateau. Record
   stop/recovery counts and zero-command drift separately. Five arrivals alone
   do not qualify the fix. Do not pool host cohorts.

Source of truth: local VLA version directory and frozen manifest. Remote copies
must match the source manifest; raw results return verified compact evidence,
with heavy archives on gpu5070ti. No source mutation after freezing.
