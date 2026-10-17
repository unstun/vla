# v226 recorded-input results

Status: component-validated GPMP interpolation correction. Parent v225 is
frozen; no physics or source/display promotion. No weight, heading, convergence
tolerance or hard-predicate changes.

With environmental scoring configured, safe cost interpolation uses integer
cell anchors and convex weights. The unconfigured objective retains upstream
arithmetic. Its graph and smoothed route CSVs are identical to v225's legacy
outputs. A regression directly exercises the old 0 -> 50 half-cell jump,
corrected continuity, grid samples, gradients and clipped-domain behavior.

Attempt02: nine packages; 165 colcon records comprise 145 distinct test cases
plus 20 wrappers, zero errors/failures/skips. Attempt01's unsupported C++17
std::clamp in the inherited C++11 map target is retained; the fix uses min/max
without changing the target's language standard.

| Building result | Unconfigured | Shared scoring |
|---|---:|---:|
| Search + smoothing | 0.0341 s | 0.6386 s |
| Integrated environmental cost | 0.274689 | 0.0005379 |
| Minimum extra edge margin | 0.105109 m | 0.142418 m |
| Minimum static-solid margin | 0.076100 m | 0.145824 m |
| Native-static rejected samples | 21/3319 | 26/3422 |

The shared optimizer reaches its existing 100-iteration cap, not a proved
convergence tolerance. The runtime remains below v224's 8.023 s, but exceeds
v225's prematurely stopped 0.113 s. Do not claim both v225's timing and v226's
route geometry as one result. Active SCAN objective+gradient is 0.0376 ms.

All 26 shared-route rejections are WrongHeight. Actual installed plugin final
admission/repair still returns no-route in both modes: 0.217/1.031 s, each with
one remaining rejected raw-graph sample on its third check. The support-grid
boundary fix is v227's separate responsibility. This version establishes soft
margin improvement; it does not establish an admitted final route.

Evidence: `results/field_probe01.log`, `results/admission_probe01.log`,
`results/field_probe_output01/`, `results/evidence/attempt02/test-result.log`.
Atlas/source identities, approximation limits and inherited upstream reuse
remain in v225/RESULTS.md and v224/REUSE.md.
