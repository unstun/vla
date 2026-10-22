# v250 — continuous support-gap query

Frozen parent: v249. Stage: experiment + analysis; zero physics steps.

The inherited mask expanded uncertain source squares into target squares and
then treated every continuous center in a target square as blocked. This
second quantization overreached the original 0.35 m domain. Bins now select
candidates only; exact continuous center-to-original-square distance decides
the same 0.35 m/0.26 m refusal. Source squares, source bytes and their conservative
interpretation remain unchanged. No endpoint is moved.

Original A02 mesh/PCD inspection establishes a false positive: its limiting rear
disc has 0.378376919 m actual distance to uncovered mesh, 28.38 mm above the hard
radius. None of the six triggering source squares intersects that disc.
The same repair permits G07 seed headings 0/pi; actual perpendicular mesh gaps
at 0.314982632 m remain refused.

The saved G07 prefix reconstructs a successful local connection using this
isolated repair (61.3 ms component measurement). This is not a physical run or
exact historical asynchronous mapper-state reproduction. Six CTest targets/
42 cases and 1,442,401 synthetic geometric queries pass. Composed qualification
and the final full-curve/stale negative checks belong to v251.
See the [combined audit](../../audits/2026-10-18_v249_generic_mechanism_repairs/RESULTS.md).
