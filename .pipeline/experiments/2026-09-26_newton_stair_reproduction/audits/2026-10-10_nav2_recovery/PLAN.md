# Diagnose and repair shared Nav2 recovery

Stage: experiment + analysis. Dr Sun authorizes a focused recovery fix and
repeated gpu5070ti simulation. The follow-up question asks about pre-MPPI v114;
include unchanged v114 as an explicit control, separate from diagnostic v122.
Use the original installed v114/v122 source receipts, CPU Newton, original scene,
policy, sensors and safety/stop thresholds. Keep all previous frozen versions.
No adaptations 2–5, hardware motion or training. Main task stays in progress.

## Ranked hypotheses and predictions

1. Route/cancel handoff race: recorded new binding is accepted or rejected while
   the native FSM still handles the previous stop; deterministic ordering replay
   reproduces a missing target. Preserving that transition fixes the replay.
2. Replacement geometry/search failure: new owner is correctly admitted, but
   original search cannot produce an admissible replacement; same-input native
   replay fails before publication. A handoff-only fix will not solve this case.
3. Stop confirmation mismatch: physical evidence exists but one state/identity
   fails to release, or full-body stillness differs between gates. Recorded
   state/stop replay pinpoints the unmet condition without changing thresholds.

## Boundary and acceptance

First reduce the already reproduced v122 recovery failures to native callbacks
and original event traces. Expected affected modules are the controller/FSM or
mission gateway only after a failing transition is isolated. Record exact owned
paths and one logical change before editing; use the next unused integer version.
Add failing regression at the actual callback/state boundary, apply minimal fix,
run inherited negative ownership/cancel/freshness tests and original physics.

Use three fresh unchanged pre-MPPI v114 diagnostic runs before fixing, then a
predeclared six-pair counterbalanced comparison of the chosen frozen baseline
and final candidate. A pilot may expose another defect; preserve it and increment
version for each subsequent logical repair. Do not replace failed final runs or
claim repair from component tests alone. Record arrival, stops/restarts, exact
owner/admission sequence, falls, timeouts and latency. If repeated missions still
fail, continue targeted diagnosis within this recovery scope.

All heavy builds, replay and physics run sequentially on gpu5070ti /data. Local
source/configuration and compact verified output are authoritative. Hash sync
before execution; preserve all raw data remotely with returned locators. No
concurrent builds during timed simulation. No automatic commits or lock removal.
