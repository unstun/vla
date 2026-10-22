# v280 Native integration: physical boundaries and equivalent source cache

Compose frozen v272 with the independently tested v277 exact GPMP boundary
states and the v279 conservative height-envelope cache. Local source owns all
six changed native files. The source-surface hard model, support, ENV225, RL,
requested poses and 0.35 m / 0.1 s protocol stay unchanged.

Retain GTSAM's existing default EliminatePreferCholesky: installed
HessianFactor.h documents automatic QR fallback for constrained cliques.
NonlinearEquality fixes both requested boundary state vectors. No new solver
framework or tunable penalty is introduced. Both GP orders must preserve exact
requested XY/yaw, including any correctly rejected intermediate trajectory.
The six development route controls need not all become feasible; their actual
first-pass outcomes are retained. The fixed50 cohort establishes coverage.

The source cache proves positive clearance over a true 0.01 m height interval;
nonpositive bounds fall back to the unchanged exact query. Require 114,477 full
source-value comparisons, 24,000 height-boundary cases, existing cached/edge/
rotation/legacy/support/ENV tests, 74 + 97 native/plugin tests, six boundary
contracts, six hard controls and H00/measured-A02. Freeze only after those
component checks. Then execute the unchanged original52 and fixed50+3 once each,
using independently frozen v276 material auditing. Physics requires the original
coverage, first-pass, raw margin and <=1.5 s median gates under this one version.

Reuse the same per-plan StaticSolidQueryCache in the existing GPMP physical-cost
callback. Previously search and final checks used it, while every optimizer
iteration repeated uncached exact solid queries. A free certificate only skips
the zero physical residual; collisions still compute full exact margin/gradient.
No factor, residual, cost weight or acceptance value changes from this reuse.
