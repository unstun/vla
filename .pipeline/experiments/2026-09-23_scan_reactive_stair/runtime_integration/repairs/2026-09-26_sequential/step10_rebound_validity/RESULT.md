# Rebound constraint validity repair

scan_27 changes only optimizer constraint bookkeeping and adds a small paired
constraint helper. Each control point owns its intersection-valid flag. A
successful current point must commit a finite, normalized base/direction pair
before marking itself as a propagation source. Propagation accepts only a
fresh valid pair. A later missing or zero-length direction does not erase an
earlier valid seed. Both duplicated assignment implementations and the short
segment branch use the same commit contract.

When a new collision produces no committed constraint, the actual rebound
callback sets STOP_FOR_ERROR. The caller resets stop state before each cost
calculation and ignores the callback's boolean; the error field therefore must
be set in that callback. The native early-exit/outer-loop chain then cancels
this optimization without requesting another rebound.

The native fixture includes verbatim source blocks and the original
ControlPoints declaration. Only map, AStar return and ROS logger are doubles.
NaN initialization makes the missing-intersection case deterministic; it does
not prove the real replay read an uninitialized value. Ten final cases cover
empty/single-node repair, missing intersection, missing/zero intersection after
a valid one in both relevant implementations, all-zero direction, valid normal
constraints, no collision and the valid short-segment branch. The old build
fails seven cases; three positive controls pass. scan_27 passes all ten in
Foxy, as well as the nine-case preceding local run. Source blocks and manifests
match the candidate. Independent review found no remaining blocker.

The full Foxy build and461-file install identity pass. In the same recorded
input, the first optimization now has one final cancellation with the explicit
no-valid-constraint error, versus21 cancellations/rebounds before. It exits
immediately afterward. All77 sampled seed chains still pass, all77 optimizer
attempts fail closed, and zero moving splines appear. Callback totals are not a
performance comparison. This verifies the local failure-state repair through
the complete runtime chain, not stair navigation or curve feasibility.

Next, an isolated post-failure observer compares the original curve point at
different footprint headings, and compares geometry-preserving global knot
scaling derived from the native dynamic bound. It does not adopt retiming or
publish a fallback trajectory. PVA changes, the fixed.8s preview and the10000
sample cap must be reported separately. All limits and Unknown blocking remain.
