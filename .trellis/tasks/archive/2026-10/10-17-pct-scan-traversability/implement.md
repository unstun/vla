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

## 2026-10-17 committed sources and authorized physical follow-up

v229 height alignment is committed as420a0ff9; v230 mission feedback as e9f8bec0.
The separately authorized single full-route physical attempt uses v231 execution
bindings with frozen v230 navigation and unchanged v219 endpoints/RL/0.35m
guards. It fails on controller_server SIGABRT near46.7s and remains unaccepted;
the task is not complete. Detailed evidence/video comparison is under
audits/2026-10-17_v230_physical_comparison. No physics retry or navigation repair
was performed. Preserve v219/v220 as the accepted physical pair.

## 2026-10-17 v232 source commit and single physical v233 execution

Approved prior audit committed1ad1862d; v232 repair/offline evidence committed
ff4cb515. The newly authorized sole physical run, frozen executionv233 with
frozen v232 install + graph + driver, passes the original v219 full-route
gate. Same endpoints, RL,0.35m guards: FINISHED121.565s, measured final
PD4.398s, XY error0.1412m, no controller abort/fall.317 source/607 installed
files and actual driver match after execution; shared FINISHED agrees.
Stair45–55s:273/275 completed rounds succeed, no >=1s low-speed pause, all100
body-edge samples at the additional0.15m cap. No sustained30Hz qualification
(25.44 successful Hz average), no repeated reliability, no feedback-detour
claim (one global route delivery). The first port check produced zero physics;
no physical retry was performed. New result/video evidence is separate from
frozen v232:versions/v233/RESULTS.md and
audits/2026-10-17_v232_physical_comparison/RESULTS.md.

## User-approved closeout,2026-10-17

Physical evidence, videos and mutable baseline selection are committedc7294f8f.
Dr Sun adoptedv232/v233 with the explicit single-route boundary and requested
archive of this parent/child family. See the archived parent CLOSEOUT.md for
the acceptance matrix, complete version/commit map and remaining gates.
No new experiment is part of archival.
