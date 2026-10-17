# v221 execution

Follow ../10-17-pct-scan-traversability/implement.md, steps 1-4.

Before editing, resolve all inherited file hashes and relevant backend specs. Add meaningful integration tests for actual returned paths and native query verdicts. Build on gpu5070ti without launching physics. Return version-owned source/build/test/replay receipts locally, then review the diff and freeze the source manifest. Any later logical repair receives a new integer version.

## Current execution, 2026-10-17

- v223 adds diagnostic physical-floor association and `EdgeClearance`, with no binary admission change. All 126,324 archived queries plus three exact planning queries preserve binary decisions. Nine packages and 158 colcon test records pass. Exact cause/intersection ledger and FCL cross-check are returned locally under v223/results.
- v224 implements one static environmental scorer used by PCT A*, WNOJ/WNOA endpoint/interpolated factors, and SCAN rebound/refinement objectives. Synthetic actual-search and native-objective/L-BFGS tests pass; target-margin saturation and heading/layer behavior are exercised. RL and recovery protocols are unchanged.
- The first Building experiment failed its intended performance/usefulness gate: shared A* 91.912 s versus legacy 11.760 ms, and integrated environmental cost did not improve. Preserve `probe_attempt01.log`, `field_probe_output/` and the first ENV224 export. This is not a passed result.
- Witness inspection identified below-floor material in the raw static PCD as a saturation source. ENV224B annotates per-voxel associated physical-floor ranges only when every retained point is explained as below that floor. Same-level soft queries may omit that volume; mixed/unassociated points and other floors remain. This has no effect on online raw occupancy or selectedSurface.
- The stock, unchanged Wait fixture segfaulted once in attempt05; an isolated retry with Python fault traces passed in 1.42 s. Do not call the intermittent runtime failure fixed. The retry-generated pytest cache was preserved outside src after the source-inventory gate correctly rejected it.
- No new simulation or robot action has run. v219/v220 remain the accepted source/display references. The subsequent recorded-input outcome below distinguishes component acceptance from the failed Building route-benefit gate.

## Recorded-input gate outcome

- v224 attempt09: nine packages, 164 colcon records (144 distinct cases plus 20 wrappers), zero failures/errors/skips. The exact-source static field is cross-checked by 30,060 PCT/native score pairs and an independent 640-sample unpartitioned SciPy/numpy oracle; no differences beyond floating-point noise.
- Final Building A* route: integrated cost 1.218110 -> 0.017219; minimum extra edge margin 0.022721 -> 0.125601 m. Search+GPMP: cost 0.271146 -> 0.725006, minimum edge margin 0.105109 -> 0.093517 m. Total planning is 8.023 s versus 0.0316 s. The new row is active but the inherited smoothing objective does not preserve the search benefit.
- Actual installed PCT plugin, RoutePolicy, final sampler and three-round repair against native STATIC_ONLY queries return truthful no-route in both modes. This separate full-reference benchmark pins original XYZ endpoints and explicit zero endpoint yaw; it is not original robot execution. Each final graph fallback retains one WrongHeight query outside the v217 diagnostic-window query set. No relaxation or connector was added.
- Actual Building SCAN environmental objective timing: zero-cost windows 2.73–3.42 ms/evaluation; active-margin window 35.24 ms/evaluation with nonzero gradient. These are single-objective timings, not total solver/control-cycle timing.
- Floors/rejection attribution are validated under v223. R8's three consumer integrations are implemented/component-tested under v224, but useful full-Building route behavior and runtime performance remain unaccepted. Keep this task in progress; do not archive it or promote runtime profiles. Remaining work is GPMP margin retention/scaling and scoring-query cost, followed by an admitted-route comparison. v222 feedback remains separate.
- Source, compact logs/XML, final scored CSVs, heavy-export hashes and failed-attempt provenance are returned under v224/results. See v223/RESULTS.md for the exact 42–62 s overlapping/first-reason ledger. No new physics, training, actuation or global-memory updates occurred.

## Continued diagnosis and recorded-input closure

- v225: offline single-cylinder XYZ atlas and analytic derivatives remove
  runtime KD-tree/finite-difference cost evaluation. Nine packages/144 cases
  pass; shared search+smoothing 0.113 s vs v224 8.023 s. Approximation ordinary
  p95 about 2 mm but worst uniform height-switch error 0.277 m is explicitly
  retained. Hard checking never consumes this approximation as a free-space grant.
- Six identical-seed GPMP ablations falsify the relative-tolerance explanation
  and zero-row wiring concern. The old objective is quartic after whitening.
  A real four-corner witness extrapolates to 73.27 despite corner maximum 50,
  then jumps at a half-cell seam. 22 interpolation/heading/weight comparisons
  select the minimal continuous integer-anchored sampling correction, preserving
  current velocity/yaw derivatives, weights and tolerances.
- v226: shared smoothing reaches minimum edge/solid 0.1424/0.1458 m in 0.639 s;
  unconfigured route bytes equal v225. Nine packages/145 cases pass. Remaining
  final WrongHeight is distinct from soft-score improvement.
- v227: physical-origin alignment passes 146 cases and fixes three old corner
  witnesses, but creates equivalent failures elsewhere. Preserve as failed.
  Float32 point minima are not a canonical lattice.
- v228: TerrainBundle binds the original SHA-verified PCT header lattice into
  native support queries, without modifying source arrays/classification/heights
  or thresholds. Five exact old/new corner witnesses pass; nine packages and
  167 colcon records (147 distinct cases +20 wrappers) pass.
- Actual installed plugin returns full-goal references in both modes, third
  check native-static rejected count zero. Shared final edge margin 0.147524 m,
  raw PCD solid margin 0.064950 m, goal error zero, total repair/admission 1.032 s.
  Legacy 0.026370/-0.029809 m, 0.225 s. Shared final cost is 0.023304 vs 0.969377
  (atlas); raw-oracle cost 0.018673 vs 0.971201. All final rotation/translation
  samples receive independent native rechecking.
- Both final references are existing raw-graph fallbacks, not admitted GPMP
  height-smoothed curves. Shared GPMP retains 26 WrongHeight samples; the hard
  gate correctly rejects them. This limitation remains explicit for next work.
- v228 original replay preserves all 126,324+3 binary verdicts and every recorded
  independent occupancy predicate. Exact 48.105 s floor remains 1.558030696 m
  with 0.2828427125 <0.35 m EdgeClearance. v223's overlap ledger remains valid.
- Compact source/test/admission/raw-oracle/replay receipts return locally under
  version-owned results. v219/v220 remain accepted physical source/display;
  RL, full-route physics, real motion, v222 feedback and recovery connectors
  are untouched. The recorded-input implementation gate passes; human diff
  review/commit remains pending. Do not imply a live-navigation result.
