# Implementation and evidence plan

1. Resolve baseline source files from local v219's pinned source inventory and inherited snapshots; record hashes.
2. Implement v221 shared native predicate/query adapter, candidate validation/repair, cache validation and generated profile binding.
3. Run focused pure/native geometry tests, installed ROS client/provider checks and fixed-input PCT cases; run inherited affected package tests on gpu5070ti.
4. Return build/test receipts, source inventories and compact recorded-input comparison to v221 locally; freeze its manifest only after the code is stable.
5. Implement v222 on the tested v221 snapshot: typed spatial feedback, route/map identity, constraint updates, expiry/clearance and no invalid cache fallback.
6. Validate actual feedback-to-planner behavior, not just payload serialization; cover old-route feedback, a persistent obstruction, reopening, other floors and a direction-specific passage.
7. Compare v219 / v221 / v222 on identical archived inputs and retain failures.
8. Update version index and scoped engineering spec. Review local diff, staged paths and receipts before any meaningful commit.
9. Present the tested code and the bounded physical comparison package for the separate physics authorization.

Remote execution copies live under /data/sun/vla_mppi_20261009/pct_scan_traversability_v221 and ..._v222. Sync only owned source overlays after local hashing; preparation verifies the parent inventory before composition. Build/test output is version-scoped. Heavy archive data stays remote.

Validation commands will be recorded in each version's build.sh and replay entry; never invoke the physics launcher as part of component verification.
