# v13: remove discarded legacy trajectory initialization

Parent: frozen v12. Stage: experiment + analysis. Repair authorized.

The v12 physical run is killed by container OOM. Its exact previous-trajectory
continuation also aborts in a bounded native replay after an earlier call warms
the manager's static first-call flag. A single-call fixture missed this branch.

The manager computes a legacy polynomial/previous-trajectory seed, then
unconditionally discards its points, timing and boundary derivatives when the
native AStar seed is installed. The legacy previous-trajectory branch uses an
unclamped current time. After a short curve expires it can have zero remaining
segment points but a one-element arc array, then access `size()-2` or endlessly
reduce sampling distance. Those computations do not feed the accepted curve.

One production change: remove the discarded initialization block. Keep the
existing native AStar seed, original arc-length resampling, hard PVA fit,
optimizer, dynamic/cruise admission and full-curve collision checks unchanged.
Do not add an alternate planner or increase the production memory limit.

Only `planner_manager.cpp` changes in `scan51_seed_init_v13`. The function
signature remains compatible. The original 66-scan fixture and native flat
recorded-curve cases check unaffected initialization; the captured v12 curve 6
continuation must survive multiple calls with boundary assertions enabled and
produce a valid curve. Then repeat bounded physical stair execution.

Prior evidence: `audits/2026-09-27_v12_process_exit/` and
`runs/v12_legacy_seed_repro02/`; attempt01 records a diagnostic compile-memory
failure and is not a runtime reproduction. Docker's primary OOM event is saved.
