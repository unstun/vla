# v280 Native source, boundary and cache integration

Frozen manifest: `b4dd7a47dea57318ffb9671a2c9fedce36e17e064f7657f60c3f143d5d586ac9`.
All 41 returned frozen files and four inventory hashes verify locally.

## Changes

- Reuse frozen v279 exact-equivalent source-cache proofs.
- In physical-support mode, use GTSAM NonlinearEquality for GPMP endpoint states;
  requested XY and yaw cannot drift under a soft prior. Keep the default solver:
  installed EliminatePreferCholesky automatically selects QR for constrained
  cliques. Both GP orders and legacy priors are covered.
- Reuse the same caller-owned query cache in GPMP's existing physical residual
  callback. Free poses keep exactly zero residual; violated poses still compute
  full exact margin/gradient. This removes repeated uncached geometry queries.

## Verified component boundary

114,477 full source comparisons are bit-identical; 24,000 height-boundary checks,
all cache/edge/rotation and old solid/support/ENV comparisons pass. 74 plugin +
97 native tests pass. Exact boundary identity passes 6/6 on the new installation
and fails 0/6 on the actual read-only frozen v272 installation.

This does not imply all six hard endpoint routes became feasible: CU08 still
collides in both GP orders, and CU13 WNOA fails support association. CU13 and
CE04 WNOJ, plus CE04 WNOA, now pass first attempt (3/6 targeted cases). Preserve
those rejected outputs. Full-cohort smoothing acceptance is measured in v281.

| Control | CPU2 global seconds | First static admission |
|---|---:|---|
| A04 | 1.384567 | pass |
| G05 | 1.427281 | pass |
| D07 | 1.638573 | pass |
| S04 | 0.091787 | pass |
| E02 | 0.124869 | pass |
| E03 | 0.105562 | pass |

H00 original full offline chain passes (global 1.422744 s); unchanged measured
A02 passes first GPMP/static. Initialization remains separately reported at
approximately 3.8 s. Native threshold 0.35 m, source/support/ENV inputs, RL and
0.1 s scans are unchanged. v281 original52/fixed50+3 is running; no full matrix,
physical-route success or new video is claimed here.
