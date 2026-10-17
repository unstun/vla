# v225: offline single-cylinder atlas and analytic shared derivatives

Parent: frozen v224. One behavior group: remove online point-cloud searches and
finite-difference environmental queries, leaving weights, RL and all hard
admission rules unchanged. GPMP scale/heading experiments and height-association
repairs receive subsequent versions after this performance measurement.

The runtime field retains native height-selected bilinear edge/terrain channels
and replaces static solid queries with an offline single-cylinder XYZ atlas.
Both continuously rotated cylinder centers retain the same body Z. No yaw bins
or per-cylinder ground snapping. Native floor/ETH/PCD source identities remain.
Initial atlas spacing is 0.05 m in XYZ; binary float32 storage remains remote.
This introduces a declared interpolation approximation only in a soft channel.
Compare it against the frozen raw scorer, reporting percentile/worst errors,
height-switch discontinuities, stairs and saturation separately. Do not claim
bitwise old-score equality or infer safety from interpolated soft scores.

Owned modules: EnvironmentalField reader/evaluator; GridMap derivative accessor;
PCT adapter/map callback gradient; SCAN curve chain rule; profile format binding;
the corresponding component tests, export and recorded-input probes. Existing
PCT/SCAN interpolation arithmetic is reused. PCL remains only in the pinned
offline reference exporter/oracle. There is no new mapper or recovery protocol.

Gate: nine-package build/regression, independent full pose/factor/curve gradient
checks, actual old/new atlas query/route timing and raw-oracle error measurements.
Native binary predicates must be unaffected at identical poses. Preserve v224
and all failed attempts; use new output names. No physics or actuation.
