# v251 — shared oriented gap geometry; offline qualified

Frozen parent: v250. Stage: experiment + analysis; zero physics steps.

GPMP now evaluates its feasibility residual against the same oriented native
gap geometry as final admission. Legal support has zero feasibility residual.
ENV225's existing edge channel also receives that same evidence in PCT search,
GPMP and SCAN; its 0.15 m soft target/weights and original atlas bytes are unchanged.
The 0.35 m hard radius, 0.18 m offset, height limits, RL and 0.1 s sensor/deadline are
unchanged. No route names, endpoint snaps or component exceptions enter code.

| Gate | Result |
|---|---|
| Unchanged 12 x 5 matrix |55/60 native static/cold-local admissions |
| First GPMP static admission |55/60; all 55 admitted routes first attempt |
| Graph fallback among admitted calls |0 |
| B09 |0/5, `pct_no_route`, retained in denominator |
| Independent historical H00 |First GPMP, static and cold SCAN pass |
| PCT/physical-factor tests |6 targets, 43 cases pass |
| Native regression |12 targets, 97 cases pass |
| Native/export support parity |10855 queries, both mismatch counts 0 |
| Hard-domain parity versus v250 |40000 real-source queries, 0 mismatches |
| Synthetic exact geometry |1442401 queries pass |
| G07 original-time prefix |Local curve clear; stale negative still refuses |
| A02 actual recorded poses |Both now Free in native C++ |

Support clear queries increase 9910→9973 through corrected target-cell geometry.
H00 goal max-coordinate error is 4.16e-8 m. Successful matrix calls take
0.563–1.071 s globally (median 0.748 s), 9.30–34.24 ms first local (median 19.54 ms),
under the recorded CPU-limited offline component protocol. This is not a
real-time scheduling claim. Saved G07's longer near-goal local attempt takes
0.549 s with shared cost; the isolated v250 connection takes 0.061 s. Preserve
that difference rather than treating both as cold-start timing.

B08 still has an independent raw-solid reference margin of -0.1903 m;
component admission does not certify its full physical route. ENV margins
cap at +0.15 m; unknown observation coverage remains explicit in each row.

Source, installed binaries, actual runtime fixtures and evaluator binaries
are SHA-bound. [Independent qualification receipt](results/acceptance_receipt.json)
is separate from the source/build receipt. Full report, first refused edge,
reconstructed global poses and retention ledger:
[combined audit](../../audits/2026-10-18_v249_generic_mechanism_repairs/RESULTS.md).

No new physical trial, commit, archive or baseline promotion. Selected physical
baseline remains v232 / v233; previous v248 R11 single physical pass remains
separate evidence.

Subsequent physical follow-up: frozen execution v252 runs A02/G07/R11 once
each. G07 and R11 pass complete route/terminal PD; A02 remains a discrete
search no-route despite continuous support passing. See the
[physical report](../../audits/2026-10-18_v251_physical_generalization/RESULTS.md).
This appends later evidence without changing v251's frozen offline manifest.
