# v201 — direct native PCT planning

Parent: frozen v200. Algorithm source: the v174 PCT package actually selected by
the v196 ARM64 Foxy environment, including its singleton-route fixes. Preserve
all previous versions and do not run physics or full-route navigation trials.

## Change boundary

Replace `PCTPlanner -> PlanRoute -> MissionBridge -> Python wrapper -> native PCT`
with `PCTPlanner -> native OfflineElePlanner`. The HTTP adapter owns only task
submission, cancellation, feedback and input conversion. Remove its planner,
planning lock/service, canonical-route cache and cached-path fallback.

The PCT algorithm stays unchanged. Export the existing float32 tomogram once to
a versioned binary map bundle, including the original validity mask and the six
matrices consumed by InitMap. The online planner loads that bundle directly in
C++; it does not embed Python or deserialize pickle.

Preserve float32 input quantization, ties-to-even grid rounding, XY axis swap,
nearest valid ground-layer selection, gateway construction and gradient signs.
Use the optimizer's height output directly: do not retain the discarded Python
wrapper's +0.5 m Z offset or add the reference height twice.

Nav2 owns the requested target pose. The adapter preserves that explicit goal
orientation (including yaw zero) and connects the native route to that fixed
target when the final connector is within the existing 2 m limit. HTTP goals
without `target_yaw_rad` use zero yaw; they no longer acquire a planner-generated
task orientation through MissionBridge. This input-contract simplification is
explicit and tested. PCT's unmodified optimized points are compared separately
against the old wrapper to distinguish algorithm parity from goal binding.

The 1 Hz planning child, SCAN, V12, terrain pipeline and terminal completion from
v200 remain unchanged. Dynamic blockage masks are out of scope.

## Checks

- Build PCT's exported native library, the planner plugin and mission adapter.
- Compare fixed Building-map and small synthetic-map inputs against the old
  Python wrapper using the same pinned native algorithm. Include non-square
  axes, floor selection, rounding ties, heights and degenerate/no-route inputs.
- Load and call the real C++ plugin with no MissionBridge or PlanRoute service.
- Exercise HTTP/action submission, cancellation, immutable target pose and launch
  parameters with the reduced adapter.
- Record source/binary identities, old-version preservation and compact results.
