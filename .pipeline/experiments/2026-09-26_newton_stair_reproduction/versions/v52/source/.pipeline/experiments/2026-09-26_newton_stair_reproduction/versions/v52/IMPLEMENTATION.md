# v52 terrain-cell lookup reuse

Parent: frozen v50, directly descended from v48. Stage: experiment + analysis.

The unchanged-native cold replay and sampled CPU profile are recorded in
`audits/2026-10-02_cold_tail_replay/RESULTS.md`. Terrain-tree lookup accounted
for 24.28% of sampled instrumented self time; this is diagnostic evidence,
not a production latency estimate.

Only `grid_map.h` and `scan_reactive_grid_methods.inc` change native behavior.
The existing scoped raw-contributor cache now also retains exact XY cell lookup
results: pointers to the original raw/scored layer vectors, including missing
cells. Signed coordinates are packed losslessly into an unsigned 64-bit key.
The table has at most 4096 entries and uses original map lookups after capacity.
Scope entry/exit and every existing input invalidation clear borrowed pointers
before either terrain snapshot is replaced. An empty guard avoids clearing a
retained hash table repeatedly during point insertion. Nested scopes retain the
outer scope's data. There is no cache reuse outside the original active scope.

Layer association, elevation equality, selection status, height limits, step
thresholds, freshness, collision/support decisions and query height corrections
still execute on each query. The cache does not store an occupancy or support
verdict. Existing final goal, yaw, PVA, dynamics, trajectory admission/ownership,
recovery attempts, controller and stop behavior retain their original code.
The internal disable switch is used only by the paired native test harness.

Runtime Python modules are byte-identical to v50 except the selected version
and native build path labels in `run_local_episode.py` and `native_graph.py`.
The navigation contract changes only its version label. Configurations are
unchanged. `runtime_preparation.json` records those exact identities.

Freeze storage references inherited v50 source snapshots by path and hash and
stores only v52-owned source/configuration. Full builds, captured inputs and
run logs remain on gpu5070ti. Compact manifests, comparisons, plots and a review
video are the local return allowlist. A component speedup cannot establish
physical continuity, route completion or sustained 30 Hz.
