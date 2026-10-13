# v8: avoid propagating sparse terrain holes into known support

Parent: frozen v7. Stage: experiment + analysis. Dr Sun authorized repair.

The captured v7 stop is reproduced in the full Building comparison audit.
Known terrain cells lose support when either scoring neighborhood has a missing
cell. This differs from pinned ETH StepFilter's handling of invalid neighbors.

One production behavior change: restore skipping absent neighbors in both
passes and invalid first-pass neighbor scores in the second pass. Keep the
queried cell present and valid, same-layer ambiguity/distance rejection, V12
hard step-height limit, raw occupancy/unknown/freshness gates and nonterrain
history precedence. No new coverage threshold or route-specific exception.

Only `plan_env/include/plan_env/eth_step_score_adaptation.h` changes in a new
native candidate `scan47_sparse_terrain_v8`. Use identical v7 YAMLs. Preserve
prior sources and freeze this candidate before build/replay. Other repairs,
including terminal failure reporting, require separate later versions.

Evidence: pinned `leggedrobotics/traversability_estimation` commit
`14d24c059e1c43466aadf328280adf6394d78039`, BSD-3-Clause,
`references/upstream/2026-09-23_eth_stepfilter_reference/StepFilter.cpp`.
This remains an adaptation: the multi-floor association and hard height gate
are local contracts, not unchanged upstream behavior.

Validation order: a failing sparse-neighbor contract against v7; candidate
fixtures preserving tall box/thin wall/ambiguous layers/unknown position and
stale data negatives; native build; original 66-scan continuation replay and
original full-curve/PVA checks; measured sensor obstacle regressions; bounded
physical stair trial only if the native checks admit a valid continuation.
The 0.6 m/s planned cruise requirement remains enabled. No successful route
claim follows from a version increment or component test.
