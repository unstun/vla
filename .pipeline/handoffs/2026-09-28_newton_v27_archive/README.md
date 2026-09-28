# Newton repair archive: through v27

Archived on 2026-09-28 (America/Los_Angeles), at Dr Sun's request.
Stage: experiment + analysis. Execution is stopped; task remains in_progress.
Local VLA is source of truth. No server restart, training or real-robot actuation
was performed in this repair sequence. v28 has not been created or implemented.

## Current result

- Last fully accepted local navigation condition remains v3: one empty12m trial.
- v8–v27 preserve one logical change per integer version. Frozen source snapshots
  for all20 versions were rehashed at archive: no mismatches. Rejected v9 and v16
  remain rejected; version increments do not indicate acceptance.
- v24 reached native short-stair arrival after4.914m net forward travel, final
  XY error.200m. Final PD handoff failed at its mid-stair goal. Its89.92s ordinary
  MP4 is preserved at `output/2026-09-27_lite3_versions/v24_stair_arrival.mp4`,
  SHA256 b67180839426511e068e40066efc9b92ff53ee1f5b2b646b299fdfcead10f75a.
- v25 restores the explicit historical complete-floor profile, but its live
  loader discarded pct_layer null and forced layer1:145points/17.244m/wrongheight.
- v26 repairs only that nullable config path. Seven loader methods and six real
  loader/TCP/native controls pass. The live route is631points/~73.41m with correct
  final body height4.83125m. Physical run v26_historical_full02 remained near the
  start; diagnostic cancel at110.731s, no arrival, zero command reconnect/protocol
  errors and verified stop/copyback. v26_historical_full01 never started physics
  because the supervisor was invoked with a relative interpreter path.
- v27 adapts OMPL1.7.0's verified direct-connection seed reduction after mandatory
  original AStar and edge checks. Eleven full native continuation replays pass;
  eight unmapped and five mapped fixture outputs exactly match v24. The v26
  stopped-state continuation changes from failure to an accepted1.847894m prefix
  twice, with full native gates and independent boundary-PVA error6.19e-15.
  This is component evidence only.
- v27_historical_full01 crashed the native SCAN process at~13.24s (ros2run reports
  Segmentation fault; exit245). Container state copyback was not verified. No
  complete-route or final PD acceptance, and no new successful full-route video.

## Crash diagnosis and exact continuation point

Evidence root: `.pipeline/experiments/2026-09-26_newton_stair_reproduction/`.

1. `audits/2026-09-27_v27_optimizer_crash/attempt02_bounds/` replays the actual
   captured seed sequence against recorded inputs. Captured seed269, fixed-height
   mode and fresh replay clock reproduces abort(exit134) immediately after the
   same inside-obstacle message. The exact failing call stack has not been
   captured; do not equate this diagnostic abort with a located live segfault.
2. `.../constraint_contract/case_results.json` extracts native assignment/rebound
   blocks verbatim and reuses the existing project harness.13cases:3positive
   controls pass,10fail, including two deterministic finite-input empty-container
   aborts. Code can set a per-point success flag before storing any constraint,
   then propagate from an empty vector. A previous point's intersection flag can
   also cause a later uninitialized intersection to be read.
3. The project's older `p2b_execution/reactive_stair/materialize_scan_27.py`
   already repairs per-point validity and paired writes. Frozen helper in
   `p2b_execution/builds/scan_27/src/bspline_opt/include/bspline_opt/`
   `rebound_constraint_utils.h` has SHA256
   cc16da1d3974982a771a79f93240053e12bfa7d6bf0dfaf478595fbf986cbaaa.
   The helper remains in current native sources, but its protected call sites
   were replaced when generic materialize.py restored pinned scan_04 optimizer
   (source SHA9744424bd58841213230e95b252706360b1d4db10eaf30e7f6bf34a857a87568).
   `candidate_reachable_goal_identity_v9.json` explicitly records that restore.
4. Next: obtain a useful stack or isolate the captured failure against the
   deterministic counterexample; then create v28 and restore only finite paired
   constraint handling. Preserve search modes, cost functions, thresholds,
   sensor/terrain/unknown rules and all final gates. Reuse existing code/tests;
   do not import unrelated later route-projection behavior. Run red/green
   constraint tests, captured seed replay, prior regressions, freeze, then physics.
5. First ASAN attempt stopped in prebuilt ROS initialization at
   new-delete-type-mismatch, before optimizer execution. It is not this crash's
   root-cause evidence. The second attempt uses UBSAN and standard-library bounds
   assertions. gdb is absent in the pinned image; addr2line is available. Do not
   start a new physical trial merely to obtain a stack before using saved inputs.

## Other open boundaries

- Emergency constant B-splines still generate position feedback in the current
  controller. They are not an explicit zero-command hold. Do not skip their safety
  checks based on identical control points.
- Blocking native retries can make measured body pose older than100ms while the
  clock advances. Same-query Free→Unknown and valid-hold→InvalidCurve transitions
  were recorded in v26. No executor or freshness relaxation was made.
- v25 had real219/280ms accepted-clock gaps and286ms body callback gap. Those
  wall-time failures are distinct from the null loader fix and native crash.
- Known13cm mapped protrusions versus independent boxes remains a pending user
  choice; generic unknown/unmapped obstacle evidence must not be overstated.
- Original Isaac A4 remains open. Sibling repositories remain read-only.

## Archive execution and backup boundary

Archive uses the main-session fallback: current inline instructions require the
main session to implement/check directly and prohibit implementation/check
subagents. No archive spawn was attempted under that restriction. Codex CLI is
available, but the delegated CLI gate was not run for the same reason.
Pipeline additions are marked [未门控]; source/hash checks here are manual/tool
verification, not an automated Codex PASS. No full chat transcript was exported.

See `process_state.json`, `snapshot_verification.json`, `archive_report.json`,
`backup_paths.txt` and `local_only_inventory.json` for verification and Git scope.
Only this window's selected changes are staged. Raw captures and rebuildable
caches remain at their project paths; unrelated window changes are preserved.
