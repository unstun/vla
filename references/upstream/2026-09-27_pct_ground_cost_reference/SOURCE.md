# Historical PCT CPU generator and raw-cost inspection

Imported from the clean `main` commit
`1cf45a1c12ca785ce533293302be09d51daf0ccb` of
https://github.com/yagami-light7/PCT-SCAN-ROS2 . The sibling checkout is a
read-only transport cache; no uncommitted sibling code was copied.
`provenance.json` records source hashes and immutable URLs. PCT-derived code is
GPL-2.0-or-later; the upstream multi-license notice and license text are retained.

The imported generator is byte-identical to the generator receipt for the
currently used Building map (SHA 6de22d1dd7fb3b2295d1d570011ede8b2f16dbcf72b48b1118e5270c300a55b0).
Use `historical_generation.json`, not the generic upstream Building defaults:
this map uses step_max 0.3, standable_ratio 0.5, safe_margin 0.5 and inflation 0.1.

The diagnostic wrapper invokes the unchanged CPU function and observes its
return-time local arrays to obtain the pre-inflation cost and retained layer
indices. It does not alter the kernel, equations, layer selection, or production
five-channel map. Runtime dependencies are NumPy and SciPy; Open3D/ROS/CUDA are
not imported when calling `make_config` and `cpu_point2map` directly on points.

Reproduce with the project's existing Python runtime and
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-09-27_pct_raw_cost/reproduce.py`.
The inflated cost, ground and ceiling channels match the original float16 map
exactly. The gradient channels have small differences; the original production
map and its gradients remain unchanged. The derived ground qualification is a
candidate, not a guarantee of obstacle safety or a physical navigation result.
