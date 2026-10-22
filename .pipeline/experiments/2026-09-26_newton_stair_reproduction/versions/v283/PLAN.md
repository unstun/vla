# v283 — Shared geometry and measured-state continuation

Status: native/execution frozen; full updated50+3 offline gate passed and all ten
once-only physical attempts completed. Physical acceptance fails:5/10goal/PD,
2/10goal/PD plus clear sampled geometry. Ten verified local videos and full
evidence are delivered; see RESULTS.md. No baseline adoption or frozen edits.

The local VLA repository is authoritative. Native parent v280 and physical
parent v282 remain immutable. Radius0.35m, LiDAR period/deadline0.1s, original
policy/PD, body envelope, scene and terminal tolerances are unchanged.

Changes are request-scoped endpoint feedback handling, bounded static-readiness
waiting, remaining-route validation, source-solid checking in the actual local
query, and measured-state reseeding when the predicted body envelope leaves
the existing map sampling precision. No scene/route/coordinate production
branches were added.

All50 legal starts are certified using >=0.10m extra physical support and solid
margins. Eight starts change: G05, CU04, CU08, CU11, CU12, CU13, CM01, CM02.
Keep the53-case denominator and three illegal controls. Fixed physical cases:
A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03; one formal attempt each.

Native identity and component tests are in native_manifest.json and results/.
Exact source snapshots are in source/. Parent differences are changes.patch.
The complete research/acceptance contract is in the active Trellis task
10-19-v283-navigation-geometry-repair.

Remote native/cohort/evaluation: /home/sun/vla_exec/navigation_geometry_v283.
Remote raw physics: /home/sun/vla_exec/physical_runs_v283.
Local return: source/configuration, compact reports/provenance and10 MP4 files;
expected local returned bytes below300MiB. Bulk data and builds remain remote.

Offline acceptance: all53 calls, >=48/50 full-chain legal passes,3/3 illegal
refusals, nonnegative independent margins, CPU2 median global<=1.5s (cold init
separate), inherited first-GPMP/admitted>=90%, and all10 fixed cases admitted.
Arrival/terminal PD and measured support/solid violations remain separate.
A failed frozen result is retained; no retry or baseline promotion is implied.
