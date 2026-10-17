# v221: shared PCT / SCAN traversability

## Goal and scope
Implement the v221 deliverable defined in ../10-17-pct-scan-traversability/prd.md. Own R1-R3, R8-R9 and route admission/cache validation in R5. Dr Sun explicitly added shared environmental scoring and clarified that boundary-following is acceptable when the swept body retains sufficient clearance; do not impose road-centering.

## Acceptance
Pass parent A1-A3, A5-A6, A8 and the v221 portion of A7.
Preserve v219 and all prior source/results. No new physics or training is included in this implementation gate.

## Authorized v232 repair, 2026-10-17

After v231's controller SIGABRT, Dr Sun specifies:
1. Stop the rebound objective immediately on STOP_FOR_ERROR/STOP_FOR_REBOUND.
2. Use finite geometric/measured yaw only for soft environmental scoring;
   preserve original hard heading freshness and admission.
3. Contain standard/unknown exceptions inside native callbacks and complete
   optimizer entries, reporting ordinary failure rather than aborting Foxy.
4. Detect actual critical child exits and steady-time node loss, fail the
   matching task, and close FAILED finish without waiting for the physics cap.

Require delayed>100ms/zero-tail/shared-cost regression, cancellation that cannot
become convergence, live two-thread callback survival, real SIGABRT with live
launch parent/running Action/paused ROS time and matching finish, plus epoch,
late-acceptance, cleanup, shutdown, hard-parity and Building-admission controls.
The request ends at the offline gate and report; no physical rerun is included.
