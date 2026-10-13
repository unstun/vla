# Why v59 stalls near 81 seconds

Stage: experiment + analysis, 2026-10-03. Diagnostic only; no navigation source, safety rule, stop protocol or simulation was changed.

**The remaining failure combines an infeasible change of footprint heading, ineffective repeated obstacle-repair searches, and an incomplete v59 timestamp fix across retries.** The final-goal search repaired by v58 is not the expensive operation in this round. The existing support guard is rejecting the new geometry correctly under its contract.

The recording is `v59_realtime_trial01`, nominal round beginning at 81.027099609 native seconds. It takes 1,236.709246 ms of wall time, performs eight replan attempts and succeeds only after the previous curve's nominal expiry. The measured hold at 81.287–82.386 s remains a failure. [Exact captured/replayed evidence](attempt03/diagnosis.json), [line-addressed logs](attempt03/line_evidence.json).

## 1. A valid remaining curve cannot make the proposed turn

At the start of this round, trajectory 1934 has **0.413574 s** remaining and passes the original complete remaining-curve collision/support check. Its endpoint is only **4.497 cm** from the sampled start, below the existing **5 cm** translation requirement. Reusing this endpoint cannot satisfy the window's progress condition. The newly selected target is **3.584 m** from the start. This creates a much larger extension request as the old window runs out.

The warm initializer selects the old endpoint as its nearest join and tests a straight connection to the new target. Its heading is **1.448594 rad (83.0°)**. The unchanged native check rejects **sample zero**, at the join itself, because rotating the footprint puts the front cylinder into an excluded support cell. None of the 42 tested alternative noninitial joins admits a direct connector to this target. Simply choosing another sample of this remaining curve is insufficient.

The front cylinder query is `(7.893085, -6.385762, 3.341046)`. Native support cell `(149, 19)` lacks the approximately 3.042 m ground layer. This is **not a map-origin mismatch**: the selected surface and physical-floor input both contain that layer, but `addGuardedEvidenceFloor()` deliberately declines to add it. The unchanged 0.35 m drop guard finds a neighboring cell at approximately `(7.554685, -6.086811)` with no floor at that level; its available floors are about 0.058, 1.508, 4.539 and 6.075 m. The unchanged step bound is 0.26 m. [Native static guard witness](floor_attempt01/floor.log).

`makeWarmStartSeed()` also invalidates its accepted warm binding on every rejection, including this new connector rejection. Therefore subsequent shorter proposals report `identity_or_owner`, although the old remaining curve passed its safety check. This is cache invalidation, not an immediate cancellation of the executing curve. Its continuation still has a finite lifetime.

Source: [warm rejection and connector](../../runtime/scan80_trajectory_epoch_v59/src/plan_manage/src/planner_manager.cpp#L130), [window admission](../../runtime/scan80_trajectory_epoch_v59/src/plan_manage/src/scan_replan_fsm.cpp#L1579), [drop guard](../../runtime/scan80_trajectory_epoch_v59/src/plan_env/include/plan_env/evidence_floor_fill.h#L38).

## 2. Optimization spoils a clear initializer, then repeats failed repairs

The first shorter target has a valid graph seed. In native replay, the fitted initializer passes the same full-curve collision check before optimization. Optimization then moves it into collision; a search between nearby control points cannot repair it. This occurs with both ordinary height optimization and fixed-height recovery, twice each on the same recorded input snapshot.

For each of those four replay trials, the optimizer makes **three failed searches with exactly identical start/end coordinates within that trial**. The initial fitted curve is clear, the optimized curve is not, and the optimizer returns failure. The first reported collision is around 0.339 s along the candidate. This disproves the narrower hypothesis that the boundary fitter itself introduced this collision. A collision-clear initializer is not necessarily dynamically feasible; this audit does not authorize publishing it without the existing dynamics and final checks.

The failure propagation is concrete: `initControlPoints()` logs **“A-star failed; aborting optimization”** and returns a path vector. Its caller in `rebound_optimize()` does not receive an explicit failure status; it increments the restart count, calls the failed initialization, doubles the obstacle weight and continues. Failed initialization supplies no useful new obstacle constraints, so repeating optimization can return to the same failed repair. An empty vector also represents an ordinary no-collision initializer, so treating every empty vector as failure would be incorrect.

The live round contains **six such failed optimizer searches**: three for the first shorter target and three for its fixed-height retry. The two corresponding log intervals, including subsequent input preparation, are approximately **436 ms and 440 ms**. These are sequential chain intervals, not exclusive optimizer timings. The original inclusive profile records **850.462 ms** in optimization and **260.896 ms** across 13 cloud callbacks; those scopes overlap and must not be added. CPU time closely matches wall time, so host scheduling delay does not explain this spike.

This is not an optimizer safety bypass: later hard PVA/dynamics and full-curve checks still reject unsafe candidates. Another replay case demonstrates why these gates matter: the optimizer reports success while its resulting whole curve is colliding. The production chain does not thereby gain permission to publish it.

Source: [failure return](../../runtime/scan80_trajectory_epoch_v59/src/bspline_opt/src/bspline_optimizer.cpp#L144), [unconditional restart](../../runtime/scan80_trajectory_epoch_v59/src/bspline_opt/src/bspline_optimizer.cpp#L1062). [Repeated-call evidence](attempt03/diagnosis.json).

## 3. v59 still loses the sampled epoch across the recovery chain

This is a defect missed by the v59 validation, and corrects the previous report's description of the final attempt as a fresh restart.

`planFromCurrentTraj()` samples the initial PVA once, then passes those same values through the recovery chain. However, each call to `reboundReplan()` independently checks whether the old curve is **still unexpired now** before retaining its sample time. Once the old curve expires during earlier failed attempts, this check drops the known sample epoch even though the supplied PVA has not been resampled.

| Captured fact | Value |
|---|---:|
| Original PVA sample time | 81.027099609 s |
| Previous curve's nominal expiry | 81.440673195 s |
| New curve 1935 origin/publication | 82.286407471 s |
| Old sample relabeled by | **1.259307862 s** |
| Maximum start-position difference across seven captured seeds | 8.882e-16 m |
| Retry velocity/acceleration differences | Exactly zero |
| Final curve's initial PVA error versus the original sample | At most 2.684e-14 in the respective units |

The final publication is explicitly `sampled=0`. Its initial state is the original sample, not newly measured odometry. Thus completion-time assignment reintroduces the very timing reset v59 was intended to remove, specifically after chained failures outlast the old curve. The stale origin is an additional recovery-continuity defect; the long search chain already explains exhaustion of the old trajectory and the pause.

The 85–90 s single-success handovers and the earlier delayed component tests remain valid measurements. They did not test this expired-parent, repeated-retry path. Comparing observer curves establishes the timestamp mismatch; it does not reconstruct exact controller receipt or heading-freeze timing.

Source: [sample once](../../runtime/scan80_trajectory_epoch_v59/src/plan_manage/src/scan_replan_fsm.cpp#L1173), [recompute origin per attempt](../../runtime/scan80_trajectory_epoch_v59/src/plan_manage/src/planner_manager.cpp#L220). [Captured curve/PVA comparison](attempt03/diagnosis.json).

## Repair direction

1. Carry the sampled PVA and its origin together through the entire retry chain. If intentionally restarting from a current state, resample that state explicitly. Add a regression that crosses the old curve's expiry between retries; a short delayed single call is insufficient.
2. Return explicit obstacle-repair failure and stop repeating an unchanged failed constraint problem. Preserve the existing overall fallback and stop semantics. Any retry reuse/deduplication must account for changed map inputs, PVA, target velocity and height mode; the live maps do change.
3. Extend the local trajectory before its usable span collapses, using a connector with feasible footprint headings around the protected region. Separate an invalid extension from the validity of the accepted remaining curve. Retain all original support, occupancy, PVA, dynamics and final-goal gates; do not remove the drop guard or reinstate v49 hard aborts.

These are recommendations, not implemented or accepted repairs. Native v59 remains frozen; no new version was created in this diagnostic turn. Sustained 30 Hz and physical continuity remain unvalidated.

## Reproducibility and limits

Two CPU-only native replay attempts completed in approximately 37.6 s each; the static floor witness completed in 5.1 s. Frozen native source hashes remained unchanged. Attempt01 failed during preparation because exact coordinate equality rejected an 8.9e-16 m resampling difference; its failure and original script are preserved. Attempt02 established the repeated failure; attempt03 added endpoint/support witnesses and removed a diagnostic narrowing warning.

The replay reconstructs 5,340 body-pose observations, 711 sensor poses, 711 scans and 1,934 curves in original observer order. It freezes the clock inside each query and does not reproduce exact live DDS batching. Diagnostic caches are shared within a snapshot, so these timings are not a claimed live speedup. Raw streams, builds and full logs remain on gpu5070ti; the local return contains compact evidence and source only.

Run from the audit directory on gpu5070ti using the recorded worker Python: `remote_probe.py --attempt NEW_ID`, then `analyze.py --attempt NEW_ID`; run `remote_floor.py --attempt NEW_ID` for the static witness. Never reuse an existing attempt ID. Commands, container image, source identities and artifact hashes are recorded under each attempt.
