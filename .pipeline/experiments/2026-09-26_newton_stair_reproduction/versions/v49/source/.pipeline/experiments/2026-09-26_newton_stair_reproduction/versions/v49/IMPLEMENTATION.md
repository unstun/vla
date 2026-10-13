# v49 implementation boundary

Parent: frozen v48. One logical change: bounded local solve/recovery. Source is
`runtime/scan72_solve_budget_v49`; `changes.patch` and `materialize.py` reproduce
all 99 native files exactly from the 98-file parent. No upstream source is edited.

The FSM starts one steady-clock deadline before target selection. All nested
warm attempts, A*, fixed-height recovery, shorter prefixes, outer retries,
L-BFGS objectives/line searches and retiming share it. Compute stops at 20 ms.
Final full-curve validation and message preparation can use the remaining time
to 25 ms. A failed final check cannot reset the compute allowance. Raw voxel
classification checks the clock every 64 offsets; other collision samples,
search expansions and solver loops have checkpoints.

A typed timeout unwinds the complete call chain. L-BFGS work buffers and the
temporary refinement weight/height mode have scope cleanup. The old published
curve and route progress are restored if a candidate was committed internally
but has not been published. The last deadline check is immediately before
publishing a fully serialized B-spline; there is no timeout rollback after
publication. No partial spline or unchecked seed can enter the controller.

Continuation requires the same run, epoch, request, goal, route, command,
generation, map epoch/revision, map instance, exact goal, trajectory ID and
start stamp. It also requires nonexpired monotonic trajectory age and a complete
remaining-curve check against freshly drained inputs under the original occupancy,
heading, support and freshness rules. It never publishes or restamps that curve.
If this check fails or cannot finish by 25 ms, the same command gate receives
`native_solve_timeout` and the original emergency B-spline is published immediately.
The original backend must still confirm controller hold and measured stillness.

The solver budget is cooperative, not an operating-system real-time guarantee.
Atomic sensor message application, allocations, ROS publication and thread
scheduling cannot be interrupted mid-operation. The measured round includes
recovery; any overshoot must be reported. Independent safety checking remains
complete, and any solve it requests uses the same deadline mechanism.

`unchanged_contracts.json` records exact parent configuration/backend equality.
The native final goal, yaw, PVA, dynamics, minimum-cruise and whole-curve gates
are unchanged. Checks with the deadline inactive compare original captured
geometry exactly; deadline checks exercise interruption and both safe outcomes.
The first test attempt is retained: an uncached full-curve check exhausted its
5 ms reserve and correctly stopped, contrary to that test's continuation
expectation. The corrected positive fixture populates the normal per-callback
raw classification cache before checking continuation; invalid and expired
inputs remain negative tests. The original attempt source is preserved beside
its build evidence. Inline review/checking follows the session's explicit mode.
