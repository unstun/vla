# v50: return to v48 and preserve trajectory continuity

Stage: planning + analysis. Dr Sun explicitly selected v48 as v50's direct parent
on 2026-10-01 and discarded v49's aggressive solve-timeout approach. Inline work;
the existing session choice to skip a Trellis task remains in force.

## Lineage and current state

- Direct integration and native-source parent: **v48** (`scan71_remaining_curve_v48`).
- Prepared native workspace: `runtime/scan73_v48_continuity_v50`.
- All 98 native files currently match v48 byte for byte. The runtime package is
  copied from v48 with only version/path adaptation, including `native_graph.py`
  and the complete unchanged backend package.
- v49 remains frozen, rejected, and outside v50's ancestry. Its files and failure
  manifests are bound by `v49_preservation.json`. The earlier proposed v49 repair
  is superseded, not applied. No v49 deadline/checkpoint/timeout state is inherited.
- v50 is **prepared, unfrozen, unbuilt and unrun**. It has no performance or
  navigation validation. No parent build result or qualification is relabelled
  as a v50 test. The runnable reference remains frozen v48.

v48's run travelled 29.7936 m along the measured 3D path (28.4787 m in XY),
climbed the stairs and retained progress. This is not complete-route acceptance:
it still measured 15.8585 Hz attempts and had no final arrival/hold result.

## What the existing v48 data changes about the diagnosis

Read-only analysis of all 1,311 completed rounds is saved in `analysis/`.
For the 113 warm-only rounds lasting at least 100 ms, **93.06% of their aggregate
wall time occurs before the first replan-start input drain has completed**.
This span includes target selection, final-goal neighborhood A*, the first input
refresh, logging and scheduling; it is not isolated optimizer or CPU time.
Across all 1,207 warm-only rounds, the same fraction is 89.77%.

A directly traceable example at simulation 55.906 s lasts 199.253 ms. The log
records a 134 ms final-goal neighborhood A* search before the manager starts,
then a 2.116 ms warm-seed check. A later optimizer diagnostic reports a 0.030 ms
iteration and 29.679 ms total including work surrounding that iteration. This
shows why another optimizer-wide deadline is poorly targeted. Existing logs
cannot fully isolate map update, scheduling and output costs.

The 1,090 ms extreme also contains several native attempts and fixed-height
recovery. Faster common target selection alone cannot be claimed to eliminate
that distinct tail. Both groups need coverage.

## Safer direction to evaluate

**First target the repeated work before warm initialization. Preserve the v48
execution and failure policy.** Treat 20–25 ms as a performance measurement target,
not a new reason to stop, reject an otherwise valid curve, or close a command.

1. Separate target selection/final-goal neighborhood search from input application,
   raw-contributor queries, seed validation, optimization/refinement, final checks
   and diagnostics. Capture wall time and thread CPU time so scheduler delay is
   not mistaken for solver work. Prefer profiling unchanged v48 or bounded recorded
   replays; establish complete input/state capture before claiming paired replay.
2. Evaluate an exact early rejection of futile goal-neighborhood searches, or a
   narrowly justified reuse of search work, before changing solver policy. A
   conservative precheck must prove that the original search has no eligible
   endpoint; an arbitrary distance cutoff is not a proof. Reuse needs explicit
   goal/route/map/input/pose/time validity and must preserve endpoint selection.
   If equivalence cannot be demonstrated, retain the original search.
3. Profile audit Candidate 4's bounded raw-contributor caching as another option.
   Cache only raw-source classification with complete invalidation. Never cache
   final collision, stair support, pose freshness or safety verdicts. Measure
   diagnostic output before considering deferred output. Select one measured
   change for the final v50 implementation rather than combining guesses.

These are candidates, not implemented optimizations. A worker-thread/asynchronous
planner is a separate, larger design: it needs immutable input ownership, fresh
publish-time validation, stale-result rejection and exact PVA handover at the
actual curve-switch time. Do not introduce that architecture as an unreviewed
performance shortcut in this prepared branch.

## Invariants and acceptance

- Keep feasible-window reuse and guarded warm-start initialization from v48.
- Preserve original search fallbacks and original stop/admission protocol.
- Keep exact final goal/yaw, PVA/dynamics, minimum cruise, complete collision and
  stair-support checks, controller/physics/sensing, freshness and command ownership.
- A slow solve by itself does not introduce an emergency-stop condition.
  Original safety stops still apply if the executing curve becomes unsafe,
  expires or loses valid ownership/evidence. Do not restamp an old curve.
- Pair the fast warm case, slow warm/pre-manager case, multi-retry extreme, stair
  transitions and new-obstacle/invalid-evidence cases with v48. Compare accepted
  geometry, boundary PVA, dynamics, decisions, original stop handling and latency.
- Test the actual backend gate handler and controller-hold/measured-stillness
  flow, not just the existence of an admission or emergency-spline message.
- Before any physics trial: complete source/package manifest, all runtime entry
  files present, native and dependency hashes verified, source frozen and all
  attempts preserved. A missing launcher must fail preflight, not first appear
  after launch.
- Report successful new-plan rate separately from attempts, controller rate,
  pauses/stops and physical progress. An early stall invalidates a latency win.
  Use matched progress segments and repeated runs for performance comparisons;
  v48's one 29.8 m run is a reference, not a statistical acceptance threshold.

No new remote execution or timing policy is introduced by this planning step.
