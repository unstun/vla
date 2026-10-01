# v28: restore finite paired rebound constraints

Stage: experiment + analysis. Parent: v27. One native optimizer change.
Requested by Dr Sun on 2026-09-28 ("continue with v28") after the v27 archive.

## Motivation

`v27_historical_full01` ended with a native SCAN segmentation fault at about
13.24 s. The saved-input diagnosis in
`audits/2026-09-27_v27_optimizer_crash/RESULT.md` isolates the replayed failure.
At captured seed 269 (fixed height), the rebound callback flags control point 2
after a zero-length intersection but stores no constraint. It then anchors on
point 3 and propagates backward into point 1 by reading `back()` from point 2's
empty list (`bspline_optimizer.cpp:930`). This is the recorded counterexample
`zero_then_valid_empty`. The project repaired this class in `scan_27`. The
guard was lost when the Newton generic materializer restored the pinned
`scan_04` optimizer.

## Exact change

`materialize.py` copies `runtime/scan59_seed_shortcut_v27` to
`runtime/scan60_constraint_guard_v28` and re-applies the 11 frozen
`scan_26 -> scan_27` optimizer hunks (generator
`p2b_execution/reactive_stair/materialize_scan_27.py`, SHA256 `0cd163ca…`).
Each hunk must occur exactly once in v27. The rewritten initial-assignment and
rebound blocks must be byte-identical to frozen `scan_27`, and every other
byte of v27 must be unchanged. Only `bspline_optimizer.cpp` changes. The helper
header already in v27 stays as it is. Its three called functions are
byte-identical to `scan_27`'s. Its later route-projection function remains
unused, so no scan_32 behavior is imported.

Intended behavior differences, all from `scan_27`:

1. A point is flagged only after a finite, normalized base/direction pair is
   stored for it in this pass.
2. A later missing or zero-length intersection no longer erases an earlier
   valid anchor.
3. Propagation copies only from a neighbor that holds a valid pair.
4. A new collision with no committed pair sets `STOP_FOR_ERROR` and ends that
   solve, instead of requesting an empty rebound.

## Preserved

Intersection search, the 1e-5 m length and 1 cm segment thresholds, A* calls
and result handling, cost weights, the 20-rebound limit, height modes,
collision/Unknown/terrain/footprint rules, v27's verified seed shortcut, the
manager's boundary PVA, dynamics, minimum cruise and full-curve gates, and the
controller, emergency hold, executor, map, speed and PD settings. The planner
YAML files are copied unchanged from v27.

## Acceptance plan and expected signals

1. Build in the pinned image with the scan59 incremental cache. Source identity
   is checked before and after.
2. Red/green: the unchanged 13-case constraint contract. v27 is expected to fail
   10 cases, as recorded in the audit. v28 is expected to pass all 13.
3. Saved-input replay with UBSAN and `_GLIBCXX_ASSERTIONS` against v28. All
   captured seeds complete three passes without abort or sanitizer report.
   Failure signal: any abort, sanitizer report or nonfinite constraint.
4. The complete v27 native regression suite on v28:
   - All 11 continuation replays accepted with full gates and negative controls.
   - Repeats identical.
   - The eight unmapped fixture outputs and the five mapped fixture outputs
     compared with v27.
   - Any difference is explained before freezing, not waived.
5. Freeze, then one historical full-route physical trial with the same profile
   as `v27_historical_full01`.

## Claim boundary

v28 removes a known undefined-behavior path. By itself it does not make
optimization succeed: states that crashed in v27 should become ordinary
optimization failures and replans. It does not address the separately recorded
emergency-hold position feedback, measured-pose age or clock-gap issues. The
known 13 cm mapped-protrusion policy is still Dr Sun's pending choice. Only a
physical run can support any navigation claim, and v3 remains the last accepted
condition until one passes.
