# v224: shared environmental soft costs

Parent: v223, preserving the v221 hard traversability contract and v219 execution/RL settings. This version has no new physics acceptance.

A single `plan_env::EnvironmentalField` implementation is linked by PCT and SCAN. A pinned static input export stores floor-associated edge distances and ETH terrain scores plus nonterrain points from the declared Building PCD. Terrain points are classified by the existing native `reactiveTerrainReturn`; no simulator mesh enters planning. This extends the existing PCD prior to a soft planning input, explicitly, without altering occupancy admission. The immutable export is shared by both consumers and hash-bound in generated profiles.

The oriented two-cylinder envelope retains radius 0.35 m, offset 0.18 m and vertical inflation 0.55/0.35 m. Penalties use an initial target margin of 0.15 m, saturate at zero above target, and remain separate for support edges and static solids. ETH difficulty is a third term. This is not a leg-contact or future foothold model. Live occupancy remains a separate native hard gate; the static soft field makes no claim about unobserved live space.

PCT adds the shared term after its inherited <5 truncation. Both WNOJ and WNOA factors, including interpolated factors, receive an independent residual after the <=15 legacy test. SCAN rebound and refinement objectives score the sampled cubic curve and propagate position/heading gradients to its control points. Existing final hard validators remain authoritative.

Acceptance: actual A* corridor preference; nonzero GPMP residual and Jacobian below both old thresholds; native SCAN cost/gradient and optimization displacement; heading/layer/saturation tests; identical scores in both consumers; unchanged legacy results; recorded-data latency and source receipts. A new simulation run and numerical weight tuning are separate from component validation.
