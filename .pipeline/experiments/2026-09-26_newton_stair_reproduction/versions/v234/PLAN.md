# v234: gpu40901 execution binding

Stage: experiment preparation and offline validation. Authorized on 2026-10-17.
The local VLA repository remains authoritative. This version changes the host
binding of frozen v232 navigation and v233 execution, not their algorithms.

- Destination: `/home/ubuntu/sun/vla_v234_20261017` on `gpu40901`.
- Navigation source: exact frozen v232, 317 composed files. Rebuild all 14
  packages and bind new installed hashes. Preserve the original607-file
  receipt for comparison; do not claim original install byte identity.
- Physics/RL/route: original v233 execution with v216 locomotion, original
  `historical_full` endpoints and unchanged 0.35 m collision/support guards.
- Images: a new pinned amd64 Foxy build using the original dependency recipe;
  unchanged original ARM factory image/library. gpu5070ti is powered off.
- Isolation: task-owned directories, containers, Python environment and CPU
  budgets. No shared Python, driver, binfmt, IsaacLab or peer process changes.
- Gate: fresh native regressions, recorded parity/Building admission, 12-second
  graph, zero-physics host/factory smoke and exact returned provenance.
- Stop after offline gates. A full-route physical trial needs a subsequent
  arrangement; no physical acceptance or timing equivalence is claimed here.

Use `host_inventory.py` before and after work. `source_gate.py` checks direct
frozen sources/install bytes instead of recursively loading historical launch
closures. Build trees are remote test infrastructure, never local deliverables.
Preserve the accepted v232 receipt and every failed new attempt. Historical
dynamic replay inputs remain on gpu5070ti; full offline acceptance stays open
until they are retrieved and replayed. No full-route launcher is enabled here.
