# v226: continuous integer-anchored PCT cost interpolation

Parent v225. Correct the legacy terrain soft cost's half-cell extrapolation
only when shared environmental scoring is configured. A* and optimization
states use integer cell anchors; use the same anchors and convex bilinear
weights. Clamp outside-domain coordinates with consistent zero clipped-axis
derivatives. Unconfigured legacy behavior remains byte-for-byte arithmetic.

No heading freeze, weight increase, optimizer tolerance change, factor cache
redesign, RL change or hard-admission relaxation. Reuse the existing interpolator
and factors; source pins/licenses remain in v224/REUSE.md.

Gate: synthetic corner/continuity/derivative regression, nine-package tests,
actual installed PCT search+smoothing and final native admission on the same
Building inputs. Preserve failed outputs and preceding frozen snapshots.
The separately diagnosed support-cell mismatch is outside this version.
