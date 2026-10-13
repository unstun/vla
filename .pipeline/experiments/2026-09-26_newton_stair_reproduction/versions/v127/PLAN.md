# MPPI adaptation 3: independent native trajectory validation interface

Stage: experiment + analysis. Dr Sun explicitly parked step 2 and authorized
step 3 from retained native v122, with compilation and testing on gpu5070ti.
Native parent v122; host parent v125. Do not inherit v126 retry reduction.
Local repository is authoritative; /data/sun/vla_mppi_20261009 is the execution
copy and bulk store. No hardware actuation, training, or adaptations 4–5.

## Gap and bounded change

Candidate-boundary/dynamic/epoch checks live inside SCANPlannerManager, while
full-curve map checking is repeated at planner, FSM safety and Nav2 controller
call sites. Introduce a stateless NativeTrajectoryValidator with explicit
boundary, dynamics, collision and publication-epoch entry points and typed
results. Reuse the native cubic/PVA and full 3D/support/heading collision helpers.
This is a reusable validation interface, not a new planar validator, runtime
plugin selector, optimizer, sampling rule or safety policy.

Owned native paths: new plan_manage/include/plan_manage/trajectory_validation.h;
planner_manager.cpp to delegate boundary/dynamics/final collision/epoch checks;
scan_replan_fsm.cpp only to delegate remaining-curve collision validation;
scan_nav2_controller/include/scan_nav2_controller/native_validation.hpp only to
delegate collision validation on its existing private snapshot view. Keep
manager/owner locks, source timestamps, map refresh/publication leases, stage
ordering, logs, retry counts, optimizer and all thresholds unchanged. Keep
minimum-cruise repair in the planner; it consumes the same dynamic verdict.

The separate entry points preserve the real caller contracts: candidate PVA and
dynamics are checked before the final map refresh; collision is checked under
an existing publication/query lease; epoch is checked after collision work.
Checking an executing remainder must not compare it to the candidate's start
boundary or rebase its clock. Reports do not grant command ownership or freshness.

Source inspiration: locally inspected Nav2 MPPI optimizer at
bcc9c48cf468588559d01942b72d511a6b990891 explicitly separates the optimal trajectory
validator from optimization. No upstream validator code or newer ROS API is copied.

## Checks and keep/park rule, declared before execution

1. Verify native diffs against v122; its full outer retry chain is preserved.
   Check every non-validation region and original configuration unchanged.
2. Build all 14 packages and run original controller/terrain tests remotely.
   Compare original native manager/helper verdicts with the new interface on
   deterministic valid/invalid PVA, velocity/acceleration, epoch and real-map
   collision cases. Verify source curve immutability and typed failure reasons.
   Preserve original sampling, threshold equality and invalid-input behavior;
   do not silently add a numerical repair in a refactor.
3. Run real recorded-map successful-curve bit parity and original exact proof,
   stale observation, independent controller clock, wrong/future/stale pose,
   map fault, immutable query and publication-pin regressions on both installs.
4. Freeze component-checked v127 before physics. Run up to two independently
   initialized same-host pairs against v122, original Building corner, CPU
   Newton, 90 s bound / early arrival and measured PD hold. No concurrent heavy
   work during physics. Source/install/image receipts are required for each arm.
5. Keep only if fixed-input verdict/curve equivalence and original safety tests
   pass, both candidate trials arrive and hold without falls, median P95 is no
   more than 10% above baseline, and median longest pause no more than baseline
   plus 1 s. A candidate navigation failure can stop early and parks v127.
   This step seeks modularity and testability; no speedup is required or implied.
   Trials do not establish population reliability or Jetson qualification.

Preserve all attempts and frozen predecessors; retain v48 as the broader
experimental reference. Return only compact metrics/logs/hash locators (target
<15 MB), with heavy evidence on gpu5070ti. Do not remove the existing Git index
lock, stage unrelated changes, or treat source freeze as physical acceptance.
