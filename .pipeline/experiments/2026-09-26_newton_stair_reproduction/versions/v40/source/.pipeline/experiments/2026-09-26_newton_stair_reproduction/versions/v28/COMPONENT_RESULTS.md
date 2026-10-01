# v28 component results

All runs used the local pinned image `sha256:f7363cc3…` (ROS 2 Humble,
amd64 emulation) on 2026-09-28. No physical episode is part of this record.

## Build

`runtime/scan60_constraint_guard_v28` built in 16.7 s with the scan59
incremental cache (`build_result.json`: passed, source unchanged). Only
`src/bspline_opt/src/bspline_optimizer.cpp` differs from v27. The 11 applied
hunks reproduce frozen `scan_27`'s assignment and rebound blocks byte for byte.
The remaining compiler warnings are the optimizer's existing unused-parameter
and VLA warnings. None of them is in the restored blocks.

## Red/green constraint contract

The same unchanged 13-case harness ran against both native trees
(`constraint_red_v27/`, `constraint_green_v28/`):

| Tree | Pass | Fail | Aborts |
|---|---|---|---|
| v27 | 3 | 10 | 2 (`zero_then_valid_empty`, `initial_zero_empty`) |
| v28 | 13 | 0 | 0 |

The v27 result matches the audit's recorded red run exactly.

## Saved-input seed replay

`runs/v28_seed_replay01` compiled attempt04's unchanged probe (UBSAN,
`_GLIBCXX_ASSERTIONS`, crash backtrace) against v28. It replayed all 32 captured
seeds three times: 96 results, exit 0, with no assertion, sanitizer report or
stack dump. All replays return `ok=0`, as v27 did for the 31 seeds before its
abort. The replay uses the final map with a fresh clock, not the live schedule.
Seed 269 now fails normally ("First three control points are in obstacles")
in every pass instead of aborting. The new `rebound_no_valid_new_constraints`
path fired six times.

## Native regression

`runs/v28_native_regression01` reran v27's unchanged suite (433 s):

- **Continuations:** all 11 manager continuation replays are accepted, with
  boundary PVA, full-curve and negative controls. Their complete JSON outputs
  are identical to v27's, as are the accepted prefixes (for example, v26
  1.847894 m and v19 2.931893 m). Repeats are identical.
- **Fixtures and contracts:** all eight unmapped and five mapped fixture outputs
  are identical to v27's. The ground and body-support contracts pass.
- **Guard activity:** outputs are identical, but four logs are not. After
  normalizing timestamps and timings, `v23`, `v23_repeat`, `v26` and
  `v26_repeat` differ from v27 at one solve each, where the new
  `rebound_no_valid_new_constraints` abort fired after an "A-star error":
  - In `v26`, v27 requested an empty rebound and then failed on "First three
    control points are in obstacles".
  - In `v23`, v27's empty rebound gave `first_optimize_step_success=1`. The
    resulting curve was then refused by the manager's full-curve gate
    (`final_spline_rejected status=1`).

  v28 ends both solves at the abort. The later fixed-height recovery and the
  accepted curves are unchanged. The only other normalized difference, an A*
  "0.2 second time limit exceeded" line in `v23`, already differs between v27's
  own `v23` and `v23_repeat`. It is wall-clock variation under emulation. v28's
  `v23` and `v23_repeat` logs match each other.

## Independent review

`runs/v28_native_regression01/independent_review.json` records a read-only
trellis-check review. It passed all eight checks: only the optimizer changed,
the edits are byte-identical to scan_27's, flags are set only after a paired
write, no unchecked empty reads remain, zero commits fail closed, the replay
supports the mechanism, the evidence is consistent, and the claim boundary
holds. Its non-blocking concerns are recorded as limits:

- **Error not always read:** `STOP_FOR_ERROR` is read only if L-BFGS consults
  `earlyExit` before converging on the same step. Otherwise the unchanged 2/3
  post-check decides. The manager's full-curve gate still applies. The same
  window already existed for `STOP_FOR_REBOUND`, and no test targets it.
- **No initial-assignment abort:** `initControlPoints` has no zero-commit abort
  of its own. This is unchanged from scan_27 and v27, and bounded.
- **Crash-freedom only:** the seed replay shows only that nothing crashes. That
  the live crash is removed remains an inference until a live run.
- **Unused mount:** the unused `/probe` mount in both regression requests is
  harmless.
- **Log counting:** "rebound." log lines also count `STOP_FOR_ERROR` aborts.
- **New acceptance condition:** `appendReboundConstraint`'s |norm - 1| <= 1e-6
  check, inherited from scan_27, is a new acceptance condition that rejects
  only degenerate directions. No threshold, weight or YAML value changed.

## Boundary

These are component outcomes. They show that the replayed undefined-behavior
path is closed and that the prior accepted continuations are preserved. They
do not show complete-floor navigation, arrival or final PD handoff. The
emergency-hold feedback, measured-pose age and clock-gap issues remain open.
