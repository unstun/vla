# v62: retain the sampled epoch across the complete retry chain

Stage: experiment + analysis, 2026-10-04. Parent frozen v59; v60/v61 are display-only and are not native parents. This corrects the already authorized trajectory-time contract after the 81-second audit. Dr Sun instructed using the Mac while gpu5070ti is occupied.

## Checkable change

Capture a checked old-curve sample time once when `planFromCurrentTraj()` samples its initial PVA. Carry that origin through all `callReboundReplan()` calls, shorter-prefix proposals, warm/native attempts and fixed-height recovery. Parent expiry during a failed solve must not turn the same retained PVA into a newly sampled state.

The manager keeps its current derivation for callers without an explicit origin. A supplied origin must have a compatible clock and must not lie in the future. Stack-owned state ends with the planning round; no member/static cache or automatic future handover is introduced. Existing elapsed-candidate rejection and every PVA, dynamics, full-curve occupancy/support, goal, yaw and stop gate remain.

## Owned native files

- `plan_manage/src/scan_replan_fsm.cpp` and its header: capture once and pass the value through every recovery call.
- `plan_manage/src/planner_manager.cpp` and its header: reuse the existing sample-validation code as the capture method and accept the explicit checked origin.

Controller, optimizer, map/search, target selection and production configuration remain exact v59. The separate repeated optimizer-search and unsafe-connector problems are not folded into this timing version. No v49 solve budget or stop change.

## Verification

1. Compile/run the actual parent FSM/manager retry path with controlled planning failures and ROS clock advancement across the recorded parent expiry. Preserve the failing parent result.
2. Run the same path for v62. Every retry and prefix receives81.027099609s even after81.440673195s; a new round derives its own sample. Cover initial/odometry calls, future/mismatched clocks and parent expiry before initial capture.
3. Build the complete native workspace on the Mac in the already cached, exact ROS image. Keep build products ephemeral in Docker; return compact request, logs and hashes.
4. Run inherited synthetic native/controller/cache/goal/endpoint/physical-role checks available from existing local sources. Recorded-map and physical tests need their original qualified inputs; report their actual availability and do not substitute synthetic data for those acceptance gates.
5. Freeze only after declared qualification is satisfied. Record source/patch/scope and pending physical acceptance separately. v48 remains the runnable reference and30Hz remains an open target.
