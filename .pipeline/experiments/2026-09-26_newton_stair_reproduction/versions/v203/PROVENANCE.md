# v203 source and execution identity

Parent: frozen v202. Replaced packages:
- `scan_nav2_controller`: remove the 2D projection callback, timer and publisher;
  minimal standalone map config; add native support/map lifecycle checks.
- `lite3_nav2_plugins`: remove TerrainLayer source/export/test from the new
  library; PCT source and algorithm remain identical to v201.
- `lite3_nav2_bridge`: one terrain manifest/loader/publisher, generated SCAN static
  bindings, disabled input-free Nav2 map shells and removal of the unused recovery process.

Native SCAN `plan_manage`, `plan_env`, path search and spline optimization are
inherited without edits. The versioned native graph is derived from v196 and
uses the v198 typed execution telemetry bridge. Prior source snapshots remain
untouched; protected-file receipts cover v196-v202.

Image: `vla-newton-foxy:v149` (Linux ARM64), digest
`sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e`.
Execution copy: `/private/tmp/vla_navigation_refactor_20261014/workspaces/v203`.
Read-only underlay: `/private/tmp/vla_navigation_refactor_20261014/underlay`.

The terrain exporter verifies the original v196 Building input records, hashes
the pinned ground helper and v201 PCT exporter, and records all resulting bytes
and source IDs. Its compact `terrain.json` is copied into verification. PCT costs,
selected navigation ground, dense surface evidence, physical presence and the
negative-only gap mask are separate roles in the same package. Combining their
configuration must not combine their semantic authority.

Build/test logs, XML, source inventory, package delta and payload hash receipts
are retained under `verification/`. Generated map payloads remain disposable in
the execution workspace; BUILD.md gives the full regeneration path. No simulator
or whole-route experiment is part of this version.
